import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:uuid/uuid.dart';

import '../../../core/errors/api_error.dart';
import '../../../core/l10n/formatters.dart';
import '../../../core/l10n/gen/app_localizations.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens.g.dart';
import '../../../design/widgets/section_header.dart';
import '../../../design/widgets/state_views.dart';
import '../../orders/data/orders_api.dart';
import '../data/fulfillment_api.dart';
import 'fulfillment_labels.dart';

const _bookable = {'cod_pending', 'ready_to_ship'};

/// Order detail "Delivery": book a courier (no shipment yet) or follow the
/// parcel and act on it. What the seller may do comes from the server
/// (`shipment.actions`); a refusal (e.g. no permission) is shown inline.
class DeliverySection extends ConsumerStatefulWidget {
  const DeliverySection({super.key, required this.order});

  final OrderDetail order;

  @override
  ConsumerState<DeliverySection> createState() => _DeliverySectionState();
}

class _DeliverySectionState extends ConsumerState<DeliverySection> {
  bool _busy = false;
  ApiError? _error;

  String get _orderId => widget.order.summary.id;

  void _refreshAll() {
    ref
      ..invalidate(orderShipmentsProvider(_orderId))
      ..invalidate(orderProvider(_orderId))
      ..invalidate(orderTimelineProvider(_orderId));
  }

  Future<bool> _run(Future<void> Function() action, String done) async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await action();
      _refreshAll();
      if (mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(done)));
      }
      return true;
    } on Object catch (e) {
      if (mounted) setState(() => _error = asApiError(e));
      return false;
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final shipments = ref.watch(orderShipmentsProvider(_orderId));
    return shipments.when(
      skipLoadingOnRefresh: false,
      loading: () => const SizedBox.shrink(),
      // Fulfillment not readable (permission/older server): the rest of the
      // order still works, so the section simply stays out of the way.
      error: (_, __) => const SizedBox.shrink(),
      data: (items) {
        final live = items.isEmpty ? null : items.first;
        final canBook =
            (live == null || live.status == 'cancelled') &&
            _bookable.contains(widget.order.summary.status);
        if (live == null && !canBook) return const SizedBox.shrink();
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            SectionHeader(l.deliveryTitle, key: const Key('delivery-section')),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: AppSpace.s4),
                child: InlineError(error: _error!),
              ),
            if (canBook)
              _BookCourier(
                orderId: _orderId,
                currency: widget.order.summary.currency,
                busy: _busy,
                onBook: (book) => _run(book, l.deliveryBooked),
              )
            else
              _ShipmentView(
                shipment: live!,
                busy: _busy,
                onAction: (a) => _run(a, l.deliveryUpdated),
              ),
          ],
        );
      },
    );
  }
}

class _BookCourier extends ConsumerStatefulWidget {
  const _BookCourier({
    required this.orderId,
    required this.currency,
    required this.busy,
    required this.onBook,
  });

  final String orderId;
  final String currency;
  final bool busy;
  final Future<bool> Function(Future<void> Function()) onBook;

  @override
  ConsumerState<_BookCourier> createState() => _BookCourierState();
}

class _BookCourierState extends ConsumerState<_BookCourier> {
  String? _selected;

  /// One key per booking attempt: retrying after a timeout replays the same
  /// booking instead of creating a second one with the courier.
  String _key = const Uuid().v4();
  final _tracking = TextEditingController();
  final _courierName = TextEditingController();

