import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/errors/api_error.dart';
import '../../../core/l10n/formatters.dart';
import '../../../core/l10n/gen/app_localizations.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens.g.dart';
import '../../../design/widgets/state_views.dart';
import '../data/twin_api.dart';
import 'twin_labels.dart';

/// True when the shop's plan doesn't include simulations (hide the entry).
bool simulationsNotInPlan(AsyncValue<Object?> v) {
  final e = v.error;
  return e is ApiError && (e.statusCode == 403);
}

/// Read-only list of recent what-if estimates (created on the web).
class SimulationsScreen extends ConsumerWidget {
  const SimulationsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final runs = ref.watch(simulationsProvider);
    return Scaffold(
      appBar: AppBar(title: Text(l.settingsWhatIf)),
      body: RefreshIndicator(
        onRefresh: () => ref.refresh(simulationsProvider.future),
        child: AsyncValueView<List<SimulationRun>>(
          value: runs,
          onRetry: () => ref.invalidate(simulationsProvider),
          data:
              (items) => ListView(
                padding: const EdgeInsets.all(AppSpace.s4),
                children: [
                  if (items.isEmpty)
                    EmptyState(
                      key: const Key('sim-empty'),
                      title: l.settingsWhatIf,
                      body: l.simEmpty,
                      icon: Icons.insights_outlined,
                    ),
                  for (final r in items) SimulationTile(run: r),
                ],
              ),
        ),
      ),
    );
  }
}

class SimulationTile extends StatelessWidget {
  const SimulationTile({super.key, required this.run});

  final SimulationRun run;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final p = AppPalette.of(context);
    final lang = Localizations.localeOf(context).languageCode;
    final r = run;
    final sub =
        r.status == 'failed'
            ? simError(l, r.errorCode)
            : !r.done
            ? l.simWorking
            : [
              l.simEstimate,
              if (simConfidence(l, r.confidence) case final c?) c,
              if (r.createdAt != null) Formatters.date(r.createdAt!, lang),
            ].join(' · ');
    return Card(
      key: Key('sim-${r.id}'),
      margin: const EdgeInsets.only(bottom: AppSpace.s2),
      child: ListTile(
        title: Text(simHeadline(l, r, lang)),
        subtitle: Text(
          sub,
          style: theme.textTheme.bodySmall?.copyWith(
            color: r.status == 'failed' ? p.danger : p.muted,
          ),
        ),
        trailing: const Icon(Icons.chevron_right),
        onTap: () => context.push('/what-if/${r.id}'),
      ),
    );
  }
}

class SimulationDetailScreen extends ConsumerWidget {
  const SimulationDetailScreen({super.key, required this.id});

  final String id;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final run = ref.watch(simulationProvider(id));
    return Scaffold(
      appBar: AppBar(title: Text(l.simEstimate)),
      body: AsyncValueView<SimulationRun>(
        value: run,
        onRetry: () => ref.invalidate(simulationProvider(id)),
        data: (r) => SimulationView(run: r),
      ),
    );
  }
}

/// An estimate: headline, key numbers with ranges, warnings, assumptions,
/// confidence, and the reminder that nothing has been changed.
class SimulationView extends StatelessWidget {
  const SimulationView({super.key, required this.run});

  final SimulationRun run;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final p = AppPalette.of(context);
    final lang = Localizations.localeOf(context).languageCode;
    final r = run;
    final warnings =
        [
          for (final w in r.warnings)
            simWarning(l, w, lang, currency: r.currency),
        ].whereType<String>().toList();
    final assumptions =
        [
          for (final a in r.assumptions) simAssumption(l, a, lang),
        ].whereType<String>().toList();
    final notIncluded = simNotIncluded(l, r);
    return ListView(
      key: const Key('sim-detail'),
      padding: const EdgeInsets.all(AppSpace.s4),
      children: [
        Text(simHeadline(l, r, lang), style: theme.textTheme.titleMedium),
        const SizedBox(height: AppSpace.s2),
        Wrap(
          spacing: AppSpace.s2,
          runSpacing: AppSpace.s2,
          children: [
            _Pill(text: l.simEstimate, bg: p.infoSoft, fg: p.info),
            if (simConfidence(l, r.confidence) case final c?)
              _Pill(
                key: const Key('sim-confidence'),
                text: c,
                bg: r.confidence == 'low' ? p.warningSoft : p.successSoft,
                fg: r.confidence == 'low' ? p.warning : p.success,
              ),
          ],
        ),
        const SizedBox(height: AppSpace.s3),
        if (r.status == 'failed')
          Text(
            simError(l, r.errorCode),
            key: const Key('sim-failed'),
            style: theme.textTheme.bodyMedium?.copyWith(color: p.danger),
          )
        else if (!r.done)
          Text(l.simWorking, style: theme.textTheme.bodyMedium)
        else ...[
          for (final f in simFacts(l, r, lang))
            Padding(
              padding: const EdgeInsets.only(bottom: AppSpace.s2),
              child: Text(f, style: theme.textTheme.bodyMedium),
            ),
          if (notIncluded != null)
            Text(
              notIncluded,
              style: theme.textTheme.bodySmall?.copyWith(color: p.muted),
            ),
          if (warnings.isNotEmpty) ...[
            const SizedBox(height: AppSpace.s3),
            Text(l.simWarningsTitle, style: theme.textTheme.titleSmall),
            const SizedBox(height: AppSpace.s1),
            for (final w in warnings)
              Padding(
                padding: const EdgeInsets.only(bottom: AppSpace.s1),
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Icon(
                      Icons.warning_amber_rounded,
                      size: 18,
                      color: p.warning,
                    ),
                    const SizedBox(width: AppSpace.s2),
                    Expanded(child: Text(w, style: theme.textTheme.bodySmall)),
                  ],
                ),
              ),
          ],
          if (assumptions.isNotEmpty) ...[
            const SizedBox(height: AppSpace.s3),
            Text(l.simAssumptionsTitle, style: theme.textTheme.titleSmall),
            const SizedBox(height: AppSpace.s1),
            for (final a in assumptions)
              Padding(
                padding: const EdgeInsets.only(bottom: AppSpace.s1),
                child: Text('• $a', style: theme.textTheme.bodySmall),
              ),
          ],
        ],
        const SizedBox(height: AppSpace.s4),
        Text(
          l.simNothingChanges,
          key: const Key('sim-nothing-changes'),
          style: theme.textTheme.bodySmall?.copyWith(color: p.muted),
        ),
      ],
    );
  }
}

class _Pill extends StatelessWidget {
  const _Pill({
    super.key,
    required this.text,
    required this.bg,
    required this.fg,
  });

  final String text;
  final Color bg;
  final Color fg;

  @override
  Widget build(BuildContext context) => DecoratedBox(
    decoration: BoxDecoration(
      color: bg,
      borderRadius: BorderRadius.circular(AppRadius.full),
    ),
    child: Padding(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpace.s2,
        vertical: AppSpace.s1,
      ),
      child: Text(
        text,
        style: Theme.of(context).textTheme.labelSmall?.copyWith(color: fg),
      ),
    ),
  );
}
