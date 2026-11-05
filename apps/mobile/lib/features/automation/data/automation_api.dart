import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/api_call.dart';
import '../../../core/api/providers.dart';

int _int(Object? v) => (v as num?)?.toInt() ?? 0;

/// Why an automated action ran, waited or was blocked (decision record, AUT-019).
@immutable
class Decision {
  const Decision({
    required this.id,
    required this.action,
    required this.decision,
    required this.rule,
    required this.mode,
    required this.createdAt,
    this.impactMinor,
    this.currency,
  });

  factory Decision.fromJson(Map<String, Object?> j) {
    final impact = j['impact'] as Map<String, Object?>?;
    return Decision(
      id: (j['id'] as String?) ?? '',
      action: (j['action'] as String?) ?? '',
      decision: (j['decision'] as String?) ?? '',
      rule: (j['rule'] as String?) ?? '',
      mode: (j['mode'] as String?) ?? 'assisted',
      createdAt:
          DateTime.tryParse((j['created_at'] as String?) ?? '')?.toLocal() ??
          DateTime.now(),
      impactMinor: (impact?['amount_minor'] as num?)?.toInt(),
      currency: impact?['currency'] as String?,
    );
  }

  final String id;
  final String action;
  final String decision;
  final String rule;
  final String mode;
  final DateTime createdAt;
  final int? impactMinor;
  final String? currency;
}

@immutable
class ControlCenter {
  const ControlCenter({
    required this.state,
    required this.mode,
    required this.currency,
    required this.orders,
    required this.revenueMinor,
    required this.aiMessages,
    required this.delivered,
    required this.inTransit,
    required this.returns,
    required this.doneAutomatically,
    required this.doneByTeam,
    required this.shareAutomatic,
    required this.approvals,
    required this.exceptions,
    required this.urgent,
    required this.feed,
  });

  factory ControlCenter.fromJson(Map<String, Object?> j) {
    final m = (j['metrics'] as Map<String, Object?>?) ?? const {};
    final a = (j['automation'] as Map<String, Object?>?) ?? const {};
    final n = (j['needs_attention'] as Map<String, Object?>?) ?? const {};
    return ControlCenter(
      state: (j['state'] as String?) ?? 'running',
      mode: (j['mode'] as String?) ?? 'assisted',
      currency: (j['currency'] as String?) ?? 'NPR',
      orders: _int(m['orders']),
      revenueMinor: (m['revenue_minor'] as num?)?.toInt(),
      aiMessages: _int(m['ai_messages']),
      delivered: _int(m['delivered']),
      inTransit: _int(m['in_transit']),
      returns: _int(m['returns']),
      doneAutomatically: _int(a['done_automatically']),
      doneByTeam: _int(a['done_by_team']),
      shareAutomatic: (a['share_automatic'] as num?)?.toDouble(),
      approvals: _int(n['approvals']),
      exceptions: _int(n['exceptions']),
      urgent: _int(n['urgent']),
      feed: itemsOf({'items': j['feed']}).map(Decision.fromJson).toList(),
    );
  }

  final String state;
  final String mode;
  final String currency;
  final int orders;

  /// Null when the person can't see order money.
  final int? revenueMinor;
  final int aiMessages;
  final int delivered;
  final int inTransit;
  final int returns;
  final int doneAutomatically;
  final int doneByTeam;
  final double? shareAutomatic;
  final int approvals;
  final int exceptions;
  final int urgent;
  final List<Decision> feed;

  int get needsAttention => approvals + exceptions;
}

@immutable
class AutomationApproval {
  const AutomationApproval({
    required this.id,
    required this.kind,
    this.workflowName,
    this.action,
    this.orderId,
    this.orderNumber,
    this.decision,
  });

  factory AutomationApproval.fromJson(Map<String, Object?> j) =>
      AutomationApproval(
        id: (j['id'] as String?) ?? '',
        kind: (j['kind'] as String?) ?? 'action',
        workflowName: j['workflow_name'] as String?,
        action: j['action'] as String?,
        orderId: j['order_id'] as String?,
        orderNumber: (j['order_number'] as num?)?.toInt(),
        decision:
            j['decision'] is Map<String, Object?>
                ? Decision.fromJson(j['decision']! as Map<String, Object?>)
                : null,
      );

  final String id;
  final String kind;
  final String? workflowName;
  final String? action;
  final String? orderId;
  final int? orderNumber;
  final Decision? decision;
}

@immutable
class WorkflowSummary {
  const WorkflowSummary({
    required this.id,
    required this.name,
    required this.status,
    required this.runs,
    this.pausedReason,
  });

  factory WorkflowSummary.fromJson(Map<String, Object?> j) => WorkflowSummary(
    id: (j['id'] as String?) ?? '',
    name: (j['name'] as String?) ?? '',
    status: (j['status'] as String?) ?? 'draft',
    pausedReason: j['paused_reason'] as String?,
    runs: {
      for (final e
          in ((j['runs'] as Map<String, Object?>?) ?? const {}).entries)
        e.key: _int(e.value),
    },
  );

  final String id;
  final String name;
  final String status;
  final String? pausedReason;
  final Map<String, int> runs;

  bool get brokeRepeatedly =>
      status == 'paused' && (pausedReason ?? '').startsWith('circuit_breaker:');
  int get completedRuns => runs['completed'] ?? 0;
  int get failedRuns => runs['failed'] ?? 0;
  int get waitingRuns =>
      (runs['waiting'] ?? 0) +
      (runs['awaiting_approval'] ?? 0) +
      (runs['running'] ?? 0);
}

class AutomationApi {
  AutomationApi(this._dio);

  final Dio _dio;

  Future<ControlCenter> controlCenter({int days = 7}) => apiCall(() async {
    final r = await _dio.get<Map<String, Object?>>(
      '/control-center',
      queryParameters: {'days': days},
    );
    return ControlCenter.fromJson(r.data!);
  });

  Future<List<AutomationApproval>> approvals() => apiCall(() async {
    final r = await _dio.get<Map<String, Object?>>('/automation/approvals');
    return itemsOf(r.data).map(AutomationApproval.fromJson).toList();
  });

  Future<void> resolve(String id, {required bool approve, String? note}) =>
      apiCall(
        () => _dio.post<Object?>(
          '/automation/approvals/$id/${approve ? 'approve' : 'reject'}',
          data: {if ((note ?? '').isNotEmpty) 'note': note},
        ),
      );

  Future<List<WorkflowSummary>> workflows() => apiCall(() async {
    final r = await _dio.get<Map<String, Object?>>('/automation/workflows');
    return itemsOf(r.data).map(WorkflowSummary.fromJson).toList();
  });

  Future<void> setStatus(String id, String status) => apiCall(
    () => _dio.post<Object?>(
      '/automation/workflows/$id/status',
      data: {'status': status},
    ),
  );
}

final automationApiProvider = Provider<AutomationApi>(
  (ref) => AutomationApi(ref.watch(dioProvider)),
);

final controlCenterProvider = FutureProvider.autoDispose<ControlCenter>(
  (ref) => ref.watch(automationApiProvider).controlCenter(),
);

final approvalsProvider = FutureProvider.autoDispose<List<AutomationApproval>>(
  (ref) => ref.watch(automationApiProvider).approvals(),
);

final workflowsProvider = FutureProvider.autoDispose<List<WorkflowSummary>>(
  (ref) => ref.watch(automationApiProvider).workflows(),
);
