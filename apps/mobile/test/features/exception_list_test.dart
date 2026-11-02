import 'package:commerce_os_seller/features/home/presentation/widgets/exception_list.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../helpers/pump.dart';

void main() {
  testWidgets('empty state is honest and actionable', (tester) async {
    await pumpLocalized(tester, const ExceptionList(items: []));
    expect(find.text('Nothing needs you right now'), findsOneWidget);
    expect(find.textContaining('Payment mismatches'), findsOneWidget);
  });

  testWidgets('empty state in Nepali', (tester) async {
    await pumpLocalized(
      tester,
      const ExceptionList(items: []),
      locale: const Locale('ne'),
    );
    expect(find.text('अहिले तपाईंले हेर्नुपर्ने केही छैन'), findsOneWidget);
  });

  testWidgets('renders every type, urgent ones first, and reports taps',
      (tester) async {
    final now = DateTime(2026, 11, 2, 10);
    final items = [
      for (final (i, t) in ExceptionType.values.indexed)
        ExceptionItem(
          id: 'e$i',
          type: t,
          subject: 'Ref ${t.code}',
          occurredAt: now.subtract(Duration(minutes: i)),
        ),
    ];
    ExceptionItem? tapped;
    await pumpLocalized(
      tester,
      ExceptionList(items: items, onTap: (e) => tapped = e),
    );

    for (final label in [
      "Payment doesn't match",
      "AI wasn't sure",
      'Large refund to approve',
      'Delivery failed',
      'Channel disconnected',
      "Stock doesn't match",
      "Post didn't publish",
      'Which size or colour?',
      'Customer wants a person',
      'Service problem',
    ]) {
      expect(find.text(label), findsOneWidget, reason: label);
    }

    // Urgent (money/customer) items are above non-urgent ones.
    final urgentY = tester.getTopLeft(find.text('Customer wants a person')).dy;
    final normalY = tester.getTopLeft(find.text("AI wasn't sure")).dy;
    expect(urgentY, lessThan(normalY));

    await tester.tap(find.text('Delivery failed'));
    expect(tapped?.type, ExceptionType.courierFailed);
  });

  testWidgets('rows meet the 48dp minimum tap target', (tester) async {
    await pumpLocalized(
      tester,
      ExceptionList(
        items: [
          ExceptionItem(
            id: '1',
            type: ExceptionType.paymentMismatch,
            subject: 'Order #1042 · eSewa',
            occurredAt: DateTime(2026, 11, 2),
          ),
        ],
        onTap: (_) {},
      ),
    );
    expect(tester.getSize(find.byType(InkWell)).height,
        greaterThanOrEqualTo(48));
  });

  test('fromCode round-trips backend codes', () {
    for (final t in ExceptionType.values) {
      expect(ExceptionType.fromCode(t.code), t);
    }
    expect(ExceptionType.fromCode('nope'), isNull);
  });
}
