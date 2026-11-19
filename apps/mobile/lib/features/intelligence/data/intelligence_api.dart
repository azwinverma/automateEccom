import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/api_call.dart';
import '../../../core/api/providers.dart';

int _int(Object? v) => (v as num?)?.toInt() ?? 0;

/// One Autopilot Score capability: A automated, F failed, M by a person,
/// X excluded (with reasons). `score` is null when there's too little
/// activity: shown as "not enough activity", never 0% or 100%.
@immutable
class CapabilityScore {
  const CapabilityScore({
    required this.code,
    required this.automated,
    required this.failed,
    required this.manual,
    required this.excludedCount,
    required this.excluded,
    required this.score,
    required this.enoughActivity,
  });

  factory CapabilityScore.fromJson(String code, Map<String, Object?> j) =>
      CapabilityScore(
        code: code,
        automated: _int(j['A']),
        failed: _int(j['F']),
        manual: _int(j['M']),
        excludedCount: _int(j['X']),
        excluded: {
          for (final e
              in ((j['excluded'] as Map<String, Object?>?) ?? const {}).entries)
            e.key: _int(e.value),
        },
        score: (j['score'] as num?)?.toDouble(),
        enoughActivity: (j['status'] as String?) == 'ok',
      );

  final String code;
  final int automated;
  final int failed;
  final int manual;
  final int excludedCount;
  final Map<String, int> excluded;
  final double? score;
  final bool enoughActivity;
}

@immutable
class AutopilotScore {
  const AutopilotScore({
    required this.windowDays,
    required this.overall,
    required this.capabilities,
    required this.hoursSaved,
  });

  factory AutopilotScore.fromJson(Map<String, Object?> j) {
    final caps = (j['capabilities'] as Map<String, Object?>?) ?? const {};
    return AutopilotScore(
      windowDays: _int(j['window_days']),
      overall: (j['overall'] as num?)?.toDouble(),
      hoursSaved: (j['hours_saved_estimate'] as num?)?.toDouble() ?? 0,
      capabilities: [
        for (final e in caps.entries)
          if (e.value is Map<String, Object?>)
            CapabilityScore.fromJson(e.key, e.value! as Map<String, Object?>),
      ],
    );
  }

  final int windowDays;
  final double? overall;
  final List<CapabilityScore> capabilities;
  final double hoursSaved;
}

@immutable
class Recommendation {
  const Recommendation({
    required this.id,
    required this.type,
    required this.what,
    required this.why,
    required this.vars,
    required this.confidence,
    required this.impact,
    required this.actionType,
  });

  factory Recommendation.fromJson(Map<String, Object?> j) {
    final ex = (j['explanation'] as Map<String, Object?>?) ?? const {};
    final action = (j['action'] as Map<String, Object?>?) ?? const {};
    return Recommendation(
      id: (j['id'] as String?) ?? '',
      type: (j['type'] as String?) ?? '',
      what: (ex['what'] as String?) ?? '',
      why: (ex['why'] as String?) ?? '',
      vars: (ex['vars'] as Map<String, Object?>?) ?? const {},
      confidence: (j['confidence'] as num?)?.toDouble() ?? 0,
      impact: (j['estimated_impact'] as Map<String, Object?>?) ?? const {},
      actionType: (action['type'] as String?) ?? 'none',
    );
  }

  final String id;
  final String type;
  final String what;
  final String why;
  final Map<String, Object?> vars;
  final double confidence;
  final Map<String, Object?> impact;
  final String actionType;
}

@immutable
class RiskFactor {
  const RiskFactor({required this.code, required this.evidence});

  factory RiskFactor.fromJson(Map<String, Object?> j) => RiskFactor(
    code: (j['code'] as String?) ?? '',
    evidence: (j['evidence'] as Map<String, Object?>?) ?? const {},
  );

  final String code;
  final Map<String, Object?> evidence;
}

