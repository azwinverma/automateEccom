import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/api_call.dart';
import '../../../core/api/providers.dart';
import '../../../core/api/request_context_interceptor.dart';

int _minor(Object? money) =>
    money is Map ? ((money['amount_minor'] as num?)?.toInt() ?? 0) : 0;
DateTime? _date(Object? v) => v is String ? DateTime.tryParse(v) : null;
List<Map<String, Object?>> _list(Object? v) =>
    ((v as List<Object?>?) ?? const [])
        .whereType<Map<String, Object?>>()
        .toList(growable: false);

/// One way to send this order: a courier service (priced) or own rider.
@immutable
class CourierOption {
  const CourierOption({
    required this.courierAccountId,
    required this.displayName,
    required this.manual,
    required this.recommended,
    this.serviceCode,
    this.priceMinor,
    this.etaMin,
    this.etaMax,
  });

  factory CourierOption.fromJson(Map<String, Object?> j) => CourierOption(
    courierAccountId: j['courier_account_id']! as String,
    displayName: (j['display_name'] as String?) ?? '',
    manual: (j['manual'] as bool?) ?? false,
    recommended: (j['recommended'] as bool?) ?? false,
    serviceCode: j['service_code'] as String?,
    priceMinor: j['price'] == null ? null : _minor(j['price']),
    etaMin: (j['eta_days_min'] as num?)?.toInt(),
    etaMax: (j['eta_days_max'] as num?)?.toInt(),
  );

  final String courierAccountId;
  final String displayName;
  final bool manual;
  final bool recommended;
  final String? serviceCode;
  final int? priceMinor;
  final int? etaMin;
  final int? etaMax;

  String get key => '$courierAccountId:${serviceCode ?? ''}';
}

@immutable
class CourierOptions {
  const CourierOptions({
    required this.options,
    required this.codAmountMinor,
    this.recommendationReason,
  });

  factory CourierOptions.fromJson(Map<String, Object?> j) => CourierOptions(
    options: _list(j['options']).map(CourierOption.fromJson).toList(),
    codAmountMinor: (j['cod_amount_minor'] as num?)?.toInt() ?? 0,
    recommendationReason:
        (j['recommendation'] as Map<String, Object?>?)?['reason'] as String?,
  );

  final List<CourierOption> options;
  final int codAmountMinor;

  /// default_courier | cheapest | only_option
  final String? recommendationReason;
}

@immutable
class ShipmentEvent {
  const ShipmentEvent({
    required this.id,
    required this.status,
    required this.applied,
    this.occurredAt,
    this.description,
    this.location,
    this.failureReason,
  });

  factory ShipmentEvent.fromJson(Map<String, Object?> j) => ShipmentEvent(
    id: j['id']! as String,
    status: (j['status'] as String?) ?? '',
    applied: (j['applied'] as bool?) ?? true,
    occurredAt: _date(j['occurred_at']),
    description: j['description'] as String?,
    location: j['location'] as String?,
    failureReason: j['failure_reason'] as String?,
  );

  final String id;
  final String status;

  /// False: the courier's event arrived after a newer one (history only).
  final bool applied;
  final DateTime? occurredAt;
  final String? description;
  final String? location;
  final String? failureReason;
}

@immutable
class DeliveryAttempt {
  const DeliveryAttempt({
    required this.id,
    required this.attemptNo,
    required this.failureReason,
    required this.recoveryStatus,
    this.failedAt,
    this.customerReply,
  });

  factory DeliveryAttempt.fromJson(Map<String, Object?> j) => DeliveryAttempt(
    id: j['id']! as String,
    attemptNo: (j['attempt_no'] as num?)?.toInt() ?? 1,
    failureReason: (j['failure_reason'] as String?) ?? 'other',
    recoveryStatus: (j['recovery_status'] as String?) ?? 'open',
    failedAt: _date(j['failed_at']),
    customerReply: j['customer_reply'] as String?,
  );

  final String id;
  final int attemptNo;
  final String failureReason;
  final String recoveryStatus;
  final DateTime? failedAt;
  final String? customerReply;
}

@immutable
class Shipment {
  const Shipment({
    required this.id,
    required this.status,
    required this.courierName,
    required this.manual,
    required this.codAmountMinor,
    required this.currency,
    this.trackingNumber,
    this.actions = const [],
    this.events = const [],
    this.attempts = const [],
  });

