import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/l10n/gen/app_localizations.dart';
import '../core/l10n/locale_controller.dart';
import '../design/app_theme.dart';
import '../design/theme_controller.dart';
import '../design/widgets/offline_banner.dart';
import 'router.dart';

class CommerceOsApp extends ConsumerWidget {
  const CommerceOsApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(routerProvider);
    final locale = ref.watch(effectiveLocaleProvider);
    return MaterialApp.router(
      onGenerateTitle: (context) => AppLocalizations.of(context).appName,
      debugShowCheckedModeBanner: false,
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
      darkTheme: AppTheme.dark(locale: locale),
      themeMode: ref.watch(themeControllerProvider),
      builder:
          (context, child) =>
              OfflineFrame(child: child ?? const SizedBox.shrink()),
    );
  }
}