/// COD delivery-risk assessment (CODI-002). Explainable, never a rejection.
@immutable
class CodRisk {
  const CodRisk({
    required this.orderId,
    required this.level,
    required this.recommendedAction,
    required this.factors,
    required this.overridden,
    required this.disputed,
    this.overrideReason,
    this.disputeNote,
  });

  factory CodRisk.fromJson(Map<String, Object?> j) => CodRisk(
    orderId: (j['order_id'] as String?) ?? '',
    level: (j['level'] as String?) ?? 'LOW',
    recommendedAction: (j['recommended_action'] as String?) ?? 'cod_ok',
    factors: ((j['factors'] as List<Object?>?) ?? const [])
        .whereType<Map<String, Object?>>()
        .map(RiskFactor.fromJson)
        .toList(growable: false),
    overridden: (j['overridden'] as bool?) ?? false,
    overrideReason: j['override_reason'] as String?,
    disputed: (j['disputed'] as bool?) ?? false,
    disputeNote: j['dispute_note'] as String?,
  );

  final String orderId;
  final String level;
  final String recommendedAction;
  final List<RiskFactor> factors;
  final bool overridden;
  final String? overrideReason;
  final bool disputed;
  final String? disputeNote;
}

int? _intOrNull(Object? v) => (v as num?)?.toInt();
double? _dbl(Object? v) => (v as num?)?.toDouble();
Map<String, String> _strMap(Object? v) => {
  for (final e in ((v as Map<String, Object?>?) ?? const {}).entries)
    if (e.value != null) e.key: e.value.toString(),
};

/// Product Brain (PBR): one recomputable profile per product. Anything that
/// couldn't be computed is listed in [notIncluded] with a reason code.
@immutable
class ProductBrain {
  const ProductBrain({
    required this.units7,
    required this.units30,
    required this.units90,
    required this.inStockDays,
    required this.demandPerDay,
    required this.available,
    required this.coverDays,
    required this.stockRisk,
    required this.stockouts,
    required this.marginPct,
    required this.contributionPerUnit,
    required this.contributionBasis,
    required this.returnRate,
    required this.topReasons,
    required this.fit,
    required this.notIncluded,
    required this.completeness,
    this.currency = 'NPR',
  });

  factory ProductBrain.fromJson(Map<String, Object?> j) => ProductBrain(
    units7: _int(j['units_7d']),
    units30: _int(j['units_30d']),
    units90: _int(j['units_90d']),
    inStockDays: _int(j['in_stock_days_90d']),
    demandPerDay: _dbl(j['demand_per_day']),
    available: _intOrNull(j['available']),
    coverDays: _dbl(j['cover_days']),
    stockRisk: j['stock_risk'] as String?,
    stockouts: _int(j['stockouts_90d']),
    marginPct: _dbl(j['margin_pct']),
    contributionPerUnit: _intOrNull(j['contribution_per_unit_minor']),
    contributionBasis: j['contribution_basis'] as String?,
    returnRate: _dbl(j['return_rate']),
    topReasons: [
      for (final r in ((j['top_reasons'] as List<Object?>?) ?? const []))
        if (r is Map<String, Object?>)
          (
            reason: (r['reason'] as String?) ?? 'other',
            units: _int(r['units']),
          ),
    ],
    fit: j['fit'] as String?,
    notIncluded: _strMap(j['not_included']),
    completeness: _dbl(j['completeness']) ?? 0,
    currency: (j['currency'] as String?) ?? 'NPR',
  );

  final int units7;
  final int units30;
  final int units90;
  final int inStockDays;
  final double? demandPerDay;
  final int? available;
  final double? coverDays;
  final String? stockRisk;
  final int stockouts;
  final double? marginPct;
  final int? contributionPerUnit;
  final String? contributionBasis;
  final double? returnRate;
  final List<({String reason, int units})> topReasons;
  final String? fit;
  final Map<String, String> notIncluded;
  final double completeness;

