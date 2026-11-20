import 'package:commerce_os_seller/features/intelligence/presentation/recommendations_section.dart';
import 'package:commerce_os_seller/features/procurement/data/procurement_api.dart';
import 'package:commerce_os_seller/features/procurement/presentation/po_detail_screen.dart';
import 'package:commerce_os_seller/features/procurement/presentation/po_list_screen.dart';
import 'package:commerce_os_seller/features/procurement/presentation/supplier_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import '../helpers/fake_adapter.dart';
import '../helpers/test_app.dart';

Map<String, Object?> _po({
  String status = 'pending_approval',
  String? reason = 'above_threshold',
  int remaining = 15,
  int received = 25,
  int defective = 2,
  bool belowMoq = true,
}) => {
  'id': 'po1',
  'number': 'PO-1001',
  'status': status,
  'source': 'recommendation',
  'supplier': {
    'id': 'sup1',
    'name': 'Bhaktapur Weavers',
    'phone': '9801111111',
  },
  'currency': 'NPR',
  'subtotal_minor': 4000000,
  'freight_minor': 200000,
  'duty_minor': 100000,
  'other_minor': 0,
  'total_minor': 4300000,
  'expected_at': null,
  'notes': null,
  'approval_reason': reason,
  'created_at': '2026-11-19T10:00:00Z',
  'lines': [
    {
      'id': 'ln1',
      'variant_id': 'v1',
      'title': 'Cotton Kurta',
      'variant': 'M',
      'sku': 'KURTA-M',
      'quantity': 40,
      'unit_cost_minor': 100000,
      'landed_unit_cost_minor': 107500,
      'received_quantity': received,
      'defective_quantity': defective,
      'remaining': remaining,
    },
  ],
  'receipts': [
    if (received > 0)
      {
        'lot_code': 'LOT-A',
        'received_at': '2026-11-18T10:00:00Z',
        'lines': [
          {'quantity': received - defective, 'defective_quantity': defective},
        ],
      },
  ],
  'warnings': [
    if (belowMoq) {'code': 'below_moq', 'variant_id': 'v1', 'moq': 50},
  ],
  'share_text':
      'Purchase order PO-1001\nTo: Bhaktapur Weavers\n- Cotton Kurta (M): 40',
};

Future<void> _pump(
  WidgetTester tester,
  Widget child,
  FakeAdapter adapter, {
  double height = 1600,
}) => pumpRouted(
  tester,
  height: height,
  initialLocation: '/',
  routes: [
    GoRoute(path: '/', builder: (_, __) => child),
    stubRoute('/purchase-orders/:id'),
    stubRoute('/suppliers/:id'),
    stubRoute('/purchase-orders'),
  ],
  adapter: adapter,
);

