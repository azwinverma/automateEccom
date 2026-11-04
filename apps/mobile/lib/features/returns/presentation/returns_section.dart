import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:uuid/uuid.dart';

import '../../../core/errors/api_error.dart';
import '../../../core/l10n/formatters.dart';
import '../../../core/l10n/gen/app_localizations.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens.g.dart';
import '../../../design/widgets/section_header.dart';
import '../../../design/widgets/state_views.dart';
import '../../fulfillment/presentation/fulfillment_labels.dart';
import '../../orders/data/orders_api.dart';
import '../data/returns_api.dart';
import 'returns_labels.dart';

const _returnable = {'delivered', 'completed', 'returned'};

/// Order detail "Returns": the order's returns and "Start a return".
/// Hidden when returns can't be read (permission) or the order isn't delivered.
class ReturnsSection extends ConsumerWidget {
  const ReturnsSection({super.key, required this.order});

  final OrderDetail order;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final status = order.summary.status;
    if (!_returnable.contains(status)) return const SizedBox.shrink();
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final palette = AppPalette.of(context);
    final lang = Localizations.localeOf(context).languageCode;
    final id = order.summary.id;
    return ref
        .watch(orderReturnsProvider(id))
        .when(
          skipLoadingOnRefresh: false,
          loading: () => const SizedBox.shrink(),
          error: (_, __) => const SizedBox.shrink(),
          data:
              (items) => Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  SectionHeader(
                    l.returnsTitle,
                    key: const Key('returns-section'),
                  ),
                  if (items.isEmpty)
                    Padding(
                      padding: const EdgeInsets.symmetric(
                        horizontal: AppSpace.s4,
                      ),
                      child: Text(
                        l.returnsNone,
                        style: theme.textTheme.bodyMedium?.copyWith(
                          color: palette.muted,
                        ),
                      ),
                    ),
                  for (final r in items)
                    ListTile(
                      key: Key('order-return-${r.summary.id}'),
                      onTap: () => context.push('/returns/${r.summary.id}'),
                      title: Row(
                        children: [
                          Expanded(
                            child: Text(
                              '${r.summary.number} · '
                              '${resolutionLabel(l, r.summary.resolution)}',
                            ),
                          ),
                          StatusChip(
                            label: returnStatusLabel(l, r.summary.status),
                            colors: returnStatusColors(
                              context,
                              r.summary.status,
                            ),
                          ),
                        ],
                      ),
                      subtitle: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          for (final ln in r.lines)
                            Text(
                              [
                                l.returnLineItem(ln.quantity, ln.label),
                                returnReasonLabel(l, ln.reason),
                                if (ln.condition != null)
                                  l.returnLineCondition(
                                    conditionLabel(l, ln.condition!),
                                  ),
                              ].join(' · '),
                            ),
                          if (r.summary.resolution == 'refund' &&
                              r.summary.refundDueMinor > 0)
                            Text(
                              l.returnRefundDue(
                                Formatters.money(
                                  r.summary.refundDueMinor,
                                  r.summary.currency,
                                  lang,
                                ),
                              ),
                            ),
                        ],
                      ),
                      trailing: const Icon(Icons.chevron_right),
                    ),
                  if (status != 'returned')
                    Padding(
                      padding: const EdgeInsets.all(AppSpace.s4),
                      child: OutlinedButton.icon(
                        key: const Key('return-start'),
                        style: OutlinedButton.styleFrom(
                          minimumSize: const Size.fromHeight(48),
                        ),
                        icon: const Icon(Icons.assignment_return_outlined),
                        label: Text(l.returnsStart),
                        onPressed: () async {
                          final created =
                              await showModalBottomSheet<ReturnDetail>(
                                context: context,
                                isScrollControlled: true,
                                builder:
                                    (_) => StartReturnSheet(
                                      orderId: id,
                                      orderNumber: order.summary.number,
                                    ),
                              );
                          if (created == null) return;
                          ref
                            ..invalidate(orderReturnsProvider(id))
                            ..invalidate(orderTimelineProvider(id));
                          if (context.mounted) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(content: Text(l.returnCreated)),
                            );
                          }
                        },
                      ),
                    ),
                ],
              ),
        );
  }
}

class _Pick {
  bool selected = false;
  int qty = 1;
  String? reason;
  String? exchangeVariantId;
}

/// Pick items, quantity, reason and refund/exchange; check the merchant's
/// policy, then create the return. One Idempotency-Key per sheet: a retry
/// after a dropped connection replays the same request.
class StartReturnSheet extends ConsumerStatefulWidget {
  const StartReturnSheet({
    super.key,
    required this.orderId,
    required this.orderNumber,
  });

  final String orderId;
  final int orderNumber;

  @override
  ConsumerState<StartReturnSheet> createState() => _StartReturnSheetState();
}