  /// From the API; NPR when an older backend doesn't send it.
  final String currency;
}

/// One waterfall line. [amountMinor] is null when the component is not included.
@immutable
class ProfitComponent {
  const ProfitComponent({
    required this.code,
    required this.amountMinor,
    required this.status,
    required this.reason,
  });

  factory ProfitComponent.fromJson(Map<String, Object?> j) => ProfitComponent(
    code: (j['code'] as String?) ?? '',
    amountMinor: _intOrNull(j['amount_minor']),
    status: (j['status'] as String?) ?? 'included',
    reason: j['reason'] as String?,
  );

  final String code;
  final int? amountMinor;
  final String status;
  final String? reason;
}

@immutable
class ProfitSummary {
  const ProfitSummary({
    required this.windowDays,
    required this.revenueMinor,
    required this.contributionMinor,
    required this.marginPct,
    required this.complete,
    required this.components,
    this.currency = 'NPR',
  });

  factory ProfitSummary.fromJson(Map<String, Object?> j) {
    final shop = (j['shop'] as Map<String, Object?>?) ?? const {};
    return ProfitSummary(
      windowDays: _int(j['window_days']),
      currency: (j['currency'] as String?) ?? 'NPR',
      revenueMinor: _int(shop['revenue_minor']),
      contributionMinor: _int(shop['contribution_minor']),
      marginPct: _dbl(shop['margin_pct']),
      complete: (shop['complete'] as bool?) ?? false,
      components: [
        for (final c in ((shop['components'] as List<Object?>?) ?? const []))
          if (c is Map<String, Object?>) ProfitComponent.fromJson(c),
      ],
    );
  }

  final int windowDays;
  final int revenueMinor;
  final int contributionMinor;
  final double? marginPct;
  final bool complete;
  final List<ProfitComponent> components;

  /// From the API; NPR when an older backend doesn't send it.
  final String currency;

  /// Components without full data (ads included: "no ad account").
  List<ProfitComponent> get gaps => [
    for (final c in components)
      if (c.status != 'included') c,
  ];
}

/// A Commerce Memory fact (MEM): versioned, evidence-backed, seller-controlled.
@immutable
class MemoryFact {
  const MemoryFact({
    required this.id,
    required this.subjectType,
    required this.subjectId,
    required this.subjectLabel,
    required this.factType,
    required this.value,
    required this.confidence,
    required this.evidence,
    required this.source,
    required this.confirmed,
    required this.version,
  });

  factory MemoryFact.fromJson(Map<String, Object?> j) => MemoryFact(
    id: (j['id'] as String?) ?? '',
    subjectType: (j['subject_type'] as String?) ?? '',
    subjectId: (j['subject_id'] as String?) ?? '',
    subjectLabel: j['subject_label'] as String?,
    factType: (j['fact_type'] as String?) ?? '',
    value: (j['value'] as Map<String, Object?>?) ?? const {},
    confidence: _dbl(j['confidence']) ?? 0,
    evidence: [
      for (final e in ((j['evidence'] as List<Object?>?) ?? const []))
        if (e is Map<String, Object?>) e,
    ],
    source: (j['source'] as String?) ?? 'derived',
    confirmed: (j['confirmed'] as bool?) ?? false,
    version: _int(j['version']),
  );

  final String id;
  final String subjectType;
  final String subjectId;
  final String? subjectLabel;
  final String factType;
  final Map<String, Object?> value;
  final double confidence;
  final List<Map<String, Object?>> evidence;
  final String source;
  final bool confirmed;
  final int version;
}

class IntelligenceApi {
  IntelligenceApi(this._dio);

  final Dio _dio;

  Future<AutopilotScore> autopilotScore() => apiCall(() async {
    final r = await _dio.get<Map<String, Object?>>(
      '/intelligence/autopilot-score',
    );
    return AutopilotScore.fromJson(r.data!);
  });