  @override
  void dispose() {
    _tracking.dispose();
    _courierName.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final palette = AppPalette.of(context);
    final lang = Localizations.localeOf(context).languageCode;
    return AsyncValueView<CourierOptions>(
      value: ref.watch(courierOptionsProvider(widget.orderId)),
      onRetry: () => ref.invalidate(courierOptionsProvider(widget.orderId)),
      loading: const SkeletonList(rows: 2),
      data: (opts) {
        if (opts.options.isEmpty) {
          return Padding(
            padding: const EdgeInsets.symmetric(horizontal: AppSpace.s4),
            child: Text(l.deliveryNoCouriers, key: const Key('delivery-none')),
          );
        }
        final selectedKey =
            _selected ??
            (opts.options.where((o) => o.recommended).firstOrNull ??
                    opts.options.first)
                .key;
        final selected = opts.options.firstWhere(
          (o) => o.key == selectedKey,
          orElse: () => opts.options.first,
        );
        final why = recommendationLabel(l, opts.recommendationReason);
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: AppSpace.s4),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    l.deliveryChooseCourier,
                    style: theme.textTheme.bodyMedium,
                  ),
                  if (why != null)
                    Text(
                      why,
                      key: const Key('delivery-why'),
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: palette.muted,
                      ),
                    ),
                  if (opts.codAmountMinor > 0)
                    Text(
                      l.deliveryCollectAmount(
                        Formatters.money(
                          opts.codAmountMinor,
                          widget.currency,
                          lang,
                        ),
                      ),
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: palette.muted,
                      ),
                    ),
                ],
              ),
            ),
            Column(
              children: [
                for (final o in opts.options)
                  RadioListTile<String>(
                    key: Key('courier-option-${o.key}'),
                    value: o.key,
                    groupValue: selected.key,
                    onChanged: (v) => setState(() => _selected = v),
                    title: Row(
                      children: [
                        Flexible(
                          child: Text(
                            [
                              o.displayName,
                              if (o.serviceCode != null) o.serviceCode!,
                            ].join(' · '),
                          ),
                        ),
                        if (o.recommended) ...[
                          const SizedBox(width: AppSpace.s2),
                          StatusChip(
                            label: l.deliveryRecommended,
                            colors: (palette.success, palette.successSoft),
                          ),
                        ],
                      ],
                    ),
                    subtitle: Text(
                      o.manual
                          ? l.deliveryOwnRider
                          : [
                            if (o.priceMinor != null)
                              Formatters.money(
                                o.priceMinor!,
                                widget.currency,
                                lang,
                              ),
                            if (o.etaMin != null && o.etaMax != null)
                              l.deliveryEta(o.etaMin!, o.etaMax!),
                          ].join(' · '),
                    ),
                  ),
              ],
            ),
            if (selected.manual)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: AppSpace.s4),
                child: Column(
                  children: [
                    TextField(
                      key: const Key('delivery-tracking'),
                      controller: _tracking,
                      maxLength: 80,
                      decoration: InputDecoration(
                        labelText: l.deliveryTrackingOptional,
                      ),
                    ),
                    TextField(
                      key: const Key('delivery-courier-name'),
                      controller: _courierName,
                      maxLength: 80,
                      decoration: InputDecoration(
                        labelText: l.deliveryCourierNameOptional,
                      ),
                    ),
                  ],
                ),
              ),
            Padding(
              padding: const EdgeInsets.all(AppSpace.s4),
              child: FilledButton(
                key: const Key('delivery-book'),
                style: FilledButton.styleFrom(
                  minimumSize: const Size.fromHeight(52),
                ),
                onPressed:
                    widget.busy
                        ? null
                        : () async {
                          final ok = await widget.onBook(
                            () => ref
                                .read(fulfillmentApiProvider)
                                .book(
                                  widget.orderId,
                                  courierAccountId: selected.courierAccountId,
                                  serviceCode: selected.serviceCode,
                                  idempotencyKey: _key,
                                  trackingNumber:
                                      selected.manual
                                          ? _tracking.text.trim()
                                          : null,
                                  courierName:
                                      selected.manual
                                          ? _courierName.text.trim()
                                          : null,
                                ),
                          );
                          if (ok && mounted) {
                            setState(() => _key = const Uuid().v4());
                          }
                        },
                child: Text(l.deliveryBook),
              ),
            ),
          ],
        );
      },
    );
  }
}

