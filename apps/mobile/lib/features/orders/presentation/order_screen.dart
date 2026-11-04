import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/errors/api_error.dart';
import '../../../core/l10n/formatters.dart';
import '../../../core/l10n/gen/app_localizations.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens.g.dart';
import '../../../design/widgets/section_header.dart';
import '../../../design/widgets/state_views.dart';
import '../data/orders_api.dart';
import 'order_labels.dart';

/// One order: what was sold, where it goes, how it's paid, what happened,
/// and the next step(s) the state machine allows.
class OrderScreen extends ConsumerStatefulWidget {
  const OrderScreen({super.key, required this.orderId});

  final String orderId;

  @override
  ConsumerState<OrderScreen> createState() => _OrderScreenState();
}

class _OrderScreenState extends ConsumerState<OrderScreen> {
  bool _busy = false;
  ApiError? _error;

  Future<void> _move(OrderDetail o, String to, {String? reason}) async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await ref
          .read(ordersApiProvider)
          .transition(
            widget.orderId,
            to,
            reason: reason,
            expectedVersion: o.summary.version,
          );
      ref
        ..invalidate(orderProvider(widget.orderId))
        ..invalidate(orderTimelineProvider(widget.orderId));
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(AppLocalizations.of(context).orderUpdated)),
        );
      }
    } on Object catch (e) {
      if (mounted) setState(() => _error = asApiError(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _cancel(OrderDetail o) async {
    final reason = await showDialog<String>(
      context: context,
      builder: (_) => const _CancelDialog(),
    );
    if (reason != null && mounted) await _move(o, 'cancelled', reason: reason);
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final order = ref.watch(orderProvider(widget.orderId));
    return Scaffold(
      appBar: AppBar(
        title: Text(
          order.valueOrNull == null
              ? l.ordersTitle
              : l.orderNumber(order.valueOrNull!.summary.number),
        ),
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          ref
            ..invalidate(orderTimelineProvider(widget.orderId))
            ..invalidate(orderProvider(widget.orderId));
          await ref.read(orderProvider(widget.orderId).future);
        },
        child: ListView(
          padding: const EdgeInsets.only(bottom: AppSpace.s8),
          children: [
            AsyncValueView<OrderDetail>(
              value: order,
              onRetry: () => ref.invalidate(orderProvider(widget.orderId)),
              data: (o) => _body(context, o),
            ),
          ],
        ),
      ),
    );
  }

  Widget _body(BuildContext context, OrderDetail o) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final palette = AppPalette.of(context);
    final lang = Localizations.localeOf(context).languageCode;
    final s = o.summary;
    String money(int minor) => Formatters.money(minor, s.currency, lang);
    final actions =
        s.allowedTransitions.where((t) => t != 'cancelled').toList()..sort(
          (a, b) => (isForwardAction(b) ? 1 : 0) - (isForwardAction(a) ? 1 : 0),
        );
    final review = reviewLabel(l, s.needsReview);
    const pad = EdgeInsets.symmetric(horizontal: AppSpace.s4);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(
            AppSpace.s4,
            AppSpace.s3,
            AppSpace.s4,
            0,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                orderStatusLabel(l, s.status),
                key: const Key('order-status'),
                style: theme.textTheme.titleMedium?.copyWith(
                  color: orderStatusColor(context, s),
                ),
              ),
              if (s.placedAt != null)
                Text(
                  Formatters.dateTime(s.placedAt!, lang),
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: palette.muted,
                  ),
                ),
              if (review != null) ...[
                const SizedBox(height: AppSpace.s2),
                Container(
                  width: double.infinity,
                  padding: const EdgeInsets.all(AppSpace.s3),
                  decoration: BoxDecoration(
                    color: palette.dangerSoft,
                    borderRadius: BorderRadius.circular(AppRadius.md),
                  ),
                  child: Text(review, key: const Key('order-review')),
                ),
              ],
            ],
          ),
        ),
        SectionHeader(l.orderItems),
        for (final line in o.lines)
          ListTile(
            title: Text(
              [
                line.title,
                if (line.variantTitle != null) line.variantTitle!,
              ].join(' · '),
            ),
            subtitle: Text(
              [
                '${line.quantity} × ${money(line.unitPriceMinor)}',
                if (line.cancelledQuantity > 0)
                  l.orderCancelledQty(line.cancelledQuantity),
                if (!line.matched) l.orderUnmatchedItem,
              ].join(' · '),
            ),
            trailing: Text(money(line.lineTotalMinor)),
          ),
        SectionHeader(l.orderTotals),
        Padding(
          padding: pad,
          child: Column(
            children: [
              _Row(l.orderSubtotal, money(o.subtotalMinor)),
              if (o.deliveryFeeMinor > 0)
                _Row(l.orderDelivery, money(o.deliveryFeeMinor)),
              if (o.discountMinor > 0)
                _Row(l.orderDiscount, '-${money(o.discountMinor)}'),
              _Row(l.orderTotal, money(s.totalMinor), bold: true),
            ],
          ),
        ),
        SectionHeader(l.orderPayment),
        Padding(
          padding: pad,
          child: Text(
            '${paymentMethodLabel(l, s.paymentMethod)} · '
            '${paymentStatusLabel(l, s.paymentStatus)}',
            key: const Key('order-payment'),
          ),
        ),
        SectionHeader(l.orderShipTo),
        Padding(
          padding: pad,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                [
                  o.shipping.recipientName,
                  o.shipping.phone,
                ].whereType<String>().join(' · '),
                style: theme.textTheme.titleSmall,
              ),
              if (o.shipping.line.isNotEmpty) Text(o.shipping.line),
              if ((o.shipping.landmark ?? '').isNotEmpty)
                Text(
                  o.shipping.landmark!,
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: palette.muted,
                  ),
                ),
            ],
          ),
        ),
        if ((o.notes ?? '').isNotEmpty) ...[
          SectionHeader(l.orderNotes),
          Padding(padding: pad, child: Text(o.notes!)),
        ],
        if (o.conversationId != null)
          Padding(
            padding: const EdgeInsets.fromLTRB(
              AppSpace.s2,
              AppSpace.s2,
              AppSpace.s4,
              0,
            ),
            child: Align(
              alignment: Alignment.centerLeft,
              child: TextButton.icon(
                onPressed: () => context.push('/inbox/${o.conversationId}'),
                icon: const Icon(Icons.chat_bubble_outline),
                label: Text(l.orderViewChat),
              ),
            ),
          ),
        const SizedBox(height: AppSpace.s4),
        if (_error != null)
          Padding(padding: pad, child: InlineError(error: _error!)),
        Padding(
          padding: const EdgeInsets.all(AppSpace.s4),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              for (final to in actions) ...[
                if (isForwardAction(to))
                  FilledButton(
                    key: Key('order-action-$to'),
                    style: FilledButton.styleFrom(
                      minimumSize: const Size.fromHeight(52),
                    ),
                    onPressed: _busy ? null : () => _move(o, to),
                    child: Text(orderActionLabel(l, to)),
                  )
                else
                  OutlinedButton(
                    key: Key('order-action-$to'),
                    style: OutlinedButton.styleFrom(
                      minimumSize: const Size.fromHeight(48),
                    ),
                    onPressed: _busy ? null : () => _move(o, to),
                    child: Text(orderActionLabel(l, to)),
                  ),
                const SizedBox(height: AppSpace.s2),
              ],
              if (s.allowedTransitions.contains('cancelled'))
                TextButton(
                  key: const Key('order-cancel'),
                  style: TextButton.styleFrom(
                    foregroundColor: palette.danger,
                    minimumSize: const Size.fromHeight(48),
                  ),
                  onPressed: _busy ? null : () => _cancel(o),
                  child: Text(l.orderCancel),
                ),
            ],
          ),
        ),
        SectionHeader(l.orderTimeline),
        _Timeline(orderId: widget.orderId),
      ],
    );
  }
}