  Future<List<Recommendation>> openRecommendations() => apiCall(() async {
    final r = await _dio.get<Map<String, Object?>>(
      '/intelligence/recommendations',
      queryParameters: {'status': 'open'},
    );
    return itemsOf(r.data).map(Recommendation.fromJson).toList();
  });

  Future<void> accept(String id) => apiCall(
    () => _dio.post<Object?>('/intelligence/recommendations/$id/accept'),
  );

  Future<void> reject(String id, String reason) => apiCall(
    () => _dio.post<Object?>(
      '/intelligence/recommendations/$id/reject',
      data: {'reason': reason},
    ),
  );

  Future<CodRisk> codRisk(String orderId) => apiCall(() async {
    final r = await _dio.get<Map<String, Object?>>(
      '/intelligence/cod/assessments/$orderId',
    );
    return CodRisk.fromJson(r.data!);
  });

  Future<CodRisk> override(String orderId, String level, String reason) =>
      apiCall(() async {
        final r = await _dio.post<Map<String, Object?>>(
          '/intelligence/cod/assessments/$orderId/override',
          data: {'level': level, 'reason': reason},
        );
        return CodRisk.fromJson(r.data!);
      });

  Future<CodRisk> dispute(String orderId, String note) => apiCall(() async {
    final r = await _dio.post<Map<String, Object?>>(
      '/intelligence/cod/assessments/$orderId/dispute',
      data: {'note': note},
    );
    return CodRisk.fromJson(r.data!);
  });

  Future<ProductBrain> productBrain(String productId) => apiCall(() async {
    final r = await _dio.get<Map<String, Object?>>(
      '/intelligence/products/$productId/brain',
    );
    return ProductBrain.fromJson(r.data!);
  });

  Future<ProfitSummary> profit({int days = 30}) => apiCall(() async {
    final r = await _dio.get<Map<String, Object?>>(
      '/intelligence/profit',
      queryParameters: {'days': days},
    );
    return ProfitSummary.fromJson(r.data!);
  });

  Future<List<MemoryFact>> memoryFacts() => apiCall(() async {
    final r = await _dio.get<Map<String, Object?>>(
      '/intelligence/memory/facts',
    );
    return itemsOf(r.data).map(MemoryFact.fromJson).toList();
  });

  Future<void> confirmFact(String id) => apiCall(
    () => _dio.post<Object?>('/intelligence/memory/facts/$id/confirm'),
  );

  Future<void> rejectFact(String id, String note) => apiCall(
    () => _dio.post<Object?>(
      '/intelligence/memory/facts/$id/reject',
      data: {'note': note},
    ),
  );
}

final intelligenceApiProvider = Provider<IntelligenceApi>(
  (ref) => IntelligenceApi(ref.watch(dioProvider)),
);

final autopilotScoreProvider = FutureProvider.autoDispose<AutopilotScore>(
  (ref) => ref.watch(intelligenceApiProvider).autopilotScore(),
);

final recommendationsProvider =
    FutureProvider.autoDispose<List<Recommendation>>(
      (ref) => ref.watch(intelligenceApiProvider).openRecommendations(),
    );

final codRiskProvider = FutureProvider.autoDispose.family<CodRisk, String>(
  (ref, orderId) => ref.watch(intelligenceApiProvider).codRisk(orderId),
);

final productBrainProvider = FutureProvider.autoDispose
    .family<ProductBrain, String>(
      (ref, productId) =>
          ref.watch(intelligenceApiProvider).productBrain(productId),
    );

final profitSummaryProvider = FutureProvider.autoDispose<ProfitSummary>(
  (ref) => ref.watch(intelligenceApiProvider).profit(),
);

final memoryFactsProvider = FutureProvider.autoDispose<List<MemoryFact>>(
  (ref) => ref.watch(intelligenceApiProvider).memoryFacts(),
);
