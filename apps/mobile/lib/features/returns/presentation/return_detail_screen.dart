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

/// One return: policy checks, neutral facts about the customer's history,
/// items, the pickup, refunds, and the actions the server allows.
class ReturnDetailScreen extends ConsumerStatefulWidget {
  const ReturnDetailScreen({super.key, required this.returnId});

  final String returnId;

  @override
  ConsumerState<ReturnDetailScreen> createState() => _ReturnDetailScreenState();
}

class _ReturnDetailScreenState extends ConsumerState<ReturnDetailScreen> {
  bool _busy = false;
  ApiError? _error;

  /// Kept across failed attempts (a retry replays the same refund); renewed
  /// only after the refund was accepted.
  String _refundKey = const Uuid().v4();

  ReturnsApi get _api => ref.read(returnsApiProvider);

  Future<bool> _run(ReturnDetail r, Future<void> Function() action) async {
    final l = AppLocalizations.of(context);
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await action();
      ref
        ..invalidate(returnDetailProvider(widget.returnId))
        ..invalidate(orderReturnsProvider(r.summary.orderId))
        ..invalidate(orderProvider(r.summary.orderId));
      for (final b in returnBuckets) {
        ref.invalidate(returnsPageProvider(b));
      }
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(l.returnDone)));
      }
      return true;
    } on Object catch (e) {
      if (mounted) setState(() => _error = asApiError(e));
      return false;
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _act(ReturnDetail r, String a) async {
    final l = AppLocalizations.of(context);
    final id = r.summary.id;
    switch (a) {
      case 'approve':
        if (r.summary.eligible) {
          if (await _confirm(context, l.returnApproveTitle, null)) {
            await _run(r, () => _api.approve(id));
          }
        } else {
          final reason = await showDialog<String>(
            context: context,
            builder:
                (_) => _ReasonDialog(
                  title: l.returnApproveTitle,
                  hint: l.returnOverrideHint,
                  label: l.returnReasonLabel,
                  fieldKey: const Key('return-override-reason'),
                ),
          );
          if (reason != null) {
            await _run(r, () => _api.approve(id, overrideReason: reason));
          }
        }
      case 'reject':
        final reason = await showDialog<String>(
          context: context,
          builder:
              (_) => _ReasonDialog(
                title: l.returnRejectTitle,
                label: l.returnRejectLabel,
                fieldKey: const Key('return-reject-reason'),
              ),
        );
        if (reason != null) await _run(r, () => _api.reject(id, reason));
      case 'cancel':
        if (await _confirm(context, l.returnCancelTitle, l.returnCancelBody)) {
          await _run(r, () => _api.cancel(id));
        }
      case 'mark_received':
        if (await _confirm(
          context,
          l.returnReceivedTitle,
          l.returnReceivedBody,
        )) {
          await _run(r, () => _api.received(id));
        }
      case 'inspect':
        if (!mounted) return;
        final items = await showModalBottomSheet<List<Map<String, Object?>>>(
          context: context,
          isScrollControlled: true,
          builder: (_) => InspectSheet(lines: r.lines),
        );
        if (items != null) await _run(r, () => _api.inspect(id, items));
      case 'refund':
        if (!mounted) return;
        final choice = await showModalBottomSheet<_RefundChoice>(
          context: context,
          isScrollControlled: true,
          builder: (_) => RefundSheet(detail: r, idempotencyKey: _refundKey),
        );
        if (choice != null) {
          final ok = await _run(
            r,
            () => _api.refund(
              r.summary.orderId,
              returnId: id,
              amountMinor: choice.amountMinor,
              method: choice.method,
              reference: choice.reference,
              idempotencyKey: choice.key,
            ),
          );
          if (ok) _refundKey = const Uuid().v4();
        }
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final detail = ref.watch(returnDetailProvider(widget.returnId));
    return Scaffold(
      appBar: AppBar(
        title: Text(
          detail.valueOrNull == null
              ? l.returnsTitle
              : l.returnDetailTitle(detail.valueOrNull!.summary.number),
        ),
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(returnDetailProvider(widget.returnId));
          await ref.read(returnDetailProvider(widget.returnId).future);
        },
        child: ListView(
          padding: const EdgeInsets.only(bottom: AppSpace.s8),
          children: [
            AsyncValueView<ReturnDetail>(
              value: detail,
              onRetry:
                  () => ref.invalidate(returnDetailProvider(widget.returnId)),
              data: (r) => _body(context, l, r),
            ),
          ],
        ),
      ),
    );
  }

  Widget _body(BuildContext context, AppLocalizations l, ReturnDetail r) {
    final theme = Theme.of(context);
    final palette = AppPalette.of(context);
    final lang = Localizations.localeOf(context).languageCode;
    String money(int m) => Formatters.money(m, r.summary.currency, lang);
    const pad = EdgeInsets.symmetric(horizontal: AppSpace.s4);
    final failed = r.checks.where((c) => !c.ok).toList();
    final actions = r.actions.where((a) => a != 'book_pickup').toList();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.all(AppSpace.s4),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Expanded(
                    child: Text(
                      resolutionLabel(l, r.summary.resolution),
                      style: theme.textTheme.titleMedium,
                    ),
                  ),
                  StatusChip(
                    key: const Key('return-status'),
                    label: returnStatusLabel(l, r.summary.status),
                    colors: returnStatusColors(context, r.summary.status),
                  ),
                ],
              ),
              if (r.summary.orderNumber != null)
                TextButton(
                  style: TextButton.styleFrom(padding: EdgeInsets.zero),
                  onPressed: () => context.push('/orders/${r.summary.orderId}'),
                  child: Text(
                    [
                      '#${r.summary.orderNumber}',
                      if ((r.summary.customerName ?? '').isNotEmpty)
                        r.summary.customerName!,
                    ].join(' · '),
                  ),
                ),
              if (r.summary.resolution == 'refund')
                Text(
                  l.returnRefundDue(money(r.summary.refundDueMinor)),
                  key: const Key('return-refund-due'),
                ),
              if ((r.overrideReason ?? '').isNotEmpty)
                Text(l.returnOverrideNote(r.overrideReason!)),
              if ((r.rejectionReason ?? '').isNotEmpty)
                Text(l.returnRejectedNote(r.rejectionReason!)),
            ],
          ),
        ),
        if (_error != null)
          Padding(padding: pad, child: InlineError(error: _error!)),
        SectionHeader(l.returnChecksTitle),
        if (failed.isEmpty)
          Padding(
            padding: pad,
            child: Text(l.returnAllOk, key: const Key('return-checks-ok')),
          )
        else
          for (final c in failed)
            ListTile(
              key: Key('return-check-${c.code}'),
              dense: true,
              leading: Icon(
                Icons.warning_amber_rounded,
                color: c.soft ? palette.warning : palette.danger,
              ),
              title: Text(checkLabel(l, c)),
            ),
        if (r.summary.signals.isNotEmpty) ...[
          SectionHeader(l.returnSignalsTitle),
          for (final s in r.summary.signals)
            ListTile(
              key: Key('return-signal-${s.code}'),
              dense: true,
              leading: Icon(Icons.info_outline, color: palette.muted),
              title: Text(signalLabel(l, s)),
            ),
        ],
        SectionHeader(l.returnItemsTitle),
        for (final ln in r.lines)
          ListTile(
            key: Key('return-line-${ln.id}'),
            title: Text(l.returnLineItem(ln.quantity, ln.label)),
            subtitle: Text(
              [
                returnReasonLabel(l, ln.reason),
                if (ln.exchangeTitle != null)
                  l.returnLineExchange(ln.exchangeTitle!),
                if (ln.condition != null)
                  l.returnLineCondition(conditionLabel(l, ln.condition!)),
              ].join(' · '),
            ),
            trailing: Text(money(ln.unitRefundMinor * ln.quantity)),
          ),
        if (r.pickup != null || r.actions.contains('book_pickup')) ...[
          SectionHeader(l.returnPickupTitle),
          if (r.pickup != null)
            ListTile(
              key: const Key('return-pickup'),
              title: Text(r.pickup!.courierName),
              subtitle:
                  r.pickup!.trackingNumber == null
                      ? null
                      : Text(l.deliveryTracking(r.pickup!.trackingNumber!)),
              trailing: StatusChip(
                label: shipmentStatusLabel(l, r.pickup!.status),
                colors: shipmentStatusColors(context, r.pickup!.status),
              ),
            )
          else
            Padding(
              padding: pad,
              child: Text(
                l.returnPickupOnWeb,
                style: theme.textTheme.bodySmall?.copyWith(
                  color: palette.muted,
                ),
              ),
            ),
        ],
        if (r.refunds.isNotEmpty) ...[
          SectionHeader(l.returnRefundsTitle),
          for (final f in r.refunds)
            ListTile(
              key: Key('return-refund-${f.id}'),
              title: Text(
                l.refundLine(
                  Formatters.money(f.amountMinor, f.currency, lang),
                  refundMethodLabel(l, f.method),
                ),
              ),
              subtitle: Text(
                [
                  refundStatusLabel(l, f.status),
                  if ((f.reference ?? '').isNotEmpty) f.reference!,
                ].join(' · '),
                style: TextStyle(
                  color:
                      f.status == 'pending_approval'
                          ? palette.warning
                          : f.status == 'failed'
                          ? palette.danger
                          : null,
                ),
              ),
            ),
        ],
        if (actions.isNotEmpty)
          Padding(
            padding: const EdgeInsets.all(AppSpace.s4),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                for (final (i, a) in actions.indexed) ...[
                  _button(l, palette, a, primary: i == 0, r: r),
                  const SizedBox(height: AppSpace.s2),
                ],
              ],
            ),
          ),
      ],
    );
  }

  Widget _button(
    AppLocalizations l,
    AppPalette palette,
    String a, {
    required bool primary,
    required ReturnDetail r,
  }) {
    final label = switch (a) {
      'approve' => l.returnActionApprove,
      'reject' => l.returnActionReject,
      'cancel' => l.returnActionCancel,
      'mark_received' => l.returnActionReceived,
      'inspect' => l.returnActionInspect,
      _ => l.returnActionRefund,
    };
    final key = Key('return-action-$a');
    final onTap = _busy ? null : () => _act(r, a);
    if (a == 'cancel' || a == 'reject') {
      return TextButton(
        key: key,
        style: TextButton.styleFrom(
          foregroundColor: palette.danger,
          minimumSize: const Size.fromHeight(48),
        ),
        onPressed: onTap,
        child: Text(label),
      );
    }
    return primary
        ? FilledButton(
          key: key,
          style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(52)),
          onPressed: onTap,
          child: Text(label),
        )
        : OutlinedButton(
          key: key,
          style: OutlinedButton.styleFrom(
            minimumSize: const Size.fromHeight(48),
          ),
          onPressed: onTap,
          child: Text(label),
        );
  }
}

