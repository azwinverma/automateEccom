import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../auth/auth_api.dart';
import '../auth/session_controller.dart';
import '../auth/token_store.dart';
import '../config/app_config.dart';
import '../l10n/locale_controller.dart';
import '../storage/providers.dart';
import 'api_client.dart';

final appConfigProvider = Provider<AppConfig>(
  (ref) => AppConfig.fromEnvironment(),
);

final tokenStoreProvider = Provider<TokenStore>(
  (ref) => TokenStore(ref.watch(secureStoreProvider)),
);

/// Overridable transport (tests inject a fake adapter).
final httpClientAdapterProvider = Provider<HttpClientAdapter?>((ref) => null);

final dioProvider = Provider<Dio>((ref) {
  final dio = buildApiDio(
    config: ref.watch(appConfigProvider),
    tokenStore: ref.watch(tokenStoreProvider),
    adapter: ref.watch(httpClientAdapterProvider),
    // Read lazily: the session depends on Dio, not the other way round.
    merchantId: () => ref.read(activeMerchantIdProvider),
    languageCode: () => ref.read(effectiveLocaleProvider).languageCode,
    onSessionEnded:
        (reason) =>
            ref.read(sessionControllerProvider.notifier).onSessionEnded(reason),
  );
  ref.onDispose(dio.close);
  return dio;
});

final authApiProvider = Provider<AuthApi>(
  (ref) => AuthApi(ref.watch(dioProvider)),
);

/// `true` when the device reports any network interface. A connected
/// interface can still have no internet, so requests also surface timeouts.
final connectivityProvider = StreamProvider<bool>((ref) async* {
  final connectivity = Connectivity();
  bool online(List<ConnectivityResult> r) =>
      r.any((c) => c != ConnectivityResult.none);
  yield online(await connectivity.checkConnectivity());
  yield* connectivity.onConnectivityChanged.map(online);
});
