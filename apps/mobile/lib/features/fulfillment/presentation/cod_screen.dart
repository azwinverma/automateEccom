import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/errors/api_error.dart';
import '../../../core/l10n/formatters.dart';
import '../../../core/l10n/gen/app_localizations.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens.g.dart';
import '../../../design/widgets/section_header.dart';
import '../../../design/widgets/state_views.dart';
import '../data/fulfillment_api.dart';
import 'fulfillment_labels.dart';

/// COD money on the go: cash still with couriers (oldest first) and courier
/// statements. Reconciling mismatches is a web task; mobile can confirm a
/// statement that already matches once the money has arrived.
class CodScreen extends ConsumerStatefulWidget {
  const CodScreen({super.key});

  @override
  ConsumerState<CodScreen> createState() => _CodScreenState();
}

class _CodScreenState extends ConsumerState<CodScreen> {
  String? _busyId;
  ApiError? _error;

  void _reload() {
    ref
      ..invalidate(codOverviewProvider)
      ..invalidate(codAwaitingProvider)
      ..invalidate(codSettlementsProvider);
  }

  Future<void> _confirm(CodSettlement st) async {
    setState(() {
      _busyId = st.id;
      _error = null;
    });
    try {
      await ref.read(fulfillmentApiProvider).confirmSettlement(st.id);
      _reload();
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(AppLocalizations.of(context).codConfirmed)),
        );
      }
    } on Object catch (e) {
      if (mounted) setState(() => _error = asApiError(e));
    } finally {
      if (mounted) setState(() => _busyId = null);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final palette = AppPalette.of(context);
    final lang = Localizations.localeOf(context).languageCode;
    String money(int m, String c) => Formatters.money(m, c, lang);
    return Scaffold(
      appBar: AppBar(title: Text(l.codTitle)),
      body: RefreshIndicator(
        onRefresh: () async {
          _reload();
          await ref.read(codOverviewProvider.future);
        },
        child: ListView(
          padding: const EdgeInsets.only(bottom: AppSpace.s8),
          children: [
            AsyncValueView<CodOverview>(
              value: ref.watch(codOverviewProvider),
              onRetry: () => ref.invalidate(codOverviewProvider),
              loading: const SkeletonList(rows: 1),
              data:
                  (o) => Padding(
                    padding: const EdgeInsets.all(AppSpace.s4),
                    child: _OverviewSummary(overview: o, currency: 'NPR'),
                  ),
            ),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: AppSpace.s4),
                child: InlineError(error: _error!),
              ),
            SectionHeader(l.codAwaitingTitle),
            AsyncValueView<List<CodAwaiting>>(
              value: ref.watch(codAwaitingProvider),
              onRetry: () => ref.invalidate(codAwaitingProvider),
              loading: const SkeletonList(rows: 2),
              isEmpty: (items) => items.isEmpty,
              empty: Padding(
                padding: const EdgeInsets.symmetric(horizontal: AppSpace.s4),
                child: Text(
                  l.codAwaitingEmpty,
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: palette.muted,
                  ),
                ),
              ),
              data:
                  (items) => Column(
                    children: [
                      for (final a in items)
                        ListTile(
                          key: Key('cod-awaiting-${a.shipmentId}'),
                          title: Text(
                            l.codOrderCourier(a.orderNumber, a.courierName),
                          ),
                          subtitle:
                              a.daysWaiting == null
                                  ? null
                                  : Text(
                                    l.codDaysWaiting(a.daysWaiting!),
                                    style: TextStyle(
                                      color:
                                          a.daysWaiting! > 14
                                              ? palette.danger
                                              : palette.muted,
                                    ),
                                  ),
                          trailing: Text(money(a.amountMinor, a.currency)),
                          onTap: () => context.push('/orders/${a.orderId}'),
                        ),
                    ],
                  ),
            ),
            SectionHeader(l.codSettlementsTitle),
            AsyncValueView<List<CodSettlement>>(
              value: ref.watch(codSettlementsProvider),
              onRetry: () => ref.invalidate(codSettlementsProvider),
              loading: const SkeletonList(rows: 2),
              isEmpty: (items) => items.isEmpty,
              empty: Padding(
                padding: const EdgeInsets.symmetric(horizontal: AppSpace.s4),
                child: Text(
                  l.codSettlementsEmpty,
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: palette.muted,
                  ),
                ),
              ),
              data:
                  (items) => Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      for (final st in items)
                        Padding(
                          key: Key('cod-settlement-${st.id}'),
                          padding: const EdgeInsets.symmetric(
                            horizontal: AppSpace.s4,
                            vertical: AppSpace.s2,
                          ),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.stretch,
                            children: [
                              Row(
                                children: [
                                  Expanded(
                                    child: Text(
                                      '${st.reference} · ${st.courierName}',
                                      style: theme.textTheme.titleSmall,
                                    ),
                                  ),
                                  Text(money(st.netMinor, st.currency)),
                                ],
                              ),
                              const SizedBox(height: AppSpace.s1),
                              Align(
                                alignment: Alignment.centerLeft,
                                child: StatusChip(
                                  label: settlementStatusLabel(l, st.status),
                                  colors: switch (st.status) {
                                    'confirmed' => (
                                      palette.success,
                                      palette.successSoft,
                                    ),
                                    'reconciled' => (
                                      palette.info,
                                      palette.infoSoft,
                                    ),
                                    _ => (palette.danger, palette.dangerSoft),
                                  },
                                ),
                              ),
                              if (st.status == 'needs_review' &&
                                  st.issueCount > 0)
                                Padding(
                                  padding: const EdgeInsets.only(
                                    top: AppSpace.s1,
                                  ),
                                  child: Text(
                                    l.codIssues(st.issueCount),
                                    style: theme.textTheme.bodySmall,
                                  ),
                                ),
                              if (st.status == 'reconciled')
                                Padding(
                                  padding: const EdgeInsets.only(
                                    top: AppSpace.s2,
                                  ),
                                  child: FilledButton(
                                    key: Key('cod-confirm-${st.id}'),
                                    style: FilledButton.styleFrom(
                                      minimumSize: const Size.fromHeight(48),
                                    ),
                                    onPressed:
                                        _busyId == null
                                            ? () => _confirm(st)
                                            : null,
                                    child: Text(l.codConfirmReceived),
                                  ),
                                ),
                            ],
                          ),
                        ),
                    ],
                  ),
            ),
          ],
        ),
      ),
    );
  }
}

