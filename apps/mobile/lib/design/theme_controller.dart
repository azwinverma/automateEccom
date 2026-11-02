import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/storage/providers.dart';

/// Colour theme choice. Light is the default for everyone (specs/26 §16);
/// dark and "same as phone" are opt-in and remembered on the device.
class ThemeController extends Notifier<ThemeMode> {
  static const _key = 'app.theme';

  @override
  ThemeMode build() => switch (ref
      .read(sharedPreferencesProvider)
      .getString(_key)) {
    'dark' => ThemeMode.dark,
    'system' => ThemeMode.system,
    _ => ThemeMode.light,
  };

  Future<void> set(ThemeMode mode) async {
    state = mode;
    await ref.read(sharedPreferencesProvider).setString(_key, mode.name);
  }
}

final themeControllerProvider = NotifierProvider<ThemeController, ThemeMode>(
  ThemeController.new,
);