Future<bool> _confirm(BuildContext context, String title, String? body) async {
  final l = AppLocalizations.of(context);
  final ok = await showDialog<bool>(
    context: context,
    builder:
        (ctx) => AlertDialog(
          title: Text(title),
          content: body == null ? null : Text(body),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(false),
              child: Text(l.deliveryKeep),
            ),
            FilledButton(
              key: const Key('return-confirm'),
              onPressed: () => Navigator.of(ctx).pop(true),
              child: Text(l.deliveryConfirm),
            ),
          ],
        ),
  );
  return ok ?? false;
}

/// A required reason (≥ 3 characters): overriding the policy, rejecting.
class _ReasonDialog extends StatefulWidget {
  const _ReasonDialog({
    required this.title,
    required this.label,
    required this.fieldKey,
    this.hint,
  });

  final String title;
  final String label;
  final String? hint;
  final Key fieldKey;

  @override
  State<_ReasonDialog> createState() => _ReasonDialogState();
}

class _ReasonDialogState extends State<_ReasonDialog> {
  final _text = TextEditingController();

  @override
  void dispose() {
    _text.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final ready = _text.text.trim().length >= 3;
    return AlertDialog(
      title: Text(widget.title),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (widget.hint != null) Text(widget.hint!),
          TextField(
            key: widget.fieldKey,
            controller: _text,
            maxLength: 300,
            maxLines: 3,
            onChanged: (_) => setState(() {}),
            decoration: InputDecoration(
              labelText: widget.label,
              helperText: ready ? null : l.returnReasonRequired,
            ),
          ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: Text(l.deliveryKeep),
        ),
        FilledButton(
          key: const Key('return-reason-save'),
          onPressed:
              ready ? () => Navigator.of(context).pop(_text.text.trim()) : null,
          child: Text(l.deliveryConfirm),
        ),
      ],
    );
  }
}

