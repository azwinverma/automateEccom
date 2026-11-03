import 'package:commerce_os_seller/app/router.dart';
import 'package:commerce_os_seller/core/auth/me.dart';
import 'package:commerce_os_seller/core/auth/session_controller.dart';
import 'package:commerce_os_seller/core/errors/api_error.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  const me = Me(
    user: AppUser(id: 'u', email: 'a@b.np', fullName: 'Sita Rai'),
    memberships: [],
  );

  test('loading and unavailable stay on splash', () {
    expect(authRedirect(const SessionLoading(), '/home'), Routes.splash);
    expect(
      authRedirect(
        const SessionUnavailable(
          ApiError(kind: ApiErrorKind.network, code: 'network_unreachable'),
        ),
        '/splash',
      ),
      isNull,
    );
  });

  test('signed out goes to login but may visit register', () {
    const s = SessionSignedOut(reason: 'refresh_token_reused');
    expect(authRedirect(s, '/home'), Routes.login);
    expect(authRedirect(s, '/settings/plan'), Routes.login);
    expect(authRedirect(s, '/register'), isNull);
    expect(authRedirect(s, '/forgot-password'), isNull); // QA-001
  });

  test('signed in without merchant must onboard', () {
    const s = SessionSignedIn(me: me, merchantId: null);
    expect(authRedirect(s, '/home'), Routes.onboarding);
    expect(authRedirect(s, '/onboarding'), isNull);
  });

  test('signed in with merchant leaves auth screens', () {
    const s = SessionSignedIn(me: me, merchantId: 'm1');
    expect(authRedirect(s, '/login'), Routes.home);
    expect(authRedirect(s, '/onboarding'), Routes.home);
    expect(authRedirect(s, '/settings/security'), isNull);
  });
}
