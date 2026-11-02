import 'package:flutter/material.dart';

import '../../../../core/l10n/gen/app_localizations.dart';
import '../../../../design/app_theme.dart';
import '../../../../design/tokens.g.dart';

enum AutopilotMode { assisted, smart, autopilot }

@immutable
class AutopilotStatus {
  const AutopilotStatus({
    required this.mode,
    required this.automatedCount,
    required this.needsAttentionCount,
  });

  final AutopilotMode mode;

  /// Null when no automation-run count exists yet (never invented).
  final int? automatedCount;
  final int needsAttentionCount;
}

/// Signature strip: current automation mode and what it did vs. what waits
/// for the seller. Pass `null` when automation isn't running yet — the strip
/// then says so instead of inventing counts.
class AutopilotStatusStrip extends StatelessWidget {
  const AutopilotStatusStrip({super.key, required this.status});

  final AutopilotStatus? status;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final palette = AppPalette.of(context);
    final s = status;

    return Container(
      decoration: BoxDecoration(
        color: theme.colorScheme.surface,
        border: Border(
          top: BorderSide(color: palette.line),
          bottom: BorderSide(color: palette.line),
        ),
      ),
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpace.s4,
        vertical: AppSpace.s3,
      ),
      child:
          s == null
              ? Row(
                children: [
                  Icon(
                    Icons.pause_circle_outline,
                    size: 20,
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                  const SizedBox(width: AppSpace.s2),
                  Text(l.autopilotTitle, style: theme.textTheme.titleSmall),
                  const SizedBox(width: AppSpace.s2),
                  Expanded(
                    child: Text(
                      l.autopilotNotActive,
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ),
                ],
              )
              : Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Wrap(
                    spacing: AppSpace.s3,
                    runSpacing: AppSpace.s1,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    children: [
                      _ModeSegments(mode: s.mode),
                      if (s.automatedCount != null)
                        _Count(
                          key: const Key('autopilot-automated'),
                          text: l.autopilotAutomated(s.automatedCount!),
                          color: palette.success,
                          icon: Icons.check,
                        ),
                      _Count(
                        key: const Key('autopilot-attention'),
                        text: l.autopilotNeedsAttention(s.needsAttentionCount),
                        color:
                            s.needsAttentionCount > 0
                                ? palette.warning
                                : theme.colorScheme.onSurfaceVariant,
                        icon: Icons.flag_outlined,
                      ),
                    ],
                  ),
                  const SizedBox(height: AppSpace.s1),
                  Text(
                    switch (s.mode) {
                      AutopilotMode.assisted => l.autopilotModeAssistedHint,
                      AutopilotMode.smart => l.autopilotModeSmartHint,
                      AutopilotMode.autopilot => l.autopilotModeAutopilotHint,
                    },
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: theme.colorScheme.onSurfaceVariant,
                    ),
                  ),
                ],
              ),
    );
  }
}

/// Three-step mode indicator: filled steps up to the active mode.
class _ModeSegments extends StatelessWidget {
  const _ModeSegments({required this.mode});

  final AutopilotMode mode;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final label = switch (mode) {
      AutopilotMode.assisted => l.autopilotModeAssisted,
      AutopilotMode.smart => l.autopilotModeSmart,
      AutopilotMode.autopilot => l.autopilotModeAutopilot,
    };
    return Semantics(
      label: '${l.autopilotTitle}: $label',
      excludeSemantics: true,
      child: Row(
        children: [
          for (final m in AutopilotMode.values)
            Container(
              width: 14,
              height: 6,
              margin: const EdgeInsetsDirectional.only(end: 2),
              color:
                  m.index <= mode.index
                      ? theme.colorScheme.primary
                      : theme.colorScheme.surfaceContainerHighest,
            ),
          const SizedBox(width: AppSpace.s2),
          Text(label, style: theme.textTheme.titleSmall),
        ],
      ),
    );
  }
}

class _Count extends StatelessWidget {
  const _Count({
    super.key,
    required this.text,
    required this.color,
    required this.icon,
  });

  final String text;
  final Color color;
  final IconData icon;

  @override
  Widget build(BuildContext context) => Row(
    mainAxisSize: MainAxisSize.min,
    children: [
      Icon(icon, size: 16, color: color),
      const SizedBox(width: AppSpace.s1),
      Text(
        text,
        style: Theme.of(context).textTheme.labelMedium?.copyWith(color: color),
      ),
    ],
  );
}
