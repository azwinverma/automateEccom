import 'package:commerce_os_seller/features/intelligence/data/intelligence_api.dart';
import 'package:commerce_os_seller/features/intelligence/presentation/memory_screen.dart';
import 'package:commerce_os_seller/features/intelligence/presentation/product_brain_card.dart';
import 'package:commerce_os_seller/features/intelligence/presentation/profit_card.dart';
import 'package:commerce_os_seller/features/intelligence/presentation/recommendations_section.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import '../helpers/fake_adapter.dart';
import '../helpers/test_app.dart';

Map<String, Object?> _brain({bool full = true, String? currency}) => {
  'product_id': 'p1',
  if (currency != null) 'currency': currency,
  'units_7d': 6,
  'units_30d': 20,
  'units_90d': 20,
  'in_stock_days_90d': 52,
  'demand_per_day': full ? 1.4 : null,
  'available': full ? 5 : null,
  'cover_days': full ? 3.6 : null,
  'stockouts_90d': full ? 1 : 0,
  'margin_pct': full ? 60.0 : null,
  'contribution_per_unit_minor': full ? 85000 : null,
  'contribution_basis': full ? 'partial' : 'cost_not_set',
  'return_rate': full ? 0.25 : null,
  'top_reasons':
      full
          ? [
            {'reason': 'size_small', 'units': 5},
          ]
          : <Object?>[],
  'fit': full ? 'small' : null,
  'stock_risk': full ? 'high' : null,
  'completeness': full ? 1.0 : 0.2,
  'not_included': {
    'channel_conversion': 'needs_content_metrics',
    'content_performance': 'needs_content_metrics',
    'seasonality': 'needs_12_months',
    if (!full) 'margin': 'cost_not_set',
    if (!full) 'contribution': 'cost_not_set',
    if (!full) 'stock': 'stock_not_tracked',
  },
};

Map<String, Object?> _profit({String? currency}) => {
  'window_days': 30,
  if (currency != null) 'currency': currency,
  'shop': {
    'revenue_minor': 1040000,
    'contribution_minor': 362500,
    'margin_pct': 34.9,
    'complete': false,
    'components': [
      {'code': 'goods', 'amount_minor': 980000, 'status': 'included'},
      {
        'code': 'packaging',
        'amount_minor': null,
        'status': 'not_included',
        'reason': 'packaging_not_set',
      },
      {
        'code': 'ads',
        'amount_minor': null,
        'status': 'not_included',
        'reason': 'no_ad_account',
      },
    ],
  },
};

Map<String, Object?> _fact(
  String id,
  String type,
  Map<String, Object?> value,
) => {
  'id': id,
  'subject_type': type.startsWith('fit') ? 'product' : 'shop',
  'subject_id': 'x',
  'subject_label': type.startsWith('fit') ? 'Dhaka Kurta' : null,
  'fact_type': type,
  'value': value,
  'confidence': 0.75,
  'evidence': [
    {'metric': 'm', 'window_days': 90},
  ],
  'status': 'active',
  'source': 'derived',
  'confirmed': false,
  'version': 1,
};

Future<void> _pump(WidgetTester tester, Widget child, FakeAdapter adapter) =>
    pumpRouted(
      tester,
      initialLocation: '/',
      routes: [
        GoRoute(
          path: '/',
          builder:
              (_, __) => Scaffold(body: SingleChildScrollView(child: child)),
        ),
      ],
      adapter: adapter,
    );

FakeAdapter _forbidden() =>
    FakeAdapter((_) => FakeResponse(403, errorBody('feature_not_in_plan')));

