import 'package:commerce_os_seller/core/api/providers.dart';
import 'package:commerce_os_seller/core/config/app_config.dart';
import 'package:commerce_os_seller/core/storage/key_value_store.dart';
import 'package:commerce_os_seller/core/storage/providers.dart';
import 'package:commerce_os_seller/features/auth/presentation/login_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../helpers/fake_adapter.dart';
import '../helpers/pump.dart';

void main() {
  late FakeAdapter adapter;
  late List<Override> overrides;

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    final prefs = await SharedPreferences.getInstance();
    adapter = FakeAdapter((o) {
      if (o.path == '/auth/login') {
        final body = o.data as Map<String, Object?>;
        if (body['password'] == 'wrong-password') {
          return FakeResponse(
            401,
            errorBody('invalid_credentials', requestId: 'req-login-1'),
          );
        }
        return const FakeResponse(
          200,
          {'mfa_required': true, 'mfa_token': 'mfa-1'},
        );
      }
      return FakeResponse(404, errorBody('not_found'));
    });
    overrides = [
      sharedPreferencesProvider.overrideWithValue(prefs),
      secureStoreProvider.overrideWithValue(InMemoryKeyValueStore()),
      appConfigProvider.overrideWithValue(
        const AppConfig(apiBaseUrl: 'http://test', getRetries: 0),
      ),
      httpClientAdapterProvider.overrideWithValue(adapter),
      connectivityProvider.overrideWith((ref) => Stream.value(true)),
    ];
  });

  Future<void> pumpLogin(WidgetTester tester, {Locale? locale}) =>
      pumpLocalized(
        tester,
        const LoginScreen(),
        overrides: overrides,
        scaffold: false,
        locale: locale ?? const Locale('en'),
      );

  testWidgets('empty submit shows required errors and sends nothing',
      (tester) async {
    await pumpLogin(tester);
    await tester.tap(find.byKey(const Key('login-submit')));
    await tester.pump();
    expect(find.text('Enter your email'), findsOneWidget);
    expect(find.text('Enter your password'), findsOneWidget);
    expect(adapter.countPath('/auth/login'), 0);
  });

  testWidgets('invalid email is rejected client-side', (tester) async {
    await pumpLogin(tester);
    await tester.enterText(find.byKey(const Key('email-field')), 'sita@');
    await tester.enterText(find.byKey(const Key('password-field')), 'x');
    await tester.tap(find.byKey(const Key('login-submit')));
    await tester.pump();
    expect(find.text("That email doesn't look right"), findsOneWidget);
    expect(adapter.countPath('/auth/login'), 0);
  });

  testWidgets('validation copy is localized in Nepali', (tester) async {
    await pumpLogin(tester, locale: const Locale('ne'));
    await tester.tap(find.byKey(const Key('login-submit')));
    await tester.pump();
    expect(find.text('इमेल हाल्नुहोस्'), findsOneWidget);
    expect(find.text('पासवर्ड हाल्नुहोस्'), findsOneWidget);
  });

  testWidgets('server error is mapped and shows request id', (tester) async {
    await pumpLogin(tester);
    await tester.enterText(
      find.byKey(const Key('email-field')),
      'sita@thamel.np',
    );
    await tester.enterText(
      find.byKey(const Key('password-field')),
      'wrong-password',
    );
    await tester.tap(find.byKey(const Key('login-submit')));
    await tester.pumpAndSettle();
    expect(find.text("Email or password didn't match."), findsOneWidget);
    expect(find.text('Ref req-login-1'), findsOneWidget);
  });

  testWidgets('mfa_required switches to the code step', (tester) async {
    await pumpLogin(tester);
    await tester.enterText(
      find.byKey(const Key('email-field')),
      'sita@thamel.np',
    );
    await tester.enterText(
      find.byKey(const Key('password-field')),
      'correct horse battery',
    );
    await tester.tap(find.byKey(const Key('login-submit')));
    await tester.pumpAndSettle();
    expect(adapter.countPath('/auth/login'), 1);
    expect(find.text('Enter your 6-digit code'), findsOneWidget);
    expect(find.byKey(const Key('mfa-code-field')), findsOneWidget);
  });
}
