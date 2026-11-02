import 'package:flutter/material.dart';

import '../../../../core/l10n/gen/app_localizations.dart';
import '../../../../design/tokens.g.dart';

/// Today's numbers. Orders/revenue/messages/shipping domains don't exist in
/// Phase 0, so every value is an explicit "not counted yet" dash — never a
/// sample number.
class TodayMetrics extends StatelessWidget {
  const TodayMetrics({super.key});

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final labels = [
      l.metricOrders,
      l.metricRevenue,
      l.metricAiMessages,
      l.metricReadyToShip,
    ];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Container(
          color: theme.colorScheme.surface,
          child: Column(
            children: [
              for (var row = 0; row < 2; row++) ...[
                if (row > 0) const Divider(),
                IntrinsicHeight(
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Expanded(child: _Metric(label: labels[row * 2])),
                      const VerticalDivider(width: 1),
                      Expanded(child: _Metric(label: labels[row * 2 + 1])),
                    ],
                  ),
                ),
              ],
            ],
          ),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(
            AppSpace.s4,
            AppSpace.s2,
            AppSpace.s4,
            0,
          ),
          child: Text(
            l.metricNotYetBody,
            style: theme.textTheme.bodySmall?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
        ),
      ],
    );
  }
}

class _Metric extends StatelessWidget {
  const _Metric({required this.label});

  final String label;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    return Semantics(
      label: l.metricUnavailableSemantics(label),
      excludeSemantics: true,
      child: Padding(
        padding: const EdgeInsets.all(AppSpace.s4),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              label,
              style: theme.textTheme.labelMedium?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: AppSpace.s1),
            Text(
              '—',
              style: theme.textTheme.headlineSmall?.copyWith(
                color: theme.colorScheme.outline,
              ),
            ),
            Text(
              l.metricNotYet,
              style: theme.textTheme.labelSmall?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
