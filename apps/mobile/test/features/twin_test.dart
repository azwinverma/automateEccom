import 'package:commerce_os_seller/features/twin/data/twin_api.dart';
import 'package:commerce_os_seller/features/twin/presentation/simulations_screen.dart';
import 'package:commerce_os_seller/features/twin/presentation/store_glance.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import '../helpers/fake_adapter.dart';
import '../helpers/test_app.dart';

Map<String, Object?> _section(
  Map<String, Object?> state, {
  bool stale = false,
}) => {
  'state': state,
  'as_of': '2026-11-20T04:30:00Z',
  'stale': stale,
  'age_s': stale ? 9000 : 30,
};

Map<String, Object?> _summary({bool stale = false, String? currency}) => {
  if (currency != null) 'currency': currency,
  'sections': {
    'orders': _section({'open': 7, 'needs_review': 2}),
    'inventory': _section({
      'tracked_variants': 12,
      'out_of_stock': 1,
      'low_stock': 3,
    }, stale: stale),
    'cod': _section({'cash_with_courier_minor': 1250000}),
    'returns': _section({'open': 0}),
    'suppliers': _section({'awaiting_approval': 1, 'overdue': 0}),
    'exceptions': _section({'total': 4}),
  },
};

Map<String, Object?> _discount({String elasticity = 'history'}) => {
  'id': 'run1',
  'kind': 'discount',
  'status': 'completed',
  'inputs': {'product_id': 'p1', 'discount_pct': 20, 'days': 14},
  'confidence': elasticity == 'history' ? 'medium' : 'low',
  'created_at': '2026-11-20T04:30:00Z',
  'outputs': {
    'label': 'estimate',
    'title': 'Dhaka Kurta',
    'days': 14,
    'discount_pct': 20,
    'units': {'expected': 30.5, 'low': 22, 'high': 41, 'baseline': 14},
    'contribution_minor': {
      'with_discount': {'expected': 2500000, 'low': 1800000, 'high': 3300000},
      'without_discount': 2800000,
    },
    'difference_minor': -300000,
    'margin_pct': {'before': 51, 'after': 38.8},
    'stockout_probability': 0.62,
    'stock_days': 9.5,
    'warnings': [
      {'code': 'earns_less_than_no_discount', 'difference_minor': -300000},
      {'code': 'stockout_likely', 'probability': 0.62},
      {'code': 'something_new'},
    ],
    'not_included': <Object?>[],
  },
  'assumptions': [
    {
      'code': 'baseline_demand',
      'vars': {'per_day': 1, 'in_stock_days': 60},
    },
    if (elasticity == 'history')
      {
        'code': 'elasticity_history',
        'vars': {'discount_days': 10, 'avg_discount_pct': 20},
      }
    else
      {'code': 'elasticity_typical_range', 'vars': <String, Object?>{}},
    {'code': 'no_seasonality', 'vars': <String, Object?>{}},
  ],
};

Map<String, Object?> _purchase() => {
  'id': 'run2',
  'kind': 'purchase_quantity',
  'status': 'completed',
  'inputs': {'variant_id': 'v1', 'quantity': 20},
  'confidence': 'medium',
  'outputs': {
    'title': 'Clay Pot',
    'variant': 'Large',
    'quantity': 20,
    'lead_days': 12,
    'stockout_before_arrival_probability': 0.35,
    'cover_days_after_arrival': 40,
    'sell_out_within_60d_probability': 0.7,
    'leftover_after_90d': 0,
    'cash_tied_up_minor': 1600000,
    'warnings': [
      {'code': 'below_moq', 'moq': 30},
    ],
    'not_included': ['contribution'],
  },
  'assumptions': [
    {
      'code': 'lead_time_supplier_terms',
      'vars': {'days': 12},
    },
  ],
};

