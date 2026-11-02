import 'package:dio/dio.dart';

import '../auth/token_pair.dart';
import '../auth/token_store.dart';
import '../config/app_config.dart';
import 'auth_interceptor.dart';
import 'request_context_interceptor.dart';
import 'retry_interceptor.dart';

BaseOptions _baseOptions(AppConfig config) => BaseOptions(
  baseUrl: config.apiV1,
  connectTimeout: config.connectTimeout,
  receiveTimeout: config.receiveTimeout,
  sendTimeout: config.sendTimeout,
  contentType: Headers.jsonContentType,
  responseType: ResponseType.json,
  headers: {'Accept': 'application/json'},
);

/// Builds the app's Dio stack.
///
/// Order: request context → auth → retry. The refresh call uses a separate
/// bare client so it never recurses into [AuthInterceptor].
Dio buildApiDio({
  required AppConfig config,
  required TokenStore tokenStore,
  required String? Function() merchantId,
  required String? Function() languageCode,
  required SessionEndedCallback onSessionEnded,
  HttpClientAdapter? adapter,
}) {
  final context = RequestContextInterceptor(
    merchantId: merchantId,
    languageCode: languageCode,
  );

  final refreshDio = Dio(_baseOptions(config));
  if (adapter != null) refreshDio.httpClientAdapter = adapter;
  refreshDio.interceptors.add(context);

  Future<TokenPair> refresher(String refreshToken) async {
    final res = await refreshDio.post<Map<String, Object?>>(
      '/auth/refresh',
      data: {'refresh_token': refreshToken},
      options: Options(extra: {ApiExtra.tenant: false}),
    );
    return TokenPair.fromJson(res.data!);
  }

  final dio = Dio(_baseOptions(config));
  if (adapter != null) dio.httpClientAdapter = adapter;
  dio.interceptors.addAll([
    context,
    AuthInterceptor(
      tokenStore: tokenStore,
      dio: dio,
      refresher: refresher,
      onSessionEnded: onSessionEnded,
    ),
    if (config.getRetries > 0)
      RetryInterceptor(dio: dio, maxRetries: config.getRetries),
  ]);
  return dio;
}
