import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';

import '../../../core/auth/permissions.dart';
import '../../../core/l10n/formatters.dart';
import '../../../core/l10n/gen/app_localizations.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens.g.dart';
import '../data/twin_api.dart';

/// "Store at a glance" on Home, from the Digital Store Twin (a derived read
/// model). Shows when its numbers were read and flags stale ones. Hidden
/// quietly on any error: the cards below carry the exact numbers.
class StoreGlanceStrip extends ConsumerWidget {
  const StoreGlanceStrip({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Shop-level totals need analytics.read. Wait for the permission list;
    // if it's known and lacks it, don't even ask. Unknown → ask; a 403 hides.
    final perms = ref.watch(myPermissionsProvider);
    if (!perms.hasValue || !mayDo(perms.value, 'analytics.read')) {
      return const SizedBox.shrink();
    }
    final s = ref.watch(twinSummaryProvider).valueOrNull;
    if (s == null || s.sections.isEmpty) return const SizedBox.shrink();
    return StoreGlanceView(summary: s);
  }
}

enum _Tone { neutral, warn, danger }

class _ChipData {
  const _ChipData(this.key, this.text, this.tone, [this.route]);
  final String key;
  final String text;
  final _Tone tone;
  final String? route;
}

class StoreGlanceView extends StatelessWidget {
  const StoreGlanceView({super.key, required this.summary});

  final TwinSummary summary;

  List<_ChipData> _chips(AppLocalizations l, String lang) {
    final out = <_ChipData>[];
    String n(int v) => Formatters.integer(v, lang);
    final orders = summary['orders'];
    if (orders != null) {
      final review = orders.count('needs_review');
      out.add(
        _ChipData(
          'orders',
          [
            l.twinOrders(n(orders.count('open'))),
            if (review > 0) l.twinToReview(n(review)),
          ].join(' · '),
          review > 0 ? _Tone.warn : _Tone.neutral,
          '/orders',
        ),
      );
    }
    final inv = summary['inventory'];
    if (inv != null && inv.count('tracked_variants') > 0) {
      final outOf = inv.count('out_of_stock');
      final low = inv.count('low_stock');
      out.add(
        _ChipData(
          'stock',
          l.twinStock(n(outOf), n(low)),
          outOf > 0
              ? _Tone.danger
              : low > 0
              ? _Tone.warn
              : _Tone.neutral,
        ),
      );
    }
    final cod = summary['cod'];
    if (cod != null && cod.count('cash_with_courier_minor') > 0) {
      out.add(
        _ChipData(
          'cash',
          l.twinCash(
            Formatters.money(
              cod.count('cash_with_courier_minor'),
              summary.currency,
              lang,
            ),
          ),
          _Tone.neutral,
          '/cod',
        ),
      );
    }
    final ret = summary['returns'];
    if (ret != null && ret.count('open') > 0) {
      out.add(
        _ChipData(
          'returns',
          l.twinReturns(n(ret.count('open'))),
          _Tone.neutral,
          '/returns',
        ),
      );
    }
    final sup = summary['suppliers'];
    if (sup != null && sup.count('awaiting_approval') > 0) {
      out.add(
        _ChipData(
          'pos',
          l.twinPosToApprove(n(sup.count('awaiting_approval'))),
          _Tone.warn,
          '/purchase-orders?status=pending_approval',
        ),
      );
    }
    if (sup != null && sup.count('overdue') > 0) {
      out.add(
        _ChipData(
          'pos-late',
          l.twinPosLate(n(sup.count('overdue'))),
          _Tone.danger,
          '/purchase-orders?status=sent',
        ),
      );
    }
    final ex = summary['exceptions'];
    if (ex != null && ex.count('total') > 0) {
      out.add(
        _ChipData(
          'attention',
          l.twinAttention(n(ex.count('total'))),
          _Tone.warn,
        ),
      );
    }
    return out;
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final p = AppPalette.of(context);
    final lang = Localizations.localeOf(context).languageCode;
    final chips = _chips(l, lang);
    if (chips.isEmpty) return const SizedBox.shrink();
    final asOf = summary.asOf;
    return Padding(
      key: const Key('store-glance'),
      padding: const EdgeInsets.fromLTRB(
        AppSpace.s4,
        0,
        AppSpace.s4,
        AppSpace.s3,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(l.twinTitle, style: theme.textTheme.titleSmall),
              ),
              if (asOf != null)
                Flexible(
                  child: Text(
                    l.twinAsOf(DateFormat.Hm(lang).format(asOf.toLocal())),
                    key: const Key('store-glance-as-of'),
                    overflow: TextOverflow.ellipsis,
                    style: theme.textTheme.bodySmall?.copyWith(color: p.muted),
                  ),
                ),
            ],
          ),
          const SizedBox(height: AppSpace.s2),
          Wrap(
            spacing: AppSpace.s2,
            runSpacing: AppSpace.s2,
            children: [
              for (final c in chips)
                _GlanceChip(
                  key: Key('glance-${c.key}'),
                  data: c,
                  palette: p,
                  onTap: c.route == null ? null : () => context.push(c.route!),
                ),
            ],
          ),
          if (summary.anyStale) ...[
            const SizedBox(height: AppSpace.s2),
            Row(
              key: const Key('store-glance-stale'),
              children: [
                Icon(Icons.schedule, size: 16, color: p.warning),
                const SizedBox(width: AppSpace.s1),
                Expanded(
                  child: Text(
                    l.twinStale,
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: p.warning,
                    ),
                  ),
                ),
              ],
            ),
          ],
        ],
      ),
    );
  }
}

class _GlanceChip extends StatelessWidget {
  const _GlanceChip({
    super.key,
    required this.data,
    required this.palette,
    this.onTap,
  });

  final _ChipData data;
  final AppPalette palette;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final (bg, fg) = switch (data.tone) {
      _Tone.danger => (palette.dangerSoft, palette.danger),
      _Tone.warn => (palette.warningSoft, palette.warning),
      _Tone.neutral => (
        theme.colorScheme.surfaceContainerHighest,
        theme.colorScheme.onSurface,
      ),
    };
    final label = Text(
      data.text,
      style: theme.textTheme.labelMedium?.copyWith(color: fg),
    );
    return Material(
      color: bg,
      borderRadius: BorderRadius.circular(AppRadius.full),
      child: InkWell(
        borderRadius: BorderRadius.circular(AppRadius.full),
        onTap: onTap,
        child: ConstrainedBox(
          constraints: const BoxConstraints(minHeight: 36),
          child: Padding(
            padding: const EdgeInsets.symmetric(
              horizontal: AppSpace.s3,
              vertical: AppSpace.s2,
            ),
            child:
                onTap == null
                    ? label
                    : Row(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Flexible(child: label),
                        const SizedBox(width: AppSpace.s1),
                        Icon(Icons.chevron_right, size: 16, color: fg),
                      ],
                    ),
          ),
        ),
      ),
    );
  }
}
