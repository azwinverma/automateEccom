import 'package:flutter/material.dart';

import '../../../../core/l10n/formatters.dart';
import '../../../../core/l10n/gen/app_localizations.dart';
import '../../../../design/tokens.g.dart';
import '../../../../design/widgets/meter_bar.dart';

/// Usage meter with 70 / 85 / 100% states. State is conveyed by colour *and*
/// text so it reads without colour vision.
class UsageMeter extends StatelessWidget {
  const UsageMeter({
    super.key,
    required this.label,
    required this.used,
    required this.limit,
    this.reserved = 0,
    this.alertLevel,
    this.periodLabel,
    this.reachedText,
  });

  final String label;
  final int used;

  /// `null` = unlimited.
  final int? limit;
  final int reserved;
  final String? alertLevel;
  final String? periodLabel;

  /// Overrides the 100% copy (e.g. a daily cap that resets tomorrow).
  final String? reachedText;

  UsageLevel get level {
    final l = limit;
    if (l == null) return UsageLevel.normal;
    final computed = usageLevelFor(l <= 0 ? 1 : (used + reserved) / l);
    final server = usageLevelFromAlert(alertLevel);
    return computed.index >= server.index ? computed : server;
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final lang = Localizations.localeOf(context).languageCode;
    final lim = limit;
    final lvl = level;
    final levelText = switch (lvl) {
      UsageLevel.normal => null,
      UsageLevel.notice => l10n.usageLevelNotice,
      UsageLevel.warning => l10n.usageLevelWarning,
      UsageLevel.reached => reachedText ?? l10n.usageLevelReached,
    };
    final amount = lim == null
        ? l10n.usageUnlimited
        : l10n.usageUsedOf(
            Formatters.integer(used, lang),
            Formatters.integer(lim, lang),
          );

    return Semantics(
      container: true,
      label: [label, amount, if (levelText != null) levelText].join(', '),
      excludeSemantics: true,
      child: Padding(
        padding: const EdgeInsets.symmetric(
          horizontal: AppSpace.s4,
          vertical: AppSpace.s3,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.baseline,
              textBaseline: TextBaseline.alphabetic,
              children: [
                Expanded(
                  child: Text(label, style: theme.textTheme.titleSmall),
                ),
                Text(
                  amount,
                  key: const Key('usage-amount'),
                  style: theme.textTheme.bodyMedium,
                ),
              ],
            ),
            if (periodLabel != null || reserved > 0)
              Text(
                [
                  if (periodLabel != null) periodLabel!,
                  if (reserved > 0) l10n.usageReserved(reserved),
                ].join(' · '),
                style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              ),
            if (lim != null) ...[
              const SizedBox(height: AppSpace.s2),
              MeterBar(
                ratio: lim <= 0 ? 1 : (used + reserved) / lim,
                level: lvl,
              ),
            ],
            if (levelText != null) ...[
              const SizedBox(height: AppSpace.s1),
              Text(
                levelText,
                key: Key('usage-level-${lvl.name}'),
                style: theme.textTheme.bodySmall?.copyWith(
                  // Sun yellow is too light for text; the bar carries it.
                  color: lvl == UsageLevel.notice
                      ? theme.colorScheme.onSurface
                      : usageLevelColor(context, lvl),
                  fontWeight:
                      lvl == UsageLevel.reached ? FontWeight.w600 : null,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