/// Inspection: a condition per item; only items that can be sold again may
/// go back on sale (restock is disabled otherwise).
class InspectSheet extends StatefulWidget {
  const InspectSheet({super.key, required this.lines});

  final List<ReturnLine> lines;

  @override
  State<InspectSheet> createState() => _InspectSheetState();
}

class _InspectSheetState extends State<InspectSheet> {
  final Map<String, String> _condition = {};
  final Map<String, int> _restock = {};

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final palette = AppPalette.of(context);
    final ready = widget.lines.every((ln) => _condition[ln.id] != null);
    return SafeArea(
      child: ConstrainedBox(
        constraints: BoxConstraints(
          maxHeight: MediaQuery.sizeOf(context).height * 0.9,
        ),
        child: ListView(
          shrinkWrap: true,
          padding: const EdgeInsets.all(AppSpace.s4),
          children: [
            Text(l.returnInspectTitle, style: theme.textTheme.titleMedium),
            for (final ln in widget.lines) ...[
              const SizedBox(height: AppSpace.s3),
              Text(
                l.returnLineItem(ln.quantity, ln.label),
                style: theme.textTheme.titleSmall,
              ),
              Wrap(
                spacing: AppSpace.s2,
                children: [
                  for (final c in returnConditions)
                    ChoiceChip(
                      key: Key('inspect-${ln.id}-$c'),
                      label: Text(conditionLabel(l, c)),
                      selected: _condition[ln.id] == c,
                      onSelected:
                          (_) => setState(() {
                            _condition[ln.id] = c;
                            _restock[ln.id] =
                                c == 'resellable' ? ln.quantity : 0;
                          }),
                    ),
                ],
              ),
              Builder(
                builder: (context) {
                  final resellable = _condition[ln.id] == 'resellable';
                  final n = _restock[ln.id] ?? 0;
                  return Row(
                    children: [
                      Expanded(
                        child: Text(
                          resellable
                              ? l.returnRestock
                              : l.returnRestockOnlyResellable,
                          style: theme.textTheme.bodySmall?.copyWith(
                            color: resellable ? null : palette.muted,
                          ),
                        ),
                      ),
                      IconButton(
                        key: Key('restock-minus-${ln.id}'),
                        icon: const Icon(Icons.remove),
                        onPressed:
                            resellable && n > 0
                                ? () => setState(() => _restock[ln.id] = n - 1)
                                : null,
                      ),
                      Text('$n', key: Key('restock-${ln.id}')),
                      IconButton(
                        key: Key('restock-plus-${ln.id}'),
                        icon: const Icon(Icons.add),
                        onPressed:
                            resellable && n < ln.quantity
                                ? () => setState(() => _restock[ln.id] = n + 1)
                                : null,
                      ),
                    ],
                  );
                },
              ),
            ],
            if (!ready)
              Text(
                l.returnPickCondition,
                style: theme.textTheme.bodySmall?.copyWith(
                  color: palette.muted,
                ),
              ),
            const SizedBox(height: AppSpace.s3),
            FilledButton(
              key: const Key('inspect-save'),
              style: FilledButton.styleFrom(
                minimumSize: const Size.fromHeight(52),
              ),
              onPressed:
                  ready
                      ? () => Navigator.of(context).pop([
                        for (final ln in widget.lines)
                          {
                            'line_id': ln.id,
                            'condition': _condition[ln.id],
                            'restock': _restock[ln.id] ?? 0,
                          },
                      ])
                      : null,
              child: Text(l.returnInspectSave),
            ),
          ],
        ),
      ),
    );
  }
}