void main() {
  testWidgets('list: rows with status, total and filter by status', (
    tester,
  ) async {
    final adapter = FakeAdapter(
      (o) => FakeResponse(200, {
        'items': [_po()],
      }),
    );
    await _pump(tester, const PurchaseOrdersScreen(), adapter);
    expect(find.text('PO-1001 · Bhaktapur Weavers'), findsOneWidget);
    expect(find.text('Waiting for approval'), findsWidgets);
    expect(find.textContaining('Items: 1 · From a suggestion'), findsOneWidget);
    await tester.ensureVisible(find.byKey(const Key('po-filter-sent')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('po-filter-sent')));
    await tester.pumpAndSettle();
    expect(adapter.requests.last.queryParameters['status'], 'sent');
    await tester.tap(find.byKey(const Key('po-row-po1')));
    await tester.pumpAndSettle();
    expect(find.text('STUB /purchase-orders/po1'), findsOneWidget);
  });

  testWidgets('list: plan without procurement shows the upsell', (
    tester,
  ) async {
    await _pump(
      tester,
      const PurchaseOrdersScreen(),
      FakeAdapter((_) => FakeResponse(403, errorBody('feature_not_in_plan'))),
    );
    expect(find.text('Not in your current plan'), findsOneWidget);
  });

  testWidgets('detail: lines, landed cost, MOQ, lots and approval reason', (
    tester,
  ) async {
    await _pump(
      tester,
      const PurchaseOrderScreen(poId: 'po1'),
      FakeAdapter((_) => FakeResponse(200, _po())),
      height: 740,
    );
    expect(
      find.text('Waiting for approval: above your purchase limit'),
      findsOneWidget,
    );
    expect(find.text('Ordered 40 · Received 23 · Left 15'), findsOneWidget);
    expect(find.text('2 damaged on arrival'), findsOneWidget);
    expect(find.textContaining('Landed Rs'), findsOneWidget);
    expect(find.text("Below the supplier's minimum of 50"), findsOneWidget);
    await tester.scrollUntilVisible(
      find.byKey(const Key('po-approve')),
      200,
      scrollable: find.byType(Scrollable).first,
    );
    expect(find.textContaining('LOT-A: 23 good, 2 damaged'), findsOneWidget);
    expect(find.byKey(const Key('po-approve')), findsOneWidget);
    expect(find.byKey(const Key('po-receive')), findsNothing);
    expect(tester.takeException(), isNull); // fits at 360px
  });

  testWidgets('approve: staff are told only owners/managers can approve', (
    tester,
  ) async {
    final adapter = FakeAdapter((o) {
      if (o.method == 'POST') {
        return FakeResponse(403, errorBody('permission_denied'));
      }
      return FakeResponse(200, _po());
    });
    await _pump(tester, const PurchaseOrderScreen(poId: 'po1'), adapter);
    await tester.tap(find.byKey(const Key('po-approve')));
    await tester.pumpAndSettle();
    expect(
      find.text('Only owners and managers can approve purchase orders'),
      findsOneWidget,
    );
  });

  testWidgets('return for changes needs a reason', (tester) async {
    Object? sent;
    final adapter = FakeAdapter((o) {
      if (o.method == 'POST') {
        sent = o.data;
        return const FakeResponse(200, {});
      }
      return FakeResponse(200, _po());
    });
    await _pump(tester, const PurchaseOrderScreen(poId: 'po1'), adapter);
    await tester.tap(find.byKey(const Key('po-return')));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const Key('po-return-reason')),
      'Wait for Tihar prices',
    );
    await tester.pump();
    await tester.tap(find.byKey(const Key('po-return-confirm')));
    await tester.pumpAndSettle();
    expect(
      adapter.requests.lastWhere((r) => r.method == 'POST').path,
      '/procurement/purchase-orders/po1/reject',
    );
    expect((sent! as Map)['reason'], 'Wait for Tihar prices');
  });

  testWidgets('receive: empty, over-receipt error, then saved with one key', (
    tester,
  ) async {
    var posts = 0;
    final keys = <Object?>[];
    final adapter = FakeAdapter((o) {
      if (o.method == 'POST') {
        posts++;
        keys.add(o.headers['Idempotency-Key']);
        if (posts == 1) {
          return const FakeResponse(400, {
            'error': {
              'code': 'receipt_over_order',
              'message': 'More than was ordered',
              'details': {'po_line_id': 'ln1', 'remaining': 15},
              'request_id': 'r1',
            },
          });
        }
        return FakeResponse(201, _po(status: 'received', remaining: 0));
      }
      return FakeResponse(200, _po(status: 'sent', reason: null));
    });
    await _pump(tester, const PurchaseOrderScreen(poId: 'po1'), adapter);
    await tester.tap(find.byKey(const Key('po-receive')));
    await tester.pumpAndSettle();
    expect(find.text('15 left to arrive'), findsOneWidget);
    await tester.tap(find.byKey(const Key('receive-save')));
    await tester.pumpAndSettle();
    expect(find.text('Enter what arrived'), findsOneWidget);
    expect(posts, 0);
    await tester.enterText(find.byKey(const Key('receive-good-ln1')), '16');
    await tester.enterText(find.byKey(const Key('receive-lot')), 'LOT-B');
    await tester.tap(find.byKey(const Key('receive-save')));
    await tester.pumpAndSettle();
    expect(
      find.text('More than was ordered: 15 left on this item'),
      findsOneWidget,
    );
    await tester.enterText(find.byKey(const Key('receive-good-ln1')), '15');
    await tester.tap(find.byKey(const Key('receive-save')));
    await tester.pumpAndSettle();
    expect(posts, 2);
    expect(keys[0], isNotNull);
    expect(keys[0], keys[1]); // the retry replays the same receipt
    expect(find.byKey(const Key('receive-save')), findsNothing);
    final body =
        adapter.requests.lastWhere((r) => r.method == 'POST').data
            as Map<String, Object?>;
    expect(body['lot_code'], 'LOT-B');
    expect((body['lines']! as List).single, {
      'po_line_id': 'ln1',
      'quantity': 15,
      'defective_quantity': 0,
    });
  });

  testWidgets('approved order: mark sent and copy the order text', (
    tester,
  ) async {
    String? copied;
    tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(
      SystemChannels.platform,
      (call) async {
        if (call.method == 'Clipboard.setData') {
          copied = (call.arguments as Map)['text'] as String?;
        }
        return null;
      },
    );
    addTearDown(
      () => tester.binding.defaultBinaryMessenger.setMockMethodCallHandler(
        SystemChannels.platform,
        null,
      ),
    );
    await _pump(
      tester,
      const PurchaseOrderScreen(poId: 'po1'),
      FakeAdapter(
        (_) => FakeResponse(200, _po(status: 'approved', reason: null)),
      ),
    );
    expect(find.byKey(const Key('po-send')), findsOneWidget);
    expect(find.byKey(const Key('po-receive')), findsOneWidget);
    await tester.tap(find.byKey(const Key('po-copy')));
    await tester.pumpAndSettle();
    expect(
      find.text('Order copied: paste it into WhatsApp, Viber or email'),
      findsOneWidget,
    );
    expect(copied, startsWith('Purchase order PO-1001'));
  });

  testWidgets('supplier: performance card with what is not included', (
    tester,
  ) async {
    await _pump(
      tester,
      const SupplierScreen(supplierId: 'sup1'),
      FakeAdapter(
        (_) => const FakeResponse(200, {
          'id': 'sup1',
          'name': 'Good Fabrics',
          'phone': '9802222222',
          'payment_terms': '50% advance',
          'default_lead_time_days': 7,
          'performance': {
            'received_units': 50,
            'avg_landed_cost_minor': 95000,
            'defect_rate': 0.02,
            'sold_units': 20,
            'quality_return_rate': 0.0,
            'on_time_rate': 1.0,
            'lead_time_days_avg': 4,
            'contribution_per_unit_minor': null,
            'not_included': ['packaging', 'something_new'],
          },
        }),
      ),
    );
    expect(find.text('Payment terms: 50% advance'), findsOneWidget);
    expect(find.text('From 50 received and 20 sold'), findsOneWidget);
    expect(find.text('2%'), findsOneWidget);
    expect(find.text('4.0 days'), findsOneWidget);
    expect(find.text('Not enough sales yet'), findsOneWidget);
    expect(find.text('Not included: packaging'), findsOneWidget);
  });

  testWidgets('supplier without measurements says so', (tester) async {
    await _pump(
      tester,
      const SupplierScreen(supplierId: 'sup1'),
      FakeAdapter(
        (_) => const FakeResponse(200, {
          'id': 'sup1',
          'name': 'New Supplier',
          'performance': null,
        }),
      ),
    );
    expect(find.byKey(const Key('sup-perf-none')), findsOneWidget);
  });

  testWidgets(
    'suggestions: reorder and supplier switch copy; reorder opens POs',
    (tester) async {
      final adapter = FakeAdapter((o) {
        if (o.method == 'POST') return const FakeResponse(200, {});
        return const FakeResponse(200, {
          'items': [
            {
              'id': 'r1',
              'type': 'reorder',
              'confidence': 0.8,
              'explanation': {
                'what': 'reorder',
                'why': 'runs_out_before_delivery',
                'vars': {
                  'title': 'Cotton Kurta',
                  'variant': 'M',
                  'days_left': 4.5,
                  'per_day': 0.67,
                  'available': 3,
                  'incoming': 0,
                  'lead_days': 10,
                  'safety_days': 3,
                  'quantity': 50,
                  'supplier': 'Bhaktapur Weavers',
                  'moq': 50,
                },
              },
              'estimated_impact': <String, Object?>{},
              'action': {'type': 'create_po_draft'},
            },
            {
              'id': 'r2',
              'type': 'supplier_switch',
              'confidence': 0.8,
              'explanation': {
                'what': 'switch_supplier',
                'why': 'true_economics',
                'vars': {
                  'title': 'Cotton Kurta',
                  'variant': null,
                  'from': 'Cheap Fabrics',
                  'to': 'Good Fabrics',
                  'gain_per_unit': 12000,
                },
              },
              'estimated_impact': <String, Object?>{},
              'action': {'type': 'set_preferred_supplier'},
            },
          ],
        });
      });
      await pumpRouted(
        tester,
        initialLocation: '/',
        routes: [
          GoRoute(
            path: '/',
            builder:
                (_, __) => const Scaffold(
                  body: SingleChildScrollView(child: RecommendationsSection()),
                ),
          ),
          stubRoute('/purchase-orders'),
        ],
        adapter: adapter,
      );
      expect(
        find.text('Reorder Cotton Kurta (M) from Bhaktapur Weavers'),
        findsOneWidget,
      );
      expect(
        find.text(
          'Runs out in 4.5 days (0.67/day, 3 in stock, 0 on the way). Delivery '
          'takes 10 days. Order 50. Supplier minimum 50',
        ),
        findsOneWidget,
      );
      expect(find.text('Buy Cotton Kurta from Good Fabrics'), findsOneWidget);
      expect(
        find.textContaining('more per unit than Cheap Fabrics'),
        findsOneWidget,
      );
      expect(find.byKey(const Key('rec-accept-r2')), findsOneWidget);
      await tester.tap(find.byKey(const Key('rec-accept-r1')));
      await tester.pumpAndSettle();
      expect(
        find.text('Draft purchase order ready: submit it for approval'),
        findsOneWidget,
      );
      await tester.tap(find.byKey(const Key('rec-open-pos')));
      await tester.pumpAndSettle();
      expect(find.text('STUB /purchase-orders?status=draft'), findsOneWidget);
    },
  );

  testWidgets(
    'permissions: no approve → no Approve/Return; no write → no Receive',
    (tester) async {
      var perms = <String>['procurement.read', 'procurement.write'];
      var po = _po();
      final adapter = FakeAdapter((o) {
        if (o.path == '/permissions/me') {
          return FakeResponse(200, {'role': 'custom', 'permissions': perms});
        }
        return FakeResponse(200, po);
      });
      await _pump(tester, const PurchaseOrderScreen(poId: 'po1'), adapter);
      expect(adapter.countPath('/permissions/me'), 1);
      expect(find.byKey(const Key('po-approve')), findsNothing);
      expect(find.byKey(const Key('po-return')), findsNothing);
      expect(
        find.byKey(const Key('po-waiting')),
        findsOneWidget,
      ); // still says why it waits
      // Sent order, viewer can only read: no Receive, but the order text can still be copied.
      perms = ['procurement.read'];
      po = _po(status: 'sent', reason: null);
      await _pump(tester, const PurchaseOrderScreen(poId: 'po1'), adapter);
      expect(find.byKey(const Key('po-receive')), findsNothing);
      expect(find.byKey(const Key('po-copy')), findsOneWidget);
      // Writer on a sent order: Receive shows.
      perms = ['procurement.read', 'procurement.write'];
      await _pump(tester, const PurchaseOrderScreen(poId: 'po1'), adapter);
      expect(find.byKey(const Key('po-receive')), findsOneWidget);
    },
  );

  testWidgets(
    'permissions unknown → actions shown, server 403 is the fallback',
    (tester) async {
      final adapter = FakeAdapter((o) {
        if (o.path == '/permissions/me') {
          return FakeResponse(500, errorBody('server_error'));
        }
        return FakeResponse(200, _po());
      });
      await _pump(tester, const PurchaseOrderScreen(poId: 'po1'), adapter);
      expect(find.byKey(const Key('po-approve')), findsOneWidget);
    },
  );

  testWidgets('supplier money uses the response currency', (tester) async {
    await _pump(
      tester,
      const SupplierScreen(supplierId: 'sup1'),
      FakeAdapter(
        (_) => const FakeResponse(200, {
          'id': 'sup1',
          'name': 'Good Fabrics',
          'currency': 'INR',
          'performance': {
            'received_units': 50,
            'avg_landed_cost_minor': 95000,
            'sold_units': 20,
            'contribution_per_unit_minor': 40000,
            'not_included': <String>[],
          },
        }),
      ),
    );
    expect(find.textContaining('INR'), findsNWidgets(2));
    expect(find.textContaining('Rs'), findsNothing);
  });

  testWidgets('suggestion money uses the list currency (gain, order value)', (
    tester,
  ) async {
    final adapter = FakeAdapter(
      (_) => const FakeResponse(200, {
        'currency': 'INR',
        'items': [
          {
            'id': 'r1',
            'type': 'reorder',
            'confidence': 0.8,
            'explanation': {
              'what': 'reorder',
              'why': 'runs_out_before_delivery',
              'vars': {
                'title': 'Cotton Kurta',
                'days_left': 4,
                'per_day': 1,
                'available': 4,
                'incoming': 0,
                'lead_days': 7,
                'quantity': 20,
                'supplier': 'Bhaktapur Weavers',
              },
            },
            'estimated_impact': {'order_value_minor': 1800000},
            'action': {'type': 'create_po_draft'},
          },
          {
            'id': 'r2',
            'type': 'supplier_switch',
            'confidence': 0.6,
            'explanation': {
              'what': 'switch_supplier',
              'why': 'true_economics',
              'vars': {
                'title': 'Cotton Kurta',
                'from': 'Cheap Fabrics',
                'to': 'Good Fabrics',
                'gain_per_unit': 12000,
              },
            },
            'estimated_impact': <String, Object?>{},
            'action': {'type': 'set_preferred_supplier'},
          },
        ],
      }),
    );
    await _pump(
      tester,
      const Scaffold(
        body: SingleChildScrollView(child: RecommendationsSection()),
      ),
      adapter,
    );
    expect(find.textContaining('Order value INR'), findsOneWidget);
    expect(find.textContaining('Earns INR'), findsOneWidget);
    expect(find.textContaining('Rs'), findsNothing);
  });

  test('purchase order parses below-MOQ warnings and totals', () {
    final po = PurchaseOrder.fromJson(_po());
    expect(po.belowMoq, {'v1': 50});
    expect(po.extrasMinor, 300000);
    expect(po.receivable, isFalse);
    expect(po.receipts.single.good, 23);
  });
}