class _OverviewSummary extends StatelessWidget {
  const _OverviewSummary({required this.overview, required this.currency});

  final CodOverview overview;
  final String currency;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final palette = AppPalette.of(context);
    final lang = Localizations.localeOf(context).languageCode;
    final o = overview;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(l.codWithCouriers, style: theme.textTheme.labelLarge),
        Text(
          Formatters.money(o.withCouriersMinor, currency, lang),
          key: const Key('cod-with-couriers'),
          style: theme.textTheme.headlineSmall,
        ),
        Text(
          l.codWithCouriersBody(o.withCouriersCount),
          style: theme.textTheme.bodySmall?.copyWith(color: palette.muted),
        ),
        if (o.overTwoWeeksMinor > 0)
          Text(
            l.codOverTwoWeeks(
              Formatters.money(o.overTwoWeeksMinor, currency, lang),
            ),
            style: theme.textTheme.bodySmall?.copyWith(color: palette.danger),
          ),
        if (o.needingReview > 0)
          Text(
            l.codNeedsReview(o.needingReview),
            style: theme.textTheme.bodySmall?.copyWith(color: palette.warning),
          ),
      ],
    );
  }
}

/// Home card: how much COD cash is still with couriers. Hidden when the
/// person can't read payments (the request is refused) or nothing is owed.
class CodHomeCard extends ConsumerWidget {
  const CodHomeCard({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final o = ref.watch(codOverviewProvider).valueOrNull;
    if (o == null || (o.withCouriersCount == 0 && o.needingReview == 0)) {
      return const SizedBox.shrink();
    }
    final palette = AppPalette.of(context);
    return Padding(
      padding: const EdgeInsets.fromLTRB(
        AppSpace.s4,
        AppSpace.s4,
        AppSpace.s4,
        0,
      ),
      child: Material(
        color: palette.infoSoft,
        borderRadius: BorderRadius.circular(AppRadius.md),
        child: InkWell(
          key: const Key('cod-home-card'),
          borderRadius: BorderRadius.circular(AppRadius.md),
          onTap: () => context.push('/cod'),
          child: Padding(
            padding: const EdgeInsets.all(AppSpace.s4),
            child: Row(
              children: [
                Expanded(child: _OverviewSummary(overview: o, currency: 'NPR')),
                const Icon(Icons.chevron_right),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
