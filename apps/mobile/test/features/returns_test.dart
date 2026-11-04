import 'dart:convert';

import 'package:commerce_os_seller/features/orders/presentation/order_screen.dart';
import 'package:commerce_os_seller/features/returns/presentation/return_detail_screen.dart';
import 'package:commerce_os_seller/features/returns/presentation/returns_list_screen.dart';
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

const _timeline = {'items': <Object?>[]};

const _returnable = {
  'order_id': 'o1',
  'order_status': 'delivered',
  'currency': 'NPR',
  'refundable_minor': 260000,
  'policy': {'allow_refund': true, 'allow_exchange': true},
  'lines': [
    {
      'order_line_id': 'l1',
      'title': 'Dhaka Kurta',
      'variant_title': 'XL',
      'returnable_quantity': 1,
      'unit_refund_minor': 245000,
      'final_sale': false,
      'exchange_options': [
        {'variant_id': 'vL', 'title': 'L', 'available': 2},
      ],
    },
  ],
};

Map<String, Object?> returnDetail({
  String status = 'requested',
  bool eligible = true,
  List<String> actions = const ['approve', 'reject', 'cancel'],
  List<Map<String, Object?>> checks = const [],
  List<Map<String, Object?>> signals = const [],
  List<Map<String, Object?>> refunds = const [],
}) => {
  'id': 'r1',
  'number': 'R-1001-1',
  'order_id': 'o1',
  'order_number': 1001,
  'customer_name': 'Bikash Rai',
  'status': status,
  'resolution': 'refund',
  'eligible': eligible,
  'signals': signals,
  'refund_due': _money(245000),
  'refundable_minor': 260000,
  'lines': [
    {
      'id': 'rl1',
      'title': 'Dhaka Kurta',
      'variant_title': 'XL',
      'quantity': 1,
      'unit_refund_minor': 245000,
      'reason': 'size_small',
      'condition': null,
    },
  ],
  'eligibility': {'checks': checks},
  'refunds': refunds,
  'pickup': null,
  'actions': actions,
};

/// The start-return sheet builds lazily: scroll its own list to [f].
Future<void> _sheetTo(WidgetTester tester, Finder f) async {
  await tester.scrollUntilVisible(
    f,
    120,
    scrollable:
        find
            .descendant(
              of: find.byKey(const Key('return-sheet')),
              matching: find.byType(Scrollable),
            )
            .first,
  );
  await tester.pumpAndSettle();
}

Future<void> _scrollTo(WidgetTester tester, Finder f) async {
  await tester.scrollUntilVisible(
    f,
    150,
    scrollable: find.byType(Scrollable).first,
  );
  await tester.ensureVisible(f);
  await tester.pumpAndSettle();
}

List<GoRoute> _routes() => [
  GoRoute(
    path: '/orders/:id',
    builder: (_, s) => OrderScreen(orderId: s.pathParameters['id']!),
  ),
  GoRoute(path: '/returns', builder: (_, __) => const ReturnsListScreen()),
  GoRoute(
    path: '/returns/:id',
    builder: (_, s) => ReturnDetailScreen(returnId: s.pathParameters['id']!),
  ),
];

