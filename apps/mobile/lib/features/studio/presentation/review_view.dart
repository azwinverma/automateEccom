import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/errors/api_error.dart';
import '../../../core/l10n/formatters.dart';
import '../../../core/l10n/gen/app_localizations.dart';
import '../../../core/l10n/money_input.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens.g.dart';
import '../../../design/widgets/section_header.dart';
import '../../../design/widgets/state_views.dart';
import '../../auth/presentation/auth_layout.dart';
import '../../catalog/data/catalog_api.dart';
import '../data/review_form.dart';
import '../data/studio_api.dart';
import '../data/studio_models.dart';
import 'widgets/attribute_review_row.dart';
import 'widgets/issue_list.dart';

String priceErrorText(AppLocalizations l, PriceInputError e) => switch (e) {
  PriceInputError.empty || PriceInputError.zero => l.validationPriceRequired,
  PriceInputError.invalid => l.validationPriceInvalid,
  PriceInputError.tooManyDecimals => l.validationPriceDecimals,
  PriceInputError.tooLarge => l.validationPriceTooLarge,
};

String variantLabel(AppLocalizations l, Map<String, String> options) =>
    options.isEmpty ? l.defaultVariant : options.values.join(' / ');

/// Step 3: seller review of a ready Studio draft → product (draft status).
class ReviewView extends ConsumerStatefulWidget {
  const ReviewView({super.key, required this.job});

  final StudioJob job;

  @override
  ConsumerState<ReviewView> createState() => _ReviewViewState();
}

class _ReviewViewState extends ConsumerState<ReviewView> {
  late final ReviewForm form;
  late final TextEditingController _titleEn;
  late final TextEditingController _titleNe;
  late final TextEditingController _descEn;
  late final TextEditingController _descNe;
  late final TextEditingController _category;
  final _price = TextEditingController();
  final Map<String, TextEditingController> _variantPrice = {};
  final Map<String, TextEditingController> _variantSku = {};
  bool _showErrors = false;
  bool _saving = false;
  ApiError? _error;

  @override
  void initState() {
    super.initState();
    form = ReviewForm.fromDraft(widget.job.draft ?? const StudioDraft());
    _titleEn = TextEditingController(text: form.titleEn);
    _titleNe = TextEditingController(text: form.titleNe);
    _descEn = TextEditingController(text: form.descriptionEn);
    _descNe = TextEditingController(text: form.descriptionNe);
    _category = TextEditingController(text: form.categoryPath.join(' / '));
  }

  @override
  void dispose() {
    for (final c in [
      _titleEn,
      _titleNe,
      _descEn,
      _descNe,
      _category,
      _price,
      ..._variantPrice.values,
      ..._variantSku.values,
    ]) {
      c.dispose();
    }
    super.dispose();
  }

  TextEditingController _ctl(Map<String, TextEditingController> m, String k) =>
      m.putIfAbsent(k, TextEditingController.new);

