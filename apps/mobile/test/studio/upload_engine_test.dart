import 'dart:typed_data';

import 'package:commerce_os_seller/core/errors/api_error.dart';
import 'package:commerce_os_seller/features/studio/data/media_api.dart';
import 'package:commerce_os_seller/features/studio/data/media_models.dart';
import 'package:commerce_os_seller/features/studio/data/upload_engine.dart';
import 'package:flutter_test/flutter_test.dart';

const _net = ApiError(kind: ApiErrorKind.network, code: 'network_unreachable');

ApiError _http(String code, int status, [Map<String, Object?> d = const {}]) =>
    ApiError(kind: ApiErrorKind.http, code: code, statusCode: status, details: d);

/// Scriptable media backend. Each queue entry is consumed per call; when a
/// queue is empty the call succeeds.
class FakeMedia implements MediaGateway {
  final List<Object> createErrors = [];
  final List<Object> putErrors = [];
  final List<Object> completeErrors = [];
  final List<MediaAsset Function(String id)> polls = [];
  final List<String> calls = [];
  int _n = 0;
  DateTime? ticketExpiry;

  Object? _next(List<Object> q) => q.isEmpty ? null : q.removeAt(0);

  @override
  Future<UploadTicket> createUpload({
    required String fileName,
    required String contentType,
    required int sizeBytes,
  }) async {
    calls.add('create');
    final e = _next(createErrors);
    if (e != null) throw e;
    final id = 'asset-${++_n}';
    return UploadTicket(
      assetId: id,
      url: 'http://api/_dev/objects/$id',
      headers: {'Content-Type': contentType},
      expiresAt: ticketExpiry,
    );
  }

  @override
  Future<void> putBytes(
    UploadTicket ticket,
    Uint8List bytes, {
    void Function(int sent, int total)? onProgress,
  }) async {
    calls.add('put:${ticket.assetId}');
    final e = _next(putErrors);
    if (e != null) throw e;
    onProgress?.call(bytes.length ~/ 2, bytes.length);
    onProgress?.call(bytes.length, bytes.length);
  }

  @override
  Future<void> complete(String assetId) async {
    calls.add('complete:$assetId');
    final e = _next(completeErrors);
    if (e != null) throw e;
  }

  @override
  Future<MediaAsset> get(String assetId) async {
    calls.add('get:$assetId');
    if (polls.isEmpty) return MediaAsset(id: assetId, status: 'ready');
    return polls.removeAt(0)(assetId);
  }
}

UploadItem _item(String id, {int size = 1000}) => UploadItem(
      localId: id,
      filePath: '/tmp/$id.jpg',
      fileName: '$id.jpg',
      contentType: 'image/jpeg',
      sizeBytes: size,
    );

