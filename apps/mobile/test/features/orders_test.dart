import 'dart:convert';

import 'package:commerce_os_seller/features/orders/presentation/order_screen.dart';
import 'package:commerce_os_seller/features/orders/presentation/orders_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import '../helpers/fake_adapter.dart';
import '../helpers/test_app.dart';

Map<String, Object?> _money(int m) => {'amount_minor': m, 'currency': 'NPR'};

Map<String, Object?> order({
  String status = 'cod_pending',
  List<String> allowed = const ['ready_to_ship', 'cancelled'],
  String? review,
  int version = 3,
}) => {
  'id': 'o1',
  'number': 1001,
  'status': status,
  'source': 'chat',
  'currency': 'NPR',
  'customer': {
    'id': 'c1',
    'display_name': 'Bikash Rai',
    'phone': '+9779807654321',
  },
  'total': _money(260000),
  'payment_method': 'cod',
  'payment_status': 'cod_pending',
  'needs_review': review,
  'placed_at': '2026-11-03T08:00:00Z',
  'version': version,
  'allowed_transitions': allowed,
  'lines': [
    {
      'id': 'l1',
      'title': 'Dhaka Kurta',
      'variant_title': 'XL',
      'sku': 'DHK-XL',
      'unit_price': _money(245000),
      'quantity': 1,
      'cancelled_quantity': 0,
      'line_total': _money(245000),
      'matched': true,
    },
  ],
  'totals': {
    'subtotal': _money(245000),
    'discount': _money(0),
    'delivery_fee': _money(15000),
    'tax': _money(0),
    'total': _money(260000),
  },
  'shipping': {
    'recipient_name': 'Bikash Rai',
    'phone': '+9779807654321',
    'district': 'kaski',
    'district_name': 'Kaski',
    'municipality': 'Pokhara Metropolitan City',
    'ward': 6,
    'area': 'Lakeside',
    'landmark': 'Near Fewa lake',
  },
  'conversation_id': null,
};

const _timeline = {
  'items': [
    {
      'id': 'e1',
      'kind': 'created',
      'actor': {'type': 'ai', 'display': 'Sales Agent'},
      'automated': true,
      'data': <String, Object?>{},
      'at': '2026-11-03T08:00:00Z',
    },
  ],
};

List<GoRoute> _routes() => [
  GoRoute(path: '/orders', builder: (_, __) => const OrdersScreen()),
  GoRoute(
    path: '/orders/:id',
    builder: (_, s) => OrderScreen(orderId: s.pathParameters['id']!),
  ),
];

void main() {
  testWidgets('list filters by the seller job and opens the order', (
    tester,
  ) async {
    final adapter = FakeAdapter((o) {
      if (o.path == '/orders') {
        final review = o.queryParameters['needs_review'] == true;
        return FakeResponse(200, {
          'items': [order(review: review ? 'stock_short' : null)],
          'next_cursor': null,
        });
      }
      if (o.path == '/orders/o1') return FakeResponse(200, order());
      if (o.path == '/orders/o1/timeline') {
        return const FakeResponse(200, _timeline);
      }
      return const FakeResponse(404);
    });
    await pumpRouted(
      tester,
      initialLocation: '/orders',
      routes: _routes(),
      adapter: adapter,
    );

    final first = adapter.requests.firstWhere((r) => r.path == '/orders');
    expect(
      first.queryParameters['status'],
      'cod_pending,payment_pending,ready_to_ship',
    );
    expect(find.text('Order #1001 · Bikash Rai'), findsOneWidget);
    expect(find.text('Rs\u00a02,600'), findsOneWidget);

    await tester.tap(find.byKey(const Key('order-filter-needsReview')));
    await tester.pumpAndSettle();
    expect(adapter.requests.last.queryParameters['needs_review'], true);
    expect(find.text('Not enough stock for this order'), findsOneWidget);

    await tester.tap(find.byKey(const Key('order-o1')));
    await tester.pumpAndSettle();
    expect(
      find.text('Lakeside, Pokhara Metropolitan City-6, Kaski'),
      findsOneWidget,
    );
    await tester.scrollUntilVisible(find.textContaining('AI Sales Agent'), 200);
    expect(
      find.textContaining('AI Sales Agent'),
      findsOneWidget,
      reason: 'timeline actor',
    );
  });

  testWidgets('detail moves the order forward with the expected version', (
    tester,
  ) async {
    var current = order();
    final adapter = FakeAdapter((o) {
      if (o.path == '/orders/o1') return FakeResponse(200, current);
      if (o.path == '/orders/o1/timeline') {
        return const FakeResponse(200, _timeline);
      }
      if (o.path == '/orders/o1/transition') {
        final body = o.data is String ? jsonDecode(o.data as String) : o.data;
        expect((body as Map)['to'], 'ready_to_ship');
        expect(body['expected_version'], 3);
        current = order(
          status: 'ready_to_ship',
          allowed: ['shipped', 'cancelled'],
          version: 4,
        );
        return FakeResponse(200, current);
      }
      return const FakeResponse(404);
    });
    await pumpRouted(
      tester,
      initialLocation: '/orders/o1',
      routes: _routes(),
      adapter: adapter,
    );

    expect(find.text('To pack (COD)'), findsOneWidget);
    expect(
      find.byKey(const Key('order-action-cancelled')),
      findsNothing,
      reason: 'cancel is separate',
    );
    await tester.ensureVisible(
      find.byKey(const Key('order-action-ready_to_ship')),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('order-action-ready_to_ship')));
    await tester.pumpAndSettle();
    expect(find.text('Ready to ship'), findsOneWidget);
    expect(find.byKey(const Key('order-action-shipped')), findsOneWidget);
  });

  testWidgets('cancel needs a reason and shows a refusal inline', (
    tester,
  ) async {
    final adapter = FakeAdapter((o) {
      if (o.path == '/orders/o1') return FakeResponse(200, order());
      if (o.path == '/orders/o1/timeline') {
        return const FakeResponse(200, _timeline);
      }
      if (o.path == '/orders/o1/transition') {
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

    await tester.ensureVisible(find.byKey(const Key('order-cancel')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('order-cancel')));
    await tester.pumpAndSettle();
    final confirm = find.byKey(const Key('cancel-confirm'));
    expect(
      tester.widget<FilledButton>(confirm).onPressed,
      isNull,
      reason: 'reason required',
    );
    await tester.enterText(
      find.byKey(const Key('cancel-reason')),
      'customer changed mind',
    );
    await tester.pumpAndSettle();
    await tester.tap(confirm);
    await tester.pumpAndSettle();
    final sent =
        adapter.requests.where((r) => r.path == '/orders/o1/transition').single;
    final body =
        sent.data is String ? jsonDecode(sent.data as String) : sent.data;
    expect((body as Map)['to'], 'cancelled');
    expect(body['reason'], 'customer changed mind');
    expect(
      find.text('To pack (COD)'),
      findsOneWidget,
      reason: 'status unchanged after 403',
    );
  });

  testWidgets('Nepali order detail fits at 360dp', (tester) async {
    final adapter = FakeAdapter((o) {
      if (o.path == '/orders/o1') {
        return FakeResponse(200, order(review: 'payment_mismatch'));
      }
      if (o.path == '/orders/o1/timeline') {
        return const FakeResponse(200, _timeline);
      }
      return const FakeResponse(404);
    });
    await pumpRouted(
      tester,
      initialLocation: '/orders/o1',
      routes: _routes(),
      adapter: adapter,
      locale: const Locale('ne'),
    );
    expect(find.text('तिरेको रकम जम्मासँग मिलेन'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