class _ShipmentView extends ConsumerWidget {
  const _ShipmentView({
    required this.shipment,
    required this.busy,
    required this.onAction,
  });

  final Shipment shipment;
  final bool busy;
  final Future<bool> Function(Future<void> Function()) onAction;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final palette = AppPalette.of(context);
    final lang = Localizations.localeOf(context).languageCode;
    final s = shipment;
    final api = ref.read(fulfillmentApiProvider);
    const pad = EdgeInsets.symmetric(horizontal: AppSpace.s4);

    Future<void> act(String action) async {
      switch (action) {
        case 'request_pickup':
          await onAction(() => api.requestPickup(s.id));
        case 'refresh':
          await onAction(() => api.refresh(s.id));
        case 'confirm_received_back':
          await onAction(() => api.receivedBack(s.id));
        case 'cancel':
          if (await _confirm(
            context,
            l.deliveryCancelTitle,
            l.deliveryCancelBody,
          )) {
            await onAction(() => api.cancel(s.id));
          }
        case 'return_to_sender':
          if (await _confirm(
            context,
            l.deliveryReturnTitle,
            l.deliveryReturnBody,
          )) {
            await onAction(() => api.returnToSender(s.id));
          }
        case 'reattempt':
          final note = await showDialog<String>(
            context: context,
            builder: (_) => const _ReattemptDialog(),
          );
          if (note != null) await onAction(() => api.reattempt(s.id, note));
        case 'update_status':
          final r = await showModalBottomSheet<_StatusChoice>(
            context: context,
            isScrollControlled: true,
            builder: (_) => ManualStatusSheet(current: s.status),
          );
          if (r != null) {
            await onAction(
              () => api.setStatus(
                s.id,
                r.status,
                failureReason: r.failureReason,
                note: r.note,
              ),
            );
          }
      }
    }

