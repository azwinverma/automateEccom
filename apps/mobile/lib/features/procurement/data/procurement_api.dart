import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/api_call.dart';
import '../../../core/api/providers.dart';
import '../../../core/api/request_context_interceptor.dart';

/// Purchase order statuses (spec 13, Phase 8), in lifecycle order.
const poStatuses = [
  'draft',
  'pending_approval',
  'approved',
  'sent',
  'partially_received',
  'received',
  'cancelled',
];

/// Filter chips on the list: null = everything.
const poFilters = <String?>[
  null,
  'pending_approval',
  'sent',
  'draft',
  'received',
];

int _int(Object? v) => (v as num?)?.toInt() ?? 0;
int? _intOrNull(Object? v) => (v as num?)?.toInt();
double? _dbl(Object? v) => (v as num?)?.toDouble();
DateTime? _date(Object? v) => v is String ? DateTime.tryParse(v) : null;
List<Map<String, Object?>> _list(Object? v) =>
    ((v as List<Object?>?) ?? const [])
        .whereType<Map<String, Object?>>()
        .toList(growable: false);

@immutable
class PoLine {
  const PoLine({
    required this.id,
    required this.variantId,
    required this.title,
    required this.variant,
    required this.sku,
    required this.quantity,
    required this.unitCostMinor,
    required this.landedUnitCostMinor,
    required this.receivedQuantity,
    required this.defectiveQuantity,
    required this.remaining,
  });

  factory PoLine.fromJson(Map<String, Object?> j) => PoLine(
    id: (j['id'] as String?) ?? '',
    variantId: (j['variant_id'] as String?) ?? '',
    title: (j['title'] as String?) ?? '',
    variant: j['variant'] as String?,
    sku: j['sku'] as String?,
    quantity: _int(j['quantity']),
    unitCostMinor: _int(j['unit_cost_minor']),
    landedUnitCostMinor: _intOrNull(j['landed_unit_cost_minor']),
    receivedQuantity: _int(j['received_quantity']),
    defectiveQuantity: _int(j['defective_quantity']),
    remaining: _int(j['remaining']),
  );

  final String id;
  final String variantId;
  final String title;
  final String? variant;
  final String? sku;
  final int quantity;
  final int unitCostMinor;
  final int? landedUnitCostMinor;
  final int receivedQuantity;
  final int defectiveQuantity;
  final int remaining;

  String get label => variant == null ? title : '$title ($variant)';
}

@immutable
class PoReceipt {
  const PoReceipt({
    required this.lotCode,
    required this.receivedAt,
    required this.good,
    required this.defective,
  });

  factory PoReceipt.fromJson(Map<String, Object?> j) {
    final lines = _list(j['lines']);
    return PoReceipt(
      lotCode: (j['lot_code'] as String?) ?? '',
      receivedAt: _date(j['received_at']),
      good: lines.fold(0, (s, l) => s + _int(l['quantity'])),
      defective: lines.fold(0, (s, l) => s + _int(l['defective_quantity'])),
    );
  }

  final String lotCode;
  final DateTime? receivedAt;
  final int good;
  final int defective;
}

@immutable
class PurchaseOrder {
  const PurchaseOrder({
    required this.id,
    required this.number,
    required this.status,
    required this.source,
    required this.supplierId,
    required this.supplierName,
    required this.supplierPhone,
    required this.currency,
    required this.subtotalMinor,
    required this.freightMinor,
    required this.dutyMinor,
    required this.otherMinor,
    required this.totalMinor,
    required this.expectedAt,
    required this.notes,
    required this.approvalReason,
    required this.createdAt,
    required this.lines,
    required this.receipts,
    required this.belowMoq,
    required this.shareText,
  });

  factory PurchaseOrder.fromJson(Map<String, Object?> j) {
    final s = (j['supplier'] as Map<String, Object?>?) ?? const {};
    return PurchaseOrder(
      id: (j['id'] as String?) ?? '',
      number: (j['number'] as String?) ?? '',
      status: (j['status'] as String?) ?? 'draft',
      source: (j['source'] as String?) ?? 'seller',
      supplierId: (s['id'] as String?) ?? '',
      supplierName: (s['name'] as String?) ?? '',
      supplierPhone: s['phone'] as String?,
      currency: (j['currency'] as String?) ?? 'NPR',
      subtotalMinor: _int(j['subtotal_minor']),
      freightMinor: _int(j['freight_minor']),
      dutyMinor: _int(j['duty_minor']),
      otherMinor: _int(j['other_minor']),
      totalMinor: _int(j['total_minor']),
      expectedAt: _date(j['expected_at']),
      notes: j['notes'] as String?,
      approvalReason: j['approval_reason'] as String?,
      createdAt: _date(j['created_at']),
      lines: _list(j['lines']).map(PoLine.fromJson).toList(growable: false),
      receipts: _list(
        j['receipts'],
      ).map(PoReceipt.fromJson).toList(growable: false),
      belowMoq: {
        for (final w in _list(j['warnings']))
          if (w['code'] == 'below_moq')
            (w['variant_id'] as String?) ?? '': _int(w['moq']),
      },
      shareText: (j['share_text'] as String?) ?? '',
    );
  }

  final String id;
  final String number;
  final String status;
  final String source;
  final String supplierId;
  final String supplierName;
  final String? supplierPhone;
  final String currency;
  final int subtotalMinor;
  final int freightMinor;
  final int dutyMinor;
  final int otherMinor;
  final int totalMinor;
  final DateTime? expectedAt;
  final String? notes;
  final String? approvalReason;
  final DateTime? createdAt;
  final List<PoLine> lines;
  final List<PoReceipt> receipts;

