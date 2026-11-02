import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

/// Thrown into a [DioException.error] when the session can no longer be
/// refreshed and tokens were wiped.
@immutable
class SessionEndedException implements Exception {
  const SessionEndedException(this.reason);

  /// Server code that ended the session, e.g. `refresh_token_reused`.
  final String reason;

  @override
  String toString() => 'SessionEndedException($reason)';
}

enum ApiErrorKind { http, network, timeout, cancelled, sessionEnded, unknown }

/// Known client-side codes in addition to the server's error codes.
abstract final class ClientErrorCodes {
  static const network = 'network_unreachable';
  static const timeout = 'timeout';
  static const cancelled = 'cancelled';
  static const server = 'server_error';
  static const unknown = 'unknown_error';
  static const sessionEnded = 'session_ended';
}

/// Typed view of the contract's error envelope
/// `{ "error": { code, message, details, request_id } }`.
@immutable
class ApiError implements Exception {
  const ApiError({
    required this.kind,
    required this.code,
    this.statusCode,
    this.message,
    this.details = const {},
    this.requestId,
    this.retryAfter,
  });

  factory ApiError.fromDio(DioException e) {
    final inner = e.error;
    if (inner is ApiError) return inner;
    final requestId = _requestIdOf(e);
    if (inner is SessionEndedException) {
      return ApiError(
        kind: ApiErrorKind.sessionEnded,
        code: inner.reason,
        statusCode: e.response?.statusCode,
        requestId: requestId,
      );
    }
    switch (e.type) {
      case DioExceptionType.connectionTimeout:
      case DioExceptionType.sendTimeout:
      case DioExceptionType.receiveTimeout:
        return ApiError(
          kind: ApiErrorKind.timeout,
          code: ClientErrorCodes.timeout,
          requestId: requestId,
        );
      case DioExceptionType.connectionError:
        return ApiError(
          kind: ApiErrorKind.network,
          code: ClientErrorCodes.network,
          requestId: requestId,
        );
      case DioExceptionType.cancel:
        return const ApiError(
          kind: ApiErrorKind.cancelled,
          code: ClientErrorCodes.cancelled,
        );
      case DioExceptionType.badResponse:
      case DioExceptionType.badCertificate:
      case DioExceptionType.unknown:
        final response = e.response;
        if (response == null) {
          return ApiError(
            kind:
                e.type == DioExceptionType.unknown
                    ? ApiErrorKind.network
                    : ApiErrorKind.unknown,
            code:
                e.type == DioExceptionType.unknown
                    ? ClientErrorCodes.network
                    : ClientErrorCodes.unknown,
            requestId: requestId,
          );
        }
        return ApiError.fromResponse(
          statusCode: response.statusCode,
          data: response.data,
          headers: response.headers,
          fallbackRequestId: requestId,
        );
    }
  }

  factory ApiError.fromResponse({
    required int? statusCode,
    required Object? data,
    Headers? headers,
    String? fallbackRequestId,
  }) {
    final envelope = parseEnvelope(data);
    final retryAfterRaw = headers?.value('retry-after');
    final retrySeconds =
        retryAfterRaw == null ? null : int.tryParse(retryAfterRaw.trim());
    final code =
        envelope?.code ??
        ((statusCode ?? 0) >= 500
            ? ClientErrorCodes.server
            : ClientErrorCodes.unknown);
    return ApiError(
      kind: ApiErrorKind.http,
      code: code,
      statusCode: statusCode,
      message: envelope?.message,
      details: envelope?.details ?? const {},
      requestId:
          envelope?.requestId ??
          headers?.value('x-request-id') ??
          fallbackRequestId,
      retryAfter: retrySeconds == null ? null : Duration(seconds: retrySeconds),
    );
  }

  /// Returns null when [data] is not the documented envelope.
  static ({
    String code,
    String? message,
    Map<String, Object?> details,
    String? requestId,
  })?
  parseEnvelope(Object? data) {
    if (data is! Map) return null;
    final error = data['error'];
    if (error is! Map) return null;
    final code = error['code'];
    if (code is! String || code.isEmpty) return null;
    final message = error['message'];
    final details = error['details'];
    final requestId = error['request_id'];
    return (
      code: code,
      message: message is String ? message : null,
      details:
          details is Map
              ? details.map((k, v) => MapEntry(k.toString(), v as Object?))
              : const <String, Object?>{},
      requestId: requestId is String ? requestId : null,
    );
  }

  static String? _requestIdOf(DioException e) {
    final fromHeader = e.response?.headers.value('x-request-id');
    if (fromHeader != null) return fromHeader;
    final sent = e.requestOptions.headers['X-Request-ID'];
    return sent is String ? sent : null;
  }

  final ApiErrorKind kind;
  final String code;
  final int? statusCode;

  /// Developer fallback only — never shown as UI copy.
  final String? message;
  final Map<String, Object?> details;
  final String? requestId;
  final Duration? retryAfter;

  bool get isOffline =>
      kind == ApiErrorKind.network || kind == ApiErrorKind.timeout;

  bool get isPermissionDenied =>
      code == 'permission_denied' || code == 'feature_not_in_plan';

  /// `validation_error` field errors keyed by the last `loc` segment.
  Map<String, String> get fieldErrors {
    final fields = details['fields'];
    if (fields is! List) return const {};
    final out = <String, String>{};
    for (final f in fields) {
      if (f is! Map) continue;
      final loc = f['loc'];
      final msg = f['msg'];
      final key = loc is List && loc.isNotEmpty ? loc.last.toString() : null;
      if (key != null) out[key] = msg is String ? msg : '';
    }
    return out;
  }

  @override
  String toString() =>
      'ApiError($code, status: $statusCode, requestId: $requestId)';
}

/// Normalises anything thrown from the data layer into an [ApiError].
ApiError asApiError(Object error) {
  if (error is ApiError) return error;
  if (error is DioException) return ApiError.fromDio(error);
  return const ApiError(
    kind: ApiErrorKind.unknown,
    code: ClientErrorCodes.unknown,
  );
}