void main() {
  testWidgets('start a return: checks the policy, sends the right body and '
      'reuses its key on retry', (tester) async {
    var creates = 0;
    final adapter = FakeAdapter((o) {
      if (o.path == '/orders/o1') {
        return FakeResponse(200, order(status: 'delivered', allowed: []));
      }
      if (o.path == '/orders/o1/timeline') {
        return const FakeResponse(200, _timeline);
      }
      if (o.path == '/orders/o1/shipments') {
        return const FakeResponse(200, {'items': <Object?>[]});
      }
      if (o.path == '/orders/o1/returns' && o.method == 'GET') {
        return const FakeResponse(200, {'items': <Object?>[]});
      }
      if (o.path == '/orders/o1/returnable') {
        return const FakeResponse(200, _returnable);
      }
      if (o.path == '/orders/o1/returns/check') {
        return const FakeResponse(200, {
          'eligible': false,
          'can_request': true,
          'checks': [
            {
              'code': 'within_window',
              'ok': false,
              'soft': true,
              'window_days': 7,
            },
            {'code': 'quantity_available', 'ok': true, 'soft': false},
          ],
        });
      }
      if (o.path == '/orders/o1/returns' && o.method == 'POST') {
        creates += 1;
        if (creates == 1) {
          return FakeResponse(409, errorBody('version_conflict'));
        }
        return FakeResponse(201, returnDetail());
      }
      return const FakeResponse(404);
    });
    await pumpRouted(
      tester,
      initialLocation: '/orders/o1',
      routes: _routes(),
      adapter: adapter,
    );

    await _scrollTo(tester, find.byKey(const Key('return-start')));
    await tester.tap(find.byKey(const Key('return-start')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('return-sheet')), findsOneWidget);
    // Nothing picked yet: can't check.
    final check = tester.widget<FilledButton>(
      find.byKey(const Key('return-check')),
    );
    expect(check.onPressed, isNull);

    await tester.tap(find.byKey(const Key('return-pick-l1')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('return-resolution-exchange')));
    await tester.pumpAndSettle();
    await _sheetTo(
      tester,
      find.byKey(const Key('return-reason-l1-size_small')),
    );
    await tester.tap(find.byKey(const Key('return-reason-l1-size_small')));
    await tester.pumpAndSettle();
    expect(find.text('Pick what to exchange each item for'), findsOneWidget);
    await _sheetTo(tester, find.byKey(const Key('return-exchange-vL')));
    await tester.tap(find.byKey(const Key('return-exchange-vL')));
    await tester.pumpAndSettle();

    await _sheetTo(tester, find.byKey(const Key('return-check')));
    await tester.tap(find.byKey(const Key('return-check')));
    await tester.pumpAndSettle();
    expect(find.text('• Outside the 7-day return window'), findsOneWidget);
    expect(
      find.textContaining('approving will need a reason'),
      findsOneWidget,
      reason: 'soft check: a warning, not a block',
    );

    await _sheetTo(tester, find.byKey(const Key('return-submit')));
    await tester.tap(find.byKey(const Key('return-submit')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('return-sheet')), findsOneWidget);
    await _sheetTo(tester, find.byKey(const Key('return-submit')));
    await tester.tap(find.byKey(const Key('return-submit')));
    await tester.pumpAndSettle();

    final posts = adapter.requests.where(
      (r) => r.path == '/orders/o1/returns' && r.method == 'POST',
    );
    expect(posts, hasLength(2));
    final keys =
        adapter.log
            .where((r) => r.path == '/orders/o1/returns')
            .map((r) => r.headers['Idempotency-Key'])
            .whereType<String>()
            .toSet();
    expect(keys, hasLength(1), reason: 'a retry replays the same return');
    expect(_body(posts.last), {
      'resolution': 'exchange',
      'lines': [
        {
          'order_line_id': 'l1',
          'quantity': 1,
          'reason': 'size_small',
          'exchange_variant_id': 'vL',
        },
      ],
    });
    expect(find.byKey(const Key('return-sheet')), findsNothing);
    expect(find.text('Return created'), findsOneWidget);
  });

  testWidgets('approving a return outside the policy needs a reason', (
    tester,
  ) async {
    var approved = false;
    final adapter = FakeAdapter((o) {
      if (o.path == '/returns/r1' && o.method == 'GET') {
        return FakeResponse(
          200,
          approved
              ? returnDetail(status: 'approved', actions: ['mark_received'])
              : returnDetail(
                eligible: false,
                checks: [
                  {'code': 'not_final_sale', 'ok': false, 'soft': true},
                ],
                signals: [
                  {'code': 'frequent_returns', 'count': 3, 'days': 90},
                ],
              ),
        );
      }
      if (o.path == '/returns/r1/approve') {
        approved = true;
        return FakeResponse(200, returnDetail(status: 'approved'));
      }
      return const FakeResponse(404);
    });
    await pumpRouted(
      tester,
      initialLocation: '/returns/r1',
      routes: _routes(),
      adapter: adapter,
    );

    expect(find.text('Final sale item'), findsOneWidget);
    expect(find.text('3 returns in the last 90 days'), findsOneWidget);
    await _scrollTo(tester, find.byKey(const Key('return-action-approve')));
    await tester.tap(find.byKey(const Key('return-action-approve')));
    await tester.pumpAndSettle();
    final save = find.byKey(const Key('return-reason-save'));
    expect(tester.widget<FilledButton>(save).onPressed, isNull);
    expect(find.text('A reason is needed'), findsOneWidget);
    await tester.enterText(
      find.byKey(const Key('return-override-reason')),
      'Loyal customer, stitching fault',
    );
    await tester.pumpAndSettle();
    await tester.tap(save);
    await tester.pumpAndSettle();
    final sent = adapter.requests.firstWhere(
      (r) => r.path == '/returns/r1/approve',
    );
    expect(_body(sent)['override_reason'], 'Loyal customer, stitching fault');
    expect(find.text('Approved'), findsOneWidget);
  });

  testWidgets('inspection: only resellable items can go back on sale; refund '
      'pending approval is explained', (tester) async {
    var inspected = false;
    final adapter = FakeAdapter((o) {
      if (o.path == '/returns/r1' && o.method == 'GET') {
        return FakeResponse(
          200,
          inspected
              ? returnDetail(
                status: 'inspected',
                actions: ['refund'],
                refunds: [
                  {
                    'id': 'f1',
                    'amount': _money(245000),
                    'method': 'esewa',
                    'status': 'pending_approval',
                  },
                ],
              )
              : returnDetail(status: 'received', actions: ['inspect']),
        );
      }
      if (o.path == '/returns/r1/inspect') {
        inspected = true;
        return const FakeResponse(200, {});
      }
      return const FakeResponse(404);
    });
    await pumpRouted(
      tester,
      initialLocation: '/returns/r1',
      routes: _routes(),
      adapter: adapter,
    );

    await _scrollTo(tester, find.byKey(const Key('return-action-inspect')));
    await tester.tap(find.byKey(const Key('return-action-inspect')));
    await tester.pumpAndSettle();
    expect(
      tester
          .widget<FilledButton>(find.byKey(const Key('inspect-save')))
          .onPressed,
      isNull,
      reason: 'every item needs a condition',
    );
    await tester.tap(find.byKey(const Key('inspect-rl1-damaged')));
    await tester.pumpAndSettle();
    expect(
      tester
          .widget<IconButton>(find.byKey(const Key('restock-plus-rl1')))
          .onPressed,
      isNull,
    );
    expect(
      find.text('Only items that can be sold again go back on sale'),
      findsOneWidget,
    );
    await tester.tap(find.byKey(const Key('inspect-rl1-resellable')));
    await tester.pumpAndSettle();
    expect(find.text('1'), findsWidgets);
    await tester.tap(find.byKey(const Key('restock-minus-rl1')));
    await tester.pumpAndSettle();
    expect(
      tester
          .widget<IconButton>(find.byKey(const Key('restock-plus-rl1')))
          .onPressed,
      isNotNull,
    );
    await tester.tap(find.byKey(const Key('inspect-rl1-damaged')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('inspect-save')));
    await tester.pumpAndSettle();
    final sent = adapter.requests.firstWhere(
      (r) => r.path == '/returns/r1/inspect',
    );
    expect(_body(sent), {
      'items': [
        {'line_id': 'rl1', 'condition': 'damaged', 'restock': 0},
      ],
    });
    await _scrollTo(tester, find.text("Waiting for a manager's approval"));
    expect(find.text("Waiting for a manager's approval"), findsOneWidget);
  });

  testWidgets('refund sheet: defaults to what is due, needs a method', (
    tester,
  ) async {
    final adapter = FakeAdapter((o) {
      if (o.path == '/returns/r1' && o.method == 'GET') {
        return FakeResponse(
          200,
          returnDetail(status: 'inspected', actions: ['refund']),
        );
      }
      if (o.path == '/orders/o1/refunds') {
        return const FakeResponse(201, {'id': 'f1'});
      }
      return const FakeResponse(404);
    });
    await pumpRouted(
      tester,
      initialLocation: '/returns/r1',
      routes: _routes(),
      adapter: adapter,
    );
    await _scrollTo(tester, find.byKey(const Key('return-action-refund')));
    await tester.tap(find.byKey(const Key('return-action-refund')));
    await tester.pumpAndSettle();
    expect(find.widgetWithText(TextField, '2450'), findsOneWidget);
    final send = find.byKey(const Key('refund-send'));
    expect(tester.widget<FilledButton>(send).onPressed, isNull);
    await tester.tap(find.byKey(const Key('refund-method-esewa')));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('refund-reference')), 'ES-99');
    await tester.pumpAndSettle();
    await tester.tap(send);
    await tester.pumpAndSettle();
    final sent = adapter.requests.firstWhere(
      (r) => r.path == '/orders/o1/refunds',
    );
    expect(_body(sent), {
      'amount_minor': 245000,
      'method': 'esewa',
      'return_id': 'r1',
      'reference': 'ES-99',
    });
    expect(
      adapter.log
          .firstWhere((r) => r.path == '/orders/o1/refunds')
          .headers['Idempotency-Key'],
      isNotNull,
    );
  });

  testWidgets('returns list: tabs with counts', (tester) async {
    final adapter = FakeAdapter((o) {
      if (o.path == '/returns') {
        final bucket = o.queryParameters['bucket'];
        return FakeResponse(200, {
          'items': bucket == 'to_decide' ? [returnDetail()] : <Object?>[],
          'next_cursor': null,
          'counts': {
            'to_decide': 1,
            'in_progress': 0,
            'to_refund': 2,
            'done': 0,
          },
        });
      }
      return const FakeResponse(404);
    });
    await pumpRouted(
      tester,
      initialLocation: '/returns',
      routes: _routes(),
      adapter: adapter,
    );
    expect(find.text('To decide (1)'), findsOneWidget);
    expect(find.text('To refund (2)'), findsOneWidget);
    expect(find.text('In progress'), findsOneWidget);
    expect(find.text('R-1001-1 · Order #1001'), findsOneWidget);
    expect(find.text('To decide'), findsOneWidget, reason: 'status chip');
    await tester.ensureVisible(find.byKey(const Key('returns-tab-done')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('returns-tab-done')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('returns-empty-done')), findsOneWidget);
  });

  testWidgets('Nepali return detail renders without raw codes', (tester) async {
    final adapter = FakeAdapter((o) {
      if (o.path == '/returns/r1') {
        return FakeResponse(
          200,
          returnDetail(
            checks: [
              {'code': 'evidence', 'ok': false, 'soft': true},
            ],
          ),
        );
      }
      return const FakeResponse(404);
    });
    await pumpRouted(
      tester,
      initialLocation: '/returns/r1',
      routes: _routes(),
      adapter: adapter,
      locale: const Locale('ne'),
    );
    expect(find.text('यो कारणका लागि फोटो चाहिन्छ'), findsOneWidget);
    expect(find.textContaining('size_small'), findsNothing);
    expect(find.textContaining('सानो भयो'), findsOneWidget);
  });
}
