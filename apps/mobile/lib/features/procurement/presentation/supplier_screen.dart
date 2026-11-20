import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/l10n/formatters.dart';
import '../../../core/l10n/gen/app_localizations.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens.g.dart';
import '../../../design/widgets/state_views.dart';
import '../data/procurement_api.dart';
import 'procurement_labels.dart';

/// Supplier contact + terms, and (on plans with Supplier Intelligence) how they perform.
class SupplierScreen extends ConsumerWidget {
  const SupplierScreen({super.key, required this.supplierId});

  final String supplierId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final palette = AppPalette.of(context);
    final value = ref.watch(supplierProvider(supplierId));
    return Scaffold(
      appBar: AppBar(title: Text(value.valueOrNull?.name ?? l.supTitle)),
      body: AsyncValueView<SupplierDetail>(
        value: value,
        onRetry: () => ref.invalidate(supplierProvider(supplierId)),
        data:
            (s) => ListView(
              padding: const EdgeInsets.all(AppSpace.s4),
              children: [
                if ((s.phone ?? '').isNotEmpty)
                  Text(s.phone!, style: theme.textTheme.bodyMedium),
                if ((s.contactName ?? '').isNotEmpty)
                  Text(
                    l.supContact(s.contactName!),
                    style: theme.textTheme.bodySmall,
                  ),
                if ((s.paymentTerms ?? '').isNotEmpty)
                  Text(
                    l.supTerms(s.paymentTerms!),
                    style: theme.textTheme.bodySmall,
                  ),
                if (s.defaultLeadTimeDays != null)
                  Text(
                    l.supLead(s.defaultLeadTimeDays.toString()),
                    style: theme.textTheme.bodySmall,
                  ),
                const SizedBox(height: AppSpace.s4),
                if (s.performance == null)
                  Text(
                    l.supPerfNone,
                    key: const Key('sup-perf-none'),
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: palette.muted,
                    ),
                  )
                else
                  SupplierPerformanceCard(
                    perf: s.performance!,
                    currency: s.currency,
                  ),
              ],
            ),
      ),
    );
  }
}

class SupplierPerformanceCard extends StatelessWidget {
  const SupplierPerformanceCard({
    super.key,
    required this.perf,
    this.currency = 'NPR',
  });

  final SupplierPerformance perf;
  final String currency;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final palette = AppPalette.of(context);
    final lang = Localizations.localeOf(context).languageCode;
    String pct(double? r) => r == null ? '–' : Formatters.percent(r, lang);
    String money(int? m) =>
        m == null ? '–' : Formatters.money(m, currency, lang);
    final rows = <(String, String)>[
      (l.supLanded, money(perf.avgLandedCostMinor)),
      (l.supDefect, pct(perf.defectRate)),
      (l.supQuality, pct(perf.qualityReturnRate)),
      (l.supOnTime, pct(perf.onTimeRate)),
      (
        l.supLeadMeasured,
        perf.leadTimeDaysAvg == null
            ? '–'
            : l.supLeadDays(perf.leadTimeDaysAvg!.toStringAsFixed(1)),
      ),
      (
        l.supProfit,
        perf.contributionPerUnitMinor == null
            ? l.supProfitMissing
            : money(perf.contributionPerUnitMinor),
      ),
    ];
    final ni = [
      for (final c in perf.notIncluded)
        if (supplierNotIncludedLabel(l, c) != null)
          supplierNotIncludedLabel(l, c)!,
    ];
    return Card(
      key: const Key('sup-perf'),
      margin: EdgeInsets.zero,
      child: Padding(
        padding: const EdgeInsets.all(AppSpace.s3),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(l.supPerfTitle, style: theme.textTheme.titleSmall),
            Text(
              l.supPerfFrom(
                perf.receivedUnits.toString(),
                perf.soldUnits.toString(),
              ),
              style: theme.textTheme.bodySmall?.copyWith(color: palette.muted),
            ),
            const SizedBox(height: AppSpace.s2),
            for (final (k, v) in rows)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 2),
                child: Row(
                  children: [
                    Expanded(child: Text(k, style: theme.textTheme.bodySmall)),
                    Flexible(
                      child: Text(
                        v,
                        textAlign: TextAlign.end,
                        style: theme.textTheme.bodyMedium,
                      ),
                    ),
                  ],
                ),
              ),
            if (ni.isNotEmpty)
              Padding(
                padding: const EdgeInsets.only(top: AppSpace.s2),
                child: Text(
                  l.supNotIncluded(ni.join(', ')),
                  key: const Key('sup-not-included'),
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: palette.muted,
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
