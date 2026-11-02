import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/auth/session_controller.dart';
import '../core/l10n/gen/app_localizations.dart';
import '../design/tokens.g.dart';
import '../design/widgets/state_views.dart';

/// Shown while tokens/`/me` load, or when `/me` failed (e.g. offline) with
/// tokens still stored.
class SplashScreen extends ConsumerWidget {
  const SplashScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final session = ref.watch(sessionControllerProvider);
    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(AppSpace.s4),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Spacer(),
              Text(l.appName, style: theme.textTheme.headlineMedium),
              const SizedBox(height: AppSpace.s4),
              if (session is SessionUnavailable)
                ErrorStateView(
                  error: session.error,
                  onRetry: () => ref
                      .read(sessionControllerProvider.notifier)
                      .bootstrap(),
                )
              else
                Row(
                  children: [
                    const SizedBox.square(
                      dimension: 16,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    ),
                    const SizedBox(width: AppSpace.s3),
                    Text(l.splashLoading, style: theme.textTheme.bodyMedium),
                  ],
                ),
              const Spacer(flex: 2),
            ],
          ),
        ),
      ),
    );
  }
}
