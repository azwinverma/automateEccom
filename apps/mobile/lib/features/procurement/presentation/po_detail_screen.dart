import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:uuid/uuid.dart';

import '../../../core/auth/permissions.dart';
import '../../../core/errors/api_error.dart';
import '../../../core/errors/error_messages.dart';
import '../../../core/l10n/formatters.dart';
import '../../../core/l10n/gen/app_localizations.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens.g.dart';
import '../../../design/widgets/section_header.dart';
import '../../../design/widgets/state_views.dart';
import '../../fulfillment/presentation/fulfillment_labels.dart';
import '../data/procurement_api.dart';
import 'procurement_labels.dart';

/// One purchase order: lines with what arrived, approval state, and the next step.
class PurchaseOrderScreen extends ConsumerStatefulWidget {
  const PurchaseOrderScreen({super.key, required this.poId});

  final String poId;

  @override
  ConsumerState<PurchaseOrderScreen> createState() =>
      _PurchaseOrderScreenState();
}

class _PurchaseOrderScreenState extends ConsumerState<PurchaseOrderScreen> {
  bool _busy = false;
  String? _error;

  ProcurementApi get _api => ref.read(procurementApiProvider);

  void _refresh() {
    ref.invalidate(purchaseOrderProvider(widget.poId));
    for (final f in poFilters) {
      ref.invalidate(purchaseOrdersProvider(f));
    }
  }

