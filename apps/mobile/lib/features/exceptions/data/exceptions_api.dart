import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/api_call.dart';
import '../../../core/api/providers.dart';
import '../../../core/auth/session_controller.dart';
import '../../../core/storage/providers.dart';

/// `GET /exceptions` item.
@immutable
class ApiException {
  const ApiException({
    required this.id,
    required this.type,
    required this.severity,
    required this.resourceType,
    required this.resourceId,
    required this.action,
    this.occurredAt,
    this.details = const {},
  });

  factory ApiException.fromJson(Map<String, Object?> j) {
    final r = (j['resource'] as Map<String, Object?>?) ?? const {};
    return ApiException(
      id: j['id']! as String,
      type: (j['type'] as String?) ?? '',
      severity: (j['severity'] as String?) ?? 'normal',
      resourceType: (r['type'] as String?) ?? '',
      resourceId: '${r['id'] ?? ''}',
      action: (j['action'] as String?) ?? '',
      occurredAt:
          j['occurred_at'] is String
              ? DateTime.tryParse(j['occurred_at']! as String)
              : null,
      details: (j['details'] as Map<String, Object?>?) ?? const {},
    );
  }

  final String id;
  final String type;

  /// urgent | high | normal
  final String severity;
  final String resourceType;
  final String resourceId;

  /// reconnect | retry_publish | reschedule | review_post | review_draft |
  /// retry_draft | confirm_attributes | dismiss
  final String action;
  final DateTime? occurredAt;
  final Map<String, Object?> details;
}

class ExceptionsApi {
  ExceptionsApi(this._dio);

  final Dio _dio;

  Future<List<ApiException>> list() => apiCall(() async {
    final r = await _dio.get<Map<String, Object?>>('/exceptions');
    return itemsOf(r.data).map(ApiException.fromJson).toList();
  });
}

final exceptionsApiProvider = Provider<ExceptionsApi>(
  (ref) => ExceptionsApi(ref.watch(dioProvider)),
);

/// Locally dismissed exception ids. The API has no dismiss endpoint (gap),
/// so `dismiss` only hides the item on this device.
class DismissedExceptions extends Notifier<Set<String>> {
  static const _key = 'exceptions.dismissed';

  @override
  Set<String> build() =>
      (ref.read(sharedPreferencesProvider).getStringList(_key) ??
              const <String>[])
          .toSet();

  Future<void> dismiss(String id) async {
    state = {...state, id};
    await ref
        .read(sharedPreferencesProvider)
        .setStringList(_key, state.toList());
  }
}

final dismissedExceptionsProvider =
    NotifierProvider<DismissedExceptions, Set<String>>(DismissedExceptions.new);

final exceptionsProvider = FutureProvider.autoDispose<List<ApiException>>((
  ref,
) async {
  ref.watch(activeMerchantIdProvider);
  final items = await ref.watch(exceptionsApiProvider).list();
  final hidden = ref.watch(dismissedExceptionsProvider);
  return items.where((e) => !hidden.contains(e.id)).toList(growable: false);
});

/// `GET /merchant` → automation_mode (assisted | smart | autopilot).
final automationModeProvider = FutureProvider.autoDispose<String?>((ref) {
  ref.watch(activeMerchantIdProvider);
  return apiCall(() async {
    final r = await ref
        .watch(dioProvider)
        .get<Map<String, Object?>>('/merchant');
    return r.data?['automation_mode'] as String?;
  });
});
