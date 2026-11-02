import 'dart:ui';

import 'package:commerce_os_seller/core/errors/api_error.dart';
import 'package:commerce_os_seller/core/errors/error_messages.dart';
import 'package:commerce_os_seller/core/l10n/gen/app_localizations.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  final en = lookupAppLocalizations(const Locale('en'));
  final ne = lookupAppLocalizations(const Locale('ne'));

  ApiError http(String code, [int status = 400]) => ApiError.fromResponse(
        statusCode: status,
        data: {
          'error': {
            'code': code,
            'message': 'dev message',
            'details': {
              'fields': [
                {
                  'loc': ['body', 'email'],
                  'msg': 'bad',
                  'type': 'value_error',
                },
              ],
            },
            'request_id': 'req-42',
          },
        },
      );

  test('parses the error envelope', () {
    final e = http('validation_error');
    expect(e.code, 'validation_error');
    expect(e.requestId, 'req-42');
    expect(e.message, 'dev message');
    expect(e.fieldErrors.keys, ['email']);
  });

  test('non-envelope 5xx becomes server_error with header request id', () {
    final e = ApiError.fromResponse(
      statusCode: 502,
      data: '<html>bad gateway</html>',
      headers: Headers.fromMap({
        'x-request-id': ['hdr-1'],
      }),
    );
    expect(e.code, ClientErrorCodes.server);
    expect(e.requestId, 'hdr-1');
    expect(localizedErrorMessage(en, e), en.errServer);
  });

  test('maps every contract code to dedicated copy (en + ne)', () {
    const codes = [
      'validation_error',
      'not_authenticated',
      'token_expired',
      'invalid_credentials',
      'mfa_invalid_code',
      'permission_denied',
      'feature_not_in_plan',
      'not_found',
      'conflict',
      'idempotency_in_progress',
      'slug_taken',
      'email_taken',
      'usage_limit_reached',
      'idempotency_key_reused',
      'invalid_state_transition',
      'rate_limited',
      'dependency_unavailable',
      'refresh_token_reused',
      'session_revoked',
    ];
    for (final l in [en, ne]) {
      for (final code in codes) {
        final msg = localizedErrorMessage(l, http(code));
        expect(msg, isNot(l.errUnknown), reason: '$code unmapped');
        expect(msg, isNot('dev message'));
      }
    }
    expect(localizedErrorMessage(en, http('invalid_credentials', 401)),
        "Email or password didn't match.");
    expect(localizedErrorMessage(ne, http('invalid_credentials', 401)),
        'इमेल वा पासवर्ड मिलेन।');
  });

  test('unknown code falls back to generic copy, never server message', () {
    expect(localizedErrorMessage(en, http('brand_new_code')), en.errUnknown);
  });

  test('network and timeout DioExceptions map to offline copy', () {
    final ro = RequestOptions(path: '/me', headers: {'X-Request-ID': 'c-1'});
    final net = ApiError.fromDio(
      DioException.connectionError(requestOptions: ro, reason: 'x'),
    );
    final slow = ApiError.fromDio(
      DioException.receiveTimeout(
        timeout: const Duration(seconds: 1),
        requestOptions: ro,
      ),
    );
    expect(net.isOffline, isTrue);
    expect(net.requestId, 'c-1');
    expect(localizedErrorMessage(ne, net), ne.errNetwork);
    expect(localizedErrorMessage(en, slow), en.errTimeout);
  });

  test('session ended reason copy', () {
    expect(sessionEndedMessage(en, null), isNull);
    expect(sessionEndedMessage(en, 'refresh_token_reused'), en.errSessionReused);
    expect(sessionEndedMessage(en, 'session_revoked'), en.errSessionRevoked);
    expect(sessionEndedMessage(en, 'whatever'), en.errSessionEnded);
  });
}
