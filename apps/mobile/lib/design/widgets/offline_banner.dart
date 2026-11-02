import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/providers.dart';
import '../../core/l10n/gen/app_localizations.dart';
import '../app_theme.dart';
import '../motion.dart';
import '../tokens.g.dart';

/// Thin app-wide banner shown while the device has no network interface.
class OfflineBanner extends ConsumerWidget {
  const OfflineBanner({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final online = ref.watch(connectivityProvider).valueOrNull ?? true;
    final palette = AppPalette.of(context);
    final theme = Theme.of(context);
    return AnimatedSize(
      duration: Motion.standard(context),
      curve: Curves.easeOut,
      child: online
          ? const SizedBox(width: double.infinity)
          : Material(
              color: palette.warningSoft,
              child: SafeArea(
                bottom: false,
                child: Semantics(
                  liveRegion: true,
                  child: Padding(
                    padding: const EdgeInsets.symmetric(
                      horizontal: AppSpace.s4,
                      vertical: AppSpace.s2,
                    ),
                    child: Row(
                      children: [
                        Icon(
                          Icons.wifi_off_outlined,
                          size: 18,
                          color: palette.warning,
                        ),
                        const SizedBox(width: AppSpace.s2),
                        Expanded(
                          child: Text(
                            AppLocalizations.of(context).offlineBanner,
                            style: theme.textTheme.bodySmall?.copyWith(
                              color: theme.brightness == Brightness.light
                                  ? AppColors.neutralInk
                                  : palette.warning,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
    );
  }
}

/// App frame: offline banner on top; when it shows, the page below no longer
/// needs the status-bar inset (the banner already consumed it).
class OfflineFrame extends ConsumerWidget {
  const OfflineFrame({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final online = ref.watch(connectivityProvider).valueOrNull ?? true;
    return Column(
      children: [
        const OfflineBanner(),
        Expanded(
          child: MediaQuery.removePadding(
            context: context,
            removeTop: !online,
            child: child,
          ),
        ),
      ],
    );
  }
}