Future<void> _pump(
  WidgetTester tester,
  Widget child,
  FakeAdapter adapter,
) async {
  await pumpRouted(
    tester,
    initialLocation: '/',
    routes: [
      GoRoute(
        path: '/',
        builder: (_, __) => Scaffold(body: SingleChildScrollView(child: child)),
      ),
      GoRoute(
        path: '/what-if/:id',
        builder: (_, s) => SimulationDetailScreen(id: s.pathParameters['id']!),
      ),
      GoRoute(
        path: '/orders',
        builder: (_, __) => const Scaffold(body: Text('ORDERS PAGE')),
      ),
    ],
    adapter: adapter,
  );
  // Permissions resolve first, then the Twin request starts: let both land.
  for (var i = 0; i < 3; i++) {
    await tester.pump(const Duration(milliseconds: 50));
  }
  await tester.pumpAndSettle();
}

Future<void> _pumpBody(WidgetTester tester, Widget child) => pumpRouted(
  tester,
  height:
      2000, // the whole estimate on screen (lazy lists don't build off-screen rows)
  initialLocation: '/',
  routes: [GoRoute(path: '/', builder: (_, __) => Scaffold(body: child))],
  adapter: FakeAdapter((_) => const FakeResponse(404)),
);

/// Twin requests with a permission list (analytics.read by default).
FakeAdapter _twin(
  Object? Function() summary, {
  List<String> perms = const ['analytics.read'],
  int status = 200,
}) => FakeAdapter(
  (o) =>
      o.path == '/permissions/me'
          ? FakeResponse(200, {'role': 'owner', 'permissions': perms})
          : FakeResponse(status, summary()),
);

