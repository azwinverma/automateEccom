import 'dart:convert';

import 'package:commerce_os_seller/features/fulfillment/presentation/cod_screen.dart';
import 'package:commerce_os_seller/features/orders/presentation/order_screen.dart';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import '../helpers/fake_adapter.dart';
import '../helpers/test_app.dart';
import 'orders_test.dart' show order;

Map<String, Object?> _money(int m) => {'amount_minor': m, 'currency': 'NPR'};

Map<String, Object?> _body(RequestOptions o) =>
    (o.data is String ? jsonDecode(o.data as String) : o.data)
        as Map<String, Object?>;

const _rates = {
  'weight_grams': 500,
  'cod_amount_minor': 260000,
  'options': [
    {
      'courier_account_id': 'ca1',
      'provider': 'sandbox_courier',
      'display_name': 'Sandbox courier',
      'is_default': true,
      'service_code': 'standard',
      'price': {'amount_minor': 17500, 'currency': 'NPR'},
      'eta_days_min': 3,
      'eta_days_max': 5,
      'cod_supported': true,
      'manual': false,
      'recommended': true,
    },
    {
      'courier_account_id': 'ca2',
      'provider': 'manual',
      'display_name': 'Own rider',
      'is_default': false,
      'service_code': null,
      'price': null,
      'eta_days_min': null,
      'eta_days_max': null,
      'cod_supported': true,
      'manual': true,
      'recommended': false,
    },
  ],
  'unavailable': <Object?>[],
  'recommendation': {
    'courier_account_id': 'ca1',
    'service_code': 'standard',
    'reason': 'default_courier',
    'method': 'rules',
  },
};

Map<String, Object?> shipment({
  String status = 'delivery_failed',
  bool manual = false,
  List<String> actions = const ['reattempt', 'return_to_sender'],
  List<Map<String, Object?>> attempts = const [],
  List<Map<String, Object?>> events = const [],
}) => {
  'id': 's1',
  'order_id': 'o1',
  'order_number': 1001,
  'courier_name': manual ? 'Ram (rider)' : 'Sandbox courier',
  'manual': manual,
  'status': status,
  'tracking_number': 'SBX123456789',
  'cod_amount': _money(260000),
  'actions': actions,
  'attempts': attempts,
  'events': events,
};

/// The page list is the first Scrollable (text fields add their own).
Future<void> _scrollTo(WidgetTester tester, Finder f) async {
  await tester.scrollUntilVisible(
    f,
    150,
    scrollable: find.byType(Scrollable).first,
  );
  await tester.ensureVisible(f);
  await tester.pumpAndSettle();
}

const _timeline = {'items': <Object?>[]};

List<GoRoute> _routes() => [
  GoRoute(
    path: '/orders/:id',
    builder: (_, s) => OrderScreen(orderId: s.pathParameters['id']!),
  ),
  GoRoute(path: '/cod', builder: (_, __) => const CodScreen()),
];

