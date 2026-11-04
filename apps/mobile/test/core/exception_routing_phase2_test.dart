import 'package:commerce_os_seller/core/l10n/gen/app_localizations_en.dart';
import 'package:commerce_os_seller/features/exceptions/data/exception_routing.dart';
import 'package:commerce_os_seller/features/exceptions/data/exceptions_api.dart';
import 'package:commerce_os_seller/features/exceptions/presentation/exception_mapping.dart';
import 'package:flutter_test/flutter_test.dart';

ApiException _e(
  String type,
  String action,
  String rtype,
  String id, [
  Map<String, Object?> d = const {},
]) => ApiException.fromJson({
  'id': '$type:$id',
  'type': type,
  'severity': 'high',
  'resource': {'type': rtype, 'id': id},
  'action': action,
  'details': d,
});

String? _route(ExceptionTarget t) => t is OpenRoute ? t.location : null;

void main() {
  test('Phase 2 exceptions open the chat or the order', () {
    expect(
      _route(
        resolveExceptionAction(
          _e('customer_escalation', 'reply', 'conversation', 'cv1'),
        ),
      ),
      '/inbox/cv1',
    );
    for (final (type, action) in [
      ('payment_mismatch', 'check_payment'),
      ('inventory_mismatch', 'fix_stock'),
      ('ambiguous_variant', 'review_order'),
    ]) {
      expect(
        _route(resolveExceptionAction(_e(type, action, 'order', 'o1'))),
        '/orders/o1',
      );
    }
    expect(
      resolveExceptionAction(
        _e('payment_mismatch', 'check_payment', 'product', 'p1'),
      ),
      isA<NoAction>(),
    );
  });

  test('labels and subjects for chats and orders', () {
    final l = AppLocalizationsEn();
    expect(exceptionActionLabel(l, 'reply'), 'Reply');
    expect(exceptionActionLabel(l, 'fix_stock'), 'Fix stock');
    final items = toExceptionItems(l, [
      _e('customer_escalation', 'reply', 'conversation', 'cv1', {
        'name': 'Bikash Rai',
      }),
      _e('payment_mismatch', 'check_payment', 'order', 'o1', {'number': 1004}),
    ]);
    expect(items.map((i) => i.subject), ['Bikash Rai', 'Order #1004']);
  });
}
