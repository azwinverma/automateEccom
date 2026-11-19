import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/l10n/formatters.dart';
import '../../../core/l10n/gen/app_localizations.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens.g.dart';
import '../data/intelligence_api.dart';
import 'intelligence_labels.dart';

/// UX-010 Profit summary on Home (true profit, last 30 days). Anything without
/// data is listed by name, never shown as zero. Hidden on 403 or failure.
class ProfitCard extends ConsumerWidget {
  const ProfitCard({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final s = ref.watch(profitSummaryProvider).valueOrNull;
    if (s == null) return const SizedBox.shrink();
    return ProfitView(summary: s);
  }
}

class ProfitView extends StatelessWidget {
  const ProfitView({super.key, required this.summary});

  final ProfitSummary summary;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final p = AppPalette.of(context);
    final lang = Localizations.localeOf(context).languageCode;
    final s = summary;
    final gaps = s.gaps;
    String money(int v) => Formatters.money(v, s.currency, lang);
    return Padding(
      key: const Key('profit-card'),
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
              Text(
                l.profitTitle(s.windowDays),
                style: theme.textTheme.titleSmall,
              ),
              const SizedBox(height: AppSpace.s2),
              Text(
                l.profitContribution(money(s.contributionMinor)),
                key: const Key('profit-contribution'),
                style: theme.textTheme.titleMedium?.copyWith(
                  color: s.contributionMinor < 0 ? p.danger : null,
                ),
              ),
              Text(
                [
                  l.profitRevenue(money(s.revenueMinor)),
                  if (s.marginPct != null)
                    l.profitMargin(s.marginPct!.toStringAsFixed(1)),
                ].join(' · '),
                style: theme.textTheme.bodySmall,
              ),
              if (gaps.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(top: AppSpace.s1),
                  child: Text(
                    l.profitGaps(
                      gaps.length,
                      gaps
                          .map((c) => profitComponentLabel(l, c.code))
                          .join(', '),
                    ),
                    key: const Key('profit-gaps'),
                    style: theme.textTheme.bodySmall?.copyWith(color: p.muted),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}
