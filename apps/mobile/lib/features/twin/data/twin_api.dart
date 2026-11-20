import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/api_call.dart';
import '../../../core/api/providers.dart';

int _int(Object? v) => (v as num?)?.toInt() ?? 0;
double? _dbl(Object? v) => (v as num?)?.toDouble();
Map<String, Object?> _map(Object? v) =>
    v is Map<String, Object?> ? v : const <String, Object?>{};

/// One Digital Store Twin section (derived, read-only; may be stale).
@immutable
class TwinSection {
  const TwinSection({
    required this.name,
    required this.state,
    required this.asOf,
    required this.stale,
  });

  factory TwinSection.fromJson(String name, Map<String, Object?> j) =>
      TwinSection(
        name: name,
        state: _map(j['state']),
        asOf: DateTime.tryParse(j['as_of'] as String? ?? ''),
        stale: j['stale'] == true,
      );

  final String name;
  final Map<String, Object?> state;
  final DateTime? asOf;
  final bool stale;

  int count(String key) => _int(state[key]);
}

@immutable
class TwinSummary {
  const TwinSummary(this.sections, {this.currency = 'NPR'});

  factory TwinSummary.fromJson(Map<String, Object?> j) => TwinSummary({
    for (final e in _map(j['sections']).entries)
      if (e.value is Map<String, Object?>)
        e.key: TwinSection.fromJson(e.key, e.value! as Map<String, Object?>),
  }, currency: (j['currency'] as String?) ?? 'NPR');

  final Map<String, TwinSection> sections;

  /// The shop's currency for money in sections (fallback NPR).
  final String currency;

  TwinSection? operator [](String name) => sections[name];

  /// The oldest "as of" among the sections (what the strip can vouch for).
  DateTime? get asOf {
    final times = [
      for (final s in sections.values)
        if (s.asOf != null) s.asOf!,
    ]..sort();
    return times.isEmpty ? null : times.first;
  }

  bool get anyStale => sections.values.any((s) => s.stale);
}

/// A what-if estimate. Outputs and assumptions are kept as the server's
/// JSON and rendered by code (see twin_labels.dart).
@immutable
class SimulationRun {
  const SimulationRun({
    required this.id,
    required this.kind,
    required this.status,
    required this.inputs,
    required this.outputs,
    required this.assumptions,
    required this.confidence,
    required this.errorCode,
    required this.createdAt,
    this.currency = 'NPR',
  });

  /// [currency] comes from the response's top level (list or detail).
  factory SimulationRun.fromJson(Map<String, Object?> j, {String? currency}) =>
      SimulationRun(
        currency: currency ?? (j['currency'] as String?) ?? 'NPR',
        id: j['id'] as String? ?? '',
        kind: j['kind'] as String? ?? '',
        status: j['status'] as String? ?? 'queued',
        inputs: _map(j['inputs']),
        outputs:
            j['outputs'] is Map<String, Object?> ? _map(j['outputs']) : null,
        assumptions: [
          for (final a in (j['assumptions'] as List<Object?>?) ?? const [])
            if (a is Map<String, Object?>) a,
        ],
        confidence: j['confidence'] as String?,
        errorCode: j['error_code'] as String?,
        createdAt: DateTime.tryParse(j['created_at'] as String? ?? ''),
      );

  final String id;
  final String kind;
  final String status;
  final Map<String, Object?> inputs;
  final Map<String, Object?>? outputs;
  final List<Map<String, Object?>> assumptions;
  final String? confidence;
  final String? errorCode;
  final DateTime? createdAt;
  final String currency;

  bool get done => status == 'completed' || status == 'failed';

  Map<String, Object?> out(String key) => _map(outputs?[key]);
  num? n(String key) => outputs?[key] as num?;
  double? pct(String key) => _dbl(outputs?[key]);
  List<Map<String, Object?>> get warnings => [
    for (final w in (outputs?['warnings'] as List<Object?>?) ?? const [])
      if (w is Map<String, Object?>) w,
  ];
}

class TwinApi {
  TwinApi(this._dio);

  final Dio _dio;

  Future<TwinSummary> summary() => apiCall(() async {
    final r = await _dio.get<Map<String, Object?>>('/twin/summary');
    return TwinSummary.fromJson(r.data!);
  });

  Future<List<SimulationRun>> simulations() => apiCall(() async {
    final r = await _dio.get<Map<String, Object?>>('/simulations');
    final currency = r.data?['currency'] as String?;
    return [
      for (final j in itemsOf(r.data))
        SimulationRun.fromJson(j, currency: currency),
    ];
  });

  Future<SimulationRun> simulation(String id) => apiCall(() async {
    final r = await _dio.get<Map<String, Object?>>('/simulations/$id');
    return SimulationRun.fromJson(r.data!);
  });
}

final twinApiProvider = Provider<TwinApi>(
  (ref) => TwinApi(ref.watch(dioProvider)),
);

final twinSummaryProvider = FutureProvider.autoDispose<TwinSummary>(
  (ref) => ref.watch(twinApiProvider).summary(),
);

final simulationsProvider = FutureProvider.autoDispose<List<SimulationRun>>(
  (ref) => ref.watch(twinApiProvider).simulations(),
);

final simulationProvider = FutureProvider.autoDispose
    .family<SimulationRun, String>(
      (ref, id) => ref.watch(twinApiProvider).simulation(id),
    );
