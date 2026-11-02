import 'package:dio/dio.dart';
import 'package:uuid/uuid.dart';

/// `RequestOptions.extra` keys understood by the interceptors.
abstract final class ApiExtra {
  /// Set `true` on state-changing endpoints marked *(idem)* in the contract.
  static const idempotent = 'idempotent';

  /// Caller-supplied key, reused across user-initiated retries of one action.
  static const idempotencyKey = 'idempotency_key';

  /// Set `false` to omit `X-Merchant-Id` (auth and `/me` endpoints).
  static const tenant = 'tenant';

  /// Set `true` to omit `Authorization` (login/register/refresh).
  static const skipAuth = 'skip_auth';
}

/// Adds X-Request-ID, X-Merchant-Id, Accept-Language and Idempotency-Key.
class RequestContextInterceptor extends Interceptor {
  RequestContextInterceptor({
    required this.merchantId,
    required this.languageCode,
    Uuid? uuid,
  }) : _uuid = uuid ?? const Uuid();

  final String? Function() merchantId;
  final String? Function() languageCode;
  final Uuid _uuid;

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    options.headers.putIfAbsent('X-Request-ID', _uuid.v4);

    final lang = languageCode();
    if (lang != null) options.headers['Accept-Language'] = lang;

    final tenantScoped = options.extra[ApiExtra.tenant] != false;
    final merchant = merchantId();
    if (tenantScoped && merchant != null) {
      options.headers['X-Merchant-Id'] = merchant;
    } else {
      options.headers.remove('X-Merchant-Id');
    }

    final supplied = options.extra[ApiExtra.idempotencyKey];
    if (supplied is String) {
      options.headers['Idempotency-Key'] = supplied;
    } else if (options.extra[ApiExtra.idempotent] == true) {
      // Persist the generated key in extra so refresh-retries reuse it.
      final key = _uuid.v4();
      options.extra[ApiExtra.idempotencyKey] = key;
      options.headers['Idempotency-Key'] = key;
    }
    handler.next(options);
  }
}
