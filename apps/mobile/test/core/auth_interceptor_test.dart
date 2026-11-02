import 'package:commerce_os_seller/core/api/api_client.dart';
import 'package:commerce_os_seller/core/api/request_context_interceptor.dart';
import 'package:commerce_os_seller/core/auth/token_pair.dart';
import 'package:commerce_os_seller/core/auth/token_store.dart';
import 'package:commerce_os_seller/core/config/app_config.dart';
import 'package:commerce_os_seller/core/errors/api_error.dart';
import 'package:commerce_os_seller/core/storage/key_value_store.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';

import '../helpers/fake_adapter.dart';

const _config = AppConfig(apiBaseUrl: 'http://test', getRetries: 0);

void main() {
  late InMemoryKeyValueStore secure;
  late TokenStore tokens;
  late List<String> endedReasons;

  setUp(() async {
    secure = InMemoryKeyValueStore();
    tokens = TokenStore(secure);
    await tokens.save(
      const TokenPair(accessToken: 'a1', refreshToken: 'r1', sessionId: 's1'),
    );
    endedReasons = [];
  });

  Dio build(FakeAdapter adapter, {String? merchant = 'm-1'}) => buildApiDio(
        config: _config,
        tokenStore: tokens,
        merchantId: () => merchant,
        languageCode: () => 'ne',
        onSessionEnded: endedReasons.add,
        adapter: adapter,
      );

  /// Protected endpoint: valid only with the rotated token.
  FakeResponse protectedEndpoint(RequestOptions o, String validToken) =>
      o.headers['Authorization'] == 'Bearer $validToken'
          ? const FakeResponse(200, {'ok': true})
          : FakeResponse(401, errorBody('token_expired'));

  test('concurrent 401 token_expired triggers exactly one refresh', () async {
    final adapter = FakeAdapter((o) async {
      if (o.path == '/auth/refresh') {
        expect(o.data, {'refresh_token': 'r1'});
        expect(o.headers.containsKey('Authorization'), isFalse);
        await Future<void>.delayed(const Duration(milliseconds: 30));
        return const FakeResponse(200, {
          'access_token': 'a2',
          'refresh_token': 'r2',
          'token_type': 'bearer',
          'expires_in': 900,
          'session_id': 's1',
        });
      }
      return protectedEndpoint(o, 'a2');
    });
    final dio = build(adapter);

    final results = await Future.wait([
      dio.get<Object?>('/merchant'),
      dio.get<Object?>('/stores'),
      dio.get<Object?>('/billing/credits'),
    ]);

    expect(results.map((r) => r.statusCode), everyElement(200));
    expect(adapter.countPath('/auth/refresh'), 1);
    expect(tokens.accessToken, 'a2');
    expect(await secure.read('auth.refresh_token'), 'r2');
    expect(endedReasons, isEmpty);
  });

  test('a 401 arriving after rotation completed replays with the new token '
      'without a second refresh', () async {
    final adapter = FakeAdapter((o) async {
      if (o.path == '/auth/refresh') {
        return const FakeResponse(
          200,
          {'access_token': 'a2', 'refresh_token': 'r2'},
        );
      }
      if (o.path == '/slow' && o.headers['Authorization'] == 'Bearer a1') {
        // Sent with a1, but the 401 only lands after /fast rotated tokens.
        await Future<void>.delayed(const Duration(milliseconds: 80));
      }
      return protectedEndpoint(o, 'a2');
    });
    final dio = build(adapter);

    final results = await Future.wait([
      dio.get<Object?>('/slow'),
      dio.get<Object?>('/fast'),
    ]);

    expect(results.map((r) => r.statusCode), everyElement(200));
    expect(adapter.countPath('/auth/refresh'), 1);
    final slowCalls = adapter.log.where((r) => r.path == '/slow');
    expect(
      slowCalls.map((r) => r.headers['Authorization']).toList(),
      ['Bearer a1', 'Bearer a2'],
    );
  });

  for (final code in ['refresh_token_reused', 'session_revoked']) {
    test('refresh 401 $code wipes tokens and ends session once', () async {
      final adapter = FakeAdapter((o) {
        if (o.path == '/auth/refresh') {
          return FakeResponse(401, errorBody(code));
        }
        return FakeResponse(401, errorBody('token_expired'));
      });
      final dio = build(adapter);

      final errors = await Future.wait([
        for (final p in ['/merchant', '/stores'])
          dio.get<Object?>(p).then<ApiError?>(
                (_) => null,
                onError: (Object e) => ApiError.fromDio(e as DioException),
              ),
      ]);

      expect(adapter.countPath('/auth/refresh'), 1);
      expect(endedReasons, [code]);
      expect(tokens.accessToken, isNull);
      expect(tokens.hasSession, isFalse);
      expect(await secure.read('auth.refresh_token'), isNull);
      for (final e in errors) {
        expect(e!.kind, ApiErrorKind.sessionEnded);
        expect(e.code, code);
      }
    });
  }

  test('network failure during refresh keeps tokens', () async {
    final adapter = FakeAdapter((o) {
      if (o.path == '/auth/refresh') return const FakeResponse.networkError();
      return FakeResponse(401, errorBody('token_expired'));
    });
    final dio = build(adapter);

    final error = await dio.get<Object?>('/merchant').then<ApiError?>(
          (_) => null,
          onError: (Object e) => ApiError.fromDio(e as DioException),
        );

    expect(error!.kind, ApiErrorKind.network);
    expect(tokens.accessToken, 'a1');
    expect(tokens.hasSession, isTrue);
    expect(endedReasons, isEmpty);
  });

  test('other 401 codes do not trigger refresh', () async {
    final adapter = FakeAdapter(
      (o) => FakeResponse(401, errorBody('invalid_credentials')),
    );
    final dio = build(adapter);
    await expectLater(dio.get<Object?>('/me'), throwsA(isA<DioException>()));
    expect(adapter.countPath('/auth/refresh'), 0);
  });

  test('adds request id, tenant and language headers; keeps idempotency key '
      'across refresh retry', () async {
    final adapter = FakeAdapter((o) {
      if (o.path == '/auth/refresh') {
        return const FakeResponse(
          200,
          {'access_token': 'a2', 'refresh_token': 'r2'},
        );
      }
      return protectedEndpoint(o, 'a2');
    });
    final dio = build(adapter);

    await dio.post<Object?>(
      '/stores',
      data: {'name': 'Thamel'},
      options: Options(extra: {ApiExtra.idempotent: true}),
    );

    final calls = adapter.log.where((r) => r.path == '/stores').toList();
    expect(calls, hasLength(2));
    final key = calls.first.headers['Idempotency-Key'] as String;
    expect(key.length, inInclusiveRange(8, 128));
    expect(calls.last.headers['Idempotency-Key'], key);
    expect(calls.first.headers['X-Merchant-Id'], 'm-1');
    expect(calls.first.headers['Accept-Language'], 'ne');
    expect(calls.first.headers['X-Request-ID'], isA<String>());
  });

  test('tenant:false omits X-Merchant-Id; skipAuth omits Authorization',
      () async {
    final adapter = FakeAdapter((o) => const FakeResponse(200, {}));
    final dio = build(adapter);
    await dio.post<Object?>(
      '/auth/login',
      data: const {},
      options: Options(
        extra: {ApiExtra.tenant: false, ApiExtra.skipAuth: true},
      ),
    );
    final r = adapter.requests.single;
    expect(r.headers.containsKey('X-Merchant-Id'), isFalse);
    expect(r.headers.containsKey('Authorization'), isFalse);
  });
}