    final actions = [
      for (final a in const [
        'reattempt',
        'request_pickup',
        'update_status',
        'confirm_received_back',
        'refresh',
        'return_to_sender',
        'cancel',
      ])
        if (s.actions.contains(a)) a,
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: pad,
          child: Row(
            children: [
              Expanded(
                child: Text(s.courierName, style: theme.textTheme.titleSmall),
              ),
              StatusChip(
                key: const Key('shipment-status'),
                label: shipmentStatusLabel(l, s.status),
                colors: shipmentStatusColors(context, s.status),
              ),
            ],
          ),
        ),
        if (s.trackingNumber != null)
          Padding(
            padding: const EdgeInsets.only(left: AppSpace.s4),
            child: Row(
              children: [
                Expanded(child: Text(l.deliveryTracking(s.trackingNumber!))),
                IconButton(
                  key: const Key('shipment-copy'),
                  tooltip: l.deliveryCopy,
                  icon: const Icon(Icons.copy_outlined, size: 20),
                  onPressed: () async {
                    await Clipboard.setData(
                      ClipboardData(text: s.trackingNumber!),
                    );
                    if (context.mounted) {
                      ScaffoldMessenger.of(
                        context,
                      ).showSnackBar(SnackBar(content: Text(l.deliveryCopied)));
                    }
                  },
                ),
              ],
            ),
          ),
        Padding(
          padding: pad,
          child: Text(
            s.codAmountMinor > 0
                ? l.deliveryCod(
                  Formatters.money(s.codAmountMinor, s.currency, lang),
                )
                : l.deliveryNothingToCollect,
            style: theme.textTheme.bodySmall?.copyWith(color: palette.muted),
          ),
        ),
        for (final a in s.attempts.reversed)
          Container(
            key: Key('attempt-${a.attemptNo}'),
            margin: const EdgeInsets.fromLTRB(
              AppSpace.s4,
              AppSpace.s3,
              AppSpace.s4,
              0,
            ),
            padding: const EdgeInsets.all(AppSpace.s3),
            decoration: BoxDecoration(
              color:
                  a.recoveryStatus == 'resolved'
                      ? palette.line
                      : palette.dangerSoft,
              borderRadius: BorderRadius.circular(AppRadius.md),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  l.deliveryAttempt(
                    a.attemptNo,
                    failureReasonLabel(l, a.failureReason),
                  ),
                  style: theme.textTheme.titleSmall,
                ),
                Text(recoveryLabel(l, a.recoveryStatus)),
                if ((a.customerReply ?? '').isNotEmpty)
                  Text(
                    l.deliveryCustomerReply(a.customerReply!),
                    style: theme.textTheme.bodySmall,
                  ),
              ],
            ),
          ),
        if (actions.isNotEmpty)
          Padding(
            padding: const EdgeInsets.all(AppSpace.s4),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                for (final (i, a) in actions.indexed) ...[
                  _actionButton(
                    l,
                    palette,
                    a,
                    primary: i == 0,
                    onTap: () => act(a),
                  ),
                  const SizedBox(height: AppSpace.s2),
                ],
              ],
            ),
          ),
        if (s.events.isNotEmpty) ...[
          Padding(
            padding: const EdgeInsets.fromLTRB(
              AppSpace.s4,
              AppSpace.s2,
              AppSpace.s4,
              0,
            ),
            child: Text(l.deliveryHistory, style: theme.textTheme.labelLarge),
          ),
          for (final e in s.events.reversed)
            ListTile(
              key: Key('shipment-event-${e.id}'),
              dense: true,
              enabled: e.applied,
              leading: Icon(
                e.applied ? Icons.local_shipping_outlined : Icons.history,
                size: 20,
                color: palette.muted,
              ),
              title: Text(
                [
                  shipmentStatusLabel(l, e.status),
                  if (e.failureReason != null)
                    failureReasonLabel(l, e.failureReason),
                ].join(' · '),
              ),
              subtitle: Text(
                [
                  if (e.occurredAt != null)
                    Formatters.dateTime(e.occurredAt!, lang),
                  if ((e.location ?? '').isNotEmpty) e.location!,
                  if (!e.applied) l.deliveryLateUpdate,
                ].join(' · '),
              ),
            ),
        ],
      ],
    );
  }

  Widget _actionButton(
    AppLocalizations l,
    AppPalette palette,
    String a, {
    required bool primary,
    required VoidCallback onTap,
  }) {
    final label = switch (a) {
      'request_pickup' => l.deliveryActionPickup,
      'cancel' => l.deliveryActionCancel,
      'reattempt' => l.deliveryActionReattempt,
      'return_to_sender' => l.deliveryActionReturn,
      'confirm_received_back' => l.deliveryActionReceivedBack,
      'update_status' => l.deliveryActionUpdateStatus,
      _ => l.deliveryActionRefresh,
    };
    final key = Key('shipment-action-$a');
    if (a == 'cancel') {
      return TextButton(
        key: key,
        style: TextButton.styleFrom(
          foregroundColor: palette.danger,
          minimumSize: const Size.fromHeight(48),
        ),
        onPressed: busy ? null : onTap,
        child: Text(label),
      );
    }
    return primary
        ? FilledButton(
          key: key,
          style: FilledButton.styleFrom(minimumSize: const Size.fromHeight(52)),
          onPressed: busy ? null : onTap,
          child: Text(label),
        )
        : OutlinedButton(
          key: key,
          style: OutlinedButton.styleFrom(
            minimumSize: const Size.fromHeight(48),
          ),
          onPressed: busy ? null : onTap,
          child: Text(label),
        );
  }
}