class _StartReturnSheetState extends ConsumerState<StartReturnSheet> {
  final String _key = const Uuid().v4();
  final Map<String, _Pick> _picks = {};
  String _resolution = 'refund';
  EligibilityResult? _check;
  bool _busy = false;
  ApiError? _error;

  _Pick _pick(String id) => _picks.putIfAbsent(id, _Pick.new);

  void _changed(VoidCallback f) => setState(() {
    f();
    _check = null; // the policy result belongs to the previous choice
  });

  List<ReturnLineInput> _lines() => [
    for (final e in _picks.entries)
      if (e.value.selected)
        ReturnLineInput(
          orderLineId: e.key,
          quantity: e.value.qty,
          reason: e.value.reason ?? 'other',
          exchangeVariantId:
              _resolution == 'exchange' ? e.value.exchangeVariantId : null,
        ),
  ];

  String? _missing(AppLocalizations l) {
    final chosen = _picks.values.where((p) => p.selected).toList();
    if (chosen.isEmpty) return l.returnPickItems;
    if (chosen.any((p) => p.reason == null)) return l.returnPickReason;
    if (_resolution == 'exchange' &&
        chosen.any((p) => p.exchangeVariantId == null)) {
      return l.returnPickExchange;
    }
    return null;
  }

  Future<void> _runCheck() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final r = await ref
          .read(returnsApiProvider)
          .check(widget.orderId, _resolution, _lines());
      if (mounted) setState(() => _check = r);
    } on Object catch (e) {
      if (mounted) setState(() => _error = asApiError(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _submit() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final r = await ref
          .read(returnsApiProvider)
          .create(
            widget.orderId,
            resolution: _resolution,
            lines: _lines(),
            idempotencyKey: _key,
          );
      if (mounted) Navigator.of(context).pop(r);
    } on Object catch (e) {
      if (mounted) setState(() => _error = asApiError(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final palette = AppPalette.of(context);
    final lang = Localizations.localeOf(context).languageCode;
    return SafeArea(
      child: Padding(
        padding: EdgeInsets.only(
          bottom: MediaQuery.viewInsetsOf(context).bottom,
        ),
        child: ConstrainedBox(
          constraints: BoxConstraints(
            maxHeight: MediaQuery.sizeOf(context).height * 0.9,
          ),
          child: AsyncValueView<Returnable>(
            value: ref.watch(returnableProvider(widget.orderId)),
            onRetry: () => ref.invalidate(returnableProvider(widget.orderId)),
            loading: const SkeletonList(rows: 3),
            data: (info) {
              final lines =
                  info.lines.where((x) => x.returnableQuantity > 0).toList();
              final missing = _missing(l);
              final check = _check;
              return ListView(
                key: const Key('return-sheet'),
                shrinkWrap: true,
                padding: const EdgeInsets.all(AppSpace.s4),
                children: [
                  Text(
                    l.returnSheetTitle(widget.orderNumber),
                    style: theme.textTheme.titleMedium,
                  ),
                  const SizedBox(height: AppSpace.s2),
                  if (lines.isEmpty)
                    Text(l.returnNothingLeft, key: const Key('return-none'))
                  else ...[
                    Text(l.returnResolution, style: theme.textTheme.titleSmall),
                    Wrap(
                      spacing: AppSpace.s2,
                      children: [
                        if (info.allowRefund)
                          ChoiceChip(
                            key: const Key('return-resolution-refund'),
                            label: Text(l.returnResolutionRefund),
                            selected: _resolution == 'refund',
                            onSelected:
                                (_) => _changed(() => _resolution = 'refund'),
                          ),
                        if (info.allowExchange)
                          ChoiceChip(
                            key: const Key('return-resolution-exchange'),
                            label: Text(l.returnResolutionExchange),
                            selected: _resolution == 'exchange',
                            onSelected:
                                (_) => _changed(() => _resolution = 'exchange'),
                          ),
                      ],
                    ),
                    const SizedBox(height: AppSpace.s3),
                    Text(l.returnPickItems, style: theme.textTheme.titleSmall),
                    for (final ln in lines)
                      _lineCard(context, l, palette, lang, info, ln),
                    if (_error != null) InlineError(error: _error!),
                    if (check != null) _checkResult(context, l, check),
                    if (missing != null)
                      Padding(
                        padding: const EdgeInsets.only(top: AppSpace.s2),
                        child: Text(
                          missing,
                          key: const Key('return-missing'),
                          style: theme.textTheme.bodySmall?.copyWith(
                            color: palette.muted,
                          ),
                        ),
                      ),
                    const SizedBox(height: AppSpace.s3),
                    if (check == null)
                      FilledButton(
                        key: const Key('return-check'),
                        style: FilledButton.styleFrom(
                          minimumSize: const Size.fromHeight(52),
                        ),
                        onPressed: missing == null && !_busy ? _runCheck : null,
                        child: Text(l.returnCheck),
                      )
                    else
                      FilledButton(
                        key: const Key('return-submit'),
                        style: FilledButton.styleFrom(
                          minimumSize: const Size.fromHeight(52),
                        ),
                        onPressed: check.canRequest && !_busy ? _submit : null,
                        child: Text(l.returnSubmit),
                      ),
                  ],
                ],
              );
            },
          ),
        ),
      ),
    );
  }

  Widget _lineCard(
    BuildContext context,
    AppLocalizations l,
    AppPalette palette,
    String lang,
    Returnable info,
    ReturnableLine ln,
  ) {
    final p = _pick(ln.orderLineId);
    final theme = Theme.of(context);
    return Container(
      key: Key('return-line-${ln.orderLineId}'),
      margin: const EdgeInsets.only(top: AppSpace.s2),
      padding: const EdgeInsets.all(AppSpace.s3),
      decoration: BoxDecoration(
        border: Border.all(color: p.selected ? palette.info : palette.line),
        borderRadius: BorderRadius.circular(AppRadius.md),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          CheckboxListTile(
            key: Key('return-pick-${ln.orderLineId}'),
            contentPadding: EdgeInsets.zero,
            value: p.selected,
            onChanged: (v) => _changed(() => p.selected = v ?? false),
            title: Text(ln.label),
            subtitle: Text(
              [
                Formatters.money(ln.unitRefundMinor, info.currency, lang),
                if (ln.finalSale) l.returnCheckFinalSale,
              ].join(' · '),
            ),
          ),
          if (p.selected) ...[
            if (ln.returnableQuantity > 1)
              Row(
                children: [
                  Expanded(child: Text(l.returnQty)),
                  IconButton(
                    key: Key('return-qty-minus-${ln.orderLineId}'),
                    icon: const Icon(Icons.remove),
                    onPressed:
                        p.qty > 1 ? () => _changed(() => p.qty -= 1) : null,
                  ),
                  Text('${p.qty}', key: Key('return-qty-${ln.orderLineId}')),
                  IconButton(
                    key: Key('return-qty-plus-${ln.orderLineId}'),
                    icon: const Icon(Icons.add),
                    onPressed:
                        p.qty < ln.returnableQuantity
                            ? () => _changed(() => p.qty += 1)
                            : null,
                  ),
                ],
              ),
            Text(l.returnReason, style: theme.textTheme.labelLarge),
            Wrap(
              spacing: AppSpace.s2,
              runSpacing: AppSpace.s1,
              children: [
                for (final r in returnReasons)
                  ChoiceChip(
                    key: Key('return-reason-${ln.orderLineId}-$r'),
                    label: Text(returnReasonLabel(l, r)),
                    selected: p.reason == r,
                    onSelected: (_) => _changed(() => p.reason = r),
                  ),
              ],
            ),
            if (_resolution == 'exchange') ...[
              const SizedBox(height: AppSpace.s2),
              Text(l.returnExchangeFor, style: theme.textTheme.labelLarge),
              if (ln.exchangeOptions.isEmpty)
                Text(
                  l.returnNoExchangeOption,
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: palette.muted,
                  ),
                )
              else
                Wrap(
                  spacing: AppSpace.s2,
                  children: [
                    for (final o in ln.exchangeOptions)
                      ChoiceChip(
                        key: Key('return-exchange-${o.variantId}'),
                        label: Text(
                          o.available == 0
                              ? l.returnOutOfStock(o.title)
                              : o.title,
                        ),
                        selected: p.exchangeVariantId == o.variantId,
                        onSelected:
                            o.available == 0
                                ? null
                                : (_) => _changed(
                                  () => p.exchangeVariantId = o.variantId,
                                ),
                      ),
                  ],
                ),
            ],
          ],
        ],
      ),
    );
  }

  Widget _checkResult(
    BuildContext context,
    AppLocalizations l,
    EligibilityResult check,
  ) {
    final palette = AppPalette.of(context);
    final theme = Theme.of(context);
    final failed = check.checks.where((c) => !c.ok).toList();
    final hard = failed.where((c) => !c.soft).toList();
    final (fg, bg) =
        failed.isEmpty
            ? (palette.success, palette.successSoft)
            : hard.isNotEmpty
            ? (palette.danger, palette.dangerSoft)
            : (palette.warning, palette.warningSoft);
    return Container(
      key: const Key('return-check-result'),
      margin: const EdgeInsets.only(top: AppSpace.s3),
      padding: const EdgeInsets.all(AppSpace.s3),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(AppRadius.md),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            failed.isEmpty
                ? l.returnAllOk
                : hard.isNotEmpty
                ? l.returnBlockedTitle
                : l.returnWarningsTitle,
            style: theme.textTheme.titleSmall?.copyWith(color: fg),
          ),
          for (final c in hard.isNotEmpty ? hard : failed)
            Text('• ${checkLabel(l, c)}', key: Key('return-failed-${c.code}')),
        ],
      ),
    );
  }
}
