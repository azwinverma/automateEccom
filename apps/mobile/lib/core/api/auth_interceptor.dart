import 'dart:async';

import 'package:dio/dio.dart';

import '../auth/token_pair.dart';
import '../auth/token_store.dart';
import '../errors/api_error.dart';
import 'request_context_interceptor.dart';

/// Exchanges a refresh token for a new [TokenPair]. Must not go through
/// [AuthInterceptor] (use a bare Dio).
typedef TokenRefresher = Future<TokenPair> Function(String refreshToken);

/// Called after tokens were wiped because the session cannot continue.
typedef SessionEndedCallback = FutureOr<void> Function(String reason);

/// Injects the bearer token and performs single-flight refresh-token rotation
/// when the API answers `401 token_expired`.
///
/// - Concurrent 401s share one `/auth/refresh` call.
/// - Requests that failed with a token older than the current one are simply
///   replayed with the current token.
/// - If refresh answers 401/403 (`refresh_token_reused`, `session_revoked`,
///   anything else), tokens are wiped and [onSessionEnded] fires so the router
///   sends the user to login.
/// - Network failures during refresh keep the tokens (weak connections).
class AuthInterceptor extends Interceptor {
  AuthInterceptor({
    required this.tokenStore,
    required this.dio,
    required this.refresher,
    required this.onSessionEnded,
  });

  final TokenStore tokenStore;
  final Dio dio;
  final TokenRefresher refresher;
  final SessionEndedCallback onSessionEnded;

  static const _tokenUsedKey = 'auth_token_used';
  static const _retriedKey = 'auth_retried';

  Future<String?>? _inflight;

  /// Visible for tests.
  bool get isRefreshing => _inflight != null;

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    if (options.extra[ApiExtra.skipAuth] != true) {
      final token = tokenStore.accessToken;
      if (token != null) {
        options.headers['Authorization'] = 'Bearer $token';
        options.extra[_tokenUsedKey] = token;
      }
    }
    handler.next(options);
  }

  @override
  Future<void> onError(
    DioException err,
    ErrorInterceptorHandler handler,
  ) async {
    final options = err.requestOptions;
    if (!_isTokenExpired(err.response) ||
        options.extra[ApiExtra.skipAuth] == true ||
        options.extra[_retriedKey] == true) {
      handler.next(err);
      return;
    }

    try {
      final current = tokenStore.accessToken;
      final used = options.extra[_tokenUsedKey];
      final String? fresh = current != null && current != used
          ? current // Someone already rotated while this request was in flight.
          : await refreshOnce();

      if (fresh == null) {
        handler.next(_sessionEnded(err, ClientErrorCodes.sessionEnded));
        return;
      }

      options
        ..extra[_retriedKey] = true
        ..headers['Authorization'] = 'Bearer $fresh';
      handler.resolve(await dio.fetch<Object?>(options));
    } on _SessionEnded catch (e) {
      handler.next(_sessionEnded(err, e.reason));
    } on DioException catch (e) {
      handler.next(e);
    }
  }

  /// Single-flight refresh. Returns the new access token, or throws
  /// [_SessionEnded] / [DioException] (network).
  Future<String?> refreshOnce() {
    return _inflight ??= _refresh().whenComplete(() => _inflight = null);
  }

  Future<String?> _refresh() async {
    final refreshToken = await tokenStore.readRefreshToken();
    if (refreshToken == null) {
      await _endSession(ClientErrorCodes.sessionEnded);
    }
    try {
      final pair = await refresher(refreshToken);
      await tokenStore.save(pair);
      return pair.accessToken;
    } on DioException catch (e) {
      final status = e.response?.statusCode;
      if (status == 401 || status == 403) {
        final code = ApiError.parseEnvelope(e.response?.data)?.code ??
            ClientErrorCodes.sessionEnded;
        await _endSession(code);
      }
      rethrow;
    }
  }

  Future<Never> _endSession(String reason) async {
    await tokenStore.clear();
    await onSessionEnded(reason);
    throw _SessionEnded(reason);
  }

  static bool _isTokenExpired(Response<Object?>? response) {
    if (response?.statusCode != 401) return false;
    return ApiError.parseEnvelope(response?.data)?.code == 'token_expired';
  }

  static DioException _sessionEnded(DioException original, String reason) =>
      DioException(
        requestOptions: original.requestOptions,
        response: original.response,
        type: DioExceptionType.badResponse,
        error: SessionEndedException(reason),
      );
}

class _SessionEnded implements Exception {
  const _SessionEnded(this.reason);
  final String reason;
}
