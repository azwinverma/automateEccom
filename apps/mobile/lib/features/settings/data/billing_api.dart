import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/providers.dart';
import '../../../core/auth/session_controller.dart';
import '../../../core/errors/api_error.dart';

DateTime? _date(Object? v) => v is String ? DateTime.tryParse(v) : null;
int _int(Object? v) => v is num ? v.toInt() : 0;
int? _intOrNull(Object? v) => v is num ? v.toInt() : null;

@immutable
class Subscription {
  const Subscription({
    required this.planCode,
    required this.planName,
    required this.status,
    this.tagline,
    this.trialEndsAt,
    this.periodStart,
    this.periodEnd,
  });

  factory Subscription.fromJson(Map<String, Object?> json) {
    final plan = (json['plan'] as Map<String, Object?>?) ?? const {};
    return Subscription(
      planCode: (plan['code'] as String?) ?? '',
      planName: (plan['name'] as String?) ?? '',
      tagline: plan['tagline'] as String?,
      status: (json['status'] as String?) ?? '',
      trialEndsAt: _date(json['trial_ends_at']),
      periodStart: _date(json['current_period_start']),
      periodEnd: _date(json['current_period_end']),
    );
  }

  final String planCode;
  final String planName;
  final String? tagline;
  final String status;
  final DateTime? trialEndsAt;
  final DateTime? periodStart;
  final DateTime? periodEnd;
}

@immutable
class UsageBurst {
  const UsageBurst({required this.period, required this.used, this.limit});

  factory UsageBurst.fromJson(Map<String, Object?> json) => UsageBurst(
    period: (json['period'] as String?) ?? 'day',
    limit: _intOrNull(json['limit']),
    used: _int(json['used']),
  );

  final String period;

  /// `null` = no burst cap.
  final int? limit;
  final int used;
}

@immutable
class UsageLimit {
  const UsageLimit({
    required this.resource,
    required this.period,
    required this.used,
    this.limit,
    this.reserved = 0,
    this.burst,
    this.alertLevel,
  });

  factory UsageLimit.fromJson(Map<String, Object?> json) => UsageLimit(
    resource: (json['resource'] as String?) ?? '',
    period: (json['period'] as String?) ?? 'month',
    limit: _intOrNull(json['limit']),
    used: _int(json['used']),
    reserved: _int(json['reserved']),
    burst:
        json['burst'] is Map<String, Object?>
            ? UsageBurst.fromJson(json['burst']! as Map<String, Object?>)
            : null,
    alertLevel: json['alert_level']?.toString(),
  );

  final String resource;
  final String period;

  /// `null` = unlimited.
  final int? limit;
  final int used;

  /// Reserved by in-flight jobs (counts toward the limit).
  final int reserved;
  final UsageBurst? burst;

  /// Server-computed "70" | "85" | "100" | null.
  final String? alertLevel;

  bool get isVideo => resource.contains('video');

  double get ratio {
    final l = limit;
    if (l == null) return 0;
    if (l <= 0) return 1;
    return (used + reserved) / l;
  }
}

@immutable
class Entitlements {
  const Entitlements({required this.features, required this.limits});

  factory Entitlements.fromJson(Map<String, Object?> json) {
    final features = (json['features'] as Map<String, Object?>?) ?? const {};
    return Entitlements(
      features: features.map((k, v) => MapEntry(k, v == true)),
      limits: ((json['limits'] as List<Object?>?) ?? const [])
          .whereType<Map<String, Object?>>()
          .map(UsageLimit.fromJson)
          .toList(growable: false),
    );
  }

  final Map<String, bool> features;
  final List<UsageLimit> limits;
}

@immutable
class Credits {
  const Credits({required this.balance, required this.transactionCount});

  factory Credits.fromJson(Map<String, Object?> json) => Credits(
    balance: _int(json['balance']),
    transactionCount:
        ((json['transactions'] as List<Object?>?) ?? const []).length,
  );

  final int balance;
  final int transactionCount;
}

class BillingApi {
  BillingApi(this._dio);

  final Dio _dio;

  Future<Map<String, Object?>> _get(String path) async {
    try {
      final res = await _dio.get<Map<String, Object?>>(path);
      return res.data ?? const {};
    } on DioException catch (e) {
      throw ApiError.fromDio(e);
    }
  }

  Future<Subscription> subscription() async =>
      Subscription.fromJson(await _get('/billing/subscription'));

  Future<Entitlements> entitlements() async =>
      Entitlements.fromJson(await _get('/billing/entitlements'));

  Future<Credits> credits() async =>
      Credits.fromJson(await _get('/billing/credits'));
}

final billingApiProvider = Provider<BillingApi>(
  (ref) => BillingApi(ref.watch(dioProvider)),
);

// Keyed on the active merchant so switching tenants refetches.
final subscriptionProvider = FutureProvider.autoDispose<Subscription>((ref) {
  ref.watch(activeMerchantIdProvider);
  return ref.watch(billingApiProvider).subscription();
});

final entitlementsProvider = FutureProvider.autoDispose<Entitlements>((ref) {
  ref.watch(activeMerchantIdProvider);
  return ref.watch(billingApiProvider).entitlements();
});

final creditsProvider = FutureProvider.autoDispose<Credits>((ref) {
  ref.watch(activeMerchantIdProvider);
  return ref.watch(billingApiProvider).credits();
});
