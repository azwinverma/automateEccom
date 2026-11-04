import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/api_call.dart';
import '../../../core/api/providers.dart';

@immutable
class VariantStock {
  const VariantStock({
    required this.variantId,
    required this.title,
    required this.tracked,
    required this.onHand,
    required this.reserved,
    required this.available,
    this.sku,
    this.low = false,
  });

  factory VariantStock.fromJson(Map<String, Object?> j) {
    final locations =
        ((j['locations'] as List<Object?>?) ?? const [])
            .whereType<Map<String, Object?>>();
    return VariantStock(
      variantId: j['variant_id']! as String,
      title: (j['title'] as String?) ?? '',
      sku: j['sku'] as String?,
      tracked: (j['tracked'] as bool?) ?? false,
      onHand: (j['on_hand'] as num?)?.toInt() ?? 0,
      reserved: (j['reserved'] as num?)?.toInt() ?? 0,
      available: (j['available'] as num?)?.toInt() ?? 0,
      low: locations.any((l) => l['low'] == true),
    );
  }

  final String variantId;
  final String title;
  final String? sku;

  /// False until stock is first recorded: untracked variants never block
  /// orders, and the Sales Agent says the shop will confirm stock.
  final bool tracked;
  final int onHand;
  final int reserved;
  final int available;
  final bool low;
}

class StockApi {
  StockApi(this._dio);

  final Dio _dio;

  Future<List<VariantStock>> productStock(String productId) =>
      apiCall(() async {
        final r = await _dio.get<Map<String, Object?>>(
          '/catalog/products/$productId/stock',
        );
        return ((r.data?['variants'] as List<Object?>?) ?? const [])
            .whereType<Map<String, Object?>>()
            .map(VariantStock.fromJson)
            .toList(growable: false);
      });

  Future<void> receive(String variantId, int quantity) => apiCall(
    () => _dio.post<Map<String, Object?>>(
      '/inventory/variants/$variantId/receive',
      data: {'quantity': quantity},
    ),
  );
}

final stockApiProvider = Provider<StockApi>(
  (ref) => StockApi(ref.watch(dioProvider)),
);

final productStockProvider = FutureProvider.autoDispose
    .family<List<VariantStock>, String>(
      (ref, productId) => ref.watch(stockApiProvider).productStock(productId),
    );