class _RefundChoice {
  const _RefundChoice(this.amountMinor, this.method, this.reference, this.key);

  final int amountMinor;
  final String method;
  final String? reference;
  final String key;
}

/// Refund: defaults to what's due (never more than the customer paid minus
/// earlier refunds). The screen supplies the Idempotency-Key, so a retry can't
/// refund twice; above the shop's threshold the server holds it for a manager.
class RefundSheet extends StatefulWidget {
  const RefundSheet({
    super.key,
    required this.detail,
    required this.idempotencyKey,
  });

  final ReturnDetail detail;
  final String idempotencyKey;

  @override
  State<RefundSheet> createState() => _RefundSheetState();
}

class _RefundSheetState extends State<RefundSheet> {
  late final int _max;
  late final TextEditingController _amount;
  final _reference = TextEditingController();
  String? _method;

  @override
  void initState() {
    super.initState();
    final d = widget.detail;
    _max = d.refundableMinor;
    final due =
        d.summary.refundDueMinor < _max ? d.summary.refundDueMinor : _max;
    _amount = TextEditingController(text: _rupees(due));
  }

  static String _rupees(int minor) =>
      minor % 100 == 0 ? '${minor ~/ 100}' : (minor / 100).toStringAsFixed(2);

  int? get _amountMinor {
    final v = double.tryParse(_amount.text.replaceAll(',', '').trim());
    return v == null ? null : (v * 100).round();
  }

