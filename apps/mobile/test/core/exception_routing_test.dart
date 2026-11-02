import 'package:commerce_os_seller/features/exceptions/data/exception_routing.dart';
import 'package:commerce_os_seller/features/exceptions/data/exceptions_api.dart';
import 'package:flutter_test/flutter_test.dart';

ApiException _e(String action, String type, String id, [Map<String, Object?> d = const {}]) =>
    ApiException.fromJson({
      'id': 'x:$id',
      'type': 'low_confidence_ai',
      'severity': 'normal',
      'resource': {'type': type, 'id': id},
      'action': action,
      'details': d,
    });

String? _route(ExceptionTarget t) => t is OpenRoute ? t.location : null;

void main() {
  test('every server action maps to a destination', () {
    expect(_route(resolveExceptionAction(_e('review_draft', 'studio_job', 'j1'))), '/studio/jobs/j1');
    expect(_route(resolveExceptionAction(_e('retry_draft', 'studio_job', 'j2'))), '/studio/jobs/j2');
    expect(_route(resolveExceptionAction(_e('retry_publish', 'product', 'p1'))), '/products/p1');
    expect(_route(resolveExceptionAction(_e('confirm_attributes', 'product', 'p2'))), '/products/p2');
    expect(_route(resolveExceptionAction(_e('review_post', 'content_post', 'c1'))), '/posts/c1');
    expect(_route(resolveExceptionAction(_e('reschedule', 'content_post', 'c2'))), '/posts/c2');
  });

  test('reconnect uses the connection id from the resource or details', () {
    final a = resolveExceptionAction(
      _e('reconnect', 'channel_connection', 'conn-1', {'provider': 'instagram'}),
    ) as ReconnectChannel;
    expect(a.connectionId, 'conn-1');
    expect(a.provider, 'instagram');

    final b = resolveExceptionAction(
      _e('reconnect', 'product', 'p1', {'connection_id': 'conn-2'}),
    ) as ReconnectChannel;
    expect(b.connectionId, 'conn-2');

    final c = resolveExceptionAction(_e('reconnect', 'content_post', 'c1')) as ReconnectChannel;
    expect(c.connectionId, isNull);
  });

  test('dismiss hides locally; unknown or mismatched actions do nothing', () {
    expect(resolveExceptionAction(_e('dismiss', 'media', 'm1')), isA<DismissLocally>());
    expect(resolveExceptionAction(_e('teleport', 'product', 'p1')), isA<NoAction>());
    expect(resolveExceptionAction(_e('review_draft', 'product', 'p1')), isA<NoAction>());
  });
}
