import 'package:commerce_os_seller/core/api/providers.dart';
import 'package:commerce_os_seller/core/config/app_config.dart';
import 'package:commerce_os_seller/core/storage/key_value_store.dart';
import 'package:commerce_os_seller/core/storage/providers.dart';
import 'package:commerce_os_seller/features/auth/presentation/forgot_password_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../helpers/fake_adapter.dart';
import '../helpers/pump.dart';

/// QA-001: password reset request from the app.
void main() {
  late FakeAdapter adapter;
  late List<Override> overrides;

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    final prefs = await SharedPreferences.getInstance();
    adapter = FakeAdapter((o) {
      if (o.path == '/auth/password/forgot') return const FakeResponse(202);
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

  testWidgets(
    'invalid email is caught locally; valid email sends once and confirms',
    (tester) async {
      await pumpLocalized(
        tester,
        const ForgotPasswordScreen(),
        overrides: overrides,
        scaffold: false,
        locale: const Locale('en'),
      );
      await tester.enterText(
        find.byKey(const Key('forgot-email')),
        'not-an-email',
      );
      await tester.tap(find.byKey(const Key('forgot-submit')));
      await tester.pumpAndSettle();
      expect(adapter.countPath('/auth/password/forgot'), 0);

      await tester.enterText(
        find.byKey(const Key('forgot-email')),
        'sita@example.com',
      );
      await tester.tap(find.byKey(const Key('forgot-submit')));
      await tester.pumpAndSettle();
      expect(adapter.countPath('/auth/password/forgot'), 1);
      expect(adapter.requests.last.data, {'email': 'sita@example.com'});
      expect(find.text('Check your email'), findsOneWidget);
    },
  );
}
