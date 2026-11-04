import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/api_call.dart';
import '../../../core/api/providers.dart';
import '../../../core/api/request_context_interceptor.dart';
import '../../fulfillment/data/fulfillment_api.dart';

int _minor(Object? money) =>
    money is Map ? ((money['amount_minor'] as num?)?.toInt() ?? 0) : 0;
String _currency(Object? money) =>
    money is Map ? ((money['currency'] as String?) ?? 'NPR') : 'NPR';
List<Map<String, Object?>> _list(Object? v) =>
    ((v as List<Object?>?) ?? const [])
        .whereType<Map<String, Object?>>()
        .toList(growable: false);

/// Controlled return reasons (spec 12); free text goes in the note.
const returnReasons = [
  'size_small',
  'size_large',
  'colour_different',
  'quality_defect',
  'damaged_in_transit',
  'not_as_described',
  'changed_mind',
  'late_delivery',
  'wrong_item',
  'other',
];

const returnConditions = ['resellable', 'damaged', 'missing', 'used'];

const refundMethods = [
  'original_payment',
  'esewa',
  'khalti',
  'fonepay',
  'bank_transfer',
  'cash',
  'other',
];

const returnBuckets = ['to_decide', 'in_progress', 'to_refund', 'done'];

@immutable
class ReturnCheck {
  const ReturnCheck({
    required this.code,
    required this.ok,
    required this.soft,
    this.windowDays,
  });

  factory ReturnCheck.fromJson(Map<String, Object?> j) => ReturnCheck(
    code: (j['code'] as String?) ?? '',
    ok: (j['ok'] as bool?) ?? true,
    soft: (j['soft'] as bool?) ?? false,
    windowDays: (j['window_days'] as num?)?.toInt(),
  );

  final String code;
  final bool ok;

  /// Soft checks can be overridden (with a reason) when approving.
  final bool soft;
  final int? windowDays;
}

@immutable
class ReturnSignal {
  const ReturnSignal({
    required this.code,
    this.count,
    this.days,
    this.returned,
    this.orders,
  });

  factory ReturnSignal.fromJson(Map<String, Object?> j) => ReturnSignal(
    code: (j['code'] as String?) ?? '',
    count: (j['count'] as num?)?.toInt(),
    days: (j['days'] as num?)?.toInt(),
    returned: (j['returned'] as num?)?.toInt(),
    orders: (j['orders'] as num?)?.toInt(),
  );

  final String code;
  final int? count;
  final int? days;
  final int? returned;
  final int? orders;
}

@immutable
class ReturnLine {
  const ReturnLine({
    required this.id,
    required this.title,
    required this.quantity,
    required this.reason,
    required this.unitRefundMinor,
    this.variantTitle,
    this.exchangeTitle,
    this.condition,
    this.restocked = 0,
  });

  factory ReturnLine.fromJson(Map<String, Object?> j) => ReturnLine(
    id: j['id']! as String,
    title: (j['title'] as String?) ?? '',
    variantTitle: j['variant_title'] as String?,
    quantity: (j['quantity'] as num?)?.toInt() ?? 1,
    reason: (j['reason'] as String?) ?? 'other',
    unitRefundMinor: (j['unit_refund_minor'] as num?)?.toInt() ?? 0,
    exchangeTitle:
        (j['exchange'] as Map<String, Object?>?)?['title'] as String?,
    condition: j['condition'] as String?,
    restocked: (j['restocked_quantity'] as num?)?.toInt() ?? 0,
  );

  final String id;
  final String title;
  final String? variantTitle;
  final int quantity;
  final String reason;
  final int unitRefundMinor;
  final String? exchangeTitle;
  final String? condition;
  final int restocked;

  String get label =>
      variantTitle == null || variantTitle == 'Default'
          ? title
          : '$title ($variantTitle)';
}

@immutable
class RefundRecord {
  const RefundRecord({
    required this.id,
    required this.amountMinor,
    required this.currency,
    required this.method,
    required this.status,
    this.reference,
  });