  factory Shipment.fromJson(Map<String, Object?> j) {
    final cod = j['cod_amount'] as Map<String, Object?>?;
    return Shipment(
      id: j['id']! as String,
      status: (j['status'] as String?) ?? 'booked',
      courierName: (j['courier_name'] as String?) ?? '',
      manual: (j['manual'] as bool?) ?? false,
      codAmountMinor: _minor(cod),
      currency: (cod?['currency'] as String?) ?? 'NPR',
      trackingNumber: j['tracking_number'] as String?,
      actions: ((j['actions'] as List<Object?>?) ?? const [])
          .whereType<String>()
          .toList(growable: false),
      events: _list(j['events']).map(ShipmentEvent.fromJson).toList(),
      attempts: _list(j['attempts']).map(DeliveryAttempt.fromJson).toList(),
    );
  }

  final String id;
  final String status;
  final String courierName;
  final bool manual;
  final int codAmountMinor;
  final String currency;
  final String? trackingNumber;
  final List<String> actions;
  final List<ShipmentEvent> events;
  final List<DeliveryAttempt> attempts;
}

@immutable
class CodAwaiting {
  const CodAwaiting({
    required this.shipmentId,
    required this.orderId,
    required this.orderNumber,
    required this.courierName,
    required this.amountMinor,
    required this.currency,
    this.daysWaiting,
  });

  factory CodAwaiting.fromJson(Map<String, Object?> j) {
    final m = j['cod_amount'] as Map<String, Object?>?;
    return CodAwaiting(
      shipmentId: j['shipment_id']! as String,
      orderId: j['order_id']! as String,
      orderNumber: (j['order_number'] as num?)?.toInt() ?? 0,
      courierName: (j['courier_name'] as String?) ?? '',
      amountMinor: _minor(m),
      currency: (m?['currency'] as String?) ?? 'NPR',
      daysWaiting: (j['days_waiting'] as num?)?.toInt(),
    );
  }

  final String shipmentId;
  final String orderId;
  final int orderNumber;
  final String courierName;
  final int amountMinor;
  final String currency;
  final int? daysWaiting;
}

@immutable
class CodSettlement {
  const CodSettlement({
    required this.id,
    required this.reference,
    required this.courierName,
    required this.status,
    required this.netMinor,
    required this.currency,
    required this.issueCount,
  });

  factory CodSettlement.fromJson(Map<String, Object?> j) => CodSettlement(
    id: j['id']! as String,
    reference: (j['reference'] as String?) ?? '',
    courierName: (j['courier_name'] as String?) ?? '',
    status: (j['status'] as String?) ?? 'needs_review',
    netMinor: (j['net_minor'] as num?)?.toInt() ?? 0,
    currency: (j['currency'] as String?) ?? 'NPR',
    issueCount: (j['issue_count'] as num?)?.toInt() ?? 0,
  );

  final String id;
  final String reference;
  final String courierName;

  /// needs_review | reconciled | confirmed
  final String status;
  final int netMinor;
  final String currency;
  final int issueCount;
}

@immutable
class CodOverview {
  const CodOverview({
    required this.withCouriersMinor,
    required this.withCouriersCount,
    required this.overTwoWeeksMinor,
    required this.needingReview,
  });

  factory CodOverview.fromJson(Map<String, Object?> j) {
    final age = (j['awaiting_by_age'] as Map<String, Object?>?) ?? const {};
    var amount = 0;
    var count = 0;
    for (final v in age.values) {
      if (v is Map) {
        amount += (v['amount_minor'] as num?)?.toInt() ?? 0;
        count += (v['count'] as num?)?.toInt() ?? 0;
      }
    }
    return CodOverview(
      withCouriersMinor: amount,
      withCouriersCount: count,
      overTwoWeeksMinor:
          ((age['d15_plus'] as Map?)?['amount_minor'] as num?)?.toInt() ?? 0,
      needingReview: (j['settlements_needing_review'] as num?)?.toInt() ?? 0,
    );
  }

  /// Delivered COD cash the couriers still owe the shop.
  final int withCouriersMinor;
  final int withCouriersCount;
  final int overTwoWeeksMinor;
  final int needingReview;
}

class FulfillmentApi {
  FulfillmentApi(this._dio);

