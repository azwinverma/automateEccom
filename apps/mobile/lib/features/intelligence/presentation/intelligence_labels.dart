import '../../../core/l10n/formatters.dart';
import '../../../core/l10n/gen/app_localizations.dart';
import '../../returns/presentation/returns_labels.dart';
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
  'fit_note_size_small' => l.recFitNoteSmall(_v(r.vars, 'title')),
  'fit_note_size_large' => l.recFitNoteLarge(_v(r.vars, 'title')),
  'review_colour_different' => l.recReviewPhotos(_v(r.vars, 'title')),
  'review_not_as_described' => l.recReviewDescription(_v(r.vars, 'title')),
  'review_quality_defect' ||
  'review_wrong_item' => l.recReviewQuality(_v(r.vars, 'title')),
  'review_damaged_in_transit' => l.recReviewPacking(_v(r.vars, 'title')),
  final w when w.startsWith('review_') && r.type == 'return_prevention' => l
      .recReviewReturns(_v(r.vars, 'title')),
  'review_price_or_cost' => l.recReviewPrice(_v(r.vars, 'title')),
  'add_cost' => l.recAddCost(_v(r.vars, 'title')),
  final w when w.startsWith('creative_') && r.type == 'creative_tip' => l
      .recCreative(
        creativePatternLabel(
          l,
          w.substring('creative_'.length),
          _v(r.vars, 'value'),
        ),
      ),
  _ => l.recOther,
};

String _money(AppLocalizations l, Object? minor) =>
    minor is num ? Formatters.money(minor.toInt(), 'NPR', l.localeName) : '–';

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
  'return_pattern' => [
    r.vars['baseline_pct'] == null
        ? l.recWhyReturnsNoBase(
          _v(r.vars, 'returned'),
          _v(r.vars, 'sold'),
          _v(r.vars, 'rate_pct'),
        )
        : l.recWhyReturns(
          _v(r.vars, 'returned'),
          _v(r.vars, 'sold'),
          _v(r.vars, 'rate_pct'),
          _v(r.vars, 'baseline_pct'),
        ),
    if (r.vars['reason'] is String && r.vars['share_pct'] != null)
      l.recWhyReturnsReason(
        _v(r.vars, 'share_pct'),
        returnReasonLabel(l, r.vars['reason']! as String).toLowerCase(),
      ),
  ].join(' '),
  'losing_money' => l.recWhyLosing(
    _money(l, (r.vars['contribution'] as num?)?.abs()),
    _v(r.vars, 'units'),
  ),
  'cost_not_set' => l.recWhyCostNotSet(_v(r.vars, 'units')),
  'creative_pattern' =>
    r.vars['outcome'] == 'inquiries'
        ? l.recWhyCreativeInquiries(_v(r.vars, 'lift_pct'), _v(r.vars, 'n'))
        : l.recWhyCreativeOrders(_v(r.vars, 'lift_pct'), _v(r.vars, 'n')),
  _ => null,
};

String? recommendationImpact(AppLocalizations l, Recommendation r) {
  final c30 = r.impact['contribution_30d_minor'];
  if (c30 is num && c30 > 0) return l.recImpactContribution(_money(l, c30));
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

String stockRiskLabel(AppLocalizations l, String risk) => switch (risk) {
  'out' => l.pbRiskOut,
  'high' => l.pbRiskHigh,
  'medium' => l.pbRiskMedium,
  _ => l.pbRiskLow,
};

/// Plain sentence for a "not included" reason; unknown codes get a generic line.
String notIncludedLabel(AppLocalizations l, String reason) => switch (reason) {
  'needs_content_metrics' => l.niNeedsContentMetrics,
  'needs_12_months' => l.niNeeds12Months,
  'no_promotions' => l.niNoPromotions,
  'not_enough_days_in_stock' => l.niNotEnoughDaysInStock,
  'no_sales' => l.niNoSales,
  'stock_not_tracked' => l.niStockNotTracked,
  'cost_not_set' => l.niCostNotSet,
  'not_enough_sales' => l.niNotEnoughSales,
  'no_delivered_sales' => l.niNoDeliveredSales,
  _ => l.niOther,
};

String profitComponentLabel(AppLocalizations l, String code) => switch (code) {
  'packaging' => l.pcPackaging,
  'ads' => l.pcAds,
  'cogs' => l.pcCogs,
  'payment_fees' => l.pcPaymentFees,
  'channel_fees' => l.pcChannelFees,
  'courier' => l.pcCourier,
  'return_shipping' => l.pcReturnShipping,
  'failed_delivery' => l.pcFailedDelivery,
  _ => l.pcOther,
};

String _num(Object? v) {
  if (v is num) {
    return v == v.roundToDouble() ? v.toInt().toString() : v.toString();
  }
  return v?.toString() ?? '–';
}

/// One sentence per fact type, from the fact's own values.
String memoryFactLabel(AppLocalizations l, MemoryFact f) {
  final v = f.value;
  final title = f.subjectLabel ?? f.subjectId;
  return switch (f.factType) {
    'fit_runs_small' => l.memFitSmall(
      title,
      _pct(v['share']),
      _num(v['returns']),
      _num(v['sold']),
    ),
    'fit_runs_large' => l.memFitLarge(
      title,
      _pct(v['share']),
      _num(v['returns']),
      _num(v['sold']),
    ),
    'repeat_cycle_days' => l.memRepeatCycle(
      _num(v['days']),
      _num(v['customers']),
    ),
    'peak_order_hours' => l.memPeakHours(
      _num(v['start_hour']),
      _num(v['end_hour']),
      _pct(v['share']),
    ),
    'best_courier_route' => l.memBestCourier(
      _num(v['courier']),
      _capitalise(f.subjectId),
      _pct(v['success']),
      _num(v['n']),
    ),
    _ => l.memOther,
  };
}

String _capitalise(String s) =>
    s.isEmpty ? s : s[0].toUpperCase() + s.substring(1);

/// A creative attribute value as a plain phrase ("Captions mixing Nepali
/// and English"). Unknown codes fall back to a generic label.
String creativePatternLabel(
  AppLocalizations l,
  String attribute,
  String value,
) => l.cgPattern('${attribute}__$value');

String creativeLiftLabel(AppLocalizations l, double lift, String outcome) {
  final pct = (lift * 100).round().toString();
  return outcome == 'inquiries' ? l.cgLiftInquiries(pct) : l.cgLiftOrders(pct);
}

String creativeConfidenceLabel(AppLocalizations l, String c) => switch (c) {
  'high' => l.cgConfHigh,
  'medium' => l.cgConfMedium,
  _ => l.cgConfLow,
};