void main() {
  testWidgets('store at a glance: chips from the Twin, as-of, navigation', (
    tester,
  ) async {
    await _pump(tester, const StoreGlanceStrip(), _twin(_summary));
    expect(find.byKey(const Key('store-glance')), findsOneWidget);
    expect(find.text('7 open orders · 2 to review'), findsOneWidget);
    expect(find.text('1 out · 3 low stock'), findsOneWidget);
    expect(find.text('Rs\u00a012,500 with couriers'), findsOneWidget);
    expect(find.text('1 POs to approve'), findsOneWidget);
    expect(find.text('4 need attention'), findsOneWidget);
    expect(find.textContaining('returns open'), findsNothing); // zero: hidden
    expect(find.byKey(const Key('store-glance-as-of')), findsOneWidget);
    expect(find.byKey(const Key('store-glance-stale')), findsNothing);
    await tester.tap(find.byKey(const Key('glance-orders')));
    await tester.pumpAndSettle();
    expect(find.text('ORDERS PAGE'), findsOneWidget);
  });

  testWidgets('store at a glance flags stale sections', (tester) async {
    await _pump(
      tester,
      const StoreGlanceStrip(),
      _twin(() => _summary(stale: true)),
    );
    expect(find.byKey(const Key('store-glance-stale')), findsOneWidget);
    expect(find.text('Some numbers may be out of date'), findsOneWidget);
  });

  testWidgets('store at a glance hides on error', (tester) async {
    await _pump(
      tester,
      const StoreGlanceStrip(),
      _twin(() => errorBody('server_error'), status: 500),
    );
    expect(find.byKey(const Key('store-glance')), findsNothing);
  });

  testWidgets('no analytics.read: the strip is never requested', (
    tester,
  ) async {
    final adapter = _twin(_summary, perms: const ['orders.read']);
    await _pump(tester, const StoreGlanceStrip(), adapter);
    debugPrint('PATHS=${adapter.requests.map((r) => r.path).toList()}');
    expect(find.byKey(const Key('store-glance')), findsNothing);
    expect(adapter.countPath('/twin/summary'), 0);
  });

  testWidgets('store at a glance uses the shop currency', (tester) async {
    await _pump(
      tester,
      const StoreGlanceStrip(),
      _twin(() => _summary(currency: 'INR')),
    );
    expect(find.textContaining('INR'), findsOneWidget);
    expect(find.textContaining('Rs'), findsNothing);
  });

  testWidgets('discount estimate: ranges, trade-off, warnings, assumptions', (
    tester,
  ) async {
    await _pumpBody(
      tester,
      SimulationView(run: SimulationRun.fromJson(_discount())),
    );
    expect(find.text('20% off Dhaka Kurta for 14 days'), findsOneWidget);
    expect(find.text('Estimate'), findsOneWidget);
    expect(find.text('Medium confidence'), findsOneWidget);
    expect(
      find.text('Sells about 30.5 (22–41) vs 14 without the discount'),
      findsOneWidget,
    );
    expect(
      find.text('Profit Rs\u00a025,000 vs Rs\u00a028,000 without the discount'),
      findsOneWidget,
    );
    expect(find.text('Rs\u00a03,000 less profit'), findsOneWidget);
    expect(find.text('Margin 51% → 38.8%'), findsOneWidget);
    expect(find.text('62% chance of selling out'), findsOneWidget);
    expect(
      find.text('Earns Rs\u00a03,000 less than not discounting'),
      findsOneWidget,
    );
    expect(find.text('Likely to sell out during the discount'), findsOneWidget);
    expect(
      find.text(
        '• Customer response from your own 10 discount days (about 20% off)',
      ),
      findsOneWidget,
    );
    expect(find.text('Nothing changes until you act.'), findsOneWidget);
  });

  testWidgets('what-if money uses the response currency', (tester) async {
    await _pumpBody(
      tester,
      SimulationView(
        run: SimulationRun.fromJson({..._discount(), 'currency': 'INR'}),
      ),
    );
    expect(find.textContaining('INR'), findsWidgets);
    expect(find.textContaining('Rs'), findsNothing);
  });

  testWidgets('no discount history: low confidence and a typical range', (
    tester,
  ) async {
    await _pumpBody(
      tester,
      SimulationView(
        run: SimulationRun.fromJson(_discount(elasticity: 'typical')),
      ),
    );
    expect(find.text('Low confidence'), findsOneWidget);
    expect(find.textContaining('No discount history yet'), findsOneWidget);
  });

  testWidgets('purchase estimate and a failed run', (tester) async {
    await _pumpBody(
      tester,
      Column(
        children: [
          Expanded(
            child: SimulationView(run: SimulationRun.fromJson(_purchase())),
          ),
          Expanded(
            child: SimulationView(
              run: SimulationRun.fromJson({
                'id': 'run3',
                'kind': 'discount',
                'status': 'failed',
                'inputs': {'discount_pct': 10, 'days': 7},
                'error_code': 'simulation_not_enough_sales',
                'assumptions': <Object?>[],
              }),
            ),
          ),
        ],
      ),
    );
    expect(find.text('Order 20 × Clay Pot (Large)'), findsOneWidget);
    expect(
      find.text(
        '35% chance of running out before the delivery arrives (12 days)',
      ),
      findsOneWidget,
    );
    expect(find.text('Cash tied up: Rs\u00a016,000'), findsOneWidget);
    expect(
      find.text("Below the supplier's minimum order of 30"),
      findsOneWidget,
    );
    expect(find.text('Not included: profit'), findsOneWidget);
    expect(
      find.text("Couldn't estimate: not enough sales yet"),
      findsOneWidget,
    );
  });

  testWidgets('results list opens a detail', (tester) async {
    await _pump(
      tester,
      Consumer(
        builder:
            (context, ref, _) => Column(
              children: [
                for (final r
                    in ref.watch(simulationsProvider).valueOrNull ??
                        const <SimulationRun>[])
                  SimulationTile(run: r),
              ],
            ),
      ),
      FakeAdapter(
        (o) =>
            o.path == '/simulations'
                ? FakeResponse(200, {
                  'items': [_discount()],
                })
                : FakeResponse(200, _discount()),
      ),
    );
    expect(find.text('20% off Dhaka Kurta for 14 days'), findsOneWidget);
    await tester.tap(find.byKey(const Key('sim-run1')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('sim-detail')), findsOneWidget);
  });

  testWidgets('a 403 means the plan lacks simulations', (tester) async {
    late AsyncValue<List<SimulationRun>> seen;
    await _pump(
      tester,
      Consumer(
        builder: (context, ref, _) {
          seen = ref.watch(simulationsProvider);
          return const SizedBox.shrink();
        },
      ),
      FakeAdapter((_) => FakeResponse(403, errorBody('feature_not_in_plan'))),
    );
    expect(simulationsNotInPlan(seen), isTrue);
  });
}
