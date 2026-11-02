import 'dart:ui';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../storage/providers.dart';

const supportedAppLocales = [Locale('en'), Locale('ne')];

/// The user's explicit language choice; `null` means "follow the phone".
class LocaleController extends Notifier<Locale?> {
  static const _key = 'app.locale';

  @override
  Locale? build() {
    final code = ref.read(sharedPreferencesProvider).getString(_key);
    return code == null ? null : Locale(code);
  }

  Future<void> set(Locale? locale) async {
    state = locale;
    final prefs = ref.read(sharedPreferencesProvider);
    if (locale == null) {
      await prefs.remove(_key);
    } else {
      await prefs.setString(_key, locale.languageCode);
    }
  }
}

final localeControllerProvider =
    NotifierProvider<LocaleController, Locale?>(LocaleController.new);

/// Picks Nepali for Nepali-language phones or phones set to Nepal; English
/// otherwise.
Locale resolveAppLocale(Locale? explicit, List<Locale>? deviceLocales) {
  if (explicit != null) return explicit;
  for (final l in deviceLocales ?? const <Locale>[]) {
    if (l.languageCode == 'ne' || l.countryCode == 'NP') {
      return const Locale('ne');
    }
    if (l.languageCode == 'en') return const Locale('en');
  }
  return const Locale('en');
}

/// Effective app locale (explicit choice or resolved from the device).
final effectiveLocaleProvider = Provider<Locale>((ref) {
  final explicit = ref.watch(localeControllerProvider);
  return resolveAppLocale(
    explicit,
    PlatformDispatcher.instance.locales,
  );
});