  Future<void> _run(Future<void> Function() call) async {
    final l = AppLocalizations.of(context);
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await call();
      _refresh();
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(l.poDone)));
      }
    } on Object catch (e) {
      final err = asApiError(e);
      if (mounted) {
        setState(
          () =>
              _error =
                  err.statusCode == 403 && err.code == 'permission_denied'
                      ? l.poManagersOnly
                      : localizedErrorMessage(l, err),
        );
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _return(PurchaseOrder po) async {
    final reason = await showDialog<String>(
      context: context,
      builder: (_) => const _ReasonDialog(),
    );
    if (reason == null || reason.length < 3) return;
    await _run(() => _api.reject(po.id, reason));
  }

  Future<void> _copy(PurchaseOrder po) async {
    final l = AppLocalizations.of(context);
    await Clipboard.setData(ClipboardData(text: po.shareText));
    if (mounted) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(l.poCopied)));
    }
  }

  Future<void> _receive(PurchaseOrder po) async {
    final done = await showModalBottomSheet<bool>(
      context: context,
      isScrollControlled: true,
      builder: (_) => ReceiveSheet(po: po),
    );
    if (done == true) _refresh();
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final value = ref.watch(purchaseOrderProvider(widget.poId));
    return Scaffold(
      appBar: AppBar(title: Text(value.valueOrNull?.number ?? l.poTitle)),
      body: AsyncValueView<PurchaseOrder>(
        value: value,
        onRetry: () => ref.invalidate(purchaseOrderProvider(widget.poId)),
        data: (po) => _body(context, po),
      ),
    );
  }

  Widget _body(BuildContext context, PurchaseOrder po) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final palette = AppPalette.of(context);
    final lang = Localizations.localeOf(context).languageCode;
    String money(int m) => Formatters.money(m, po.currency, lang);
    final waiting = poApprovalLabel(l, po.status, po.approvalReason);
    final perms = ref.watch(myPermissionsProvider).valueOrNull;
    final canWrite = mayDo(perms, 'procurement.write');
    final canApprove = mayDo(perms, 'procurement.approve');
    return ListView(
      padding: const EdgeInsets.only(bottom: AppSpace.s8),
      children: [
        Padding(
          padding: const EdgeInsets.all(AppSpace.s4),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Wrap(
                spacing: AppSpace.s2,
                runSpacing: AppSpace.s2,
                crossAxisAlignment: WrapCrossAlignment.center,
                children: [
                  StatusChip(
                    label: poStatusLabel(l, po.status),
                    colors: poStatusColors(context, po.status),
                  ),
                  if (po.source == 'recommendation')
                    Text(
                      l.poFromSuggestion,
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: palette.muted,
                      ),
                    ),
                ],
              ),
              const SizedBox(height: AppSpace.s2),
              InkWell(
                key: const Key('po-supplier'),
                onTap: () => context.push('/suppliers/${po.supplierId}'),
                child: Padding(
                  padding: const EdgeInsets.symmetric(vertical: AppSpace.s1),
                  child: Row(
                    children: [
                      Expanded(
                        child: Text(
                          po.supplierName,
                          style: theme.textTheme.titleMedium,
                        ),
                      ),
                      Text(
                        l.poSupplierOpen,
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: palette.muted,
                        ),
                      ),
                      const Icon(Icons.chevron_right, size: 18),
                    ],
                  ),
                ),
              ),
              if (waiting != null)
                Padding(
                  padding: const EdgeInsets.only(top: AppSpace.s1),
                  child: Text(
                    waiting,
                    key: const Key('po-waiting'),
                    style: theme.textTheme.bodyMedium?.copyWith(
                      color: palette.warning,
                    ),
                  ),
                ),
              const SizedBox(height: AppSpace.s2),
              Text(
                l.poTotal(money(po.totalMinor)),
                key: const Key('po-total'),
                style: theme.textTheme.titleSmall,
              ),
              Text(
                [
                  l.poGoods(money(po.subtotalMinor)),
                  if (po.extrasMinor > 0) l.poExtras(money(po.extrasMinor)),
                ].join(' · '),
                style: theme.textTheme.bodySmall,
              ),
              if (po.expectedAt != null)
                Text(
                  l.poExpected(Formatters.date(po.expectedAt!, lang)),
                  style: theme.textTheme.bodySmall,
                ),
              if ((po.notes ?? '').isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(top: AppSpace.s2),
                  child: Text(po.notes!, style: theme.textTheme.bodySmall),
                ),
            ],
          ),
        ),
        for (final ln in po.lines)
          Padding(
            key: Key('po-line-${ln.id}'),
            padding: const EdgeInsets.fromLTRB(
              AppSpace.s4,
              0,
              AppSpace.s4,
              AppSpace.s2,
            ),
            child: Card(
              margin: EdgeInsets.zero,
              child: Padding(
                padding: const EdgeInsets.all(AppSpace.s3),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(ln.label, style: theme.textTheme.titleSmall),
                    if ((ln.sku ?? '').isNotEmpty)
                      Text(
                        ln.sku!,
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: palette.muted,
                        ),
                      ),
                    Text(
                      l.poLineQty(
                        ln.quantity.toString(),
                        (ln.receivedQuantity - ln.defectiveQuantity).toString(),
                        ln.remaining.toString(),
                      ),
                      style: theme.textTheme.bodySmall,
                    ),
                    if (ln.defectiveQuantity > 0)
                      Text(
                        l.poLineDefective(ln.defectiveQuantity.toString()),
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: palette.danger,
                        ),
                      ),
                    Text(
                      l.poLineCost(
                        money(ln.unitCostMinor),
                        ln.landedUnitCostMinor == null
                            ? '–'
                            : money(ln.landedUnitCostMinor!),
                      ),
                      style: theme.textTheme.bodySmall,
                    ),
                    if (po.belowMoq[ln.variantId] != null)
                      Text(
                        l.poBelowMoq(po.belowMoq[ln.variantId].toString()),
                        key: Key('po-moq-${ln.id}'),
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: palette.warning,
                        ),
                      ),
                  ],
                ),
              ),
            ),
          ),
        if (po.extrasMinor > 0)
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: AppSpace.s4),
            child: Text(
              l.poLandedHint,
              style: theme.textTheme.bodySmall?.copyWith(color: palette.muted),
            ),
          ),
        if (po.receipts.isNotEmpty) ...[
          SectionHeader(l.poReceipts),
          for (final r in po.receipts)
            Padding(
              padding: const EdgeInsets.symmetric(
                horizontal: AppSpace.s4,
                vertical: AppSpace.s1,
              ),
              child: Text(
                [
                  l.poReceiptLine(
                    r.lotCode,
                    r.good.toString(),
                    r.defective.toString(),
                  ),
                  if (r.receivedAt != null)
                    Formatters.date(r.receivedAt!, lang),
                ].join(' · '),
                style: theme.textTheme.bodySmall,
              ),
            ),
        ],
        if (_error != null)
          Padding(
            padding: const EdgeInsets.fromLTRB(
              AppSpace.s4,
              AppSpace.s3,
              AppSpace.s4,
              0,
            ),
            child: Text(
              _error!,
              key: const Key('po-error'),
              style: theme.textTheme.bodyMedium?.copyWith(
                color: palette.danger,
              ),
            ),
          ),
        Padding(
          padding: const EdgeInsets.all(AppSpace.s4),
          child: Wrap(
            spacing: AppSpace.s2,
            runSpacing: AppSpace.s2,
            children: [
              if (po.status == 'draft' && canWrite)
                FilledButton(
                  key: const Key('po-submit'),
                  onPressed:
                      _busy ? null : () => _run(() => _api.submit(po.id)),
                  child: Text(l.poSubmit),
                ),
              if (po.status == 'pending_approval' && canApprove) ...[
                FilledButton(
                  key: const Key('po-approve'),
                  onPressed:
                      _busy ? null : () => _run(() => _api.approve(po.id)),
                  child: Text(l.poApprove),
                ),
                OutlinedButton(
                  key: const Key('po-return'),
                  onPressed: _busy ? null : () => _return(po),
                  child: Text(l.poReturn),
                ),
              ],
              if (po.status == 'approved' && canWrite)
                FilledButton(
                  key: const Key('po-send'),
                  onPressed:
                      _busy ? null : () => _run(() => _api.markSent(po.id)),
                  child: Text(l.poMarkSent),
                ),
              if (po.receivable && canWrite)
                FilledButton.tonal(
                  key: const Key('po-receive'),
                  onPressed: _busy ? null : () => _receive(po),
                  child: Text(l.poReceive),
                ),
              if (po.status != 'draft' && po.status != 'cancelled')
                OutlinedButton.icon(
                  key: const Key('po-copy'),
                  onPressed: () => _copy(po),
                  icon: const Icon(Icons.copy_outlined, size: 18),
                  label: Text(l.poCopyOrder),
                ),
            ],
          ),
        ),
      ],
    );
  }
}

