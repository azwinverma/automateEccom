import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../core/auth/session_controller.dart';
import '../core/l10n/gen/app_localizations.dart';
import '../features/auth/presentation/login_screen.dart';
import '../features/auth/presentation/register_screen.dart';
import '../features/home/presentation/coming_soon_screen.dart';
import '../features/home/presentation/home_screen.dart';
import '../features/home/presentation/widgets/quick_actions.dart';
import '../features/onboarding/presentation/onboarding_screen.dart';
import '../features/settings/presentation/plan_usage_screen.dart';
import '../features/settings/presentation/security_screen.dart';
import '../features/settings/presentation/settings_screen.dart';
import 'splash_screen.dart';

abstract final class Routes {
  static const splash = '/splash';
  static const login = '/login';
  static const register = '/register';
  static const onboarding = '/onboarding';
  static const home = '/home';
  static const settings = '/settings';
}

/// Pure redirect rule, unit-testable without widgets.
String? authRedirect(SessionState session, String location) {
  const publicRoutes = {Routes.login, Routes.register};
  switch (session) {
    case SessionLoading():
    case SessionUnavailable():
      return location == Routes.splash ? null : Routes.splash;
    case SessionSignedOut():
      return publicRoutes.contains(location) ? null : Routes.login;
    case SessionSignedIn(:final needsOnboarding):
      if (needsOnboarding) {
        return location == Routes.onboarding ? null : Routes.onboarding;
      }
      if (publicRoutes.contains(location) ||
          location == Routes.splash ||
          location == Routes.onboarding) {
        return Routes.home;
      }
      return null;
  }
}

/// Bridges Riverpod session changes to go_router's refreshListenable.
class _SessionListenable extends ChangeNotifier {
  _SessionListenable(Ref ref) {
    ref.listen(sessionControllerProvider, (_, __) => notifyListeners());
  }
}

final routerProvider = Provider<GoRouter>((ref) {
  final refresh = _SessionListenable(ref);
  final router = GoRouter(
    initialLocation: Routes.splash,
    refreshListenable: refresh,
    redirect: (context, state) =>
        authRedirect(ref.read(sessionControllerProvider), state.matchedLocation),
    routes: [
      GoRoute(path: Routes.splash, builder: (_, __) => const SplashScreen()),
      GoRoute(path: Routes.login, builder: (_, __) => const LoginScreen()),
      GoRoute(
        path: Routes.register,
        builder: (_, __) => const RegisterScreen(),
      ),
      GoRoute(
        path: Routes.onboarding,
        builder: (_, __) => const OnboardingScreen(),
      ),
      StatefulShellRoute.indexedStack(
        builder: (context, state, shell) => _HomeShell(shell: shell),
        branches: [
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: Routes.home,
                builder: (_, __) => const HomeScreen(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: Routes.settings,
                builder: (_, __) => const SettingsScreen(),
                routes: [
                  GoRoute(
                    path: 'security',
                    builder: (_, __) => const SecurityScreen(),
                  ),
                  GoRoute(
                    path: 'plan',
                    builder: (_, __) => const PlanUsageScreen(),
                  ),
                ],
              ),
            ],
          ),
        ],
      ),
      GoRoute(
        path: '/soon/:feature',
        redirect: (_, state) =>
            QuickAction.fromSlug(state.pathParameters['feature'] ?? '') == null
                ? Routes.home
                : null,
        builder: (_, state) => ComingSoonScreen(
          action: QuickAction.fromSlug(state.pathParameters['feature']!)!,
        ),
      ),
    ],
  );
  ref.onDispose(() {
    router.dispose();
    refresh.dispose();
  });
  return router;
});

class _HomeShell extends StatelessWidget {
  const _HomeShell({required this.shell});

  final StatefulNavigationShell shell;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return Scaffold(
      body: shell,
      bottomNavigationBar: NavigationBar(
        selectedIndex: shell.currentIndex,
        onDestinationSelected: (i) =>
            shell.goBranch(i, initialLocation: i == shell.currentIndex),
        destinations: [
          NavigationDestination(
            icon: const Icon(Icons.home_outlined),
            selectedIcon: const Icon(Icons.home),
            label: l.navHome,
          ),
          NavigationDestination(
            icon: const Icon(Icons.settings_outlined),
            selectedIcon: const Icon(Icons.settings),
            label: l.navSettings,
          ),
        ],
      ),
    );
  }
}
