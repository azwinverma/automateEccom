import 'package:flutter/material.dart';

import '../../../core/l10n/gen/app_localizations.dart';
import '../../../design/app_theme.dart';

String poStatusLabel(AppLocalizations l, String s) => switch (s) {
  'draft' => l.poStatusDraft,
  'pending_approval' => l.poStatusPending,
  'approved' => l.poStatusApproved,
  'sent' => l.poStatusSent,
  'partially_received' => l.poStatusPartial,
  'received' => l.poStatusReceived,
  'cancelled' => l.poStatusCancelled,
  _ => s,
};

(Color, Color) poStatusColors(BuildContext context, String s) {
  final p = AppPalette.of(context);
  return switch (s) {
    'pending_approval' => (p.warning, p.warningSoft),
    'received' => (p.success, p.successSoft),
    'cancelled' || 'draft' => (p.muted, p.line),
    _ => (p.info, p.infoSoft),
  };
}

/// Why a PO waits; null when it doesn't.
String? poApprovalLabel(AppLocalizations l, String status, String? reason) {
  if (status != 'pending_approval') return null;
  return reason == 'above_threshold'
      ? l.poApprovalAbove
      : l.poApprovalNeedsApprover;
}

/// "Not included" codes from supplier performance, in words (unknown codes skipped).
String? supplierNotIncludedLabel(AppLocalizations l, String code) =>
    switch (code) {
      'courier' => l.supNiCourier,
      'packaging' => l.supNiPackaging,
      'payment_fees' => l.supNiPayment,
      'return_shipping' => l.supNiReturnShipping,
      'no_sales' => l.supNiNoSales,
      _ => null,
    };