/// Enter what arrived: good and damaged per line, optional lot code (PRO-005).
class ReceiveSheet extends ConsumerStatefulWidget {
  const ReceiveSheet({super.key, required this.po});

  final PurchaseOrder po;

  @override
  ConsumerState<ReceiveSheet> createState() => _ReceiveSheetState();
}

class _ReceiveSheetState extends ConsumerState<ReceiveSheet> {
  /// One key per sheet: a retry replays the same receipt and never stocks twice.
  final String _key = const Uuid().v4();
  final _lot = TextEditingController();
  late final Map<String, (TextEditingController, TextEditingController)> _qty =
      {
        for (final ln in widget.po.lines.where((x) => x.remaining > 0))
          ln.id: (TextEditingController(), TextEditingController()),
      };
  bool _busy = false;
  String? _error;

  @override
  void dispose() {
    _lot.dispose();
    for (final c in _qty.values) {
      c.$1.dispose();
      c.$2.dispose();
    }
    super.dispose();
  }

  int _n(TextEditingController c) => int.tryParse(c.text.trim()) ?? 0;

  Future<void> _save() async {
    final l = AppLocalizations.of(context);
    final lines = [
      for (final e in _qty.entries)
        if (_n(e.value.$1) + _n(e.value.$2) > 0)
          {
            'po_line_id': e.key,
            'quantity': _n(e.value.$1),
            'defective_quantity': _n(e.value.$2),
          },
    ];
    if (lines.isEmpty) {
      setState(() => _error = l.poReceiveEmpty);
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await ref
          .read(procurementApiProvider)
          .receive(
            widget.po.id,
            lines: lines,
            lotCode: _lot.text.trim(),
            idempotencyKey: _key,
          );
      if (mounted) Navigator.pop(context, true);
    } on Object catch (e) {
      final err = asApiError(e);
      if (!mounted) return;
      setState(() {
        _busy = false;
        _error =
            err.code == 'receipt_over_order'
                ? l.poReceiveOver('${err.details['remaining'] ?? '–'}')
                : localizedErrorMessage(l, err);
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final palette = AppPalette.of(context);
    final digits = [FilteringTextInputFormatter.digitsOnly];
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(context).bottom),
      child: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(AppSpace.s4),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(l.poReceiveTitle, style: theme.textTheme.titleMedium),
              const SizedBox(height: AppSpace.s3),
              for (final ln in widget.po.lines.where((x) => x.remaining > 0))
                Padding(
                  padding: const EdgeInsets.only(bottom: AppSpace.s3),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(ln.label, style: theme.textTheme.titleSmall),
                      Text(
                        l.poReceiveLeft(ln.remaining.toString()),
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: palette.muted,
                        ),
                      ),
                      const SizedBox(height: AppSpace.s1),
                      Row(
                        children: [
                          Expanded(
                            child: TextField(
                              key: Key('receive-good-${ln.id}'),
                              controller: _qty[ln.id]!.$1,
                              keyboardType: TextInputType.number,
                              inputFormatters: digits,
                              decoration: InputDecoration(
                                labelText: l.poReceiveGood,
                              ),
                            ),
                          ),
                          const SizedBox(width: AppSpace.s2),
                          Expanded(
                            child: TextField(
                              key: Key('receive-bad-${ln.id}'),
                              controller: _qty[ln.id]!.$2,
                              keyboardType: TextInputType.number,
                              inputFormatters: digits,
                              decoration: InputDecoration(
                                labelText: l.poReceiveDefective,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
              TextField(
                key: const Key('receive-lot'),
                controller: _lot,
                maxLength: 40,
                decoration: InputDecoration(labelText: l.poReceiveLot),
              ),
              if (_error != null)
                Padding(
                  padding: const EdgeInsets.only(bottom: AppSpace.s2),
                  child: Text(
                    _error!,
                    key: const Key('receive-error'),
                    style: theme.textTheme.bodyMedium?.copyWith(
                      color: palette.danger,
                    ),
                  ),
                ),
              SizedBox(
                width: double.infinity,
                child: FilledButton(
                  key: const Key('receive-save'),
                  onPressed: _busy ? null : _save,
                  child: Text(l.poReceiveSave),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ReasonDialog extends StatefulWidget {
  const _ReasonDialog();

  @override
  State<_ReasonDialog> createState() => _ReasonDialogState();
}

class _ReasonDialogState extends State<_ReasonDialog> {
  final _c = TextEditingController();

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return AlertDialog(
      title: Text(l.poReturnTitle),
      content: TextField(
        key: const Key('po-return-reason'),
        controller: _c,
        maxLength: 300,
        decoration: InputDecoration(labelText: l.poReturnReason),
        onChanged: (_) => setState(() {}),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: Text(l.poCancel),
        ),
        FilledButton(
          key: const Key('po-return-confirm'),
          onPressed:
              _c.text.trim().length >= 3
                  ? () => Navigator.pop(context, _c.text.trim())
                  : null,
          child: Text(l.poReturn),
        ),
      ],
    );
  }
}