void main() {
  testWidgets('no shipment: options with the recommendation preselected, '
      'booking sends one idempotency key', (tester) async {
    var shipments = <Object?>[];
    final adapter = FakeAdapter((o) {
      if (o.path == '/orders/o1') return FakeResponse(200, order());
      if (o.path == '/orders/o1/timeline') {
        return const FakeResponse(200, _timeline);
      }
      if (o.path == '/orders/o1/shipments' && o.method == 'GET') {
        return FakeResponse(200, {'items': shipments});
      }
      if (o.path == '/couriers/rates') return const FakeResponse(200, _rates);
      if (o.path == '/orders/o1/shipments' && o.method == 'POST') {
        final s = shipment(status: 'booked', actions: ['request_pickup']);
        shipments = [s];
        return FakeResponse(201, s);
      }
      return const FakeResponse(404);
    });
    await pumpRouted(
      tester,
      initialLocation: '/orders/o1',
      routes: _routes(),
      adapter: adapter,
    );

    await _scrollTo(tester, find.byKey(const Key('delivery-book')));
    expect(find.text('Recommended: your default courier'), findsOneWidget);
    expect(find.text('Recommended'), findsOneWidget);
    expect(find.textContaining('3–5 days'), findsOneWidget);
    expect(
      find.text('The courier collects Rs 2,600 at the door'),
      findsOneWidget,
    );
    final first = tester.widget<RadioListTile<String>>(
      find.byKey(const Key('courier-option-ca1:standard')),
    );
    expect(first.groupValue, 'ca1:standard', reason: 'recommended preselected');

    // Own rider asks for an optional tracking number.
    await tester.ensureVisible(find.byKey(const Key('courier-option-ca2:')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('courier-option-ca2:')));
    await tester.pumpAndSettle();
    await _scrollTo(tester, find.byKey(const Key('delivery-tracking')));
    expect(find.byKey(const Key('delivery-tracking')), findsOneWidget);
    await tester.ensureVisible(
      find.byKey(const Key('courier-option-ca1:standard')),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('courier-option-ca1:standard')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('delivery-tracking')), findsNothing);

    await tester.ensureVisible(find.byKey(const Key('delivery-book')));
    await tester.tap(find.byKey(const Key('delivery-book')));
    await tester.pumpAndSettle();
    final keys =
        adapter.log
            .where((r) => r.path == '/orders/o1/shipments')
            .map((r) => r.headers['Idempotency-Key'])
            .whereType<String>();
    expect(keys, hasLength(1), reason: 'one booking, one key');
    final sent = adapter.requests.firstWhere(
      (r) => r.path == '/orders/o1/shipments' && r.method == 'POST',
    );
    expect(_body(sent)['courier_account_id'], 'ca1');
    expect(_body(sent)['service_code'], 'standard');
    expect(find.text('Booked'), findsOneWidget);
    expect(
      find.byKey(const Key('shipment-action-request_pickup')),
      findsOneWidget,
    );
  });

  testWidgets('failed delivery shows the attempt, reply and reattempt action', (
    tester,
  ) async {
    final adapter = FakeAdapter((o) {
      if (o.path == '/orders/o1') {
        return FakeResponse(
          200,
          order(status: 'delivery_failed', allowed: const []),
        );
      }
      if (o.path == '/orders/o1/timeline') {
        return const FakeResponse(200, _timeline);
      }
      if (o.path == '/orders/o1/shipments') {
        return FakeResponse(200, {
          'items': [
            shipment(
              attempts: [
                {
                  'id': 'a1',
                  'attempt_no': 1,
                  'failure_reason': 'customer_unreachable',
                  'recovery_status': 'customer_replied',
                  'customer_reply': 'Tomorrow after 3pm',
                },
              ],
              events: [
                {
                  'id': 'e1',
                  'status': 'picked_up',
                  'applied': true,
                  'occurred_at': '2026-11-03T08:00:00Z',
                },
                {
                  'id': 'e2',
                  'status': 'in_transit',
                  'applied': false,
                  'occurred_at': '2026-11-03T07:00:00Z',
                },
                {
                  'id': 'e3',
                  'status': 'delivery_failed',
                  'failure_reason': 'customer_unreachable',
                  'applied': true,
                  'occurred_at': '2026-11-03T10:00:00Z',
                },
              ],
            ),
          ],
        });
      }
      if (o.path == '/shipments/s1/reattempt') {
        return FakeResponse(200, shipment(status: 'reattempt_requested'));
      }
      return const FakeResponse(404);
    });
    await pumpRouted(
      tester,
      initialLocation: '/orders/o1',
      routes: _routes(),
      adapter: adapter,
    );

    await _scrollTo(tester, find.byKey(const Key('shipment-action-reattempt')));
    expect(
      find.text("Attempt 1: Couldn't reach the customer's phone"),
      findsOneWidget,
    );
    expect(
      find.text('Customer replied: ask the courier to try again'),
      findsOneWidget,
    );
    expect(find.text('Customer replied: “Tomorrow after 3pm”'), findsOneWidget);
    expect(
      find.byKey(const Key('shipment-action-return_to_sender')),
      findsOneWidget,
    );
    expect(find.byKey(const Key('shipment-action-cancel')), findsNothing);

    await tester.tap(find.byKey(const Key('shipment-action-reattempt')));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const Key('reattempt-note')),
      'Call before 3pm',
    );
    await tester.tap(find.byKey(const Key('reattempt-send')));
    await tester.pumpAndSettle();
    final sent = adapter.requests.singleWhere(
      (r) => r.path == '/shipments/s1/reattempt',
    );
    expect(_body(sent)['note'], 'Call before 3pm');

    await _scrollTo(tester, find.byKey(const Key('shipment-event-e2')));
    expect(find.textContaining('Late update from the courier'), findsOneWidget);
  });

  testWidgets('own rider: a failed delivery needs a reason before saving', (
    tester,
  ) async {
    final adapter = FakeAdapter((o) {
      if (o.path == '/orders/o1') {
        return FakeResponse(200, order(status: 'shipped', allowed: const []));
      }
      if (o.path == '/orders/o1/timeline') {
        return const FakeResponse(200, _timeline);
      }
      if (o.path == '/orders/o1/shipments') {
        return FakeResponse(200, {
          'items': [
            shipment(
              status: 'picked_up',
              manual: true,
              actions: ['update_status', 'set_tracking'],
            ),
          ],
        });
      }
      if (o.path == '/shipments/s1/status') {
        return FakeResponse(200, shipment(status: 'delivery_failed'));
      }
      return const FakeResponse(404);
    });
    await pumpRouted(
      tester,
      initialLocation: '/orders/o1',
      routes: _routes(),
      adapter: adapter,
    );

    await _scrollTo(
      tester,
      find.byKey(const Key('shipment-action-update_status')),
    );
    expect(find.text('Ram (rider)'), findsOneWidget);
    await tester.tap(find.byKey(const Key('shipment-action-update_status')));
    await tester.pumpAndSettle();
    expect(
      find.byKey(const Key('manual-status-picked_up')),
      findsNothing,
      reason: 'current status not offered',
    );
    await tester.tap(find.byKey(const Key('manual-status-delivery_failed')));
    await tester.pumpAndSettle();
    final save = find.byKey(const Key('manual-status-save'));
    await tester.ensureVisible(save);
    expect(tester.widget<FilledButton>(save).onPressed, isNull);
    expect(find.byKey(const Key('manual-reason-required')), findsOneWidget);
    await tester.tap(find.byKey(const Key('manual-reason-customer_refused')));
    await tester.pumpAndSettle();
    await tester.ensureVisible(save);
    expect(tester.widget<FilledButton>(save).onPressed, isNotNull);
    await tester.tap(save);
    await tester.pumpAndSettle();
    final sent = adapter.requests.singleWhere(
      (r) => r.path == '/shipments/s1/status',
    );
    expect(_body(sent)['status'], 'delivery_failed');
    expect(_body(sent)['failure_reason'], 'customer_refused');
  });

  testWidgets('order without shipment access still renders', (tester) async {
    final adapter = FakeAdapter((o) {
      if (o.path == '/orders/o1') return FakeResponse(200, order());
      if (o.path == '/orders/o1/timeline') {
        return const FakeResponse(200, _timeline);
      }
      if (o.path == '/orders/o1/shipments') {
        return FakeResponse(403, errorBody('permission_denied'));
      }
      return const FakeResponse(404);
    });
    await pumpRouted(
      tester,
      initialLocation: '/orders/o1',
      routes: _routes(),
      adapter: adapter,
    );
    expect(find.byKey(const Key('delivery-section')), findsNothing);
    expect(find.text('To pack (COD)'), findsOneWidget);
  });

  testWidgets('COD screen: cash with couriers, statements, confirm', (
    tester,
  ) async {
    var status = 'reconciled';
    final adapter = FakeAdapter((o) {
      if (o.path == '/cod/overview') {
        return const FakeResponse(200, {
          'awaiting_by_age': {
            'd0_7': {'count': 2, 'amount_minor': 400000},
            'd8_14': {'count': 0, 'amount_minor': 0},
            'd15_plus': {'count': 1, 'amount_minor': 120000},
          },
          'settlements_needing_review': 1,
        });
      }
      if (o.path == '/cod/awaiting') {
        return FakeResponse(200, {
          'items': [
            {
              'shipment_id': 's9',
              'order_id': 'o9',
              'order_number': 1009,
              'courier_name': 'Sandbox courier',
              'cod_amount': _money(120000),
              'days_waiting': 18,
            },
          ],
        });
      }
      if (o.path == '/cod/settlements') {
        return FakeResponse(200, {
          'items': [
            {
              'id': 'st1',
              'reference': 'SBX-STMT-1',
              'courier_name': 'Sandbox courier',
              'status': status,
              'net_minor': 480000,
              'currency': 'NPR',
              'issue_count': 0,
            },
            {
              'id': 'st2',
              'reference': 'SBX-STMT-2',
              'courier_name': 'Sandbox courier',
              'status': 'needs_review',
              'net_minor': 50000,
              'currency': 'NPR',
              'issue_count': 2,
            },
          ],
        });
      }
      if (o.path == '/cod/settlements/st1/confirm') {
        status = 'confirmed';
        return const FakeResponse(200, {'id': 'st1'});
      }
      return const FakeResponse(404);
    });
    await pumpRouted(
      tester,
      initialLocation: '/cod',
      routes: _routes(),
      adapter: adapter,
    );

    expect(find.text('Rs 5,200'), findsOneWidget);
    expect(
      find.text('Cash from 3 delivered parcels not received yet'),
      findsOneWidget,
    );
    expect(find.text('Rs 1,200 waiting more than 2 weeks'), findsOneWidget);
    expect(find.text('Order #1009 · Sandbox courier'), findsOneWidget);
    expect(find.text('18 days waiting'), findsOneWidget);
    await _scrollTo(tester, find.byKey(const Key('cod-confirm-st1')));
    expect(
      find.text("2 lines don't match. Check them on the web."),
      findsOneWidget,
    );
    expect(find.byKey(const Key('cod-confirm-st2')), findsNothing);
    await tester.tap(find.byKey(const Key('cod-confirm-st1')));
    await tester.pumpAndSettle();
    expect(adapter.countPath('/cod/settlements/st1/confirm'), 1);
    expect(find.text('Received'), findsOneWidget);
  });

  testWidgets('Nepali COD screen fits at 360dp', (tester) async {
    final adapter = FakeAdapter((o) {
      if (o.path == '/cod/overview') {
        return const FakeResponse(200, {
          'awaiting_by_age': {
            'd0_7': {'count': 1, 'amount_minor': 245000},
          },
          'settlements_needing_review': 0,
        });
      }
      if (o.path == '/cod/awaiting' || o.path == '/cod/settlements') {
        return const FakeResponse(200, {'items': <Object?>[]});
      }
      return const FakeResponse(404);
    });
    await pumpRouted(
      tester,
      initialLocation: '/cod',
      routes: _routes(),
      adapter: adapter,
      locale: const Locale('ne'),
    );
    expect(find.text('कुरियरसँग'), findsOneWidget);
    expect(find.text('अहिलेसम्म कुरियर विवरण छैन।'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