void main() {
  testWidgets('product brain: numbers, risk chip, fit and plain-word gaps', (
    tester,
  ) async {
    await _pump(
      tester,
      ProductBrainView(brain: ProductBrain.fromJson(_brain())),
      FakeAdapter((_) => const FakeResponse(404)),
    );
    await tester.pumpAndSettle();
    expect(find.text('About 1.4 a day, from 52 days in stock'), findsOneWidget);
    expect(find.text('5 available · about 3.6 days left'), findsOneWidget);
    expect(find.byKey(const Key('pb-risk-high')), findsOneWidget);
    expect(find.text('Runs out soon'), findsOneWidget);
    expect(find.text("Margin 60.0% at today's price and cost"), findsNothing);
    expect(find.textContaining('Margin 60'), findsOneWidget);
    expect(find.textContaining('some costs not included'), findsOneWidget);
    // No currency from an older backend: falls back to NPR.
    expect(find.textContaining('Profit per unit: Rs\u00a0850'), findsOneWidget);
    expect(find.text('Returned: 25% of delivered'), findsOneWidget);
    expect(find.byKey(const Key('pb-fit')), findsOneWidget);
    // Two sections share one reason: the sentence appears once.
    expect(
      find.text('Channel and content results arrive with content tracking.'),
      findsOneWidget,
    );
    expect(find.textContaining('needs_'), findsNothing);
  });

  testWidgets('product brain: missing data is explained, never zero', (
    tester,
  ) async {
    await _pump(
      tester,
      ProductBrainView(brain: ProductBrain.fromJson(_brain(full: false))),
      FakeAdapter((_) => const FakeResponse(404)),
    );
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('pb-demand')), findsNothing);
    expect(find.byKey(const Key('pb-contribution')), findsNothing);
    expect(find.text('Add a cost to see margin and profit.'), findsOneWidget);
    expect(find.text("Stock isn't tracked for this product."), findsOneWidget);
    expect(find.textContaining('Margin'), findsNothing);
    expect(find.textContaining('Returned:'), findsNothing);
  });

  testWidgets('product brain card hides on 403', (tester) async {
    await _pump(tester, const ProductBrainCard(productId: 'p1'), _forbidden());
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('product-brain')), findsNothing);
  });

  testWidgets('profit card: contribution, margin and what is not included', (
    tester,
  ) async {
    await _pump(
      tester,
      const ProfitCard(),
      FakeAdapter(
        (o) =>
            o.path == '/intelligence/profit'
                ? FakeResponse(200, _profit(currency: 'NPR'))
                : const FakeResponse(404),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('profit-card')), findsOneWidget);
    expect(find.textContaining('Margin 34.9%'), findsOneWidget);
    expect(
      find.text('Profit before fixed costs Rs\u00a03,625'),
      findsOneWidget,
    );
    expect(find.textContaining('Sales Rs\u00a010,400'), findsOneWidget);
    expect(
      find.text('2 items not included: packaging, ad spend'),
      findsOneWidget,
    );
  });

  testWidgets('money uses the currency the API sends', (tester) async {
    await _pump(
      tester,
      Column(
        children: [
          ProfitView(summary: ProfitSummary.fromJson(_profit(currency: 'INR'))),
          ProductBrainView(
            brain: ProductBrain.fromJson(_brain(currency: 'INR')),
          ),
        ],
      ),
      FakeAdapter((_) => const FakeResponse(404)),
    );
    await tester.pumpAndSettle();
    expect(
      find.text('Profit before fixed costs INR\u00a03,625'),
      findsOneWidget,
    );
    expect(
      find.textContaining('Profit per unit: INR\u00a0850'),
      findsOneWidget,
    );
    expect(find.textContaining('Rs\u00a0'), findsNothing);
  });

  testWidgets('profit card hides on 403', (tester) async {
    await _pump(tester, const ProfitCard(), _forbidden());
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('profit-card')), findsNothing);
  });

  testWidgets('new suggestion types read as plain sentences; apply works', (
    tester,
  ) async {
    var open = <Map<String, Object?>>[
      {
        'id': 'r1',
        'type': 'return_prevention',
        'confidence': 0.6,
        'explanation': {
          'what': 'fit_note_size_small',
          'why': 'return_pattern',
          'vars': {
            'title': 'Dhaka Kurta',
            'returned': 6,
            'sold': 12,
            'rate_pct': 50,
            'baseline_pct': 13,
            'reason': 'size_small',
            'share_pct': 83,
          },
        },
        'estimated_impact': {'return_rate_now': 0.5},
        'action': {'type': 'confirm_fact'},
      },
      {
        'id': 'r2',
        'type': 'profit_loss',
        'confidence': 0.8,
        'explanation': {
          'what': 'review_price_or_cost',
          'why': 'losing_money',
          'vars': {'title': 'Shawl', 'units': 6, 'contribution': -12000},
        },
        'estimated_impact': <String, Object?>{},
        'action': {'type': 'none'},
      },
      {
        'id': 'r3',
        'type': 'profit_data',
        'confidence': 0.9,
        'explanation': {
          'what': 'add_cost',
          'why': 'cost_not_set',
          'vars': {'title': 'Topi', 'units': 3},
        },
        'estimated_impact': <String, Object?>{},
        'action': {'type': 'none'},
      },
      {
        'id': 'r4',
        'type': 'restock',
        'confidence': 0.7,
        'explanation': {
          'what': 'restock',
          'why': 'selling_low_stock',
          'vars': {
            'title': 'Kurta',
            'sold_30d': 6,
            'available': 1,
            'cover_days': 5.0,
            'contribution_30d': 510000,
          },
        },
        'estimated_impact': {
          'cover_days': 5.0,
          'contribution_30d_minor': 510000,
        },
        'action': {'type': 'none'},
      },
    ];
    final adapter = FakeAdapter((o) {
      if (o.path == '/intelligence/recommendations') {
        return FakeResponse(200, {'items': open});
      }
      if (o.path == '/intelligence/recommendations/r1/accept') {
        open = open.where((r) => r['id'] != 'r1').toList();
        return const FakeResponse(200, {'id': 'r1', 'status': 'executed'});
      }
      return const FakeResponse(404);
    });
    await _pump(tester, const RecommendationsSection(), adapter);
    await tester.pumpAndSettle();
    expect(find.text('Tell customers Dhaka Kurta runs small'), findsOneWidget);
    expect(
      find.text(
        '6 of 12 returned (50%; shop average 13%) 83% of returns say: too small',
      ),
      findsOneWidget,
    );
    expect(find.text('Review the price or cost of Shawl'), findsOneWidget);
    expect(find.textContaining('Lost'), findsOneWidget);
    expect(find.text('Add a cost for Topi'), findsOneWidget);
    expect(find.textContaining('Worth about'), findsOneWidget);
    expect(find.byKey(const Key('rec-accept-r2')), findsNothing);
    await tester.tap(find.byKey(const Key('rec-accept-r1')));
    await tester.pumpAndSettle();
    expect(adapter.requests.any((r) => r.path.endsWith('/r1/accept')), isTrue);
    expect(find.byKey(const Key('rec-r1')), findsNothing);
  });

  testWidgets('memory: sentences per fact, confirm and reject with a reason', (
    tester,
  ) async {
    var facts = [
      _fact('f1', 'fit_runs_small', {'share': 0.83, 'returns': 5, 'sold': 12}),
      _fact('f2', 'repeat_cycle_days', {'days': 20, 'customers': 6}),
      _fact('f3', 'peak_order_hours', {
        'start_hour': 19,
        'end_hour': 22,
        'share': 0.4,
      }),
      _fact('f4', 'something_new', <String, Object?>{}),
    ];
    final adapter = FakeAdapter((o) {
      if (o.path == '/intelligence/memory/facts') {
        return FakeResponse(200, {'items': facts});
      }
      if (o.path == '/intelligence/memory/facts/f1/confirm') {
        facts = [
          {...facts.first, 'confirmed': true},
          ...facts.skip(1),
        ];
        return const FakeResponse(200, <String, Object?>{});
      }
      if (o.path == '/intelligence/memory/facts/f3/reject') {
        facts = facts.where((f) => f['id'] != 'f3').toList();
        return const FakeResponse(200, <String, Object?>{});
      }
      return const FakeResponse(404);
    });
    await pumpRouted(
      tester,
      initialLocation: '/',
      routes: [GoRoute(path: '/', builder: (_, __) => const MemoryScreen())],
      adapter: adapter,
    );
    await tester.pumpAndSettle();
    expect(
      find.text(
        'Dhaka Kurta runs small: 83% of returns say too small (5 returns, 12 sold)',
      ),
      findsOneWidget,
    );
    expect(
      find.text('Customers reorder about every 20 days (6 repeat customers)'),
      findsOneWidget,
    );
    expect(find.textContaining('between 19:00 and 22:00'), findsOneWidget);
    await tester.scrollUntilVisible(
      find.text('Something learned about your shop'),
      200,
    );
    expect(find.text('Something learned about your shop'), findsOneWidget);
    await tester.scrollUntilVisible(find.byKey(const Key('fact-f1')), -200);
    expect(find.textContaining('Confidence 75%'), findsWidgets);
    expect(find.textContaining('From the last 90 days'), findsWidgets);
    await tester.ensureVisible(find.byKey(const Key('fact-confirm-f1')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('fact-confirm-f1')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('fact-confirmed-f1')), findsOneWidget);
    expect(find.byKey(const Key('fact-confirm-f1')), findsNothing);
    await tester.ensureVisible(find.byKey(const Key('fact-reject-f3')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('fact-reject-f3')));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const Key('fact-reason')),
      'We close at 6pm',
    );
    await tester.pump();
    await tester.tap(find.byKey(const Key('fact-reject-confirm')));
    await tester.pumpAndSettle();
    final rej = adapter.requests.firstWhere(
      (r) => r.path.endsWith('/f3/reject'),
    );
    expect(rej.data, {'note': 'We close at 6pm'});
    expect(find.byKey(const Key('fact-f3')), findsNothing);
  });

  testWidgets('memory: empty state and manager-only error', (tester) async {
    await pumpRouted(
      tester,
      initialLocation: '/',
      routes: [GoRoute(path: '/', builder: (_, __) => const MemoryScreen())],
      adapter: FakeAdapter(
        (o) =>
            o.path == '/intelligence/memory/facts'
                ? const FakeResponse(200, {'items': <Object?>[]})
                : const FakeResponse(404),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('memory-empty')), findsOneWidget);
  });

  testWidgets('memory: staff without permission see why', (tester) async {
    final adapter = FakeAdapter((o) {
      if (o.path == '/intelligence/memory/facts') {
        return FakeResponse(200, {
          'items': [
            _fact('f2', 'repeat_cycle_days', {'days': 20, 'customers': 6}),
          ],
        });
      }
      return FakeResponse(403, errorBody('forbidden'));
    });
    await pumpRouted(
      tester,
      initialLocation: '/',
      routes: [GoRoute(path: '/', builder: (_, __) => const MemoryScreen())],
      adapter: adapter,
    );
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('fact-confirm-f2')));
    await tester.pumpAndSettle();
    expect(
      find.text('Only owners and managers can change these.'),
      findsOneWidget,
    );
  });
}
