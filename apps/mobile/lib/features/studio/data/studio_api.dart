import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/providers.dart';
import '../../../core/api/request_context_interceptor.dart';
import '../../../core/errors/api_error.dart';
import 'studio_models.dart';

/// Seller-confirmed product payload for `POST /studio/jobs/{id}/apply`.
class ApplyProduct {
  const ApplyProduct({
    required this.title,
    this.titleNe,
    this.description,
    this.descriptionNe,
    this.options = const [],
    required this.variants,
  });

  final String title;
  final String? titleNe;
  final String? description;
  final String? descriptionNe;
  final List<({String name, List<String> values})> options;
  final List<({Map<String, String> options, int priceMinor, String? sku})>
  variants;

  Map<String, Object?> toJson() => {
    'title': title,
    if (titleNe != null && titleNe!.isNotEmpty) 'title_ne': titleNe,
    if (description != null && description!.isNotEmpty)
      'description': description,
    if (descriptionNe != null && descriptionNe!.isNotEmpty)
      'description_ne': descriptionNe,
    'options': [
      for (final o in options) {'name': o.name, 'values': o.values},
    ],
    'variants': [
      for (final v in variants)
        {
          'options': v.options,
          'price_minor': v.priceMinor,
          if (v.sku != null && v.sku!.isNotEmpty) 'sku': v.sku,
        },
    ],
  };
}

class StudioApi {
  StudioApi(this._dio);

  final Dio _dio;

  Future<T> _call<T>(Future<T> Function() run) async {
    try {
      return await run();
    } on DioException catch (e) {
      throw ApiError.fromDio(e);
    }
  }

  Future<StudioJob> createJob({
    required List<String> assetIds,
    required String locale,
    String? sellerNotes,
    required String idempotencyKey,
  }) => _call(() async {
    final res = await _dio.post<Map<String, Object?>>(
      '/studio/jobs',
      data: {
        'asset_ids': assetIds,
        'locale': locale,
        if (sellerNotes != null && sellerNotes.trim().isNotEmpty)
          'seller_notes': sellerNotes.trim(),
      },
      options: Options(extra: {ApiExtra.idempotencyKey: idempotencyKey}),
    );
    return StudioJob.fromJson(res.data!);
  });

  Future<StudioJob> getJob(String id) => _call(() async {
    final res = await _dio.get<Map<String, Object?>>('/studio/jobs/$id');
    return StudioJob.fromJson(res.data!);
  });

  Future<List<StudioJob>> listJobs({String? status, int limit = 30}) => _call(
    () async {
      final res = await _dio.get<Map<String, Object?>>(
        '/studio/jobs',
        queryParameters: {'limit': limit, if (status != null) 'status': status},
      );
      return ((res.data!['items'] as List<Object?>?) ?? const [])
          .whereType<Map<String, Object?>>()
          .map(StudioJob.fromJson)
          .toList(growable: false);
    },
  );

  Future<StudioJob> retry(String id) => _call(() async {
    final res = await _dio.post<Map<String, Object?>>('/studio/jobs/$id/retry');
    return StudioJob.fromJson(res.data!);
  });

  /// Returns the created product's id (server replays for an applied job).
  Future<Map<String, Object?>> apply(
    String jobId, {
    required ApplyProduct product,
    List<String>? categoryPath,
    required List<String> acceptedAttributeKeys,
  }) => _call(() async {
    final res = await _dio.post<Map<String, Object?>>(
      '/studio/jobs/$jobId/apply',
      data: {
        'product': product.toJson(),
        if (categoryPath != null && categoryPath.isNotEmpty)
          'category_path': categoryPath,
        'accepted_attribute_keys': acceptedAttributeKeys,
      },
    );
    return res.data!;
  });
}

final studioApiProvider = Provider<StudioApi>(
  (ref) => StudioApi(ref.watch(dioProvider)),
);
