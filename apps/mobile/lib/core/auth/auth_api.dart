import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';

import '../api/request_context_interceptor.dart';
import '../errors/api_error.dart';
import 'me.dart';
import 'token_pair.dart';

/// Outcome of `POST /auth/login`.
sealed class LoginResult {
  const LoginResult();
}

final class LoginSucceeded extends LoginResult {
  const LoginSucceeded(this.tokens);
  final TokenPair tokens;
}

final class LoginNeedsMfa extends LoginResult {
  const LoginNeedsMfa(this.mfaToken);
  final String mfaToken;
}

@immutable
class AuthSession {
  const AuthSession({
    required this.id,
    required this.current,
    this.deviceName,
    this.ip,
    this.userAgent,
    this.createdAt,
    this.lastUsedAt,
  });

  factory AuthSession.fromJson(Map<String, Object?> json) => AuthSession(
        id: json['id']! as String,
        current: (json['current'] as bool?) ?? false,
        deviceName: json['device_name'] as String?,
        ip: json['ip'] as String?,
        userAgent: json['user_agent'] as String?,
        createdAt: _date(json['created_at']),
        lastUsedAt: _date(json['last_used_at']),
      );

  final String id;
  final bool current;
  final String? deviceName;
  final String? ip;
  final String? userAgent;
  final DateTime? createdAt;
  final DateTime? lastUsedAt;
}

DateTime? _date(Object? v) => v is String ? DateTime.tryParse(v) : null;

const _public = {ApiExtra.skipAuth: true, ApiExtra.tenant: false};
const _userScoped = {ApiExtra.tenant: false};

/// Thin typed wrapper over the Phase 0 auth + `/me` endpoints.
class AuthApi {
  AuthApi(this._dio);

  final Dio _dio;

  Future<T> _call<T>(Future<T> Function() run) async {
    try {
      return await run();
    } on DioException catch (e) {
      throw ApiError.fromDio(e);
    }
  }

  Future<LoginResult> login({
    required String email,
    required String password,
    String? deviceName,
  }) =>
      _call(() async {
        final res = await _dio.post<Map<String, Object?>>(
          '/auth/login',
          data: {
            'email': email,
            'password': password,
            if (deviceName != null) 'device_name': deviceName,
          },
          options: Options(extra: _public),
        );
        final data = res.data!;
        if (data['mfa_required'] == true) {
          return LoginNeedsMfa(data['mfa_token']! as String);
        }
        return LoginSucceeded(TokenPair.fromJson(data));
      });

  Future<TokenPair> verifyMfa({
    required String mfaToken,
    required String code,
  }) =>
      _call(() async {
        final res = await _dio.post<Map<String, Object?>>(
          '/auth/mfa/verify',
          data: {'mfa_token': mfaToken, 'code': code},
          options: Options(extra: _public),
        );
        return TokenPair.fromJson(res.data!);
      });

  Future<void> register({
    required String email,
    required String password,
    required String fullName,
    String? phone,
    String? locale,
  }) =>
      _call(() async {
        await _dio.post<Object?>(
          '/auth/register',
          data: {
            'email': email,
            'password': password,
            'full_name': fullName,
            if (phone != null && phone.isNotEmpty) 'phone': phone,
            if (locale != null) 'locale': locale,
          },
          options: Options(extra: _public),
        );
      });

  Future<void> logout(String refreshToken) => _call(() async {
        await _dio.post<Object?>(
          '/auth/logout',
          data: {'refresh_token': refreshToken},
          options: Options(extra: _userScoped),
        );
      });

  Future<Me> me() => _call(() async {
        final res = await _dio.get<Map<String, Object?>>(
          '/me',
          options: Options(extra: _userScoped),
        );
        return Me.fromJson(res.data!);
      });

  Future<void> updateLocale(String locale) => _call(() async {
        await _dio.patch<Object?>(
          '/me',
          data: {'locale': locale},
          options: Options(extra: _userScoped),
        );
      });

  Future<List<AuthSession>> sessions() => _call(() async {
        final res = await _dio.get<Map<String, Object?>>(
          '/auth/sessions',
          options: Options(extra: _userScoped),
        );
        return ((res.data!['items'] as List<Object?>?) ?? const [])
            .whereType<Map<String, Object?>>()
            .map(AuthSession.fromJson)
            .toList(growable: false);
      });

  Future<void> revokeSession(String id) => _call(() async {
        await _dio.delete<Object?>(
          '/auth/sessions/$id',
          options: Options(extra: _userScoped),
        );
      });

  Future<void> revokeAllOtherSessions() => _call(() async {
        await _dio.post<Object?>(
          '/auth/sessions/revoke-all',
          options: Options(extra: _userScoped),
        );
      });
}
