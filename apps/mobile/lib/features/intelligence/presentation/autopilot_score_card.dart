import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/l10n/formatters.dart';
import '../../../core/l10n/gen/app_localizations.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens.g.dart';
import '../data/intelligence_api.dart';
import 'intelligence_labels.dart';

/// UX-017 Autopilot Score: eligible operations automated successfully.
/// Hidden when it can't load (e.g. 403).
class AutopilotScoreCard extends ConsumerWidget {
  const AutopilotScoreCard({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final s = ref.watch(autopilotScoreProvider).valueOrNull;
    if (s == null) return const SizedBox.shrink();
    return AutopilotScoreView(score: s);
  }
}

class AutopilotScoreView extends StatelessWidget {
  const AutopilotScoreView({super.key, required this.score});

  final AutopilotScore score;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final palette = AppPalette.of(context);
    final lang = Localizations.localeOf(context).languageCode;
    final caps = [...score.capabilities]..sort(
      (a, b) => (b.automated + b.failed + b.manual).compareTo(
        a.automated + a.failed + a.manual,
      ),
    );
    return Padding(
      key: const Key('aps-card'),
      padding: const EdgeInsets.fromLTRB(
        AppSpace.s4,
        0,
        AppSpace.s4,
        AppSpace.s3,
      ),
      child: Card(
        margin: EdgeInsets.zero,
        child: Padding(
          padding: const EdgeInsets.all(AppSpace.s4),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(l.apsTitle, style: theme.textTheme.titleSmall),
              Text(
                l.apsWindow(score.windowDays),
                style: theme.textTheme.bodySmall?.copyWith(
                  color: palette.muted,
                ),
              ),
              const SizedBox(height: AppSpace.s2),
              Text(
                score.overall == null
                    ? l.apsNotEnough
                    : Formatters.percent(score.overall!, lang),
                key: const Key('aps-overall'),
                style:
                    score.overall == null
                        ? theme.textTheme.titleMedium
                        : theme.textTheme.headlineMedium,
              ),
              if (score.hoursSaved > 0)
                Text(
                  l.apsHoursSaved(score.hoursSaved.toStringAsFixed(1)),
                  key: const Key('aps-hours'),
                  style: theme.textTheme.bodySmall,
                ),
              const SizedBox(height: AppSpace.s3),
              for (final c in caps)
                Padding(
                  key: Key('aps-cap-${c.code}'),
                  padding: const EdgeInsets.only(bottom: AppSpace.s2),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              capabilityLabel(l, c.code),
                              style: theme.textTheme.bodyMedium,
                            ),
                          ),
                          Text(
                            c.enoughActivity && c.score != null
                                ? Formatters.percent(c.score!, lang)
                                : l.apsCapNotEnough,
                            style: theme.textTheme.bodySmall?.copyWith(
                              color: c.enoughActivity ? null : palette.muted,
                            ),
                          ),
                        ],
                      ),
                      Text(
                        l.apsCounts(c.automated, c.failed, c.manual),
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: palette.muted,
                        ),
                      ),
                      for (final e in c.excluded.entries)
                        Text(
                          l.apsExcluded(e.value, exclusionLabel(l, e.key)),
                          style: theme.textTheme.bodySmall?.copyWith(
                            color: palette.muted,
                          ),
                        ),
                    ],
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}
