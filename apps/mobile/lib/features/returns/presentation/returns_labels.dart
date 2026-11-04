import 'package:flutter/material.dart';

import '../../../core/l10n/gen/app_localizations.dart';
import '../../../design/app_theme.dart';
import '../data/returns_api.dart';

String returnStatusLabel(AppLocalizations l, String s) => switch (s) {
  'approved' => l.returnStatusApproved,
  'rejected' => l.returnStatusRejected,
  'in_transit' => l.returnStatusInTransit,
  'received' => l.returnStatusReceived,
  'inspected' => l.returnStatusInspected,
  'refunded' => l.returnStatusRefunded,
  'exchanged' => l.returnStatusExchanged,
  'closed' => l.returnStatusClosed,
  'cancelled' => l.returnStatusCancelled,
  _ => l.returnStatusRequested,
};

(Color, Color) returnStatusColors(BuildContext context, String s) {
  final p = AppPalette.of(context);
  return switch (s) {
    'requested' => (p.warning, p.warningSoft),
    'refunded' || 'exchanged' => (p.success, p.successSoft),
    'rejected' || 'cancelled' || 'closed' => (p.muted, p.line),
    _ => (p.info, p.infoSoft),
  };
}

String resolutionLabel(AppLocalizations l, String r) =>
    r == 'exchange' ? l.returnResolutionExchange : l.returnResolutionRefund;

String returnReasonLabel(AppLocalizations l, String r) => switch (r) {
  'size_small' => l.returnReasonSizeSmall,
  'size_large' => l.returnReasonSizeLarge,
  'colour_different' => l.returnReasonColourDifferent,
  'quality_defect' => l.returnReasonQualityDefect,
  'damaged_in_transit' => l.returnReasonDamagedInTransit,
  'not_as_described' => l.returnReasonNotAsDescribed,
  'changed_mind' => l.returnReasonChangedMind,
  'late_delivery' => l.returnReasonLateDelivery,
  'wrong_item' => l.returnReasonWrongItem,
  _ => l.returnReasonOther,
};

String conditionLabel(AppLocalizations l, String c) => switch (c) {
  'resellable' => l.returnConditionResellable,
  'damaged' => l.returnConditionDamaged,
  'missing' => l.returnConditionMissing,
  _ => l.returnConditionUsed,
};

String checkLabel(AppLocalizations l, ReturnCheck c) => switch (c.code) {
  'order_delivered' => l.returnCheckOrderDelivered,
  'within_window' =>
    c.windowDays == null
        ? l.returnCheckWindowPlain
        : l.returnCheckWindow(c.windowDays!),
  'not_final_sale' => l.returnCheckFinalSale,
  'evidence' => l.returnCheckEvidence,
  'quantity_available' => l.returnCheckQuantity,
  'resolution_allowed' => l.returnCheckResolution,
  'exchange_same_product' => l.returnCheckExchangeProduct,
  'exchange_in_stock' => l.returnCheckExchangeStock,
  _ => l.returnCheckGeneric,
};

/// Abuse signals are this shop's own facts, shown neutrally (no labels).
String signalLabel(AppLocalizations l, ReturnSignal s) => switch (s.code) {
  'frequent_returns' => l.returnSignalFrequent(s.count ?? 0, s.days ?? 90),
  'high_return_rate' => l.returnSignalRate(
    s.returned ?? 0,
    s.orders ?? 0,
    s.days ?? 180,
  ),
  'high_value' => l.returnSignalValue,
  _ => l.returnSignalGeneric,
};

String refundMethodLabel(AppLocalizations l, String m) => switch (m) {
  'original_payment' => l.refundMethodOriginal,
  'esewa' => l.refundMethodEsewa,
  'khalti' => l.refundMethodKhalti,
  'fonepay' => l.refundMethodFonepay,
  'bank_transfer' => l.refundMethodBank,
  'cash' => l.refundMethodCash,
  _ => l.refundMethodOther,
};

String refundStatusLabel(AppLocalizations l, String s) => switch (s) {
  'pending_approval' => l.refundPending,
  'succeeded' => l.refundStatusSucceeded,
  'failed' => l.refundStatusFailed,
  'rejected' => l.refundStatusRejected,
  _ => l.refundStatusProcessing,
};
