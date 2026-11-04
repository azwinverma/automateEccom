import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/api_call.dart';
import '../../../core/api/providers.dart';

int _minor(Object? money) =>
    money is Map ? ((money['amount_minor'] as num?)?.toInt() ?? 0) : 0;

@immutable
class OrderLine {
  const OrderLine({
    required this.id,
    required this.title,
    required this.quantity,
    required this.cancelledQuantity,
    required this.unitPriceMinor,
    required this.lineTotalMinor,
    this.variantTitle,
    this.sku,
    this.matched = true,
  });

  factory OrderLine.fromJson(Map<String, Object?> j) => OrderLine(
    id: j['id']! as String,
    title: (j['title'] as String?) ?? '',
    variantTitle: j['variant_title'] as String?,
    sku: j['sku'] as String?,
    quantity: (j['quantity'] as num?)?.toInt() ?? 0,
    cancelledQuantity: (j['cancelled_quantity'] as num?)?.toInt() ?? 0,
    unitPriceMinor: _minor(j['unit_price']),
    lineTotalMinor: _minor(j['line_total']),
    matched: (j['matched'] as bool?) ?? true,
  );

  final String id;
  final String title;
  final String? variantTitle;
  final String? sku;
  final int quantity;
  final int cancelledQuantity;
  final int unitPriceMinor;
  final int lineTotalMinor;
  final bool matched;
}

@immutable
class ShippingAddress {
  const ShippingAddress({
    this.recipientName,
    this.phone,
    this.districtName,
    this.municipality,
    this.ward,
    this.area,
    this.landmark,
    this.text,
  });

  factory ShippingAddress.fromJson(Map<String, Object?> j) => ShippingAddress(
    recipientName: j['recipient_name'] as String?,
    phone: j['phone'] as String?,
    districtName: (j['district_name'] ?? j['district']) as String?,
    municipality: j['municipality'] as String?,
    ward: (j['ward'] as num?)?.toInt(),
    area: j['area'] as String?,
    landmark: j['landmark'] as String?,
    text: j['text'] as String?,
  );

  final String? recipientName;
  final String? phone;
  final String? districtName;
  final String? municipality;
  final int? ward;
  final String? area;
  final String? landmark;
  final String? text;

  /// One-line address: "Pulchowk, Lalitpur Metropolitan City-3, Lalitpur".
  String get line {
    final parts = [
      if ((area ?? '').isNotEmpty) area!,
      if ((municipality ?? '').isNotEmpty)
        ward == null ? municipality! : '$municipality-$ward',
      if ((districtName ?? '').isNotEmpty) districtName!,
    ];
    return parts.isEmpty ? (text ?? '') : parts.join(', ');
  }
}

@immutable
class OrderSummary {
  const OrderSummary({
    required this.id,
    required this.number,
    required this.status,
    required this.source,
    required this.currency,
    required this.totalMinor,
    required this.paymentMethod,
    required this.paymentStatus,
    required this.version,
    this.allowedTransitions = const [],
    this.customerName,
    this.customerPhone,
    this.needsReview,
    this.placedAt,
    this.externalNumber,
  });

  factory OrderSummary.fromJson(Map<String, Object?> j) {
    final c = j['customer'] as Map<String, Object?>?;
    return OrderSummary(
      id: j['id']! as String,
      number: (j['number'] as num?)?.toInt() ?? 0,
      status: (j['status'] as String?) ?? 'draft',
      source: (j['source'] as String?) ?? 'seller',
      currency: (j['currency'] as String?) ?? 'NPR',
      totalMinor: _minor(j['total']),
      paymentMethod: (j['payment_method'] as String?) ?? 'cod',
      paymentStatus: (j['payment_status'] as String?) ?? 'unpaid',
      version: (j['version'] as num?)?.toInt() ?? 1,
      allowedTransitions: ((j['allowed_transitions'] as List<Object?>?) ??
              const [])
          .whereType<String>()
          .toList(growable: false),
      customerName: c?['display_name'] as String?,
      customerPhone: c?['phone'] as String?,
      needsReview: j['needs_review'] as String?,
      placedAt:
          j['placed_at'] is String
              ? DateTime.tryParse(j['placed_at']! as String)
              : null,
      externalNumber: j['external_number'] as String?,
    );
  }

  final String id;
  final int number;

  /// draft | pending_confirmation | confirmed | payment_pending | cod_pending
  /// | ready_to_ship | shipped | delivered | completed | cancelled |
  /// delivery_failed | returned
  final String status;
  final String source;
  final String currency;
  final int totalMinor;
  final String paymentMethod;
  final String paymentStatus;
  final int version;
  final List<String> allowedTransitions;
  final String? customerName;
  final String? customerPhone;
  final String? needsReview;
  final DateTime? placedAt;
  final String? externalNumber;
}

