import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/l10n/gen/app_localizations.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens.g.dart';
import '../data/intelligence_api.dart';
import 'intelligence_labels.dart';

/// UX-022 "What sells" on Home: learning progress, or the patterns that
/// bring orders (likes alone never count). Hidden on 403 or failure.
class CreativeGenomeCard extends ConsumerWidget {
  const CreativeGenomeCard({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final g = ref.watch(creativeGenomeProvider).valueOrNull;
    if (g == null) return const SizedBox.shrink();
    return CreativeGenomeView(
      genome: g,
      onSeeAll: () => context.push('/what-sells'),
    );
  }
}

class CreativeGenomeView extends StatelessWidget {
  const CreativeGenomeView({super.key, required this.genome, this.onSeeAll});

  final CreativeGenome genome;
  final VoidCallback? onSeeAll;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final p = AppPalette.of(context);
    final g = genome;
    final top = g.recommended.take(3).toList();
    return Padding(
      key: const Key('creative-genome-card'),
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
              Text(l.cgTitle, style: theme.textTheme.titleSmall),
              const SizedBox(height: AppSpace.s2),
              if (!g.ready) ...[
                Text(
                  l.cgLearning(g.measuredPosts, g.minPosts),
                  key: const Key('cg-learning'),
                  style: theme.textTheme.bodyMedium,
                ),
                const SizedBox(height: AppSpace.s2),
                ClipRRect(
                  borderRadius: BorderRadius.circular(AppRadius.sm),
                  child: LinearProgressIndicator(
                    value:
                        g.minPosts == 0
                            ? 0
                            : (g.measuredPosts / g.minPosts)
                                .clamp(0, 1)
                                .toDouble(),
                    minHeight: 6,
                  ),
                ),
                const SizedBox(height: AppSpace.s2),
                Text(
                  l.cgLearningHint(g.minPosts),
                  style: theme.textTheme.bodySmall?.copyWith(color: p.muted),
                ),
              ] else if (top.isEmpty)
                Text(
                  l.cgNothingYet,
                  key: const Key('cg-nothing'),
                  style: theme.textTheme.bodySmall?.copyWith(color: p.muted),
                )
              else
                for (final x in top) PatternRow(pref: x, outcome: g.outcome),
              if (g.ready && g.engagementOnly.isNotEmpty) ...[
                const SizedBox(height: AppSpace.s2),
                for (final x in g.engagementOnly.take(2))
                  Text(
                    '${creativePatternLabel(l, x.attribute, x.value)}: ${l.cgEngagementOnly}',
                    key: Key('cg-engagement-${x.attribute}-${x.value}'),
                    style: theme.textTheme.bodySmall?.copyWith(color: p.muted),
                  ),
              ],
              if (g.ready && g.preferences.isNotEmpty && onSeeAll != null)
                Align(
                  alignment: AlignmentDirectional.centerStart,
                  child: TextButton(
                    key: const Key('cg-see-all'),
                    onPressed: onSeeAll,
                    child: Text(l.cgSeeAll),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

/// One pattern: phrase, lift, sample size and confidence.
class PatternRow extends StatelessWidget {
  const PatternRow({super.key, required this.pref, required this.outcome});

  final CreativePreference pref;
  final String outcome;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final p = AppPalette.of(context);
    final x = pref;
    return Padding(
      key: Key('cg-pattern-${x.attribute}-${x.value}'),
      padding: const EdgeInsets.only(bottom: AppSpace.s2),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            creativePatternLabel(l, x.attribute, x.value),
            style: theme.textTheme.bodyMedium?.copyWith(
              fontWeight: FontWeight.w600,
            ),
          ),
          Text(
            [
              if (x.lift > 0) creativeLiftLabel(l, x.lift, outcome),
              l.cgEvidence(
                x.n.toString(),
                creativeConfidenceLabel(l, x.confidence),
              ),
            ].join(' · '),
            style: theme.textTheme.bodySmall?.copyWith(color: p.muted),
          ),
        ],
      ),
    );
  }
}

/// All learned patterns (recommended first, then the rest).
class CreativeGenomeScreen extends ConsumerWidget {
  const CreativeGenomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final g = ref.watch(creativeGenomeProvider).valueOrNull;
    return Scaffold(
      appBar: AppBar(title: Text(l.cgTitle)),
      body: RefreshIndicator(
        onRefresh: () => ref.refresh(creativeGenomeProvider.future),
        child: ListView(
          padding: const EdgeInsets.only(top: AppSpace.s3, bottom: AppSpace.s8),
          children: [
            if (g != null) ...[
              CreativeGenomeView(genome: g),
              if (g.ready &&
                  g.preferences.any((x) => !x.recommended && !x.engagementOnly))
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: AppSpace.s4),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        l.cgOtherPatterns,
                        style: theme.textTheme.titleSmall,
                      ),
                      const SizedBox(height: AppSpace.s2),
                      for (final x in g.preferences.where(
                        (x) => !x.recommended && !x.engagementOnly,
                      ))
                        PatternRow(pref: x, outcome: g.outcome),
                    ],
                  ),
                ),
            ],
          ],
        ),
      ),
    );
  }
}
