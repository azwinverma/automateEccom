import 'package:flutter/material.dart';

import '../../../core/l10n/gen/app_localizations.dart';
import '../../../design/app_theme.dart';
import '../data/orders_api.dart';

String orderStatusLabel(AppLocalizations l, String status) => switch (status) {
  'draft' => l.orderStatusDraft,
  'pending_confirmation' => l.orderStatusPendingConfirmation,
  'confirmed' => l.orderStatusConfirmed,
  'payment_pending' => l.orderStatusPaymentPending,
  'cod_pending' => l.orderStatusCodPending,
  'ready_to_ship' => l.orderStatusReadyToShip,
  'shipped' => l.orderStatusShipped,
  'delivered' => l.orderStatusDelivered,
  'completed' => l.orderStatusCompleted,
  'cancelled' => l.orderStatusCancelled,
  'delivery_failed' => l.orderStatusDeliveryFailed,
  'returned' => l.orderStatusReturned,
  _ => status,
};

/// The button label for moving an order to [to]. Cancelling is a separate,
/// confirmed action and never appears here.
String orderActionLabel(AppLocalizations l, String to) => switch (to) {
  'confirmed' => l.orderActionConfirm,
  'ready_to_ship' => l.orderActionReadyToShip,
  'shipped' => l.orderActionShipped,
  'delivered' => l.orderActionDelivered,
  'completed' => l.orderActionCompleted,
  'delivery_failed' => l.orderActionDeliveryFailed,
  'returned' => l.orderActionReturned,
  _ => orderStatusLabel(l, to),
};

/// Forward (happy-path) moves get the filled button; detours are outlined.
bool isForwardAction(String to) => const {
  'confirmed',
  'ready_to_ship',
  'shipped',
  'delivered',
  'completed',
}.contains(to);

String paymentStatusLabel(AppLocalizations l, String status) =>
    switch (status) {
      'unpaid' => l.payStatusUnpaid,
      'pending' => l.payStatusPending,
      'paid' => l.payStatusPaid,
      'failed' => l.payStatusFailed,
      'refunded' => l.payStatusRefunded,
      'cod_pending' => l.payStatusCodPending,
      'cod_collected' => l.payStatusCodCollected,
      _ => status,
    };

String paymentMethodLabel(AppLocalizations l, String method) =>
    method == 'cod' ? l.paymentCod : l.paymentPrepaid;

String? reviewLabel(AppLocalizations l, String? needsReview) =>
    switch (needsReview) {
      null => null,
      'payment_mismatch' => l.orderReviewPaymentMismatch,
      'paid_after_cancel' => l.orderReviewPaidAfterCancel,
      'stock_short' => l.orderReviewStockShort,
      'unmatched_items' => l.orderReviewUnmatched,
      'address_incomplete' => l.orderReviewAddress,
      final other => other,
    };

/// Status colour: done = success, problems = danger, waiting = warning.
Color orderStatusColor(BuildContext context, OrderSummary o) {
  final p = AppPalette.of(context);
  if (o.needsReview != null) return p.danger;
  return switch (o.status) {
    'delivered' || 'completed' => p.success,
    'cancelled' || 'returned' => p.muted,
    'delivery_failed' => p.danger,
    'shipped' => p.info,
    _ => p.warning,
  };
}