  factory RefundRecord.fromJson(Map<String, Object?> j) => RefundRecord(
    id: j['id']! as String,
    amountMinor: _minor(j['amount']),
    currency: _currency(j['amount']),
    method: (j['method'] as String?) ?? 'other',
    status: (j['status'] as String?) ?? 'processing',
    reference: j['reference'] as String?,
  );

  final String id;
  final int amountMinor;
  final String currency;
  final String method;

  /// pending_approval | processing | succeeded | failed | rejected
  final String status;
  final String? reference;
}

@immutable
class ReturnSummary {
  const ReturnSummary({
    required this.id,
    required this.number,
    required this.orderId,
    required this.status,
    required this.resolution,
    required this.eligible,
    required this.refundDueMinor,
    required this.currency,
    this.orderNumber,
    this.customerName,
    this.signals = const [],
  });

  factory ReturnSummary.fromJson(Map<String, Object?> j) => ReturnSummary(
    id: j['id']! as String,
    number: (j['number'] as String?) ?? '',
    orderId: (j['order_id'] as String?) ?? '',
    orderNumber: (j['order_number'] as num?)?.toInt(),
    customerName: j['customer_name'] as String?,
    status: (j['status'] as String?) ?? 'requested',
    resolution: (j['resolution'] as String?) ?? 'refund',
    eligible: (j['eligible'] as bool?) ?? true,
    refundDueMinor: _minor(j['refund_due']),
    currency: _currency(j['refund_due']),
    signals: _list(j['signals']).map(ReturnSignal.fromJson).toList(),
  );

  final String id;
  final String number;
  final String orderId;
  final int? orderNumber;
  final String? customerName;
  final String status;

  /// refund | exchange
  final String resolution;
  final bool eligible;
  final int refundDueMinor;
  final String currency;
  final List<ReturnSignal> signals;
}

@immutable
class ReturnDetail {
  const ReturnDetail({
    required this.summary,
    required this.lines,
    required this.checks,
    required this.refunds,
    required this.actions,
    required this.refundableMinor,
    this.pickup,
    this.overrideReason,
    this.rejectionReason,
  });

  factory ReturnDetail.fromJson(Map<String, Object?> j) => ReturnDetail(
    summary: ReturnSummary.fromJson(j),
    lines: _list(j['lines']).map(ReturnLine.fromJson).toList(),
    checks:
        _list(
          (j['eligibility'] as Map<String, Object?>?)?['checks'],
        ).map(ReturnCheck.fromJson).toList(),
    refunds: _list(j['refunds']).map(RefundRecord.fromJson).toList(),
    actions: ((j['actions'] as List<Object?>?) ?? const [])
        .whereType<String>()
        .toList(growable: false),
    refundableMinor: (j['refundable_minor'] as num?)?.toInt() ?? 0,
    pickup:
        j['pickup'] is Map<String, Object?>
            ? Shipment.fromJson(j['pickup']! as Map<String, Object?>)
            : null,
    overrideReason: j['override_reason'] as String?,
    rejectionReason: j['rejection_reason'] as String?,
  );

  final ReturnSummary summary;
  final List<ReturnLine> lines;
  final List<ReturnCheck> checks;
  final List<RefundRecord> refunds;

  /// Server-driven: approve | reject | cancel | book_pickup | mark_received |
  /// inspect | refund.
  final List<String> actions;
  final int refundableMinor;
  final Shipment? pickup;
  final String? overrideReason;
  final String? rejectionReason;
}

@immutable
class ExchangeOption {
  const ExchangeOption({
    required this.variantId,
    required this.title,
    this.available,
  });

  factory ExchangeOption.fromJson(Map<String, Object?> j) => ExchangeOption(
    variantId: j['variant_id']! as String,
    title: (j['title'] as String?) ?? '',
    available: (j['available'] as num?)?.toInt(),
  );

