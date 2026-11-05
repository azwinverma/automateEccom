import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/l10n/formatters.dart';
import '../../../core/l10n/gen/app_localizations.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens.g.dart';
import '../data/automation_api.dart';
import 'automation_labels.dart';

/// UX-016 Autopilot Control Center: "Your store is running." with real numbers
/// from the last 7 days, what automation did, and what needs the seller.
/// Hidden when the summary can't load (the rest of Home still works).
class ControlCenterCard extends ConsumerWidget {
  const ControlCenterCard({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final cc = ref.watch(controlCenterProvider).valueOrNull;
    if (cc == null) return const SizedBox.shrink();
    return ControlCenterView(data: cc);
  }
}

class ControlCenterView extends StatelessWidget {
  const ControlCenterView({super.key, required this.data});

  final ControlCenter data;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final palette = AppPalette.of(context);
    final lang = Localizations.localeOf(context).languageCode;
    final (headline, fg, bg) = switch (data.state) {
      'attention' => (l.ccStateAttention, palette.danger, palette.dangerSoft),
      'waiting' => (l.ccStateWaiting, palette.warning, palette.warningSoft),
      _ => (l.ccStateRunning, palette.success, palette.successSoft),
    };
    String n(int v) => Formatters.integer(v, lang);
    final tiles = <(String, String, Key)>[
      (l.ccOrders, n(data.orders), const Key('cc-orders')),
      if (data.revenueMinor != null)
        (
          l.ccRevenue,
          Formatters.money(data.revenueMinor!, data.currency, lang),
          const Key('cc-revenue'),
        ),
      (l.ccAiMessages, n(data.aiMessages), const Key('cc-ai')),
      (l.ccDelivered, n(data.delivered), const Key('cc-delivered')),
      (l.ccInTransit, n(data.inTransit), const Key('cc-in-transit')),
      (l.ccReturns, n(data.returns), const Key('cc-returns')),
    ];
    return Padding(
      key: const Key('control-center'),
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
              Row(
                children: [
                  Container(
                    width: 10,
                    height: 10,
                    decoration: BoxDecoration(
                      color: fg,
                      shape: BoxShape.circle,
                    ),
                  ),
                  const SizedBox(width: AppSpace.s2),
                  Expanded(
                    child: Text(
                      headline,
                      key: Key('cc-state-${data.state}'),
                      style: theme.textTheme.titleMedium,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: AppSpace.s1),
              Text(
                '${modeLabel(l, data.mode)} · ${l.ccPeriod}',
                style: theme.textTheme.bodySmall?.copyWith(
                  color: palette.muted,
                ),
              ),
              const SizedBox(height: AppSpace.s3),
              Wrap(
                spacing: AppSpace.s2,
                runSpacing: AppSpace.s2,
                children: [
                  for (final (label, value, key) in tiles)
                    Container(
                      key: key,
                      width: 96,
                      padding: const EdgeInsets.all(AppSpace.s2),
                      decoration: BoxDecoration(
                        border: Border.all(color: palette.line),
                        borderRadius: BorderRadius.circular(AppRadius.md),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            value,
                            style: theme.textTheme.titleMedium,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                          Text(
                            label,
                            style: theme.textTheme.bodySmall?.copyWith(
                              color: palette.muted,
                            ),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                        ],
                      ),
                    ),
                ],
              ),
              const SizedBox(height: AppSpace.s3),
              Text(
                [
                  l.ccDoneAuto(data.doneAutomatically),
                  l.ccDoneTeam(data.doneByTeam),
                  if (data.shareAutomatic != null)
                    l.ccShare(Formatters.percent(data.shareAutomatic!, lang)),
                ].join(' · '),
                key: const Key('cc-automation'),
                style: theme.textTheme.bodySmall,
              ),
              const SizedBox(height: AppSpace.s2),
              Material(
                color: data.needsAttention > 0 ? bg : palette.line,
                borderRadius: BorderRadius.circular(AppRadius.md),
                child: InkWell(
                  key: const Key('cc-needs-attention'),
                  borderRadius: BorderRadius.circular(AppRadius.md),
                  onTap: () => context.push('/automation/approvals'),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(
                      horizontal: AppSpace.s3,
                      vertical: AppSpace.s2,
                    ),
                    child: Row(
                      children: [
                        Expanded(
                          child: Text(l.ccNeedsAttention(data.needsAttention)),
                        ),
                        const Icon(Icons.chevron_right, size: 18),
                      ],
                    ),
                  ),
                ),
              ),
              Wrap(
                spacing: AppSpace.s2,
                children: [
                  TextButton(
                    key: const Key('cc-feed'),
                    onPressed: () => context.push('/automation/feed'),
                    child: Text(l.ccFeedLink),
                  ),
                  TextButton(
                    key: const Key('cc-workflows'),
                    onPressed: () => context.push('/automation'),
                    child: Text(l.ccWorkflowsLink),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