Future<bool> _confirm(BuildContext context, String title, String body) async {
  final l = AppLocalizations.of(context);
  final ok = await showDialog<bool>(
    context: context,
    builder:
        (ctx) => AlertDialog(
          title: Text(title),
          content: Text(body),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(ctx).pop(false),
              child: Text(l.deliveryKeep),
            ),
            FilledButton(
              key: const Key('delivery-confirm'),
              onPressed: () => Navigator.of(ctx).pop(true),
              child: Text(l.deliveryConfirm),
            ),
          ],
        ),
  );
  return ok ?? false;
}

class _ReattemptDialog extends StatefulWidget {
  const _ReattemptDialog();

  @override
  State<_ReattemptDialog> createState() => _ReattemptDialogState();
}

class _ReattemptDialogState extends State<_ReattemptDialog> {
  final _note = TextEditingController();

  @override
  void dispose() {
    _note.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return AlertDialog(
      title: Text(l.deliveryReattemptTitle),
      content: TextField(
        key: const Key('reattempt-note'),
        controller: _note,
        maxLength: 500,
        maxLines: 3,
        decoration: InputDecoration(labelText: l.deliveryReattemptNote),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: Text(l.deliveryKeep),
        ),
        FilledButton(
          key: const Key('reattempt-send'),
          onPressed: () => Navigator.of(context).pop(_note.text.trim()),
          child: Text(l.deliverySend),
        ),
      ],
    );
  }
}

class _StatusChoice {
  const _StatusChoice(this.status, this.failureReason, this.note);

  final String status;
  final String? failureReason;
  final String? note;
}

/// Own rider / courier without an API: the seller records what happened.
/// A failed delivery needs a reason (it drives recovery and later learning).
class ManualStatusSheet extends StatefulWidget {
  const ManualStatusSheet({super.key, required this.current});

  final String current;

  @override
  State<ManualStatusSheet> createState() => _ManualStatusSheetState();
}

class _ManualStatusSheetState extends State<ManualStatusSheet> {
  static const _statuses = [
    'picked_up',
    'in_transit',
    'out_for_delivery',
    'delivered',
    'delivery_failed',
  ];
  String? _status;
  String? _reason;
  final _note = TextEditingController();

  @override
  void dispose() {
    _note.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final needsReason = _status == 'delivery_failed';
    final ready = _status != null && (!needsReason || _reason != null);
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
              Text(l.deliveryStatusTitle, style: theme.textTheme.titleMedium),
              const SizedBox(height: AppSpace.s2),
              Wrap(
                spacing: AppSpace.s2,
                runSpacing: AppSpace.s2,
                children: [
                  for (final st in _statuses)
                    if (st != widget.current)
                      ChoiceChip(
                        key: Key('manual-status-$st'),
                        label: Text(shipmentStatusLabel(l, st)),
                        selected: _status == st,
                        onSelected: (_) => setState(() => _status = st),
                      ),
                ],
              ),
              if (needsReason) ...[
                const SizedBox(height: AppSpace.s4),
                Text(
                  l.deliveryFailureReason,
                  style: theme.textTheme.titleSmall,
                ),
                for (final r in failureReasons)
                  RadioListTile<String>(
                    key: Key('manual-reason-$r'),
                    value: r,
                    groupValue: _reason,
                    onChanged: (v) => setState(() => _reason = v),
                    title: Text(failureReasonLabel(l, r)),
                  ),
                if (_reason == null)
                  Text(
                    l.deliveryReasonRequired,
                    key: const Key('manual-reason-required'),
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: AppPalette.of(context).danger,
                    ),
                  ),
              ],
              TextField(
                controller: _note,
                maxLength: 500,
                decoration: InputDecoration(labelText: l.deliveryNote),
              ),
              FilledButton(
                key: const Key('manual-status-save'),
                style: FilledButton.styleFrom(
                  minimumSize: const Size.fromHeight(52),
                ),
                onPressed:
                    ready
                        ? () => Navigator.of(context).pop(
                          _StatusChoice(
                            _status!,
                            needsReason ? _reason : null,
                            _note.text.trim(),
                          ),
                        )
                        : null,
                child: Text(l.deliverySave),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
