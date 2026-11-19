import 'package:commerce_os_seller/features/intelligence/data/intelligence_api.dart';
import 'package:commerce_os_seller/features/intelligence/presentation/autopilot_score_card.dart';
import 'package:commerce_os_seller/features/intelligence/presentation/cod_risk_card.dart';
import 'package:commerce_os_seller/features/intelligence/presentation/recommendations_section.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import '../helpers/fake_adapter.dart';
import '../helpers/test_app.dart';

Map<String, Object?> _score({double? overall}) => {
  'window_days': 30,
  'overall': overall,
  'hours_saved_estimate': 4.5,
  'capabilities': {
    'customer_replies': {
      'A': 40,
      'F': 2,
      'M': 8,
      'X': 3,
      'excluded': {'missing_entitlement': 3},
      'score': 0.8,
      'status': 'ok',
    },
    'refunds': {
      'A': 1,
      'F': 0,
      'M': 1,
      'X': 0,
      'excluded': <String, Object?>{},
      'score': null,
      'status': 'not_enough_activity',
    },
  },
};

Map<String, Object?> _rec(String id) => {
  'id': id,
  'type': 'automation_lever',
  'status': 'open',
  'confidence': 0.85,
  'explanation': {
    'what': 'lever.enable_r2',
    'why': 'manual_gap',
    'vars': {'manual': 12, 'eligible': 30, 'capability': 'shipment_creation'},
  },
  'estimated_impact': {'score_to': 0.72},
  'action': {'type': 'enable_r2'},
};

