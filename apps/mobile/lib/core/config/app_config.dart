import 'package:flutter/foundation.dart';

/// Build-time configuration. Override with
/// `--dart-define=API_BASE_URL=https://api.example.com`.
@immutable
class AppConfig {
  const AppConfig({
    required this.apiBaseUrl,
    this.connectTimeout = const Duration(seconds: 10),
    this.receiveTimeout = const Duration(seconds: 25),
    this.sendTimeout = const Duration(seconds: 25),
    this.getRetries = 2,
  });

  factory AppConfig.fromEnvironment({TargetPlatform? platform}) {
    const defined = String.fromEnvironment('API_BASE_URL');
    final host = defined.isNotEmpty
        ? defined
        : defaultBaseUrlFor(platform ?? defaultTargetPlatform);
    return AppConfig(apiBaseUrl: host);
  }

  /// Android emulators reach the host machine on 10.0.2.2; iOS simulators
  /// share the host network stack.
  static String defaultBaseUrlFor(TargetPlatform platform) =>
      platform == TargetPlatform.android
          ? 'http://10.0.2.2:8000'
          : 'http://localhost:8000';

  /// Origin without trailing slash, e.g. `http://localhost:8000`.
  final String apiBaseUrl;

  /// Weak-mobile-network friendly timeouts.
  final Duration connectTimeout;
  final Duration receiveTimeout;
  final Duration sendTimeout;

  /// Automatic retries for GET requests on connection errors/timeouts.
  final int getRetries;

  String get apiV1 => '${apiBaseUrl.replaceAll(RegExp(r'/+$'), '')}/api/v1';
}
