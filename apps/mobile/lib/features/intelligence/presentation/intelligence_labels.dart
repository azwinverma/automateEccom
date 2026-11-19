import '../../../core/l10n/gen/app_localizations.dart';
import '../data/intelligence_api.dart';

String capabilityLabel(AppLocalizations l, String code) => switch (code) {
  'customer_replies' => l.apsCapCustomerReplies,
  'order_capture' => l.apsCapOrderCapture,
  'shipment_creation' => l.apsCapShipmentCreation,
  'pickup_requests' => l.apsCapPickupRequests,
  'delivery_notifications' => l.apsCapDeliveryNotifications,
  'delivery_recovery' => l.apsCapDeliveryRecovery,
  'returns' => l.apsCapReturns,
  'refunds' => l.apsCapRefunds,
  'marketing' => l.apsCapMarketing,
  _ => l.apsCapOther,
};

String exclusionLabel(AppLocalizations l, String reason) => switch (reason) {
  'above_threshold' || 'high_risk' => l.apsExclAboveThreshold,
  'missing_entitlement' => l.apsExclNotInPlan,
  'missing_capability' => l.apsExclNoCapability,
  _ => l.apsExclOther,
};

String _v(Map<String, Object?> vars, String k) {
  final v = vars[k];
  if (v == null) return '–';
  if (v is double) {
    return v == v.roundToDouble() ? v.toInt().toString() : v.toString();
  }
  return v.toString();
}

String _pct(Object? v) {
  final d = (v as num?)?.toDouble();
  return d == null ? '–' : (d * 100).round().toString();
}

/// What the suggestion proposes, in plain words.
String recommendationWhat(AppLocalizations l, Recommendation r) => switch (r
    .what) {
  'lever.set_mode' => l.recSetMode,
  'lever.activate_template' => l.recActivateTemplate,
  'lever.enable_r2' => l.recEnableR2,
  'lever.enable_return_auto_approve' => l.recEnableReturnAuto,
  'lever.enable_customer_notifications' => l.recEnableNotifications,
  'lever.plan_upgrade' => l.recPlanUpgrade,
  'lever.set_courier_selection' => l.recCourierSelection,
  'restock' => l.recRestock(
    [
      _v(r.vars, 'title'),
      if (r.vars['variant'] != null && r.vars['variant'] != 'Default')
        '(${_v(r.vars, 'variant')})',
    ].join(' '),
  ),
  _ => l.recOther,
};

/// Why, from the evidence the backend computed (never new numbers).
String? recommendationWhy(AppLocalizations l, Recommendation r) => switch (r
    .why) {
  'manual_gap' => l.recWhyManualGap(
    _v(r.vars, 'manual'),
    _v(r.vars, 'eligible'),
    capabilityLabel(l, _v(r.vars, 'capability')).toLowerCase(),
  ),
  'better_route_courier' => l.recWhyCourier(
    _pct(r.vars['their_success']),
    _pct(r.vars['default_success']),
    _v(r.vars, 'destination'),
    _v(r.vars, 'their_n'),
  ),
  'selling_low_stock' => l.recWhyRestock(
    _v(r.vars, 'sold_30d'),
    _v(r.vars, 'available'),
    _v(r.vars, 'cover_days'),
  ),
  _ => null,
};

String? recommendationImpact(AppLocalizations l, Recommendation r) {
  final to = r.impact['score_to'];
  if (to is num) return l.recImpactScore('${(to * 100).round()}%');
  final pts = r.impact['success_gain_points'];
  if (pts is num) return l.recImpactCourier(pts.toString());
  return null;
}

String riskLevelLabel(AppLocalizations l, String level) => switch (level) {
  'HIGHER' => l.riskLevelHigher,
  'MEDIUM' => l.riskLevelMedium,
  _ => l.riskLevelLow,
};

String riskActionLabel(AppLocalizations l, String action) => switch (action) {
  'verify_phone' => l.riskActionVerifyPhone,
  'request_partial_advance' => l.riskActionPartialAdvance,
  'manual_review' => l.riskActionManualReview,
  _ => l.riskActionOk,
};

/// Null for a factor this app version doesn't know (skipped, never a raw code).
String? riskFactorLabel(AppLocalizations l, RiskFactor f) {
  final e = f.evidence;
  return switch (f.code) {
    'delivery_history' => l.riskFactorHistory(
      _v(e, 'delivered'),
      _v(e, 'failed'),
    ),
    'new_customer' => l.riskFactorNewCustomer,
    'return_history' => l.riskFactorReturns(_v(e, 'returns')),
    'address_completeness' =>
      e['complete'] == false
          ? l.riskFactorAddressMissing
          : l.riskFactorAddressPartial,
    'order_value' => l.riskFactorOrderValue(_v(e, 'ratio')),
    'route_failures' => l.riskFactorRoute(
      _pct(e['failed_rate']),
      _v(e, 'district'),
    ),
    _ => null,
  };
}
