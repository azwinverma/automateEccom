import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'key_value_store.dart';

/// Secure storage for secrets (tokens). Overridden in tests.
final secureStoreProvider = Provider<KeyValueStore>(
  (ref) => SecureKeyValueStore(),
);

/// Non-secret preferences (language, last merchant). Must be overridden in
/// `main()` with an already-loaded instance.
final sharedPreferencesProvider = Provider<SharedPreferences>(
  (ref) => throw UnimplementedError('sharedPreferencesProvider not overridden'),
);
