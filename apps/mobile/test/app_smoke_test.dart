import 'package:commerce_os_seller/app/app.dart';
import 'package:commerce_os_seller/core/api/providers.dart';
import 'package:commerce_os_seller/core/config/app_config.dart';
import 'package:commerce_os_seller/core/l10n/locale_controller.dart';
import 'package:commerce_os_seller/core/storage/key_value_store.dart';
import 'package:commerce_os_seller/core/storage/providers.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'helpers/fake_adapter.dart';

const _me = {
  'user': {
    'id': 'u1',
    'email': 'sita@thamel.np',
    'full_name': 'Sita Rai',
    'phone': null,
    'locale': 'en',
    'email_verified': false,
    'mfa_enabled': false,
  },
  'memberships': [
    {
      'merchant': {'id': 'm1', 'name': 'Thamel Handloom', 'slug': 'thamel'},
      'role': 'owner',
      'status': 'active',
    },
  ],
};

FakeResponse _api(dynamic o) {
  final path = (o as dynamic).path as String;
  switch (path) {
    case '/me':
      return const FakeResponse(200, _me);
    case '/billing/subscription':
      return const FakeResponse(200, {
        'plan': {'code': 'growth', 'name': 'Growth', 'tagline': null},
        'plan_version': 1,
        'status': 'trialing',
        'trial_ends_at': '2026-11-16T00:00:00Z',
        'current_period_start': '2026-11-02T00:00:00Z',
        'current_period_end': '2026-12-02T00:00:00Z',
      });
    case '/billing/entitlements':
      return const FakeResponse(200, {
        'features': {'ai.product_studio': true},
        'limits': [
          {
            'resource': 'ai_text_generations',
            'period': 'month',
            'limit': 500,
            'used': 430,
            'reserved': 3,
            'burst': {'period': 'day', 'limit': null, 'used': 0},
            'alert_level': '85',
          },
          {
            'resource': 'premium_video_credits',
            'period': 'month',
            'limit': 20,
            'used': 6,
            'reserved': 0,
            'burst': {'period': 'day', 'limit': 4, 'used': 1},
            'alert_level': null,
          },
        ],
      });
    case '/billing/credits':
      return const FakeResponse(
        200,
        {'balance': 0, 'currency': 'credits', 'transactions': <Object?>[]},
      );
    case '/auth/sessions':
      return const FakeResponse(200, {
        'items': [
          {
            'id': 's1',
            'device_name': 'Android phone',
            'ip': '27.34.0.1',
            'user_agent': 'x',
            'created_at': '2026-11-01T08:00:00Z',
            'last_used_at': '2026-11-02T08:00:00Z',
            'current': true,
          },
          {
            'id': 's2',
            'device_name': 'Chrome on Windows',
            'ip': '27.34.0.9',
            'user_agent': 'y',
            'created_at': '2026-10-01T08:00:00Z',
            'last_used_at': '2026-10-30T08:00:00Z',
            'current': false,
          },
        ],
      });
  }
  return FakeResponse(404, errorBody('not_found'));
}

Future<FakeAdapter> _boot(
  WidgetTester tester, {
  required bool signedIn,
  String locale = 'en',
}) async {
  SharedPreferences.setMockInitialValues({'app.locale': locale});
  final prefs = await SharedPreferences.getInstance();
  final secure = InMemoryKeyValueStore();
  if (signedIn) {
    secure.values['auth.access_token'] = 'a1';
    secure.values['auth.refresh_token'] = 'r1';
  }
  final adapter = FakeAdapter(_api);
  tester.view.physicalSize = const Size(360 * 3, 740 * 3);
  tester.view.devicePixelRatio = 3;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        sharedPreferencesProvider.overrideWithValue(prefs),
        secureStoreProvider.overrideWithValue(secure),
        appConfigProvider.overrideWithValue(
          const AppConfig(apiBaseUrl: 'http://test', getRetries: 0),
        ),
        httpClientAdapterProvider.overrideWithValue(adapter),
        connectivityProvider.overrideWith((ref) => Stream.value(true)),
        effectiveLocaleProvider.overrideWith(
          (ref) => ref.watch(localeControllerProvider) ?? const Locale('en'),
        ),
      ],
      child: const CommerceOsApp(),
    ),
  );
  await tester.pumpAndSettle();
  return adapter;
}

void main() {
  testWidgets('signed out boots to login', (tester) async {
    await _boot(tester, signedIn: false);
    expect(find.text('Log in to your shop'), findsOneWidget);
  });

  testWidgets('signed in: home shows honest empty states, sends tenant header',
      (tester) async {
    final adapter = await _boot(tester, signedIn: true);
    expect(find.text('Namaste, Sita'), findsOneWidget);
    expect(find.text('Thamel Handloom'), findsOneWidget);
    expect(find.text('Nothing needs you right now'), findsOneWidget);
    expect(find.textContaining('Not active yet'), findsOneWidget);
    await tester.scrollUntilVisible(find.text('Ready to ship'), 200);
    expect(find.text('Not counted yet'), findsNWidgets(4));

    // Quick action → honest Phase 1 explainer.
    await tester.scrollUntilVisible(find.text('Capture product'), -200);
    await tester.tap(find.text('Capture product'));
    await tester.pumpAndSettle();
    expect(find.text('Coming in the next release'), findsOneWidget);
    await tester.pageBack();
    await tester.pumpAndSettle();

    // Settings → Plan & usage.
    await tester.tap(find.text('Settings'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Plan & usage'));
    await tester.pumpAndSettle();
    expect(find.text('Growth'), findsOneWidget);
    expect(find.textContaining('Trial'), findsOneWidget);
    expect(find.text('Almost at the limit'), findsOneWidget);
    expect(find.text('Video credits'), findsOneWidget);
    expect(find.text('1 of 4'), findsOneWidget);
    final billing =
        adapter.log.firstWhere((r) => r.path == '/billing/entitlements');
    expect(billing.headers['X-Merchant-Id'], 'm1');
    expect(billing.headers['Authorization'], 'Bearer a1');
    final me = adapter.log.firstWhere((r) => r.path == '/me');
    expect(me.headers.containsKey('X-Merchant-Id'), isFalse);

    await tester.pageBack();
    await tester.pumpAndSettle();
    await tester.tap(find.text('Security & devices'));
    await tester.pumpAndSettle();
    expect(find.text('This phone'), findsOneWidget);
    expect(find.text('Chrome on Windows'), findsOneWidget);
    expect(find.text('Log out all other devices'), findsOneWidget);
  });

  testWidgets('Nepali home renders without overflow', (tester) async {
    await _boot(tester, signedIn: true, locale: 'ne');
    expect(find.text('नमस्ते, Sita'), findsOneWidget);
    expect(find.text('अहिले तपाईंले हेर्नुपर्ने केही छैन'), findsOneWidget);
    await tester.tap(find.text('सेटिङ'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('प्लान र प्रयोग'));
    await tester.pumpAndSettle();
    expect(find.text('भिडियो क्रेडिट'), findsOneWidget);
  });
}