  /// variant id → the supplier's minimum order quantity it falls short of.
  final Map<String, int> belowMoq;
  final String shareText;

  int get extrasMinor => freightMinor + dutyMinor + otherMinor;
  bool get receivable =>
      status == 'approved' ||
      status == 'sent' ||
      status == 'partially_received';
}

/// SPI-001 performance; every number may be missing (thin data shows "–").
@immutable
class SupplierPerformance {
  const SupplierPerformance({
    required this.receivedUnits,
    required this.avgLandedCostMinor,
    required this.defectRate,
    required this.soldUnits,
    required this.qualityReturnRate,
    required this.onTimeRate,
    required this.leadTimeDaysAvg,
    required this.contributionPerUnitMinor,
    required this.notIncluded,
  });

  factory SupplierPerformance.fromJson(Map<String, Object?> j) =>
      SupplierPerformance(
        receivedUnits: _int(j['received_units']),
        avgLandedCostMinor: _intOrNull(j['avg_landed_cost_minor']),
        defectRate: _dbl(j['defect_rate']),
        soldUnits: _int(j['sold_units']),
        qualityReturnRate: _dbl(j['quality_return_rate']),
        onTimeRate: _dbl(j['on_time_rate']),
        leadTimeDaysAvg: _dbl(j['lead_time_days_avg']),
        contributionPerUnitMinor: _intOrNull(j['contribution_per_unit_minor']),
        notIncluded: ((j['not_included'] as List<Object?>?) ?? const [])
            .whereType<String>()
            .toList(growable: false),
      );

  final int receivedUnits;
  final int? avgLandedCostMinor;
  final double? defectRate;
  final int soldUnits;
  final double? qualityReturnRate;
  final double? onTimeRate;
  final double? leadTimeDaysAvg;
  final int? contributionPerUnitMinor;
  final List<String> notIncluded;
}

@immutable
class SupplierDetail {
  const SupplierDetail({
    required this.id,
    required this.name,
    required this.phone,
    required this.contactName,
    required this.paymentTerms,
    required this.defaultLeadTimeDays,
    required this.performance,
    this.currency = 'NPR',
  });

  factory SupplierDetail.fromJson(Map<String, Object?> j) {
    final p = j['performance'];
    return SupplierDetail(
      id: (j['id'] as String?) ?? '',
      name: (j['name'] as String?) ?? '',
      phone: j['phone'] as String?,
      contactName: j['contact_name'] as String?,
      paymentTerms: j['payment_terms'] as String?,
      defaultLeadTimeDays: _intOrNull(j['default_lead_time_days']),
      performance:
          p is Map<String, Object?> ? SupplierPerformance.fromJson(p) : null,
      currency: (j['currency'] as String?) ?? 'NPR',
    );
  }

  final String id;
  final String name;
  final String? phone;
  final String? contactName;
  final String? paymentTerms;
  final int? defaultLeadTimeDays;
  final SupplierPerformance? performance;
  final String currency;
}

class ProcurementApi {
  ProcurementApi(this._dio);

  final Dio _dio;

  Future<List<PurchaseOrder>> list(String? status) => apiCall(() async {
    final r = await _dio.get<Map<String, Object?>>(
      '/procurement/purchase-orders',
      queryParameters: {if (status != null) 'status': status},
    );
    return _list(
      r.data?['items'],
    ).map(PurchaseOrder.fromJson).toList(growable: false);
  });

  Future<PurchaseOrder> get(String id) => apiCall(() async {
    final r = await _dio.get<Map<String, Object?>>(
      '/procurement/purchase-orders/$id',
    );
    return PurchaseOrder.fromJson(r.data ?? const {});
  });

  Future<void> _post(String path, [Object? data]) =>
      apiCall(() => _dio.post<Object?>(path, data: data ?? const {}));

  Future<void> submit(String id) =>
      _post('/procurement/purchase-orders/$id/submit');

  Future<void> approve(String id) =>
      _post('/procurement/purchase-orders/$id/approve');

  Future<void> reject(String id, String reason) =>
      _post('/procurement/purchase-orders/$id/reject', {'reason': reason});

  Future<void> markSent(String id) =>
      _post('/procurement/purchase-orders/$id/send');

  /// [idempotencyKey]: one per receive sheet, reused on retry (never stocks twice).
  Future<void> receive(
    String id, {
    required List<Map<String, Object?>> lines,
    String? lotCode,
    required String idempotencyKey,
  }) => apiCall(
    () => _dio.post<Object?>(
      '/procurement/purchase-orders/$id/receipts',
      data: {
        'lines': lines,
        if (lotCode != null && lotCode.isNotEmpty) 'lot_code': lotCode,
      },
      options: Options(extra: {ApiExtra.idempotencyKey: idempotencyKey}),
    ),
  );

  Future<SupplierDetail> supplier(String id) => apiCall(() async {
    final r = await _dio.get<Map<String, Object?>>(
      '/procurement/suppliers/$id',
    );
    return SupplierDetail.fromJson(r.data ?? const {});
  });
}

final procurementApiProvider = Provider<ProcurementApi>(
  (ref) => ProcurementApi(ref.watch(dioProvider)),
);

final purchaseOrdersProvider = FutureProvider.autoDispose
    .family<List<PurchaseOrder>, String?>(
      (ref, status) => ref.watch(procurementApiProvider).list(status),
    );

final purchaseOrderProvider = FutureProvider.autoDispose
    .family<PurchaseOrder, String>(
      (ref, id) => ref.watch(procurementApiProvider).get(id),
    );

final supplierProvider = FutureProvider.autoDispose
    .family<SupplierDetail, String>(
      (ref, id) => ref.watch(procurementApiProvider).supplier(id),
    );
