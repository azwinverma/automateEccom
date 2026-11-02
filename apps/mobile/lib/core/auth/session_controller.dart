import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/providers.dart';
import '../errors/api_error.dart';
import '../storage/providers.dart';
import 'auth_api.dart';
import 'me.dart';
import 'token_pair.dart';

sealed class SessionState {
  const SessionState();
}

/// Reading stored tokens / loading `/me`.
final class SessionLoading extends SessionState {
  const SessionLoading();
}

final class SessionSignedOut extends SessionState {
  const SessionSignedOut({this.reason});

  /// Server/client code explaining a forced sign-out
  /// (`refresh_token_reused`, `session_revoked`, `session_ended`).
  final String? reason;
}

/// Tokens exist but `/me` could not load (usually offline). Tokens are kept.
final class SessionUnavailable extends SessionState {
  const SessionUnavailable(this.error);
  final ApiError error;
}

final class SessionSignedIn extends SessionState {
  const SessionSignedIn({required this.me, required this.merchantId});
  final Me me;

  /// Active tenant; `null` means the user must create a merchant first.
  final String? merchantId;

  bool get needsOnboarding => merchantId == null;

  MerchantSummary? get merchant {
    for (final m in me.activeMemberships) {
      if (m.merchant.id == merchantId) return m.merchant;
    }
    return null;
  }
}

class SessionController extends Notifier<SessionState> {
  static const _kMerchant = 'session.merchant_id';

  @override
  SessionState build() {
    Future.microtask(bootstrap);
    return const SessionLoading();
  }

  AuthApi get _api => ref.read(authApiProvider);

  Future<void> bootstrap() async {
    state = const SessionLoading();
    final tokens = ref.read(tokenStoreProvider);
    await tokens.load();
    if (!tokens.hasSession) {
      state = const SessionSignedOut();
      return;
    }
    await _loadMe();
  }

  Future<void> _loadMe({String? preferMerchantId}) async {
    try {
      final me = await _api.me();
      final merchantId = _pickMerchant(me, preferMerchantId);
      if (merchantId != null) {
        await ref
            .read(sharedPreferencesProvider)
            .setString(_kMerchant, merchantId);
      }
      state = SessionSignedIn(me: me, merchantId: merchantId);
    } on ApiError catch (e) {
      if (e.kind == ApiErrorKind.sessionEnded) {
        state = SessionSignedOut(reason: e.code);
      } else if (e.statusCode == 401) {
        await ref.read(tokenStoreProvider).clear();
        state = const SessionSignedOut(reason: ClientErrorCodes.sessionEnded);
      } else {
        state = SessionUnavailable(e);
      }
    }
  }

  String? _pickMerchant(Me me, String? prefer) {
    final active = me.activeMemberships;
    if (active.isEmpty) return null;
    final stored = prefer ??
        ref.read(sharedPreferencesProvider).getString(_kMerchant);
    return active
        .firstWhere(
          (m) => m.merchant.id == stored,
          orElse: () => active.first,
        )
        .merchant
        .id;
  }

  /// Returns the MFA token when a second step is needed; otherwise signs in.
  Future<String?> login({
    required String email,
    required String password,
  }) async {
    final result = await _api.login(
      email: email,
      password: password,
      deviceName: _deviceName(),
    );
    switch (result) {
      case LoginNeedsMfa(:final mfaToken):
        return mfaToken;
      case LoginSucceeded(:final tokens):
        await _completeSignIn(tokens);
        return null;
    }
  }

  Future<void> verifyMfa({
    required String mfaToken,
    required String code,
  }) async {
    final tokens = await _api.verifyMfa(mfaToken: mfaToken, code: code);
    await _completeSignIn(tokens);
  }

  /// Registers and then signs in with the same credentials. Returns an MFA
  /// token in the unlikely case the server requires one.
  Future<String?> register({
    required String email,
    required String password,
    required String fullName,
    String? phone,
    String? locale,
  }) async {
    await _api.register(
      email: email,
      password: password,
      fullName: fullName,
      phone: phone,
      locale: locale,
    );
    return login(email: email, password: password);
  }

  Future<void> _completeSignIn(TokenPair tokens) async {
    await ref.read(tokenStoreProvider).save(tokens);
    await _loadMe();
  }

  /// Reloads `/me`, e.g. after creating a merchant.
  Future<void> refreshMe({String? preferMerchantId}) =>
      _loadMe(preferMerchantId: preferMerchantId);

  Future<void> logout() async {
    final tokens = ref.read(tokenStoreProvider);
    final refresh = await tokens.readRefreshToken();
    if (refresh != null) {
      try {
        await _api.logout(refresh);
      } on ApiError {
        // Local sign-out must succeed even offline; the server session will
        // expire or can be revoked from another device.
      }
    }
    await tokens.clear();
    await ref.read(sharedPreferencesProvider).remove(_kMerchant);
    state = const SessionSignedOut();
  }

  /// Called by the auth interceptor after tokens were wiped.
  void onSessionEnded(String reason) {
    state = SessionSignedOut(reason: reason);
  }

  static String _deviceName() => switch (defaultTargetPlatform) {
        TargetPlatform.android => 'Android phone',
        TargetPlatform.iOS => 'iPhone',
        _ => 'Mobile device',
      };
}

final sessionControllerProvider =
    NotifierProvider<SessionController, SessionState>(SessionController.new);

final activeMerchantIdProvider = Provider<String?>((ref) {
  final s = ref.watch(sessionControllerProvider);
  return s is SessionSignedIn ? s.merchantId : null;
});