Map<String, Object?> _risk({String level = 'HIGHER'}) => {
  'order_id': 'o1',
  'level': level,
  'recommended_action': 'verify_phone',
  'factors': [
    {
      'code': 'delivery_history',
      'evidence': {'delivered': 0, 'failed': 2},
    },
    {
      'code': 'route_failures',
      'evidence': {'failed_rate': 0.31, 'district': 'Jhapa'},
    },
    {'code': 'some_future_factor', 'evidence': <String, Object?>{}},
  ],
  'overridden': false,
  'disputed': false,
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

FakeAdapter _none() => FakeAdapter((_) => const FakeResponse(404));

void main() {
  testWidgets('score: null overall says not enough activity, never 0%', (
    tester,
  ) async {
    await _pump(
      tester,
      AutopilotScoreView(score: AutopilotScore.fromJson(_score())),
      _none(),
    );
    await tester.pumpAndSettle();
    expect(find.text('Not enough activity yet'), findsOneWidget);
    expect(find.text('0%'), findsNothing);
    expect(find.textContaining('estimated'), findsOneWidget);
  });

  testWidgets('score: a thin capability shows "not enough activity"', (
    tester,
  ) async {
    await _pump(
      tester,
      AutopilotScoreView(score: AutopilotScore.fromJson(_score(overall: 0.8))),
      _none(),
    );
    await tester.pumpAndSettle();
    expect(find.text('80%'), findsWidgets);
    final refunds = find.byKey(const Key('aps-cap-refunds'));
    expect(
      find.descendant(of: refunds, matching: find.text('not enough activity')),
      findsOneWidget,
    );
    expect(find.textContaining('customer_replies'), findsNothing);
    expect(find.textContaining('missing_entitlement'), findsNothing);
  });

  testWidgets('score card hides on 403', (tester) async {
    await _pump(
      tester,
      const AutopilotScoreCard(),
      FakeAdapter((_) => FakeResponse(403, errorBody('feature_not_in_plan'))),
    );
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('aps-card')), findsNothing);
  });

  testWidgets('suggestion: plain words, apply calls accept', (tester) async {
    var open = [_rec('r1')];
    final adapter = FakeAdapter((o) {
      if (o.path == '/intelligence/recommendations') {
        return FakeResponse(200, {'items': open});
      }
      if (o.path == '/intelligence/recommendations/r1/accept') {
        open = [];
        return const FakeResponse(200, {'id': 'r1', 'status': 'executed'});
      }
      return const FakeResponse(404);
    });
    await _pump(tester, const RecommendationsSection(), adapter);
    await tester.pumpAndSettle();
    expect(find.textContaining('12 of 30'), findsOneWidget);
    expect(find.textContaining('High'), findsOneWidget);
    expect(find.textContaining('72%'), findsOneWidget);
    expect(find.textContaining('enable_r2'), findsNothing);
    await tester.tap(find.byKey(const Key('rec-accept-r1')));
    await tester.pumpAndSettle();
    expect(adapter.countPath('/intelligence/recommendations/r1/accept'), 1);
    expect(find.byKey(const Key('rec-r1')), findsNothing);
  });

  testWidgets('suggestion: dismiss sends the reason', (tester) async {
    Object? sent;
    final adapter = FakeAdapter((o) {
      if (o.path == '/intelligence/recommendations') {
        return FakeResponse(200, {
          'items': [_rec('r2')],
        });
      }
      if (o.path == '/intelligence/recommendations/r2/reject') {
        sent = o.data;
        return const FakeResponse(200, {'id': 'r2', 'status': 'rejected'});
      }
      return const FakeResponse(404);
    });
    await _pump(tester, const RecommendationsSection(), adapter);
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('rec-dismiss-r2')));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('rec-reason')), 'Not now');
    await tester.pump();
    await tester.tap(find.byKey(const Key('rec-dismiss-confirm')));
    await tester.pumpAndSettle();
    expect(adapter.countPath('/intelligence/recommendations/r2/reject'), 1);
    expect(sent, {'reason': 'Not now'});
  });

  testWidgets('suggestion: a 403 on apply says only managers can', (
    tester,
  ) async {
    final adapter = FakeAdapter((o) {
      if (o.path == '/intelligence/recommendations') {
        return FakeResponse(200, {
          'items': [_rec('r3')],
        });
      }
      if (o.path == '/intelligence/recommendations/r3/accept') {
        return FakeResponse(403, errorBody('permission_denied'));
      }
      return const FakeResponse(404);
    });
    await _pump(tester, const RecommendationsSection(), adapter);
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('rec-accept-r3')));
    await tester.pumpAndSettle();
    expect(find.text('Only managers can apply this'), findsOneWidget);
    expect(find.byKey(const Key('rec-r3')), findsOneWidget);
  });

  testWidgets('delivery risk: factors in plain words and the fairness line', (
    tester,
  ) async {
    await _pump(
      tester,
      const CodRiskCard(orderId: 'o1', paymentMethod: 'cod'),
      FakeAdapter(
        (o) =>
            o.path == '/intelligence/cod/assessments/o1'
                ? FakeResponse(200, _risk())
                : const FakeResponse(404),
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('Delivery risk'), findsOneWidget);
    expect(find.textContaining('Delivered 0, failed 2 before'), findsOneWidget);
    expect(find.textContaining('31%'), findsOneWidget);
    expect(find.textContaining('Jhapa'), findsOneWidget);
    expect(find.textContaining('some_future_factor'), findsNothing);
    expect(find.textContaining('null'), findsNothing);
    expect(find.textContaining('• '), findsNWidgets(2));
    expect(find.textContaining('Never on name'), findsOneWidget);
  });

  testWidgets('delivery risk hides for prepaid orders and on 404', (
    tester,
  ) async {
    final adapter = FakeAdapter((_) => const FakeResponse(404));
    await _pump(
      tester,
      const CodRiskCard(orderId: 'o1', paymentMethod: 'cod'),
      adapter,
    );
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('cod-risk')), findsNothing);
    await _pump(
      tester,
      const CodRiskCard(orderId: 'o2', paymentMethod: 'prepaid'),
      adapter,
    );
    await tester.pumpAndSettle();
    expect(adapter.countPath('/intelligence/cod/assessments/o2'), 0);
  });

  testWidgets('delivery risk: override needs a reason before saving', (
    tester,
  ) async {
    Object? sent;
    final adapter = FakeAdapter((o) {
      if (o.path == '/intelligence/cod/assessments/o1') {
        return FakeResponse(200, _risk());
      }
      if (o.path == '/intelligence/cod/assessments/o1/override') {
        sent = o.data;
        return FakeResponse(200, {
          ..._risk(level: 'LOW'),
          'overridden': true,
          'override_reason': 'Regular buyer',
        });
      }
      return const FakeResponse(404);
    });
    await _pump(
      tester,
      const CodRiskCard(orderId: 'o1', paymentMethod: 'cod'),
      adapter,
    );
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('cod-risk-override')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('cod-risk-choose-LOW')));
    await tester.enterText(find.byKey(const Key('cod-risk-reason')), 'ok');
    await tester.pump();
    final save = find.byKey(const Key('cod-risk-save'));
    expect(tester.widget<FilledButton>(save).onPressed, isNull);
    await tester.enterText(
      find.byKey(const Key('cod-risk-reason')),
      'Regular buyer',
    );
    await tester.pump();
    expect(tester.widget<FilledButton>(save).onPressed, isNotNull);
    await tester.tap(save);
    await tester.pumpAndSettle();
    expect(sent, {'level': 'LOW', 'reason': 'Regular buyer'});
    expect(find.text('You changed this: Regular buyer'), findsOneWidget);
    expect(find.byKey(const Key('cod-risk-level-LOW')), findsOneWidget);
  });

  testWidgets('delivery risk renders in Nepali', (tester) async {
    await pumpRouted(
      tester,
      initialLocation: '/',
      routes: [
        GoRoute(
          path: '/',
          builder:
              (_, __) => Scaffold(
                body: SingleChildScrollView(
                  child: CodRiskView(risk: CodRisk.fromJson(_risk())),
                ),
              ),
        ),
      ],
      adapter: _none(),
      locale: const Locale('ne'),
    );
    await tester.pumpAndSettle();
    expect(find.text('Delivery risk'), findsNothing);
    expect(find.textContaining('HIGHER'), findsNothing);
  });
}
