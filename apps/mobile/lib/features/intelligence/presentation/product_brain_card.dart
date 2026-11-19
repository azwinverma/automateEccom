import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/l10n/formatters.dart';
import '../../../core/l10n/gen/app_localizations.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens.g.dart';
import '../../../design/widgets/section_header.dart';
import '../../returns/presentation/returns_labels.dart';
import '../data/intelligence_api.dart';
import 'intelligence_labels.dart';

/// UX-018 Product Brain + UX-012 stock risk on the product screen.
/// Hidden quietly when the plan doesn't include it (403) or it can't load.
class ProductBrainCard extends ConsumerWidget {
  const ProductBrainCard({super.key, required this.productId});

  final String productId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final b = ref.watch(productBrainProvider(productId)).valueOrNull;
    if (b == null) return const SizedBox.shrink();
    return ProductBrainView(brain: b);
  }
}

class ProductBrainView extends StatelessWidget {
  const ProductBrainView({super.key, required this.brain});

  final ProductBrain brain;

  String _num(double v) =>
      v >= 10 ? v.round().toString() : v.toStringAsFixed(1);

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final p = AppPalette.of(context);
    final lang = Localizations.localeOf(context).languageCode;
    final b = brain;
    final muted = theme.textTheme.bodySmall?.copyWith(color: p.muted);
    // Each distinct reason once, as a plain sentence.
    final missing = {
      for (final r in b.notIncluded.values) notIncludedLabel(l, r),
    };
    final (fg, bg) = switch (b.stockRisk) {
      'out' || 'high' => (p.danger, p.dangerSoft),
      'medium' => (p.warning, p.warningSoft),
      _ => (p.success, p.successSoft),
    };
    return Column(
      key: const Key('product-brain'),
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SectionHeader(l.pbTitle),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: AppSpace.s4),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              if (b.demandPerDay != null)
                Text(
                  l.pbDemand(_num(b.demandPerDay!), b.inStockDays),
                  key: const Key('pb-demand'),
                  style: theme.textTheme.titleSmall,
                ),
              Text(l.pbUnits(b.units7, b.units30, b.units90), style: muted),
              const SizedBox(height: AppSpace.s2),
              if (b.available != null)
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        b.coverDays != null
                            ? l.pbStock(b.available!, _num(b.coverDays!))
                            : l.pbStockOnly(b.available!),
                        style: theme.textTheme.bodyMedium,
                      ),
                    ),
                    if (b.stockRisk != null)
                      Container(
                        key: Key('pb-risk-${b.stockRisk}'),
                        padding: const EdgeInsets.symmetric(
                          horizontal: AppSpace.s2,
                          vertical: 2,
                        ),
                        decoration: BoxDecoration(
                          color: bg,
                          borderRadius: BorderRadius.circular(AppRadius.md),
                        ),
                        child: Text(
                          stockRiskLabel(l, b.stockRisk!),
                          style: theme.textTheme.labelMedium?.copyWith(
                            color: fg,
                          ),
                        ),
                      ),
                  ],
                ),
              if (b.stockouts > 0)
                Text(l.pbStockouts(b.stockouts), style: muted),
              if (b.marginPct != null)
                Text(
                  l.pbMargin(_num(b.marginPct!)),
                  style: theme.textTheme.bodyMedium,
                ),
              if (b.contributionPerUnit != null)
                Text(
                  (b.contributionBasis == 'complete'
                      ? l.pbContribution
                      : l.pbContributionPartial)(
                    Formatters.money(b.contributionPerUnit!, b.currency, lang),
                  ),
                  key: const Key('pb-contribution'),
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: b.contributionPerUnit! < 0 ? p.danger : null,
                  ),
                ),
              if (b.returnRate != null)
                Text(
                  l.pbReturnRate((b.returnRate! * 100).round().toString()),
                  style: theme.textTheme.bodyMedium,
                ),
              if (b.topReasons.isNotEmpty)
                Text(
                  l.pbTopReason(
                    returnReasonLabel(l, b.topReasons.first.reason),
                  ),
                  style: muted,
                ),
              if (b.fit != null)
                Padding(
                  padding: const EdgeInsets.only(top: AppSpace.s1),
                  child: Text(
                    b.fit == 'small' ? l.pbFitSmall : l.pbFitLarge,
                    key: const Key('pb-fit'),
                    style: theme.textTheme.bodySmall?.copyWith(color: p.info),
                  ),
                ),
              const SizedBox(height: AppSpace.s2),
              for (final m in missing)
                Text(m, style: muted, key: Key('pb-missing-${m.hashCode}')),
              Text(
                l.pbCompleteness((b.completeness * 100).round().toString()),
                style: muted,
              ),
            ],
          ),
        ),
      ],
    );
  }
}