  final String variantId;
  final String title;

  /// null = stock isn't tracked for this variant.
  final int? available;
}

@immutable
class ReturnableLine {
  const ReturnableLine({
    required this.orderLineId,
    required this.title,
    required this.returnableQuantity,
    required this.unitRefundMinor,
    required this.finalSale,
    required this.exchangeOptions,
    this.variantTitle,
  });

  factory ReturnableLine.fromJson(Map<String, Object?> j) => ReturnableLine(
    orderLineId: j['order_line_id']! as String,
    title: (j['title'] as String?) ?? '',
    variantTitle: j['variant_title'] as String?,
    returnableQuantity: (j['returnable_quantity'] as num?)?.toInt() ?? 0,
    unitRefundMinor: (j['unit_refund_minor'] as num?)?.toInt() ?? 0,
    finalSale: (j['final_sale'] as bool?) ?? false,
    exchangeOptions:
        _list(j['exchange_options']).map(ExchangeOption.fromJson).toList(),
  );

  final String orderLineId;
  final String title;
  final String? variantTitle;
  final int returnableQuantity;
  final int unitRefundMinor;
  final bool finalSale;
  final List<ExchangeOption> exchangeOptions;

  String get label =>
      variantTitle == null || variantTitle == 'Default'
          ? title
          : '$title ($variantTitle)';
}

@immutable
class Returnable {
  const Returnable({
    required this.lines,
    required this.currency,
    required this.allowRefund,
    required this.allowExchange,
  });

  factory Returnable.fromJson(Map<String, Object?> j) {
    final policy = (j['policy'] as Map<String, Object?>?) ?? const {};
    return Returnable(
      lines: _list(j['lines']).map(ReturnableLine.fromJson).toList(),
      currency: (j['currency'] as String?) ?? 'NPR',
      allowRefund: (policy['allow_refund'] as bool?) ?? true,
      allowExchange: (policy['allow_exchange'] as bool?) ?? true,
    );
  }

  final List<ReturnableLine> lines;
  final String currency;
  final bool allowRefund;
  final bool allowExchange;
}

@immutable
class ReturnLineInput {
  const ReturnLineInput({
    required this.orderLineId,
    required this.quantity,
    required this.reason,
    this.exchangeVariantId,
  });

  final String orderLineId;
  final int quantity;
  final String reason;
  final String? exchangeVariantId;

  Map<String, Object?> toJson() => {
    'order_line_id': orderLineId,
    'quantity': quantity,
    'reason': reason,
    if (exchangeVariantId != null) 'exchange_variant_id': exchangeVariantId,
  };
}

@immutable
class EligibilityResult {
  const EligibilityResult({
    required this.eligible,
    required this.canRequest,
    required this.checks,
  });

  factory EligibilityResult.fromJson(Map<String, Object?> j) =>
      EligibilityResult(
        eligible: (j['eligible'] as bool?) ?? false,
        canRequest: (j['can_request'] as bool?) ?? false,
        checks: _list(j['checks']).map(ReturnCheck.fromJson).toList(),
      );

  final bool eligible;
  final bool canRequest;
  final List<ReturnCheck> checks;
}

@immutable
class ReturnsPage {
  const ReturnsPage({required this.items, required this.counts});

  final List<ReturnSummary> items;
  final Map<String, int> counts;
}

class ReturnsApi {
  ReturnsApi(this._dio);

  final Dio _dio;

  Future<List<ReturnDetail>> forOrder(String orderId) => apiCall(() async {
    final r = await _dio.get<Map<String, Object?>>('/orders/$orderId/returns');
    return itemsOf(r.data).map(ReturnDetail.fromJson).toList();
  });

  Future<Returnable> returnable(String orderId) => apiCall(() async {
    final r = await _dio.get<Map<String, Object?>>(
      '/orders/$orderId/returnable',
    );
    return Returnable.fromJson(r.data!);
  });

