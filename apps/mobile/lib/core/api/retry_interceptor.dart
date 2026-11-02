import 'package:dio/dio.dart';

/// Retries GET requests on connection errors/timeouts with short backoff.
/// Writes are never auto-retried here (idempotent writes are retried by the
/// user with the same Idempotency-Key).
class RetryInterceptor extends Interceptor {
  RetryInterceptor({
    required this.dio,
    this.maxRetries = 2,
    this.baseDelay = const Duration(milliseconds: 700),
  });

  final Dio dio;
  final int maxRetries;
  final Duration baseDelay;

  static const _attemptKey = 'retry_attempt';

  bool _retryable(DioException e) =>
      e.requestOptions.method.toUpperCase() == 'GET' &&
      (e.type == DioExceptionType.connectionError ||
          e.type == DioExceptionType.connectionTimeout ||
          e.type == DioExceptionType.receiveTimeout);

  @override
  Future<void> onError(
    DioException err,
    ErrorInterceptorHandler handler,
  ) async {
    final attempt = (err.requestOptions.extra[_attemptKey] as int?) ?? 0;
    if (!_retryable(err) || attempt >= maxRetries) {
      handler.next(err);
      return;
    }
    await Future<void>.delayed(baseDelay * (attempt + 1));
    final options = err.requestOptions..extra[_attemptKey] = attempt + 1;
    try {
      handler.resolve(await dio.fetch<Object?>(options));
    } on DioException catch (e) {
      handler.next(e);
    }
  }
}
