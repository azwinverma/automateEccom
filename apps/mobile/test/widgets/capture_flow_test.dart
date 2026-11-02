import 'dart:typed_data';

import 'package:commerce_os_seller/features/studio/data/capture_controller.dart';
import 'package:commerce_os_seller/features/studio/data/photo_picker.dart';
import 'package:commerce_os_seller/features/studio/presentation/capture_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import '../helpers/fake_adapter.dart';
import '../helpers/test_app.dart';

class FakePicker implements PhotoPicker {
  @override
  Future<PickedPhoto?> camera() async => (path: '/cam/c.jpg', name: 'c.jpg', size: 2048);

  @override
  Future<List<PickedPhoto>> gallery({required int limit}) async => [
        (path: '/g/a.jpg', name: 'a.jpg', size: 1024),
        (path: '/g/b.png', name: 'b.png', size: 1024),
      ].take(limit).toList();

  @override
  Future<List<PickedPhoto>> recoverLost() async => const [];
}

class MemFiles implements CaptureFileStore {
  @override
  Future<String> persist(String sourcePath, String extension) async => sourcePath;
  @override
  Future<Uint8List> read(String path) async => Uint8List(1024);
  @override
  Future<void> delete(String path) async {}
}

void main() {
  late FakeAdapter adapter;
  var n = 0;

  setUp(() {
    n = 0;
    adapter = FakeAdapter((o) {
      if (o.path == '/media/uploads') {
        final id = 'a${++n}';
        return FakeResponse(201, {
          'asset_id': id,
          'upload': {
            'method': 'PUT',
            'url': 'http://test/_dev/objects/m/$id/original?exp=1&sig=x',
            'headers': {'Content-Type': (o.data as Map)['content_type']},
            'expires_at': '2099-01-01T00:00:00Z',
          },
        });
      }
      if (o.method == 'PUT') return const FakeResponse(200);
      if (o.path.endsWith('/complete')) return const FakeResponse(202, {'id': 'x', 'status': 'uploaded'});
      if (o.path == '/media/a1') {
        return const FakeResponse(200, {'id': 'a1', 'status': 'ready', 'quality_flags': ['too_dark']});
      }
      if (o.path == '/media/a2') {
        return const FakeResponse(200, {'id': 'a2', 'status': 'ready', 'quality_flags': <String>[]});
      }
      if (o.path == '/studio/jobs') {
        return const FakeResponse(202, {'id': 'j9', 'status': 'queued'});
      }
      return FakeResponse(404, errorBody('not_found'));
    });
  });

  Future<void> pump(WidgetTester tester, Locale locale) => pumpRouted(
        tester,
        initialLocation: '/studio/capture',
        adapter: adapter,
        locale: locale,
        overrides: [
          photoPickerProvider.overrideWithValue(FakePicker()),
          captureFileStoreProvider.overrideWithValue(MemFiles()),
        ],
        routes: [
          GoRoute(path: '/studio/capture', builder: (_, __) => const CaptureScreen()),
          stubRoute('/studio/jobs/:id'),
        ],
      );

  testWidgets('en: gallery → uploads → tips → draft job created', (tester) async {
    await pump(tester, const Locale('en'));
    expect(find.text('Add at least one photo to continue.'), findsOneWidget);

    await tester.tap(find.byKey(const Key('capture-gallery')));
    await tester.pumpAndSettle();

    expect(find.text('Ready'), findsNWidgets(2));
    expect(find.text('Photo looks dark. Try near a window.'), findsOneWidget);
    expect(find.text('2 of 6 photos'), findsOneWidget);

    // Signed PUT: exact headers, no Authorization / tenant headers.
    final put = adapter.log.firstWhere((r) => r.path.contains('/_dev/objects/'));
    expect(put.headers['Content-Type'] ?? put.headers['content-type'], 'image/jpeg');
    expect(put.headers.containsKey('Authorization'), isFalse);
    expect(put.headers.containsKey('X-Merchant-Id'), isFalse);

    await tester.tap(find.byKey(const Key('capture-submit')));
    await tester.pumpAndSettle();
    final job = adapter.log.singleWhere((r) => r.path == '/studio/jobs');
    expect(job.headers['Idempotency-Key'], isA<String>());
    final body = adapter.requests.singleWhere((r) => r.path == '/studio/jobs').data as Map;
    expect(body['asset_ids'], ['a1', 'a2']);
    expect(body['locale'], 'en');
    expect(find.text('STUB /studio/jobs/j9'), findsOneWidget);
  });

  testWidgets('ne: Nepali copy and tips render at 360dp', (tester) async {
    await pump(tester, const Locale('ne'));
    expect(find.text('फोटो खिच्नुहोस्'), findsOneWidget);
    await tester.tap(find.byKey(const Key('capture-camera')));
    await tester.pumpAndSettle();
    expect(find.text('तयार'), findsOneWidget);
    expect(find.text('फोटो अँध्यारो देखियो। झ्यालनजिक खिचेर हेर्नुहोस्।'), findsOneWidget);
    expect(find.text('६ मध्ये १ फोटो'), findsOneWidget);
  });
}