  Future<void> _editAttribute(EditableAttribute a) async {
    final l = AppLocalizations.of(context);
    final ctl = TextEditingController(text: a.value);
    final value = await showDialog<String>(
      context: context,
      builder:
          (ctx) => AlertDialog(
            title: Text(l.attrEditTitle(humaniseKey(a.source.key))),
            content: TextField(
              controller: ctl,
              autofocus: true,
              maxLength: 500,
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx),
                child: Text(l.actionCancel),
              ),
              FilledButton(
                onPressed: () => Navigator.pop(ctx, ctl.text),
                child: Text(l.actionSave),
              ),
            ],
          ),
    );
    ctl.dispose();
    if (value == null || value.trim().isEmpty) return;
    setState(() {
      a.value = value.trim();
      a.decision =
          value.trim() == a.source.value
              ? AttributeDecision.accepted
              : AttributeDecision.edited;
    });
  }

  Future<void> _save() async {
    setState(() => _showErrors = true);
    if (form.validate().isNotEmpty) return;
    final payload = form.toApply();
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      final detail = await ref
          .read(studioApiProvider)
          .apply(
            widget.job.id,
            product: payload.product,
            categoryPath: payload.categoryPath,
            acceptedAttributeKeys: payload.acceptedKeys,
          );
      final productId = detail['id']! as String;
      if (payload.editedValues.isNotEmpty) {
        try {
          await ref
              .read(catalogApiProvider)
              .setAttributes(productId, payload.editedValues);
        } on ApiError {
          // Product exists; the product screen shows any unconfirmed detail.
        }
      }
      if (mounted) {
        context.pushReplacement('/products/$productId?job=${widget.job.id}');
      }
    } on Object catch (e) {
      if (mounted) setState(() => _error = asApiError(e));
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final palette = AppPalette.of(context);
    final lang = Localizations.localeOf(context).languageCode;
    final draft = widget.job.draft ?? const StudioDraft();
    final problems = _showErrors ? form.validate() : const <ReviewProblem>[];
    bool has(ReviewProblemKind k) => problems.any((p) => p.kind == k);
    ReviewProblem? priceProblem([String? key]) =>
        problems
            .where(
              (p) =>
                  (p.kind == ReviewProblemKind.priceRequired ||
                      p.kind == ReviewProblemKind.priceInvalid) &&
                  p.variantKey == key,
            )
            .firstOrNull;

    final issues = [
      ...widget.job.issues,
      if (!draft.isProductPhoto &&
          !widget.job.issues.any((i) => i.kind == 'not_a_product_photo'))
        const DraftIssue(field: 'photos', kind: 'not_a_product_photo'),
    ];

    final neFirst = lang == 'ne';
    Widget titleField(bool ne) => TextField(
      key: Key(ne ? 'title-ne' : 'title-en'),
      controller: ne ? _titleNe : _titleEn,
      maxLength: 120,
      onChanged:
          (v) => setState(() => ne ? form.titleNe = v : form.titleEn = v),
      decoration: InputDecoration(
        labelText: ne ? l.fieldTitleNe : l.fieldTitleEn,
        errorText:
            has(ReviewProblemKind.titleRequired)
                ? l.validationTitleRequired
                : null,
      ),
    );
    Widget descField(bool ne) => TextField(
      controller: ne ? _descNe : _descEn,
      maxLines: 6,
      minLines: 3,
      maxLength: 2000,
      onChanged: (v) => ne ? form.descriptionNe = v : form.descriptionEn = v,
      decoration: InputDecoration(
        labelText: ne ? l.fieldDescriptionNe : l.fieldDescriptionEn,
        alignLabelWithHint: true,
      ),
    );

    final combos = form.variantCombinations;
    const pad = EdgeInsets.symmetric(horizontal: AppSpace.s4);

    return Scaffold(
      appBar: AppBar(title: Text(l.reviewTitle)),
      body: ListView(
        padding: const EdgeInsets.only(bottom: AppSpace.s8),
        children: [
          Padding(
            padding: pad,
            child: Row(
              children: [
                Icon(Icons.edit_note, size: 20, color: palette.automation),
                const SizedBox(width: AppSpace.s2),
                Expanded(
                  child: Text(
                    l.reviewAiNote,
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: theme.colorScheme.onSurfaceVariant,
                    ),
                  ),
                ),
              ],
            ),
          ),
          if (issues.isNotEmpty) ...[
            SectionHeader(l.reviewSectionWarnings),
            Padding(padding: pad, child: IssueList(issues: issues)),
          ],
          SectionHeader(l.reviewSectionText),
          Padding(
            padding: pad,
            child: Column(
              children: [
                titleField(neFirst),
                titleField(!neFirst),
                descField(neFirst),
                const SizedBox(height: AppSpace.s2),
                descField(!neFirst),
              ],
            ),
          ),
          SectionHeader(
            l.reviewSectionCategory,
            trailing:
                draft.categoryPath.isEmpty
                    ? null
                    : Text(
                      l.confidenceLabel(
                        Formatters.percent(draft.categoryConfidence, lang),
                      ),
                      style: theme.textTheme.labelSmall?.copyWith(
                        color: palette.automation,
                      ),
                    ),
          ),
          Padding(
            padding: pad,
            child: TextField(
              controller: _category,
              onChanged: (v) => form.categoryPath = v.split('/'),
              decoration: InputDecoration(helperText: l.fieldCategoryHint),
            ),
          ),
          if (form.attributes.isNotEmpty) ...[
            SectionHeader(l.reviewSectionDetails),
            for (final a in form.attributes) ...[
              AttributeReviewRow(
                attribute: a,
                showError: has(ReviewProblemKind.attributesUnchecked),
                onAccept:
                    () =>
                        setState(() => a.decision = AttributeDecision.accepted),
                onEdit: () => _editAttribute(a),
              ),
              const Divider(height: 1),
            ],
            if (has(ReviewProblemKind.attributesUnchecked))
              Padding(
                padding: const EdgeInsets.fromLTRB(
                  AppSpace.s4,
                  AppSpace.s2,
                  AppSpace.s4,
                  0,
                ),
                child: Text(
                  l.attrUncheckedError(form.uncheckedAttributes.length),
                  key: const Key('attr-unchecked-error'),
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: palette.danger,
                  ),
                ),
              ),
          ],
          if (form.checklist.isNotEmpty) ...[
            SectionHeader(l.reviewSectionChecklist),
            for (final e in form.checklist.entries)
              CheckboxListTile(
                value: e.value,
                controlAffinity: ListTileControlAffinity.leading,
                title: Text(e.key),
                onChanged:
                    (v) => setState(() => form.checklist[e.key] = v ?? false),
              ),
          ],
          SectionHeader(l.reviewSectionPrice),
          Padding(
            padding: pad,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Text(
                  l.reviewPriceNote,
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                ),
                const SizedBox(height: AppSpace.s3),
                for (final o in form.options)
                  _OptionEditor(
                    key: ObjectKey(o),
                    option: o,
                    onChanged: () => setState(() {}),
                    onRemove: () => setState(() => form.options.remove(o)),
                  ),
                if (has(ReviewProblemKind.optionValuesRequired))
                  Text(
                    l.optionValuesRequired,
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: palette.danger,
                    ),
                  ),
                if (form.options.length < maxOptions)
                  Align(
                    alignment: AlignmentDirectional.centerStart,
                    child: TextButton.icon(
                      onPressed:
                          () => setState(
                            () => form.options.add(EditableOption('', [])),
                          ),
                      icon: const Icon(Icons.add),
                      label: Text(l.optionAdd),
                    ),
                  ),
                Text(
                  has(ReviewProblemKind.tooManyVariants)
                      ? l.tooManyVariants
                      : l.variantsCount(
                        combos.length > maxVariants
                            ? maxVariants
                            : combos.length,
                      ),
                  style: theme.textTheme.labelMedium?.copyWith(
                    color:
                        has(ReviewProblemKind.tooManyVariants)
                            ? palette.danger
                            : theme.colorScheme.onSurfaceVariant,
                  ),
                ),
                if (combos.length > 1)
                  SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    value: form.samePrice,
                    title: Text(l.samePriceToggle),
                    onChanged: (v) => setState(() => form.samePrice = v),
                  ),
                const SizedBox(height: AppSpace.s2),
                if (form.samePrice || combos.length <= 1)
                  _PriceField(
                    key: const Key('price-field'),
                    controller: _price,
                    label: l.fieldPrice,
                    error: priceProblem()?.priceError,
                    onChanged:
                        (v) => setState(() {
                          form.price = v;
                          form.samePrice = true;
                        }),
                  )
                else
                  for (final c in combos.take(maxVariants)) ...[
                    _PriceField(
                      key: Key('price-${variantKey(c)}'),
                      controller: _ctl(_variantPrice, variantKey(c)),
                      label: l.fieldPriceFor(variantLabel(l, c)),
                      error: priceProblem(variantKey(c))?.priceError,
                      onChanged:
                          (v) => setState(
                            () => form.variantPrices[variantKey(c)] = v,
                          ),
                    ),
                    TextField(
                      controller: _ctl(_variantSku, variantKey(c)),
                      onChanged: (v) => form.variantSkus[variantKey(c)] = v,
                      decoration: InputDecoration(labelText: l.fieldSku),
                    ),
                    const SizedBox(height: AppSpace.s4),
                  ],
              ],
            ),
          ),
        ],
      ),
      bottomNavigationBar: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(
            AppSpace.s4,
            AppSpace.s2,
            AppSpace.s4,
            AppSpace.s3,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (_error != null) ...[
                InlineError(error: _error!),
                const SizedBox(height: AppSpace.s2),
              ] else if (problems.isNotEmpty) ...[
                Text(
                  l.reviewFixProblems,
                  key: const Key('review-fix-problems'),
                  textAlign: TextAlign.center,
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: palette.danger,
                  ),
                ),
                const SizedBox(height: AppSpace.s2),
              ],
              SubmitButton(
                key: const Key('review-save'),
                label: l.reviewCreate,
                busy: _saving,
                onPressed: _save,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _PriceField extends StatelessWidget {
  const _PriceField({
    super.key,
    required this.controller,
    required this.label,
    required this.onChanged,
    this.error,
  });

  final TextEditingController controller;
  final String label;
  final ValueChanged<String> onChanged;
  final PriceInputError? error;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return TextField(
      controller: controller,
      keyboardType: const TextInputType.numberWithOptions(decimal: true),
      inputFormatters: [
        FilteringTextInputFormatter.allow(RegExp(r'[0-9०-९.,\s]')),
      ],
      onChanged: onChanged,
      decoration: InputDecoration(
        labelText: label,
        prefixText:
            Localizations.localeOf(context).languageCode == 'ne'
                ? 'रू '
                : 'Rs ',
        errorText: error == null ? null : priceErrorText(l, error!),
      ),
    );
  }
}

