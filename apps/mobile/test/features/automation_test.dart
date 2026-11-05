import 'package:commerce_os_seller/features/automation/data/automation_api.dart';
import 'package:commerce_os_seller/features/automation/presentation/approvals_screen.dart';
import 'package:commerce_os_seller/features/automation/presentation/control_center.dart';
import 'package:commerce_os_seller/features/automation/presentation/workflows_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import '../helpers/fake_adapter.dart';
import '../helpers/test_app.dart';

Map<String, Object?> controlCenter({
  String state = 'running',
  int? revenue = 520000,
  int approvals = 0,
  int exceptions = 0,
}) => {
  'period_days': 7,
  'mode': 'smart',
  'state': state,
  'currency': 'NPR',
  'metrics': {
    'orders': 12,
    'revenue_minor': revenue,
    'ai_messages': 40,
    'messages_sent': 55,
    'delivered': 9,
    'in_transit': 3,
    'returns': 1,
  },
  'automation': {
    'done_automatically': 30,
    'done_by_team': 10,
    'share_automatic': 0.75,
  },
  'needs_attention': {
    'approvals': approvals,
    'exceptions': exceptions,
    'urgent': 0,
  },
  'feed': [
    {
      'id': 'd1',
      'action': 'book_courier',
      'decision': 'AUTO_EXECUTE',
      'rule': 'smart_r1',
      'mode': 'smart',
      'created_at': '2026-11-05T08:00:00Z',
      'impact': {'amount_minor': 10000, 'currency': 'NPR'},
    },
  ],
};

Widget _cc(Map<String, Object?> j) => Scaffold(
  body: SingleChildScrollView(
    child: ControlCenterView(data: ControlCenter.fromJson(j)),
  ),
);

Map<String, Object?> _approval(String id) => {
  'id': id,
  'run_id': 'run1',
  'workflow_id': 'w1',
  'workflow_name': 'Book courier when packed',
  'step_id': 'book',
  'kind': 'action',
  'action': 'book_courier',
  'order_id': 'o1',
  'order_number': 1001,
  'decision': {
    'id': 'd9',
    'action': 'book_courier',
    'decision': 'REQUIRE_APPROVAL',
    'rule': 'assisted_mode',
    'mode': 'assisted',
    'created_at': '2026-11-05T08:00:00Z',
  },
};

Future<void> _pumpView(
  WidgetTester tester,
  Widget child, {
  Locale locale = const Locale('en'),
}) => pumpRouted(
  tester,
  initialLocation: '/',
  routes: [GoRoute(path: '/', builder: (_, __) => child)],
  adapter: FakeAdapter((_) => const FakeResponse(404)),
  locale: locale,
);