class _Row extends StatelessWidget {
  const _Row(this.label, this.value, {this.bold = false});

  final String label;
  final String value;
  final bool bold;

  @override
  Widget build(BuildContext context) {
    final style =
        bold
            ? Theme.of(context).textTheme.titleSmall
            : Theme.of(context).textTheme.bodyMedium;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: AppSpace.s1),
      child: Row(
        children: [
          Expanded(child: Text(label, style: style)),
          Text(value, style: style),
        ],
      ),
    );
  }
}

class _Timeline extends ConsumerWidget {
  const _Timeline({required this.orderId});

  final String orderId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final lang = Localizations.localeOf(context).languageCode;
    final muted = AppPalette.of(context).muted;
    return AsyncValueView<List<OrderEvent>>(
      value: ref.watch(orderTimelineProvider(orderId)),
      onRetry: () => ref.invalidate(orderTimelineProvider(orderId)),
      loading: const SkeletonList(rows: 2),
      data:
          (events) => Column(
            children: [
              for (final e in events.reversed)
                ListTile(
                  dense: true,
                  leading: Icon(
                    e.automated ? Icons.bolt_outlined : Icons.person_outline,
                    size: 20,
                    color: muted,
                  ),
                  title: Text(_eventText(l, e)),
                  subtitle: Text(
                    [
                      if (e.at != null) Formatters.dateTime(e.at!, lang),
                      switch (e.actorType) {
                        'ai' => l.timelineByAi,
                        'user' || 'staff' => e.actorDisplay ?? '',
                        'webhook' => e.provider ?? e.actorDisplay ?? '',
                        _ => l.timelineAutomatic,
                      },
                    ].where((s) => s.isNotEmpty).join(' · '),
                  ),
                ),
            ],
          ),
    );
  }

  String _eventText(AppLocalizations l, OrderEvent e) => switch (e.kind) {
    'created' => l.timelineCreated,
    'imported' => l.timelineImported(e.provider ?? ''),
    'status_changed' => l.timelineStatus(orderStatusLabel(l, e.toStatus ?? '')),
    'lines_cancelled' => l.timelineLinesCancelled,
    'note' => l.timelineNote((e.data['note'] as String?) ?? ''),
    'payment_recorded' => l.timelinePayment,
    'payment_failed' => l.timelinePaymentFailed,
    'payment_mismatch' => l.timelinePaymentMismatch,
    _ => l.timelineOther,
  };
}

class _CancelDialog extends StatefulWidget {
  const _CancelDialog();

  @override
  State<_CancelDialog> createState() => _CancelDialogState();
}

class _CancelDialogState extends State<_CancelDialog> {
  final _reason = TextEditingController();

  @override
  void dispose() {
    _reason.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final palette = AppPalette.of(context);
    return AlertDialog(
      title: Text(l.orderCancelTitle),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(l.orderCancelBody),
          const SizedBox(height: AppSpace.s3),
          TextField(
            key: const Key('cancel-reason'),
            controller: _reason,
            maxLength: 300,
            decoration: InputDecoration(
              labelText: l.orderCancelReason,
              hintText: l.orderCancelReasonHint,
            ),
            onChanged: (_) => setState(() {}),
          ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: Text(l.orderCancelKeep),
        ),
        FilledButton(
          key: const Key('cancel-confirm'),
          style: FilledButton.styleFrom(backgroundColor: palette.danger),
          onPressed:
              _reason.text.trim().length < 2
                  ? null
                  : () => Navigator.of(context).pop(_reason.text.trim()),
          child: Text(l.orderCancelConfirm),
        ),
      ],
    );
  }
}
