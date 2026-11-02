import 'package:commerce_os_seller/core/l10n/gen/app_localizations.dart';
import 'package:commerce_os_seller/core/l10n/locale_controller.dart';
import 'package:commerce_os_seller/design/app_theme.dart';
import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

Future<void> pumpLocalized(
  WidgetTester tester,
  Widget child, {
  Locale locale = const Locale('en'),
  List<Override> overrides = const [],
  bool scaffold = true,
}) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: overrides,
      child: MaterialApp(
        locale: locale,
        supportedLocales: supportedAppLocales,
        localizationsDelegates: const [
          AppLocalizations.delegate,
          GlobalMaterialLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
        ],
        theme: AppTheme.light(locale: locale),
        home: scaffold
            ? Scaffold(body: SingleChildScrollView(child: child))
            : child,
      ),
    ),
  );
  await tester.pumpAndSettle();
}