void main() {
  testWidgets('Control Center: headline per state, numbers, automation share', (
    tester,
  ) async {
    for (final (state, text) in [
      ('running', 'Your store is running.'),
      ('waiting', 'A few things are waiting for you.'),
      ('attention', 'Something needs you now.'),
    ]) {
      await _pumpView(
        tester,
        _cc(controlCenter(state: state, approvals: 2, exceptions: 1)),
      );
      await tester.pumpAndSettle();
      expect(find.text(text), findsOneWidget);
    }
    expect(find.textContaining('Smart mode'), findsOneWidget);
    expect(find.byKey(const Key('cc-revenue')), findsOneWidget);
    expect(find.textContaining('30 done automatically'), findsOneWidget);
    expect(find.textContaining('75%'), findsOneWidget);
    expect(find.text('3 things need you'), findsOneWidget);
  });

  testWidgets('Control Center hides revenue when the person can’t see money', (
    tester,
  ) async {
    await _pumpView(tester, _cc(controlCenter(revenue: null)));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('cc-revenue')), findsNothing);
    expect(find.byKey(const Key('cc-orders')), findsOneWidget);
    expect(find.text('Nothing needs you'), findsOneWidget);
  });

  testWidgets('Control Center renders in Nepali', (tester) async {
    await _pumpView(tester, _cc(controlCenter()), locale: const Locale('ne'));
    await tester.pumpAndSettle();
    expect(find.text('तपाईंको पसल चलिरहेको छ।'), findsOneWidget);
  });

  testWidgets('approve calls the endpoint and the item goes away', (
    tester,
  ) async {
    var pending = [_approval('s1')];
    final adapter = FakeAdapter((o) {
      if (o.path == '/automation/approvals') {
        return FakeResponse(200, {'items': pending});
      }
      if (o.path == '/automation/approvals/s1/approve') {
        pending = [];
        return const FakeResponse(200, {'id': 'run1', 'status': 'completed'});
      }
      return const FakeResponse(404);
    });
    await pumpRouted(
      tester,
      initialLocation: '/a',
      routes: [
        GoRoute(path: '/a', builder: (_, __) => const ApprovalsScreen()),
      ],
      adapter: adapter,
    );
    expect(find.text('Book a courier'), findsOneWidget);
    expect(find.text('Waiting: Your shop is in Assisted mode'), findsOneWidget);
    expect(find.text('Order #1001'), findsOneWidget);
    await tester.tap(find.byKey(const Key('approval-approve-s1')));
    await tester.pumpAndSettle();
    expect(adapter.countPath('/automation/approvals/s1/approve'), 1);
    expect(find.byKey(const Key('approval-s1')), findsNothing);
    expect(find.byKey(const Key('approvals-empty')), findsOneWidget);
  });

  testWidgets('a refused approval says only managers can approve', (
    tester,
  ) async {
    final adapter = FakeAdapter((o) {
      if (o.path == '/automation/approvals') {
        return FakeResponse(200, {
          'items': [_approval('s2')],
        });
      }
      if (o.path == '/automation/approvals/s2/reject') {
        return FakeResponse(403, errorBody('permission_denied'));
      }
      return const FakeResponse(404);
    });
    await pumpRouted(
      tester,
      initialLocation: '/a',
      routes: [
        GoRoute(path: '/a', builder: (_, __) => const ApprovalsScreen()),
      ],
      adapter: adapter,
    );
    await tester.tap(find.byKey(const Key('approval-reject-s2')));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const Key('approval-note')),
      'Call first',
    );
    await tester.tap(find.byKey(const Key('approval-reject-confirm')));
    await tester.pumpAndSettle();
    expect(find.text('Only managers can approve automation.'), findsOneWidget);
    expect(find.byKey(const Key('approval-s2')), findsOneWidget);
  });

  testWidgets('workflows list: status labels and on/off', (tester) async {
    final adapter = FakeAdapter((o) {
      if (o.path == '/automation/workflows') {
        return const FakeResponse(200, {
          'items': [
            {
              'id': 'w1',
              'name': 'Book courier',
              'status': 'active',
              'runs': {'completed': 4, 'failed': 1, 'waiting': 2},
            },
            {
              'id': 'w2',
              'name': 'Reviews',
              'status': 'draft',
              'runs': <String, Object?>{},
            },
            {
              'id': 'w3',
              'name': 'Pickups',
              'status': 'paused',
              'paused_reason': 'circuit_breaker:request_pickup',
              'runs': {'failed': 3},
            },
          ],
        });
      }
      if (o.path == '/automation/workflows/w2/status') {
        return FakeResponse(403, errorBody('permission_denied'));
      }
      return const FakeResponse(404);
    });
    await pumpRouted(
      tester,
      initialLocation: '/w',
      routes: [
        GoRoute(path: '/w', builder: (_, __) => const WorkflowsScreen()),
      ],
      adapter: adapter,
    );
    expect(find.text('On'), findsOneWidget);
    expect(find.text('Off'), findsOneWidget);
    expect(find.text('Paused after repeated failures'), findsOneWidget);
    expect(find.text('4 done · 2 in progress · 1 failed'), findsOneWidget);
    await tester.tap(find.byKey(const Key('workflow-toggle-w2')));
    await tester.pumpAndSettle();
    expect(
      find.text('Only managers can turn workflows on or off.'),
      findsOneWidget,
    );
  });
}
