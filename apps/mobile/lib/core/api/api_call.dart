import 'package:dio/dio.dart';

import '../errors/api_error.dart';

/// Runs a Dio call and converts transport errors to [ApiError].
Future<T> apiCall<T>(Future<T> Function() run) async {
  try {
    return await run();
  } on DioException catch (e) {
    throw ApiError.fromDio(e);
  }
}

List<Map<String, Object?>> itemsOf(Map<String, Object?>? data) =>
    ((data?['items'] as List<Object?>?) ?? const [])
        .whereType<Map<String, Object?>>()
        .toList(growable: false);
