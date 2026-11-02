import 'package:commerce_os_seller/core/api/providers.dart';
import 'package:commerce_os_seller/core/config/app_config.dart';
import 'package:commerce_os_seller/core/l10n/gen/app_localizations.dart';
import 'package:commerce_os_seller/core/l10n/locale_controller.dart';
import 'package:commerce_os_seller/core/storage/key_value_store.dart';
import 'package:commerce_os_seller/core/storage/providers.dart';
import 'package:commerce_os_seller/design/app_theme.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'fake_adapter.dart';

/// Builds a routed app at 360×740dp with a fake transport.
Future<GoRouter> pumpRouted(
  WidgetTester tester, {
  required String initialLocation,
  required List<RouteBase> routes,
  required FakeAdapter adapter,
  Locale locale = const Locale('en'),
  List<Override> overrides = const [],
  double height = 740,
  bool settle = true,
}) async {
  SharedPreferences.setMockInitialValues({});
  final prefs = await SharedPreferences.getInstance();
  tester.view.physicalSize = Size(360 * 3, height * 3);
  tester.view.devicePixelRatio = 3;
  addTearDown(tester.view.reset);
  final router = GoRouter(initialLocation: initialLocation, routes: routes);
  addTearDown(router.dispose);
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        sharedPreferencesProvider.overrideWithValue(prefs),
        secureStoreProvider.overrideWithValue(InMemoryKeyValueStore()),
        appConfigProvider.overrideWithValue(
          const AppConfig(apiBaseUrl: 'http://test', getRetries: 0),
        ),
        httpClientAdapterProvider.overrideWithValue(adapter),
        connectivityProvider.overrideWith((ref) => Stream.value(true)),
        ...overrides,
      ],
      child: MaterialApp.router(
        routerConfig: router,
        locale: locale,
        supportedLocales: supportedAppLocales,
        localizationsDelegates: const [
          AppLocalizations.delegate,
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        theme: AppTheme.light(locale: locale),
      ),
    ),
  );
  if (settle) {
    await tester.pumpAndSettle();
  } else {
    await tester.pump();
    await tester.pump();
  }
  return router;
}

/// Placeholder destination that shows its location.
GoRoute stubRoute(String path) => GoRoute(
      path: path,
      builder: (_, s) => Scaffold(body: Text('STUB ${s.uri}')),
    );
