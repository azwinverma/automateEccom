import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/l10n/formatters.dart';
import '../../../core/l10n/gen/app_localizations.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens.g.dart';
import '../../../design/widgets/section_header.dart';
import '../../../design/widgets/state_views.dart';
import '../data/billing_api.dart';
import 'widgets/resource_labels.dart';
import 'widgets/usage_meter.dart';
import 'widgets/video_credit_meter.dart';

class PlanUsageScreen extends ConsumerWidget {
  const PlanUsageScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);

    Future<void> refresh() async {
      ref
        ..invalidate(subscriptionProvider)
        ..invalidate(entitlementsProvider)
        ..invalidate(creditsProvider);
      await Future.wait<Object?>([
        ref.read(subscriptionProvider.future),
        ref.read(entitlementsProvider.future),
        ref.read(creditsProvider.future),
      ]).catchError((Object _) => <Object?>[]);
    }

    return Scaffold(
      appBar: AppBar(title: Text(l.planTitle)),
      body: RefreshIndicator(
        onRefresh: refresh,
        child: ListView(
          padding: const EdgeInsets.only(bottom: AppSpace.s8),
          children: [
            AsyncValueView<Subscription>(
              value: ref.watch(subscriptionProvider),
              onRetry: () => ref.invalidate(subscriptionProvider),
              loading: const SkeletonList(rows: 1),
              data: (s) => _PlanHeader(subscription: s),
            ),
            SectionHeader(l.usageTitle),
            ColoredBox(
              color: theme.colorScheme.surface,
              child: AsyncValueView<Entitlements>(
                value: ref.watch(entitlementsProvider),
                onRetry: () => ref.invalidate(entitlementsProvider),
                isEmpty: (e) => e.limits.isEmpty,
                empty: EmptyState(title: l.usageEmpty),
                data: (e) => _UsageList(limits: e.limits),
              ),
            ),
            SectionHeader(l.creditsTitle),
            ColoredBox(
              color: theme.colorScheme.surface,
              child: AsyncValueView<Credits>(
                value: ref.watch(creditsProvider),
                onRetry: () => ref.invalidate(creditsProvider),
                loading: const SkeletonList(rows: 1),
                data: (c) => _CreditsRow(credits: c),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _PlanHeader extends StatelessWidget {
  const _PlanHeader({required this.subscription});

  final Subscription subscription;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final palette = AppPalette.of(context);
    final lang = Localizations.localeOf(context).languageCode;
    final s = subscription;

    final (String status, Color color) = switch (s.status) {
      'trialing' => (
          s.trialEndsAt == null
              ? l.planStatusActive
              : l.planStatusTrialing(Formatters.date(s.trialEndsAt!, lang)),
          palette.info,
        ),
      'active' => (l.planStatusActive, palette.success),
      'past_due' => (l.planStatusPastDue, palette.warning),
      'canceled' || 'cancelled' => (l.planStatusCanceled, palette.danger),
      final other => (other, theme.colorScheme.onSurfaceVariant),
    };

    return Padding(
      padding: const EdgeInsets.fromLTRB(
        AppSpace.s4,
        AppSpace.s4,
        AppSpace.s4,
        0,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(s.planName, style: theme.textTheme.headlineSmall),
          if (s.tagline != null && s.tagline!.isNotEmpty)
            Text(
              s.tagline!,
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
          const SizedBox(height: AppSpace.s2),
          Text(status, style: theme.textTheme.labelLarge?.copyWith(color: color)),
          if (s.periodStart != null && s.periodEnd != null)
            Text(
              l.planPeriod(
                Formatters.date(s.periodStart!, lang),
                Formatters.date(s.periodEnd!, lang),
              ),
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
        ],
      ),
    );
  }
}

class _UsageList extends StatelessWidget {
  const _UsageList({required this.limits});

  final List<UsageLimit> limits;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final rows = <Widget>[];
    for (final u in limits) {
      if (rows.isNotEmpty) rows.add(const Divider(indent: AppSpace.s4));
      if (u.isVideo) {
        rows.add(
          VideoCreditMeter(
            monthlyUsed: u.used,
            monthlyLimit: u.limit,
            monthlyReserved: u.reserved,
            monthlyAlertLevel: u.alertLevel,
            dailyUsed: u.burst?.used ?? 0,
            dailyLimit: u.burst?.limit,
          ),
        );
      } else {
        rows.add(
          UsageMeter(
            label: resourceLabel(l, u.resource),
            used: u.used,
            limit: u.limit,
            reserved: u.reserved,
            alertLevel: u.alertLevel,
            periodLabel: switch (u.period) {
              'month' => l.usagePeriodMonth,
              'day' => l.usagePeriodDay,
              _ => null,
            },
          ),
        );
      }
    }
    return Column(children: rows);
  }
}

class _CreditsRow extends StatelessWidget {
  const _CreditsRow({required this.credits});

  final Credits credits;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final lang = Localizations.localeOf(context).languageCode;
    return Padding(
      padding: const EdgeInsets.all(AppSpace.s4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            l.creditsBalance(Formatters.integer(credits.balance, lang)),
            style: theme.textTheme.titleMedium,
          ),
          if (credits.transactionCount == 0)
            Text(
              l.creditsNoTransactions,
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
        ],
      ),
    );
  }
}