  @override
  void dispose() {
    _amount.dispose();
    _reference.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final lang = Localizations.localeOf(context).languageCode;
    final amount = _amountMinor;
    final tooMuch = amount != null && amount > _max;
    final ready = amount != null && amount > 0 && !tooMuch && _method != null;
    return SafeArea(
      child: Padding(
        padding: EdgeInsets.only(
          bottom: MediaQuery.viewInsetsOf(context).bottom,
        ),
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(AppSpace.s4),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(l.refundTitle, style: theme.textTheme.titleMedium),
              TextField(
                key: const Key('refund-amount'),
                controller: _amount,
                keyboardType: const TextInputType.numberWithOptions(
                  decimal: true,
                ),
                onChanged: (_) => setState(() {}),
                decoration: InputDecoration(
                  labelText: l.refundAmount,
                  helperText: l.refundMax(
                    Formatters.money(
                      _max,
                      widget.detail.summary.currency,
                      lang,
                    ),
                  ),
                  errorText: tooMuch ? l.refundTooMuch : null,
                ),
              ),
              const SizedBox(height: AppSpace.s3),
              Text(l.refundMethod, style: theme.textTheme.titleSmall),
              Wrap(
                spacing: AppSpace.s2,
                runSpacing: AppSpace.s1,
                children: [
                  for (final m in refundMethods)
                    ChoiceChip(
                      key: Key('refund-method-$m'),
                      label: Text(refundMethodLabel(l, m)),
                      selected: _method == m,
                      onSelected: (_) => setState(() => _method = m),
                    ),
                ],
              ),
              if (_method != null && _method != 'original_payment')
                TextField(
                  key: const Key('refund-reference'),
                  controller: _reference,
                  maxLength: 120,
                  decoration: InputDecoration(labelText: l.refundReference),
                ),
              const SizedBox(height: AppSpace.s3),
              FilledButton(
                key: const Key('refund-send'),
                style: FilledButton.styleFrom(
                  minimumSize: const Size.fromHeight(52),
                ),
                onPressed:
                    ready
                        ? () => Navigator.of(context).pop(
                          _RefundChoice(
                            amount,
                            _method!,
                            _reference.text.trim(),
                            widget.idempotencyKey,
                          ),
                        )
                        : null,
                child: Text(l.refundSend),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
