import 'package:flutter/material.dart';

import '../../../core/l10n/gen/app_localizations.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens.g.dart';
import 'widgets/quick_actions.dart';

/// Honest placeholder for Phase 1 capabilities: says what it will do, shows
/// nothing simulated.
class ComingSoonScreen extends StatelessWidget {
  const ComingSoonScreen({super.key, required this.action});

  final QuickAction action;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final palette = AppPalette.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(action.label(l))),
      body: ListView(
        padding: const EdgeInsets.all(AppSpace.s4),
        children: [
          Icon(action.icon, size: 32, color: theme.colorScheme.primary),
          const SizedBox(height: AppSpace.s3),
          Align(
            alignment: AlignmentDirectional.centerStart,
            child: Container(
              padding: const EdgeInsets.symmetric(
                horizontal: AppSpace.s2,
                vertical: AppSpace.s1,
              ),
              decoration: BoxDecoration(
                color: palette.infoSoft,
                borderRadius: BorderRadius.circular(AppRadius.sm),
              ),
              child: Text(
                l.comingSoonBadge,
                style: theme.textTheme.labelSmall?.copyWith(
                  color: palette.info,
                ),
              ),
            ),
          ),
          const SizedBox(height: AppSpace.s6),
          Text(l.comingSoonWhat, style: theme.textTheme.titleMedium),
          const SizedBox(height: AppSpace.s2),
          Text(action.description(l), style: theme.textTheme.bodyLarge),
          const SizedBox(height: AppSpace.s6),
          const Divider(),
          const SizedBox(height: AppSpace.s4),
          Text(
            l.comingSoonHonest,
            style: theme.textTheme.bodySmall?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
        ],
      ),
    );
  }
}
