import 'package:commerce_os_seller/features/studio/data/review_form.dart';
import 'package:commerce_os_seller/features/studio/data/studio_models.dart';
import 'package:flutter_test/flutter_test.dart';

StudioDraft _draft({
  List<DraftOption> options = const [],
  List<DraftAttribute> attributes = const [],
}) =>
    StudioDraft(
      titleEn: 'Dhaka topi',
      titleNe: 'ढाका टोपी',
      suggestedOptions: options,
      attributes: attributes,
      categoryPath: const ['Accessories', 'Hats'],
    );

Set<ReviewProblemKind> _kinds(ReviewForm f) => f.validate().map((p) => p.kind).toSet();

void main() {
  test('price is required; the AI never fills it', () {
    final f = ReviewForm.fromDraft(_draft());
    expect(f.price, isEmpty);
    expect(_kinds(f), {ReviewProblemKind.priceRequired});
    f.price = '0';
    expect(_kinds(f), {ReviewProblemKind.priceRequired});
    f.price = '12.345';
    expect(_kinds(f), {ReviewProblemKind.priceInvalid});
    f.price = '1,250.50';
    expect(f.validate(), isEmpty);
    expect(f.toApply().product.variants.single.priceMinor, 125050);
  });

  test('attributes below 75% must be acknowledged; ≥75% are pre-accepted', () {
    final f = ReviewForm.fromDraft(_draft(attributes: const [
      DraftAttribute(key: 'material', value: 'Cotton', confidence: 0.92),
      DraftAttribute(key: 'origin', value: 'Palpa', confidence: 0.6),
      DraftAttribute(key: 'pattern', value: 'Dhaka', confidence: 0.749),
    ]))
      ..price = '650';
    expect(_kinds(f), {ReviewProblemKind.attributesUnchecked});
    expect(f.uncheckedAttributes.map((a) => a.source.key), ['origin', 'pattern']);

    f.attributes[1].decision = AttributeDecision.accepted;
    f.attributes[2]
      ..value = 'Palpali Dhaka'
      ..decision = AttributeDecision.edited;
    expect(f.validate(), isEmpty);

    final out = f.toApply();
    expect(out.acceptedKeys, ['material', 'origin']);
    expect(out.editedValues, {'pattern': 'Palpali Dhaka'});
  });

  test('variants are the cartesian product of option values', () {
    final f = ReviewForm.fromDraft(_draft(options: const [
      DraftOption(name: 'Size', values: ['S', 'M']),
      DraftOption(name: 'Colour', values: ['Red', 'Black', 'White']),
    ]));
    expect(f.variantCombinations, hasLength(6));
    expect(f.variantCombinations.first, {'Size': 'S', 'Colour': 'Red'});
  });

  test('per-variant prices are each required', () {
    final f = ReviewForm.fromDraft(_draft(options: const [
      DraftOption(name: 'Size', values: ['S', 'M']),
    ]))
      ..samePrice = false
      ..variantPrices[variantKey({'Size': 'S'})] = '500';
    final problems = f.validate();
    expect(problems, hasLength(1));
    expect(problems.single.kind, ReviewProblemKind.priceRequired);
    expect(problems.single.variantKey, variantKey({'Size': 'M'}));

    f
      ..variantPrices[variantKey({'Size': 'M'})] = '550.5'
      ..variantSkus[variantKey({'Size': 'M'})] = 'TOPI-M';
    final v = f.toApply().product.variants;
    expect(v.map((x) => x.priceMinor), [50000, 55050]);
    expect(v.last.sku, 'TOPI-M');
  });

  test('no options → one default variant', () {
    final f = ReviewForm.fromDraft(_draft())..price = '99';
    final v = f.toApply().product.variants.single;
    expect(v.options, isEmpty);
    expect(f.toApply().product.toJson()['options'], isEmpty);
  });

  test('title: needs Nepali or English; English falls back to Nepali', () {
    final f = ReviewForm.fromDraft(_draft())
      ..price = '100'
      ..titleEn = ''
      ..titleNe = '';
    expect(_kinds(f), contains(ReviewProblemKind.titleRequired));
    f.titleNe = 'ढाका टोपी';
    expect(f.validate(), isEmpty);
    expect(f.toApply().product.title, 'ढाका टोपी');
  });

  test('option without values is flagged; >100 variants is flagged', () {
    final f = ReviewForm.fromDraft(_draft())..price = '100';
    f.options.add(EditableOption('Size', []));
    expect(_kinds(f), {ReviewProblemKind.optionValuesRequired});
    f.options
      ..clear()
      ..addAll([
        EditableOption('A', [for (var i = 0; i < 11; i++) 'a$i']),
        EditableOption('B', [for (var i = 0; i < 10; i++) 'b$i']),
      ]);
    expect(_kinds(f), {ReviewProblemKind.tooManyVariants});
  });

  test('apply payload matches the API shape', () {
    final f = ReviewForm.fromDraft(_draft(options: const [
      DraftOption(name: 'Size', values: ['Free']),
    ]))
      ..price = '650'
      ..categoryPath = [' Accessories ', '', 'Hats'];
    final out = f.toApply();
    expect(out.categoryPath, ['Accessories', 'Hats']);
    expect(out.product.toJson(), {
      'title': 'Dhaka topi',
      'title_ne': 'ढाका टोपी',
      'options': [
        {'name': 'Size', 'values': ['Free']},
      ],
      'variants': [
        {'options': {'Size': 'Free'}, 'price_minor': 65000},
      ],
    });
  });
}