  final Dio _dio;

  Future<CourierOptions> rates(String orderId) => apiCall(() async {
    final r = await _dio.get<Map<String, Object?>>(
      '/couriers/rates',
      queryParameters: {'order_id': orderId},
    );
    return CourierOptions.fromJson(r.data!);
  });

  Future<List<Shipment>> forOrder(String orderId) => apiCall(() async {
    final r = await _dio.get<Map<String, Object?>>(
      '/orders/$orderId/shipments',
    );
    return itemsOf(r.data).map(Shipment.fromJson).toList();
  });

  /// [idempotencyKey]: one per booking attempt, reused on retry so a double
  /// tap or a dropped connection never books the courier twice.
  Future<Shipment> book(
    String orderId, {
    required String courierAccountId,
    required String idempotencyKey,
    String? serviceCode,
    String? trackingNumber,
    String? courierName,
  }) => apiCall(() async {
    final r = await _dio.post<Map<String, Object?>>(
      '/orders/$orderId/shipments',
      data: {
        'courier_account_id': courierAccountId,
        if (serviceCode != null) 'service_code': serviceCode,
        if ((trackingNumber ?? '').isNotEmpty)
          'tracking_number': trackingNumber,
        if ((courierName ?? '').isNotEmpty) 'courier_name': courierName,
      },
      options: Options(extra: {ApiExtra.idempotencyKey: idempotencyKey}),
    );
    return Shipment.fromJson(r.data!);
  });

  Future<void> _post(String path, [Object? data]) =>
      apiCall(() => _dio.post<Object?>(path, data: data ?? const {}));

  Future<void> requestPickup(String id) => _post('/shipments/pickup', {
    'shipment_ids': [id],
  });

  Future<void> cancel(String id) => _post('/shipments/$id/cancel');

  Future<void> refresh(String id) => _post('/shipments/$id/refresh');

  Future<void> reattempt(String id, String? note) => _post(
    '/shipments/$id/reattempt',
    {if ((note ?? '').isNotEmpty) 'note': note},
  );

  Future<void> returnToSender(String id) => _post('/shipments/$id/return');

  Future<void> receivedBack(String id) => _post('/shipments/$id/received-back');

  Future<void> setStatus(
    String id,
    String status, {
    String? failureReason,
    String? note,
  }) => _post('/shipments/$id/status', {
    'status': status,
    if (failureReason != null) 'failure_reason': failureReason,
    if ((note ?? '').isNotEmpty) 'note': note,
  });

  Future<CodOverview> codOverview() => apiCall(() async {
    final r = await _dio.get<Map<String, Object?>>('/cod/overview');
    return CodOverview.fromJson(r.data!);
  });

  Future<List<CodAwaiting>> codAwaiting() => apiCall(() async {
    final r = await _dio.get<Map<String, Object?>>('/cod/awaiting');
    return itemsOf(r.data).map(CodAwaiting.fromJson).toList();
  });

  Future<List<CodSettlement>> settlements() => apiCall(() async {
    final r = await _dio.get<Map<String, Object?>>('/cod/settlements');
    return itemsOf(r.data).map(CodSettlement.fromJson).toList();
  });

  Future<void> confirmSettlement(String id) =>
      _post('/cod/settlements/$id/confirm');
}

final fulfillmentApiProvider = Provider<FulfillmentApi>(
  (ref) => FulfillmentApi(ref.watch(dioProvider)),
);

final orderShipmentsProvider = FutureProvider.autoDispose
    .family<List<Shipment>, String>(
      (ref, orderId) => ref.watch(fulfillmentApiProvider).forOrder(orderId),
    );

final courierOptionsProvider = FutureProvider.autoDispose
    .family<CourierOptions, String>(
      (ref, orderId) => ref.watch(fulfillmentApiProvider).rates(orderId),
    );

final codOverviewProvider = FutureProvider.autoDispose<CodOverview>(
  (ref) => ref.watch(fulfillmentApiProvider).codOverview(),
);

final codAwaitingProvider = FutureProvider.autoDispose<List<CodAwaiting>>(
  (ref) => ref.watch(fulfillmentApiProvider).codAwaiting(),
);

final codSettlementsProvider = FutureProvider.autoDispose<List<CodSettlement>>(
  (ref) => ref.watch(fulfillmentApiProvider).settlements(),
);
