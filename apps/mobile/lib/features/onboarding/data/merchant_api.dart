import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/providers.dart';
import '../../../core/api/request_context_interceptor.dart';
import '../../../core/auth/me.dart';
import '../../../core/errors/api_error.dart';

class MerchantApi {
  MerchantApi(this._dio);

  final Dio _dio;

  /// `POST /merchants` *(idem)*. Pass the same [idempotencyKey] when the user
  /// retries after a network failure so the server replays instead of
  /// creating a second shop.
  Future<MerchantSummary> create({
    required String name,
    required String defaultLocale,
    required String idempotencyKey,
  }) async {
    try {
      final res = await _dio.post<Map<String, Object?>>(
        '/merchants',
        data: {
          'name': name,
          'country': 'NP',
          'currency': 'NPR',
          'timezone': 'Asia/Kathmandu',
          'default_locale': defaultLocale,
        },
        options: Options(
          extra: {
            ApiExtra.tenant: false,
            ApiExtra.idempotencyKey: idempotencyKey,
          },
        ),
      );
      final data = res.data!;
      final merchant = data['merchant'] ?? data;
      return MerchantSummary.fromJson(merchant as Map<String, Object?>);
    } on DioException catch (e) {
      throw ApiError.fromDio(e);
    }
  }
}

final merchantApiProvider = Provider<MerchantApi>(
  (ref) => MerchantApi(ref.watch(dioProvider)),
);
