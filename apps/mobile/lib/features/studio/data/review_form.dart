import 'package:flutter/foundation.dart';

import '../../../core/l10n/money_input.dart';
import 'studio_api.dart';
import 'studio_models.dart';

/// Below this, AI attributes need an explicit seller tap (backend policy
/// default for PRODUCT_EXTRACTION is 0.75).
const attributeConfidenceThreshold = 0.75;

/// Catalog API limits.
const maxOptions = 3;
const maxVariants = 100;

class EditableOption {
  EditableOption(this.name, List<String> values) : values = [...values];
  String name;
  final List<String> values;
}

enum AttributeDecision { pending, accepted, edited }

class EditableAttribute {
  EditableAttribute(this.source)
    : value = source.value,
      decision =
          source.confidence >= attributeConfidenceThreshold
              ? AttributeDecision.accepted
              : AttributeDecision.pending;

  final DraftAttribute source;
  String value;
  AttributeDecision decision;

  bool get needsCheck => source.confidence < attributeConfidenceThreshold;
  bool get acknowledged => decision != AttributeDecision.pending;
}

enum ReviewProblemKind {
  titleRequired,
  priceRequired,
  priceInvalid,
  attributesUnchecked,
  tooManyVariants,
  optionValuesRequired,
}

@immutable
class ReviewProblem {
  const ReviewProblem(this.kind, {this.variantKey, this.priceError});
  final ReviewProblemKind kind;
  final String? variantKey;
  final PriceInputError? priceError;
}

/// Stable key for a variant's option combination, e.g. "Colour=Red|Size=M".
String variantKey(Map<String, String> options) =>
    (options.entries.toList()..sort((a, b) => a.key.compareTo(b.key)))
        .map((e) => '${e.key}=${e.value}')
        .join('|');

/// Seller review state for a ready Studio job. Pure Dart; the screen binds
/// controllers to it.
class ReviewForm {
  ReviewForm.fromDraft(StudioDraft d)
    : titleEn = d.titleEn,
      titleNe = d.titleNe,
      descriptionEn = d.descriptionEn,
      descriptionNe = d.descriptionNe,
      categoryPath = [...d.categoryPath],
      options = [
        for (final o in d.suggestedOptions.take(maxOptions))
          EditableOption(o.name, o.values.take(50).toList()),
      ],
      attributes = [for (final a in d.attributes) EditableAttribute(a)],
      checklist = {for (final s in d.needsSellerInput) s: false};

  String titleEn;
  String titleNe;
  String descriptionEn;
  String descriptionNe;
  List<String> categoryPath;
  final List<EditableOption> options;
  final List<EditableAttribute> attributes;

  /// `needs_seller_input` items → ticked by the seller (informational).
  final Map<String, bool> checklist;

  /// One price for every variant (default) or per-variant prices.
  bool samePrice = true;
  String price = '';
  final Map<String, String> variantPrices = {};
  final Map<String, String> variantSkus = {};

  List<EditableOption> get usableOptions => options
      .where((o) => o.name.trim().isNotEmpty && o.values.isNotEmpty)
      .toList(growable: false);

  /// Cartesian product of option values; a single `{}` variant when the
  /// product has no options.
  List<Map<String, String>> get variantCombinations {
    var combos = <Map<String, String>>[{}];
    for (final o in usableOptions) {
      combos = [
        for (final c in combos)
          for (final v in o.values) {...c, o.name.trim(): v},
      ];
      if (combos.length > maxVariants) break;
    }
    return combos;
  }

  List<EditableAttribute> get uncheckedAttributes =>
      attributes.where((a) => !a.acknowledged).toList(growable: false);

  List<ReviewProblem> validate() {
    final problems = <ReviewProblem>[];
    if (titleEn.trim().isEmpty && titleNe.trim().isEmpty) {
      problems.add(const ReviewProblem(ReviewProblemKind.titleRequired));
    }
    if (options.any((o) => o.name.trim().isNotEmpty && o.values.isEmpty)) {
      problems.add(const ReviewProblem(ReviewProblemKind.optionValuesRequired));
    }
    final combos = variantCombinations;
    if (combos.length > maxVariants) {
      problems.add(const ReviewProblem(ReviewProblemKind.tooManyVariants));
    } else if (samePrice) {
      final p = parseRupeesToPaisa(price);
      if (p.error != null) {
        problems.add(
          ReviewProblem(
            p.error == PriceInputError.empty || p.error == PriceInputError.zero
                ? ReviewProblemKind.priceRequired
                : ReviewProblemKind.priceInvalid,
            priceError: p.error,
          ),
        );
      }
    } else {
      for (final c in combos) {
        final k = variantKey(c);
        final p = parseRupeesToPaisa(variantPrices[k] ?? '');
        if (p.error != null) {
          problems.add(
            ReviewProblem(
              p.error == PriceInputError.empty ||
                      p.error == PriceInputError.zero
                  ? ReviewProblemKind.priceRequired
                  : ReviewProblemKind.priceInvalid,
              variantKey: k,
              priceError: p.error,
            ),
          );
        }
      }
    }
    if (uncheckedAttributes.isNotEmpty) {
      problems.add(const ReviewProblem(ReviewProblemKind.attributesUnchecked));
    }
    return problems;
  }

  /// Builds the apply payload. Call only when [validate] is empty.
  ({
    ApplyProduct product,
    List<String> acceptedKeys,
    Map<String, String> editedValues,
    List<String> categoryPath,
  })
  toApply() {
    final opts = usableOptions;
    final title = titleEn.trim().isNotEmpty ? titleEn.trim() : titleNe.trim();
    final shared = samePrice ? parseRupeesToPaisa(price).paisa! : null;
    final variants = [
      for (final c in variantCombinations)
        (
          options: c,
          priceMinor:
              shared ??
              parseRupeesToPaisa(variantPrices[variantKey(c)] ?? '').paisa!,
          sku: samePrice ? null : variantSkus[variantKey(c)]?.trim(),
        ),
    ];
    return (
      product: ApplyProduct(
        title: title,
        titleNe: titleNe.trim(),
        description: descriptionEn.trim(),
        descriptionNe: descriptionNe.trim(),
        options: [
          for (final o in opts) (name: o.name.trim(), values: o.values),
        ],
        variants: variants,
      ),
      acceptedKeys: [
        for (final a in attributes)
          if (a.decision == AttributeDecision.accepted) a.source.key,
      ],
      editedValues: {
        for (final a in attributes)
          if (a.decision == AttributeDecision.edited &&
              a.value.trim().isNotEmpty)
            a.source.key: a.value.trim(),
      },
      categoryPath: [
        for (final p in categoryPath)
          if (p.trim().isNotEmpty) p.trim(),
      ],
    );
  }
}