void main() {
  late FakeMedia media;
  late List<Duration> waits;
  late List<List<UploadItem>> snapshots;

  UploadEngine engine({int retries = 4}) => UploadEngine(
        api: media,
        readFile: (_) async => Uint8List(1000),
        onChanged: snapshots.add,
        delay: (d) async => waits.add(d),
        maxAutoRetries: retries,
        now: () => DateTime.utc(2026, 11, 2, 8),
      );

  setUp(() {
    media = FakeMedia();
    waits = [];
    snapshots = [];
  });

  test('success: create → put → complete → poll → ready with flags', () async {
    media.polls.addAll([
      (id) => MediaAsset(id: id, status: 'processing'),
      (id) => MediaAsset(id: id, status: 'ready', qualityFlags: const ['too_dark']),
    ]);
    final e = engine()..add([_item('p1')]);
    await e.idle();

    final item = e.items.single;
    expect(item.phase, UploadPhase.ready);
    expect(item.assetId, 'asset-1');
    expect(item.qualityFlags, ['too_dark']);
    expect(media.calls, [
      'create',
      'put:asset-1',
      'complete:asset-1',
      'get:asset-1',
      'get:asset-1',
    ]);
    // Progress was reported during the PUT.
    expect(
      snapshots.expand((s) => s).where((i) => i.phase == UploadPhase.uploading).map((i) => i.progress),
      contains(0.5),
    );
    // Poll backoff starts at 1s.
    expect(waits, [const Duration(seconds: 1)]);
  });

  test('network failure on PUT retries with backoff and reuses the slot', () async {
    media.putErrors.addAll([_net, _net]);
    final e = engine()..add([_item('p1')]);
    await e.idle();

    expect(e.items.single.phase, UploadPhase.ready);
    expect(media.calls.where((c) => c == 'create'), hasLength(1));
    expect(media.calls.where((c) => c.startsWith('put')), hasLength(3));
    expect(waits.take(2), [const Duration(seconds: 1), const Duration(seconds: 2)]);
  });

  test('pauses after exhausting retries, then resumes from the PUT', () async {
    media.putErrors.addAll([_net, _net, _net]);
    final e = engine(retries: 2)..add([_item('p1')]);
    await e.idle();

    final paused = e.items.single;
    expect(paused.phase, UploadPhase.waitingRetry);
    expect(paused.pausedFrom, UploadPhase.uploading);
    expect(paused.errorCode, 'network_unreachable');

    e.retry();
    await e.idle();
    expect(e.items.single.phase, UploadPhase.ready);
    // No second upload slot was created.
    expect(media.calls.where((c) => c == 'create'), hasLength(1));
  });

  test('rejected asset ends in rejected with reason', () async {
    media.polls.add(
      (id) => MediaAsset(id: id, status: 'rejected', rejectionReason: 'not_an_image'),
    );
    final e = engine()..add([_item('p1')]);
    await e.idle();
    expect(e.items.single.phase, UploadPhase.rejected);
    expect(e.items.single.rejectionReason, 'not_an_image');
  });

  test('409 upload_missing on complete re-PUTs the bytes', () async {
    media.completeErrors.add(_http('upload_missing', 409));
    final e = engine()..add([_item('p1')]);
    await e.idle();
    expect(e.items.single.phase, UploadPhase.ready);
    expect(media.calls, [
      'create',
      'put:asset-1',
      'complete:asset-1',
      'put:asset-1',
      'complete:asset-1',
      'get:asset-1',
    ]);
  });

  test('restored item with an expired URL starts a fresh upload slot', () async {
    final stale = _item('p1').copyWith(
      phase: UploadPhase.uploading,
      assetId: () => 'asset-old',
      ticket: () => UploadTicket(
        assetId: 'asset-old',
        url: 'http://api/_dev/objects/asset-old',
        headers: const {'Content-Type': 'image/jpeg'},
        expiresAt: DateTime.utc(2026, 11, 2, 7), // before "now"
      ),
    );
    final e = engine()..restore([stale]);
    await e.idle();
    expect(media.calls, isNot(contains('put:asset-old')));
    expect(media.calls.take(2), ['create', 'put:asset-1']);
    expect(e.items.single.phase, UploadPhase.ready);
  });

  test('clock skew: a just-issued ticket is used even if it looks expired',
      () async {
    media.ticketExpiry = DateTime.utc(2026, 11, 2, 7); // device clock ahead
    final e = engine()..add([_item('p1')]);
    await e.idle();
    expect(media.calls.where((c) => c == 'create'), hasLength(1));
    expect(e.items.single.phase, UploadPhase.ready);
  });

  test('server rejects the signature → bounded retries, then pause', () async {
    media.putErrors.addAll([
      for (var i = 0; i < 5; i++) _http('invalid_signature', 403),
    ]);
    final e = engine(retries: 2)..add([_item('p1')]);
    await e.idle();
    expect(e.items.single.phase, UploadPhase.waitingRetry);
    expect(media.calls.where((c) => c == 'create').length, lessThanOrEqualTo(3));
  });

  test('quota and size errors are not retried', () async {
    media.createErrors.add(
      _http('usage_limit_reached', 402, {'resource': 'storage_mb'}),
    );
    final e = engine()..add([_item('p1'), _item('big', size: 21 * 1024 * 1024)]);
    await e.idle();
    final byId = {for (final i in e.items) i.localId: i};
    expect(byId['p1']!.phase, UploadPhase.failed);
    expect(byId['p1']!.errorCode, 'usage_limit_reached');
    expect(byId['big']!.phase, UploadPhase.failed);
    expect(byId['big']!.errorCode, 'file_too_large');
    expect(waits, isEmpty);
    expect(media.calls, ['create']); // the 21 MB file never hit the API
  });

  test('state survives a restart: persisted mid-PUT resumes, not re-creates', () async {
    final e1 = engine()..add([_item('p1')]);
    await e1.idle();
    // Simulate the app dying right after create (phase=uploading persisted).
    final persisted = UploadItem.fromJson(
      snapshots
          .expand((s) => s)
          .firstWhere((i) => i.phase == UploadPhase.uploading)
          .toJson(),
    );
    expect(persisted.assetId, 'asset-1');
    expect(persisted.ticket?.url, 'http://api/_dev/objects/asset-1');

    media.calls.clear();
    final e2 = engine()..restore([persisted]);
    await e2.idle();
    expect(e2.items.single.phase, UploadPhase.ready);
    expect(media.calls.first, 'put:asset-1');
    expect(media.calls, isNot(contains('create')));
  });

  test('asset still pending_upload after restart → complete again', () async {
    media.polls.add((id) => MediaAsset(id: id, status: 'pending_upload'));
    final restored = _item('p1').copyWith(
      phase: UploadPhase.processing,
      assetId: () => 'asset-9',
    );
    final e = engine()..restore([restored]);
    await e.idle();
    expect(media.calls, ['get:asset-9', 'complete:asset-9', 'get:asset-9']);
    expect(e.items.single.phase, UploadPhase.ready);
  });

  test('several photos all reach ready', () async {
    final e = engine()..add([_item('a'), _item('b'), _item('c')]);
    await e.idle();
    expect(e.items.every((i) => i.phase == UploadPhase.ready), isTrue);
  });
}
