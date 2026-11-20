import '../../../core/l10n/formatters.dart';
import '../../../core/l10n/gen/app_localizations.dart';
import '../data/twin_api.dart';

String _num(Object? v, String lang, {int digits = 1}) {
  if (v is! num) return '–';
  if (v == v.roundToDouble()) return Formatters.integer(v.toInt(), lang);
  return v.toStringAsFixed(digits);
}

String _pct(Object? probability) =>
    probability is num ? (probability * 100).round().toString() : '–';

String _money(Object? minor, String lang, String currency) =>
    minor is num ? Formatters.money(minor.round(), currency, lang) : '–';

String simHeadline(AppLocalizations l, SimulationRun r, String lang) {
  final o = r.outputs ?? r.inputs;
  switch (r.kind) {
    case 'discount':
      return l.simHeadDiscount(
        _num(o['discount_pct'] ?? r.inputs['discount_pct'], lang),
        (o['title'] as String?) ?? '',
        _num(o['days'] ?? r.inputs['days'], lang),
      );
    case 'purchase_quantity':
      final variant = o['variant'] as String?;
      final title = [
        (o['title'] as String?) ?? '',
        if (variant != null) '($variant)',
      ].join(' ');
      return l.simHeadPurchase(
        _num(o['quantity'] ?? r.inputs['quantity'], lang),
        title,
      );
  }
  return r.kind;
}

String? simConfidence(AppLocalizations l, String? c) => switch (c) {
  'low' => l.simConfidenceLow,
  'medium' => l.simConfidenceMedium,
  'high' => l.simConfidenceHigh,
  _ => null,
};

String simError(AppLocalizations l, String? code) => l.simFailed(switch (code) {
  'simulation_not_enough_sales' => l.simErrNotEnoughSales,
  'simulation_no_variants' => l.simErrNoVariants,
  'product_not_found' || 'variant_not_found' => l.simErrNotFound,
  _ => l.simErrGeneric,
});

/// The key numbers of an estimate, as plain sentences (ranges included).
List<String> simFacts(AppLocalizations l, SimulationRun r, String lang) {
  final out = <String>[];
  if (r.kind == 'discount') {
    final u = r.out('units');
    if (u.isNotEmpty) {
      out.add(
        l.simUnits(
          _num(u['expected'], lang),
          _num(u['low'], lang),
          _num(u['high'], lang),
          _num(u['baseline'], lang),
        ),
      );
    }
    final c = r.out('contribution_minor');
    final withD = c['with_discount'];
    if (withD is Map && c['without_discount'] != null) {
      out.add(
        l.simProfit(
          _money(withD['expected'], lang, r.currency),
          _money(c['without_discount'], lang, r.currency),
        ),
      );
    }
    final diff = r.n('difference_minor');
    if (diff != null && diff != 0) {
      out.add(
        diff > 0
            ? l.simMoreProfit(_money(diff, lang, r.currency))
            : l.simLessProfit(_money(-diff, lang, r.currency)),
      );
    }
    final m = r.out('margin_pct');
    if (m['before'] != null && m['after'] != null) {
      out.add(l.simMargin(_num(m['before'], lang), _num(m['after'], lang)));
    }
    if (r.n('stockout_probability') != null) {
      out.add(l.simStockout(_pct(r.n('stockout_probability'))));
    }
    if (r.n('stock_days') != null) {
      out.add(l.simStockDays(_num(r.n('stock_days'), lang)));
    }
  } else if (r.kind == 'purchase_quantity') {
    out.add(
      l.simStockoutBefore(
        _pct(r.n('stockout_before_arrival_probability')),
        _num(r.n('lead_days'), lang),
      ),
    );
    if (r.n('cover_days_after_arrival') != null) {
      out.add(l.simCover(_num(r.n('cover_days_after_arrival'), lang)));
    }
    out.add(l.simSellOut(_pct(r.n('sell_out_within_60d_probability'))));
    out.add(l.simLeftover(_num(r.n('leftover_after_90d'), lang)));
    if (r.n('cash_tied_up_minor') != null) {
      out.add(l.simCash(_money(r.n('cash_tied_up_minor'), lang, r.currency)));
    }
  }
  return out;
}

String? simWarning(
  AppLocalizations l,
  Map<String, Object?> w,
  String lang, {
  String currency = 'NPR',
}) => switch (w['code']) {
  'below_min_margin' => l.simWBelowMinMargin(_num(w['min_margin_pct'], lang)),
  'earns_less_than_no_discount' => l.simWEarnsLess(
    _money((w['difference_minor'] as num?)?.abs(), lang, currency),
  ),
  'loses_money_per_unit' => l.simWLosesMoney(
    _money((w['per_unit_minor'] as num?)?.abs(), lang, currency),
  ),
  'stockout_likely' => l.simWStockoutLikely,
  'below_moq' => l.simWBelowMoq(_num(w['moq'], lang)),
  'may_sell_out_before_delivery' => l.simWMaySellOut,
  'slow_to_sell' => l.simWSlow(_num(w['leftover_90'], lang)),
  _ => null,
};

String? simAssumption(AppLocalizations l, Map<String, Object?> a, String lang) {
  final v =
      a['vars'] is Map<String, Object?>
          ? a['vars']! as Map<String, Object?>
          : const <String, Object?>{};
  return switch (a['code']) {
    'baseline_demand' => l.simABaseline(
      _num(v['per_day'], lang),
      _num(v['in_stock_days'], lang),
    ),
    'elasticity_history' => l.simAElasticityHistory(
      _num(v['discount_days'], lang),
      _num(v['avg_discount_pct'], lang),
    ),
    'elasticity_typical_range' => l.simAElasticityTypical,
    'stock_caps_sales' => l.simAStockCaps(_num(v['stock'], lang)),
    'stock_not_tracked' => l.simAStockNotTracked,
    'other_costs_per_unit_unchanged' => l.simAOtherCosts,
    'returns_like_recent_sales' => l.simAReturns,
    'no_seasonality' => l.simANoSeasonality,
    'variant_demand' => l.simAVariantDemand(
      _num(v['per_day'], lang),
      _num(v['sold_90d'], lang),
    ),
    'lead_time_measured' => l.simALeadMeasured(_num(v['days'], lang)),
    'lead_time_supplier_terms' => l.simALeadTerms(_num(v['days'], lang)),
    'lead_time_default' => l.simALeadDefault(_num(v['days'], lang)),
    'incoming_arrives_first' => l.simAIncoming(_num(v['incoming'], lang)),
    'poisson_demand' => l.simAPoisson,
    'unit_cost_landed' => l.simAUnitLanded,
    'unit_cost_purchase_price' => l.simAUnitPurchase,
    _ => null,
  };
}

String? simNotIncluded(AppLocalizations l, SimulationRun r) {
  final items =
      [
        for (final c
            in (r.outputs?['not_included'] as List<Object?>?) ?? const [])
          switch (c) {
            'contribution_cost_not_set' => l.simNIProfitCost,
            'unit_cost' => l.simNIUnitCost,
            'contribution' => l.simNIProfit,
            _ => null,
          },
      ].whereType<String>().toList();
  return items.isEmpty ? null : l.simNotIncluded(items.join(', '));
}
