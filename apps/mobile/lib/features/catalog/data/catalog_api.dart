import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/api_call.dart';
import '../../../core/api/providers.dart';

@immutable
class ProductVariant {
  const ProductVariant({
    required this.id,
    required this.options,
    required this.priceMinor,
    required this.currency,
    required this.status,
    this.sku,
  });

  factory ProductVariant.fromJson(Map<String, Object?> j) {
    final price = (j['price'] as Map<String, Object?>?) ?? const {};
    return ProductVariant(
      id: j['id']! as String,
      options: ((j['options'] as Map<String, Object?>?) ?? const {}).map(
        (k, v) => MapEntry(k, '$v'),
      ),
      priceMinor: (price['amount_minor'] as num?)?.toInt() ?? 0,
      currency: (price['currency'] as String?) ?? 'NPR',
      status: (j['status'] as String?) ?? 'active',
      sku: j['sku'] as String?,
    );
  }

  final String id;
  final Map<String, String> options;
  final int priceMinor;
  final String currency;
  final String status;
  final String? sku;
}

@immutable
class ProductAttribute {
  const ProductAttribute({
    required this.key,
    required this.value,
    required this.confirmed,
    this.confidence,
    this.source,
  });

  factory ProductAttribute.fromJson(Map<String, Object?> j) => ProductAttribute(
    key: j['key']! as String,
    value: (j['value'] as String?) ?? '',
    confirmed: (j['confirmed'] as bool?) ?? false,
    confidence: (j['confidence'] as num?)?.toDouble(),
    source: j['source'] as String?,
  );

  final String key;
  final String value;
  final bool confirmed;
  final double? confidence;
  final String? source;
}

/// `GET /catalog/products/{id}` (subset).
@immutable
class ProductDetail {
  const ProductDetail({
    required this.id,
    required this.title,
    required this.status,
    required this.version,
    this.titleNe,
    this.variants = const [],
    this.attributes = const [],
  });

  factory ProductDetail.fromJson(Map<String, Object?> j) => ProductDetail(
    id: j['id']! as String,
    title: (j['title'] as String?) ?? '',
    titleNe: j['title_ne'] as String?,
    status: (j['status'] as String?) ?? 'draft',
    version: (j['version'] as num?)?.toInt() ?? 1,
    variants: ((j['variants'] as List<Object?>?) ?? const [])
        .whereType<Map<String, Object?>>()
        .map(ProductVariant.fromJson)
        .toList(growable: false),
    attributes: ((j['attributes'] as List<Object?>?) ?? const [])
        .whereType<Map<String, Object?>>()
        .map(ProductAttribute.fromJson)
        .toList(growable: false),
  );

  final String id;
  final String title;
  final String? titleNe;

  /// draft | active | archived
  final String status;
  final int version;
  final List<ProductVariant> variants;
  final List<ProductAttribute> attributes;

  List<ProductVariant> get activeVariants =>
      variants.where((v) => v.status == 'active').toList(growable: false);

  List<ProductAttribute> get unconfirmed =>
      attributes.where((a) => !a.confirmed).toList(growable: false);
}

@immutable
class ChannelListing {
  const ChannelListing({
    required this.connectionId,
    required this.status,
    this.provider,
    this.lastErrorCode,
  });

  factory ChannelListing.fromJson(Map<String, Object?> j) => ChannelListing(
    connectionId: j['connection_id']! as String,
    status: (j['status'] as String?) ?? 'pending',
    provider: j['provider'] as String?,
    lastErrorCode: j['last_error_code'] as String?,
  );

  final String connectionId;

  /// pending | publishing | published | failed | out_of_sync | unpublished
  final String status;
  final String? provider;
  final String? lastErrorCode;

  bool get inFlight => status == 'pending' || status == 'publishing';
}

class CatalogApi {
  CatalogApi(this._dio);

  final Dio _dio;

  Future<ProductDetail> product(String id) => apiCall(() async {
    final r = await _dio.get<Map<String, Object?>>('/catalog/products/$id');
    return ProductDetail.fromJson(r.data!);
  });

  Future<ProductDetail> setStatus(String id, String status, int version) =>
      apiCall(() async {
        final r = await _dio.post<Map<String, Object?>>(
          '/catalog/products/$id/status',
          data: {'status': status, 'version': version},
        );
        return ProductDetail.fromJson(r.data!);
      });

  Future<ProductDetail> confirmAttributes(String id, List<String> keys) =>
      apiCall(() async {
        final r = await _dio.post<Map<String, Object?>>(
          '/catalog/products/$id/attributes/confirm',
          data: {'keys': keys},
        );
        return ProductDetail.fromJson(r.data!);
      });

  /// Seller-entered values (stored as confirmed, source=seller).
  Future<ProductDetail> setAttributes(String id, Map<String, String> values) =>
      apiCall(() async {
        final r = await _dio.put<Map<String, Object?>>(
          '/catalog/products/$id/attributes',
          data: {
            'items': [
              for (final e in values.entries)
                {'key': e.key, 'value': e.value, 'locale': 'en'},
            ],
          },
        );
        return ProductDetail.fromJson(r.data!);
      });

  Future<ProductDetail> updateTitle(String id, String title, int version) =>
      apiCall(() async {
        final r = await _dio.patch<Map<String, Object?>>(
          '/catalog/products/$id',
          data: {'title': title, 'version': version},
        );
        return ProductDetail.fromJson(r.data!);
      });

  Future<ProductDetail> updateVariantPrice(
    String productId,
    String variantId,
    int priceMinor,
  ) => apiCall(() async {
    final r = await _dio.patch<Map<String, Object?>>(
      '/catalog/products/$productId/variants/$variantId',
      data: {'price_minor': priceMinor},
    );
    return ProductDetail.fromJson(r.data!);
  });

  Future<List<ChannelListing>> publish(String id, List<String> connectionIds) =>
      apiCall(() async {
        final r = await _dio.post<Map<String, Object?>>(
          '/catalog/products/$id/publish',
          data: {'connection_ids': connectionIds},
        );
        return itemsOf(r.data).map(ChannelListing.fromJson).toList();
      });

  Future<List<ChannelListing>> listings(String id) => apiCall(() async {
    final r = await _dio.get<Map<String, Object?>>(
      '/catalog/products/$id/listings',
    );
    return itemsOf(r.data).map(ChannelListing.fromJson).toList();
  });
}

final catalogApiProvider = Provider<CatalogApi>(
  (ref) => CatalogApi(ref.watch(dioProvider)),
);