  Future<EligibilityResult> check(
    String orderId,
    String resolution,
    List<ReturnLineInput> lines,
  ) => apiCall(() async {
    final r = await _dio.post<Map<String, Object?>>(
      '/orders/$orderId/returns/check',
      data: {
        'resolution': resolution,
        'lines': [for (final l in lines) l.toJson()],
      },
    );
    return EligibilityResult.fromJson(r.data!);
  });

  /// [idempotencyKey]: one per sheet, reused on retry (no duplicate returns).
  Future<ReturnDetail> create(
    String orderId, {
    required String resolution,
    required List<ReturnLineInput> lines,
    required String idempotencyKey,
  }) => apiCall(() async {
    final r = await _dio.post<Map<String, Object?>>(
      '/orders/$orderId/returns',
      data: {
        'resolution': resolution,
        'lines': [for (final l in lines) l.toJson()],
      },
      options: Options(extra: {ApiExtra.idempotencyKey: idempotencyKey}),
    );
    return ReturnDetail.fromJson(r.data!);
  });

  Future<ReturnDetail> get(String id) => apiCall(() async {
    final r = await _dio.get<Map<String, Object?>>('/returns/$id');
    return ReturnDetail.fromJson(r.data!);
  });

  Future<ReturnsPage> list(String bucket) => apiCall(() async {
    final r = await _dio.get<Map<String, Object?>>(
      '/returns',
      queryParameters: {'bucket': bucket},
    );
    final counts = (r.data?['counts'] as Map<String, Object?>?) ?? const {};
    return ReturnsPage(
      items: itemsOf(r.data).map(ReturnSummary.fromJson).toList(),
      counts: {
        for (final e in counts.entries) e.key: (e.value as num?)?.toInt() ?? 0,
      },
    );
  });

  Future<void> _post(String path, [Object? data]) =>
      apiCall(() => _dio.post<Object?>(path, data: data ?? const {}));

  Future<void> approve(String id, {String? overrideReason}) => _post(
    '/returns/$id/approve',
    {if ((overrideReason ?? '').isNotEmpty) 'override_reason': overrideReason},
  );

  Future<void> reject(String id, String reason) =>
      _post('/returns/$id/reject', {'reason': reason});

  Future<void> cancel(String id) => _post('/returns/$id/cancel');

  Future<void> received(String id) => _post('/returns/$id/received');

  Future<void> inspect(String id, List<Map<String, Object?>> items) =>
      _post('/returns/$id/inspect', {'items': items});

  Future<void> refund(
    String orderId, {
    required String returnId,
    required int amountMinor,
    required String method,
    required String idempotencyKey,
    String? reference,
  }) => apiCall(
    () => _dio.post<Object?>(
      '/orders/$orderId/refunds',
      data: {
        'amount_minor': amountMinor,
        'method': method,
        'return_id': returnId,
        if ((reference ?? '').isNotEmpty) 'reference': reference,
      },
      options: Options(extra: {ApiExtra.idempotencyKey: idempotencyKey}),
    ),
  );
}

final returnsApiProvider = Provider<ReturnsApi>(
  (ref) => ReturnsApi(ref.watch(dioProvider)),
);

final orderReturnsProvider = FutureProvider.autoDispose
    .family<List<ReturnDetail>, String>(
      (ref, orderId) => ref.watch(returnsApiProvider).forOrder(orderId),
    );

final returnableProvider = FutureProvider.autoDispose
    .family<Returnable, String>(
      (ref, orderId) => ref.watch(returnsApiProvider).returnable(orderId),
    );

final returnDetailProvider = FutureProvider.autoDispose
    .family<ReturnDetail, String>(
      (ref, id) => ref.watch(returnsApiProvider).get(id),
    );

final returnsPageProvider = FutureProvider.autoDispose
    .family<ReturnsPage, String>(
      (ref, bucket) => ref.watch(returnsApiProvider).list(bucket),
    );
