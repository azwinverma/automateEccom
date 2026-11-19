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