@immutable
class OrderDetail {
  const OrderDetail({
    required this.summary,
    required this.lines,
    required this.subtotalMinor,
    required this.deliveryFeeMinor,
    required this.discountMinor,
    required this.shipping,
    this.notes,
    this.cancelReason,
    this.conversationId,
  });

  factory OrderDetail.fromJson(Map<String, Object?> j) {
    final totals = (j['totals'] as Map<String, Object?>?) ?? const {};
    return OrderDetail(
      summary: OrderSummary.fromJson(j),
      lines: ((j['lines'] as List<Object?>?) ?? const [])
          .whereType<Map<String, Object?>>()
          .map(OrderLine.fromJson)
          .toList(growable: false),
      subtotalMinor: _minor(totals['subtotal']),
      deliveryFeeMinor: _minor(totals['delivery_fee']),
      discountMinor: _minor(totals['discount']),
      shipping: ShippingAddress.fromJson(
        (j['shipping'] as Map<String, Object?>?) ?? const {},
      ),
      notes: j['notes'] as String?,
      cancelReason: j['cancel_reason'] as String?,
      conversationId: j['conversation_id'] as String?,
    );
  }

  final OrderSummary summary;
  final List<OrderLine> lines;
  final int subtotalMinor;
  final int deliveryFeeMinor;
  final int discountMinor;
  final ShippingAddress shipping;
  final String? notes;
  final String? cancelReason;
  final String? conversationId;
}

@immutable
class OrderEvent {
  const OrderEvent({
    required this.id,
    required this.kind,
    required this.actorType,
    required this.automated,
    this.toStatus,
    this.actorDisplay,
    this.provider,
    this.at,
    this.data = const {},
  });

  factory OrderEvent.fromJson(Map<String, Object?> j) {
    final actor = (j['actor'] as Map<String, Object?>?) ?? const {};
    return OrderEvent(
      id: j['id']! as String,
      kind: (j['kind'] as String?) ?? '',
      toStatus: j['to_status'] as String?,
      actorType: (actor['type'] as String?) ?? 'system',
      actorDisplay: actor['display'] as String?,
      automated: (j['automated'] as bool?) ?? false,
      provider: j['provider'] as String?,
      at: j['at'] is String ? DateTime.tryParse(j['at']! as String) : null,
      data: (j['data'] as Map<String, Object?>?) ?? const {},
    );
  }

  final String id;
  final String kind;
  final String? toStatus;
  final String actorType;
  final String? actorDisplay;
  final bool automated;
  final String? provider;
  final DateTime? at;
  final Map<String, Object?> data;
}

/// The order list filters on the seller's job, not raw statuses.
enum OrderFilter {
  needsAction('cod_pending,payment_pending,ready_to_ship'),
  needsReview(null),
  all(null);

  const OrderFilter(this.statuses);
  final String? statuses;
}

class OrdersApi {
  OrdersApi(this._dio);

  final Dio _dio;

  Future<List<OrderSummary>> list(OrderFilter filter) => apiCall(() async {
    final r = await _dio.get<Map<String, Object?>>(
      '/orders',
      queryParameters: {
        if (filter.statuses != null) 'status': filter.statuses,
        if (filter == OrderFilter.needsReview) 'needs_review': true,
      },
    );
    return itemsOf(r.data).map(OrderSummary.fromJson).toList();
  });

  Future<OrderDetail> get(String id) => apiCall(() async {
    final r = await _dio.get<Map<String, Object?>>('/orders/$id');
    return OrderDetail.fromJson(r.data!);
  });

  Future<List<OrderEvent>> timeline(String id) => apiCall(() async {
    final r = await _dio.get<Map<String, Object?>>('/orders/$id/timeline');
    return itemsOf(r.data).map(OrderEvent.fromJson).toList();
  });

  /// [expectedVersion] makes a stale screen fail with `version_conflict`
  /// instead of overwriting someone else's change.
  Future<OrderDetail> transition(
    String id,
    String to, {
    String? reason,
    int? expectedVersion,
  }) => apiCall(() async {
    final r = await _dio.post<Map<String, Object?>>(
      '/orders/$id/transition',
      data: {
        'to': to,
        if (reason != null) 'reason': reason,
        if (expectedVersion != null) 'expected_version': expectedVersion,
      },
    );
    return OrderDetail.fromJson(r.data!);
  });
}

final ordersApiProvider = Provider<OrdersApi>(
  (ref) => OrdersApi(ref.watch(dioProvider)),
);

final ordersProvider = FutureProvider.autoDispose
    .family<List<OrderSummary>, OrderFilter>(
      (ref, filter) => ref.watch(ordersApiProvider).list(filter),
    );

final orderProvider = FutureProvider.autoDispose.family<OrderDetail, String>(
  (ref, id) => ref.watch(ordersApiProvider).get(id),
);

final orderTimelineProvider = FutureProvider.autoDispose
    .family<List<OrderEvent>, String>(
      (ref, id) => ref.watch(ordersApiProvider).timeline(id),
    );