class _OptionEditor extends StatefulWidget {
  const _OptionEditor({
    super.key,
    required this.option,
    required this.onChanged,
    required this.onRemove,
  });

  final EditableOption option;
  final VoidCallback onChanged;
  final VoidCallback onRemove;

  @override
  State<_OptionEditor> createState() => _OptionEditorState();
}

class _OptionEditorState extends State<_OptionEditor> {
  late final TextEditingController _name = TextEditingController(
    text: widget.option.name,
  );
  late final TextEditingController _values = TextEditingController(
    text: widget.option.values.join(', '),
  );

  @override
  void dispose() {
    _name.dispose();
    _values.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: AppSpace.s3),
      child: Column(
        children: [
          Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _name,
                  maxLength: 60,
                  onChanged: (v) {
                    widget.option.name = v;
                    widget.onChanged();
                  },
                  decoration: InputDecoration(
                    labelText: l.optionName,
                    counterText: '',
                  ),
                ),
              ),
              IconButton(
                tooltip: l.optionRemove,
                onPressed: widget.onRemove,
                icon: const Icon(Icons.delete_outline),
              ),
            ],
          ),
          const SizedBox(height: AppSpace.s2),
          TextField(
            controller: _values,
            onChanged: (v) {
              final values = <String>[];
              for (final s in v.split(RegExp('[,،]'))) {
                final t = s.trim();
                if (t.isNotEmpty && !values.contains(t) && values.length < 50) {
                  values.add(t);
                }
              }
              widget.option.values
                ..clear()
                ..addAll(values);
              widget.onChanged();
            },
            decoration: InputDecoration(labelText: l.optionValuesHint),
          ),
        ],
      ),
    );
  }
}
