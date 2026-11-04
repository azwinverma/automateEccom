import 'package:flutter/material.dart';

import '../../../core/l10n/gen/app_localizations.dart';
import '../../../design/app_theme.dart';

String shipmentStatusLabel(AppLocalizations l, String s) => switch (s) {
  'booked' => l.shipStatusBooked,
  'pickup_requested' => l.shipStatusPickupRequested,
  'picked_up' => l.shipStatusPickedUp,
  'in_transit' => l.shipStatusInTransit,
  'out_for_delivery' => l.shipStatusOutForDelivery,
  'delivered' => l.shipStatusDelivered,
  'delivery_failed' => l.shipStatusDeliveryFailed,
  'reattempt_requested' => l.shipStatusReattemptRequested,
  'returning' => l.shipStatusReturning,
  'returned_to_origin' => l.shipStatusReturnedToOrigin,
  'cancelled' => l.shipStatusCancelled,
  'lost' => l.shipStatusLost,
  _ => l.shipStatusInTransit,
};

const failureReasons = [
  'customer_unreachable',
  'customer_unavailable',
  'customer_refused',
  'address_incorrect',
  'cod_not_ready',
  'rescheduled_by_customer',
  'other',
];

String failureReasonLabel(AppLocalizations l, String? r) => switch (r) {
  'customer_unreachable' => l.failReasonCustomerUnreachable,
  'customer_unavailable' => l.failReasonCustomerUnavailable,
  'customer_refused' => l.failReasonCustomerRefused,
  'address_incorrect' => l.failReasonAddressIncorrect,
  'cod_not_ready' => l.failReasonCodNotReady,
  'rescheduled_by_customer' => l.failReasonRescheduled,
  _ => l.failReasonOther,
};

String recoveryLabel(AppLocalizations l, String s) => switch (s) {
  'open' => l.recoveryOpen,
  'awaiting_customer' => l.recoveryAwaitingCustomer,
  'customer_replied' => l.recoveryCustomerReplied,
  'reattempt_requested' => l.recoveryReattemptRequested,
  'returning' => l.recoveryReturning,
  'escalated' => l.recoveryEscalated,
  _ => l.recoveryResolved,
};

String? recommendationLabel(AppLocalizations l, String? reason) =>
    switch (reason) {
      'default_courier' => l.deliveryWhyDefault,
      'cheapest' => l.deliveryWhyCheapest,
      'only_option' => l.deliveryWhyOnly,
      _ => null,
    };

String settlementStatusLabel(AppLocalizations l, String s) => switch (s) {
  'reconciled' => l.codStatusReconciled,
  'confirmed' => l.codStatusConfirmed,
  _ => l.codStatusNeedsReview,
};

/// (foreground, background) for a shipment status chip.
(Color, Color) shipmentStatusColors(BuildContext context, String s) {
  final p = AppPalette.of(context);
  return switch (s) {
    'delivered' => (p.success, p.successSoft),
    'delivery_failed' || 'lost' => (p.danger, p.dangerSoft),
    'returning' || 'returned_to_origin' || 'cancelled' => (p.muted, p.line),
    'booked' || 'pickup_requested' => (p.warning, p.warningSoft),
    _ => (p.info, p.infoSoft),
  };
}

class StatusChip extends StatelessWidget {
  const StatusChip({super.key, required this.label, required this.colors});

  final String label;
  final (Color, Color) colors;

  @override
  Widget build(BuildContext context) => Container(
    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
    decoration: BoxDecoration(
      color: colors.$2,
      borderRadius: BorderRadius.circular(999),
    ),
    child: Text(
      label,
      style: Theme.of(
        context,
      ).textTheme.labelMedium?.copyWith(color: colors.$1),
    ),
  );
}
