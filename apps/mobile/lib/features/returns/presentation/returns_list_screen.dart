import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/l10n/formatters.dart';
import '../../../core/l10n/gen/app_localizations.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens.g.dart';
import '../../../design/widgets/state_views.dart';
import '../../fulfillment/presentation/fulfillment_labels.dart';
import '../data/returns_api.dart';
import 'returns_labels.dart';

String _tabLabel(AppLocalizations l, String b) => switch (b) {
  'to_decide' => l.returnsTabToDecide,
  'in_progress' => l.returnsTabInProgress,
  'to_refund' => l.returnsTabToRefund,
  _ => l.returnsTabDone,
};

/// Returns by stage: to decide, in progress, to refund, done.
class ReturnsListScreen extends ConsumerWidget {
  const ReturnsListScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    // Counts come with every page; the first tab's page is always loaded.
    final counts =
        ref.watch(returnsPageProvider('to_decide')).valueOrNull?.counts;
    return DefaultTabController(
      length: returnBuckets.length,
      child: Scaffold(
        appBar: AppBar(
          title: Text(l.returnsTitle),
          bottom: TabBar(
            isScrollable: true,
            tabAlignment: TabAlignment.start,
            tabs: [
              for (final b in returnBuckets)
                Tab(
                  key: Key('returns-tab-$b'),
                  text:
                      counts == null || (counts[b] ?? 0) == 0
                          ? _tabLabel(l, b)
                          : l.returnsTabCount(_tabLabel(l, b), counts[b]!),
                ),
            ],
          ),
        ),
        body: TabBarView(
          children: [for (final b in returnBuckets) _Bucket(bucket: b)],
        ),
      ),
    );
  }
}

class _Bucket extends ConsumerWidget {
  const _Bucket({required this.bucket});

  final String bucket;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final palette = AppPalette.of(context);
    final lang = Localizations.localeOf(context).languageCode;
    return RefreshIndicator(
      onRefresh: () async {
        ref.invalidate(returnsPageProvider(bucket));
        await ref.read(returnsPageProvider(bucket).future);
      },
      child: ListView(
        children: [
          AsyncValueView<ReturnsPage>(
            value: ref.watch(returnsPageProvider(bucket)),
            onRetry: () => ref.invalidate(returnsPageProvider(bucket)),
            loading: const SkeletonList(rows: 4),
            isEmpty: (p) => p.items.isEmpty,
            empty: Padding(
              padding: const EdgeInsets.all(AppSpace.s4),
              child: Text(
                l.returnsEmpty,
                key: Key('returns-empty-$bucket'),
                style: TextStyle(color: palette.muted),
              ),
            ),
            data:
                (p) => Column(
                  children: [
                    for (final r in p.items)
                      ListTile(
                        key: Key('returns-row-${r.id}'),
                        onTap: () => context.push('/returns/${r.id}'),
                        title: Text(
                          l.returnsListItem(r.number, r.orderNumber ?? 0),
                        ),
                        subtitle: Text(
                          [
                            if ((r.customerName ?? '').isNotEmpty)
                              r.customerName!,
                            resolutionLabel(l, r.resolution),
                            if (r.resolution == 'refund' &&
                                r.refundDueMinor > 0)
                              Formatters.money(
                                r.refundDueMinor,
                                r.currency,
                                lang,
                              ),
                          ].join(' · '),
                        ),
                        trailing: StatusChip(
                          label: returnStatusLabel(l, r.status),
                          colors: returnStatusColors(context, r.status),
                        ),
                      ),
                  ],
                ),
          ),
        ],
      ),
    );
  }
}

/// Home card: returns waiting for a decision. Hidden when none, or when the
/// person can't read returns (the request is refused).
class ReturnsHomeCard extends ConsumerWidget {
  const ReturnsHomeCard({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final palette = AppPalette.of(context);
    final n =
        ref
            .watch(returnsPageProvider('to_decide'))
            .valueOrNull
            ?.counts['to_decide'] ??
        0;
    if (n == 0) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.fromLTRB(
        AppSpace.s4,
        AppSpace.s4,
        AppSpace.s4,
        0,
      ),
      child: Material(
        color: palette.warningSoft,
        borderRadius: BorderRadius.circular(AppRadius.md),
        child: InkWell(
          key: const Key('returns-home-card'),
          borderRadius: BorderRadius.circular(AppRadius.md),
          onTap: () => context.push('/returns'),
          child: Padding(
            padding: const EdgeInsets.all(AppSpace.s4),
            child: Row(
              children: [
                const Icon(Icons.assignment_return_outlined),
                const SizedBox(width: AppSpace.s3),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        l.returnsHomeCard(n),
                        style: theme.textTheme.titleSmall,
                      ),
                      Text(
                        l.returnsHomeCardBody,
                        style: theme.textTheme.bodySmall?.copyWith(
                          color: palette.muted,
                        ),
                      ),
                    ],
                  ),
                ),
                const Icon(Icons.chevron_right),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
