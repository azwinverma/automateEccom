import 'package:flutter/material.dart';

import '../app_theme.dart';
import '../motion.dart';
import '../tokens.g.dart';

/// Usage alert levels from the billing spec: 70%, 85%, 100%.
enum UsageLevel { normal, notice, warning, reached }

UsageLevel usageLevelFor(double ratio) {
  if (ratio >= 1.0) return UsageLevel.reached;
  if (ratio >= 0.85) return UsageLevel.warning;
  if (ratio >= 0.70) return UsageLevel.notice;
  return UsageLevel.normal;
}

/// Server `alert_level` ("70"|"85"|"100") — the stricter of server and
/// client-computed levels wins.
UsageLevel usageLevelFromAlert(String? alert) => switch (alert) {
  '100' => UsageLevel.reached,
  '85' => UsageLevel.warning,
  '70' => UsageLevel.notice,
  _ => UsageLevel.normal,
};

Color usageLevelColor(BuildContext context, UsageLevel level) {
  final palette = AppPalette.of(context);
  return switch (level) {
    UsageLevel.normal => Theme.of(context).colorScheme.primary,
    UsageLevel.notice => palette.accentSun,
    UsageLevel.warning => palette.warning,
    UsageLevel.reached => palette.danger,
  };
}

/// Flat, square-ended progress bar (no pill).
class MeterBar extends StatelessWidget {
  const MeterBar({super.key, required this.ratio, required this.level});

  final double ratio;
  final UsageLevel level;

  @override
  Widget build(BuildContext context) {
    final track = Theme.of(context).colorScheme.surfaceContainerHighest;
    final clamped = ratio.clamp(0.0, 1.0);
    return ClipRRect(
      borderRadius: BorderRadius.circular(AppRadius.sm / 2),
      child: SizedBox(
        height: 6,
        child: Stack(
          children: [
            Positioned.fill(child: ColoredBox(color: track)),
            TweenAnimationBuilder<double>(
              tween: Tween(begin: 0, end: clamped),
              duration: Motion.standard(context),
              builder:
                  (context, v, _) => FractionallySizedBox(
                    widthFactor: v,
                    heightFactor: 1,
                    alignment: AlignmentDirectional.centerStart,
                    child: ColoredBox(color: usageLevelColor(context, level)),
                  ),
            ),
          ],
        ),
      ),
    );
  }
}
