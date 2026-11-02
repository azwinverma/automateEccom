import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:cross_file/cross_file.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path_provider/path_provider.dart';
import 'package:uuid/uuid.dart';

import '../../../core/api/providers.dart';
import '../../../core/auth/session_controller.dart';
import '../../../core/storage/providers.dart';
import 'media_api.dart';
import 'upload_engine.dart';

/// Max photos per Studio job (backend MAX_IMAGES).
const maxCapturePhotos = 6;

/// Copies picked photos into app storage so they survive the OS clearing
/// picker temp files while the app is backgrounded or killed.
abstract interface class CaptureFileStore {
  Future<String> persist(String sourcePath, String extension);
  Future<Uint8List> read(String path);
  Future<void> delete(String path);
}

class AppDirCaptureFileStore implements CaptureFileStore {
  Future<Directory> _dir() async {
    final base = await getApplicationSupportDirectory();
    final d = Directory('${base.path}/capture');
    if (!d.existsSync()) await d.create(recursive: true);
    return d;
  }

  @override
  Future<String> persist(String sourcePath, String extension) async {
    final d = await _dir();
    final target = '${d.path}/${const Uuid().v4()}.$extension';
    await File(sourcePath).copy(target);
    return target;
  }

  @override
  Future<Uint8List> read(String path) => File(path).readAsBytes();

  @override
  Future<void> delete(String path) async {
    final f = File(path);
    if (f.existsSync()) await f.delete();
  }
}

/// Flutter web (local testing in Chrome): there is no app file system, so picked photos are kept in
/// memory for the session, keyed by their blob URL. A page reload drops unfinished uploads.
class MemoryCaptureFileStore implements CaptureFileStore {
  final _bytes = <String, Uint8List>{};

  @override
  Future<String> persist(String sourcePath, String extension) async {
    _bytes[sourcePath] = await XFile(sourcePath).readAsBytes();
    return sourcePath;
  }

  @override
  Future<Uint8List> read(String path) async =>
      _bytes[path] ?? (throw StateError('photo no longer available'));

  @override
  Future<void> delete(String path) async => _bytes.remove(path);
}

final captureFileStoreProvider = Provider<CaptureFileStore>(
  (ref) => kIsWeb ? MemoryCaptureFileStore() : AppDirCaptureFileStore(),
);

/// Content type from file extension; null if the API won't accept it.
String? contentTypeFor(String path) {
  final ext = path.split('.').last.toLowerCase();
  return switch (ext) {
    'jpg' || 'jpeg' => 'image/jpeg',
    'png' => 'image/png',
    'webp' => 'image/webp',
    'heic' => 'image/heic',
    'heif' => 'image/heif',
    _ => null,
  };
}

@immutable
class CaptureState {
  const CaptureState({this.items = const [], this.notes = ''});

  final List<UploadItem> items;
  final String notes;

  List<UploadItem> get ready =>
      items.where((i) => i.phase == UploadPhase.ready).toList(growable: false);

  bool get anyActive => items.any((i) => i.isActive);
  bool get anyPaused => items.any((i) => i.phase == UploadPhase.waitingRetry);
  int get remainingSlots => maxCapturePhotos - items.length;
}

/// Owns the current capture session. Kept alive app-wide so uploads continue
/// while the seller navigates; persisted to SharedPreferences so a killed app
/// resumes the same selection on next launch.
class CaptureController extends Notifier<CaptureState> {
  static String _key(String? merchant) => 'studio.capture.${merchant ?? '-'}';

  late UploadEngine _engine;
  String? _merchant;

  @override
  CaptureState build() {
    _merchant = ref.watch(activeMerchantIdProvider);
    final store = ref.watch(captureFileStoreProvider);
    _engine = UploadEngine(
      api: ref.watch(mediaApiProvider),
      readFile: store.read,
      onChanged: _onEngineChanged,
    );
    ref.onDispose(_engine.dispose);

    // Back online → resume anything paused for the network.
    ref.listen(connectivityProvider, (prev, next) {
      final was = prev?.valueOrNull ?? true;
      if (next.valueOrNull == true && !was) _engine.retry();
    });

    final restored = _load();
    if (restored.items.isNotEmpty) {
      Future.microtask(() => _engine.restore(restored.items));
    }
    return restored;
  }

  CaptureState _load() {
    final raw = ref.read(sharedPreferencesProvider).getString(_key(_merchant));
    if (raw == null) return const CaptureState();
    try {
      final j = jsonDecode(raw) as Map<String, Object?>;
      return CaptureState(
        notes: (j['notes'] as String?) ?? '',
        items:
            ((j['items'] as List<Object?>?) ?? const [])
                .whereType<Map<String, Object?>>()
                .map(UploadItem.fromJson)
                .toList(),
      );
    } on Object {
      return const CaptureState();
    }
  }

  void _persist() {
    final prefs = ref.read(sharedPreferencesProvider);
    if (state.items.isEmpty && state.notes.isEmpty) {
      unawaited(prefs.remove(_key(_merchant)));
      return;
    }
    unawaited(
      prefs.setString(
        _key(_merchant),
        jsonEncode({
          'notes': state.notes,
          'items': [for (final i in state.items) i.toJson()],
        }),
      ),
    );
  }

  void _onEngineChanged(List<UploadItem> items) {
    state = CaptureState(items: items, notes: state.notes);
    _persist();
  }

  /// Adds picked files (paths from image_picker). Returns how many were
  /// skipped because the 6-photo limit was reached.
  Future<int> addFiles(
    List<({String path, String name, int size})> files,
  ) async {
    final store = ref.read(captureFileStoreProvider);
    final room = state.remainingSlots;
    final accepted = files.take(room < 0 ? 0 : room).toList();
    final items = <UploadItem>[];
    for (final f in accepted) {
      final type = contentTypeFor(f.name) ?? contentTypeFor(f.path);
      final ext = f.path.split('.').last.toLowerCase();
      final stored = await store.persist(f.path, ext);
      items.add(
        UploadItem(
          localId: const Uuid().v4(),
          filePath: stored,
          fileName: f.name,
          contentType: type ?? 'application/octet-stream',
          sizeBytes: f.size,
          phase: type == null ? UploadPhase.failed : UploadPhase.queued,
          errorCode: type == null ? 'unsupported_media_type' : null,
        ),
      );
    }
    _engine.add(items);
    return files.length - accepted.length;
  }

  void retry([String? localId]) => _engine.retry(localId);

  Future<void> remove(String localId) async {
    final item = state.items.where((i) => i.localId == localId).firstOrNull;
    _engine.remove(localId);
    if (item != null) {
      await ref.read(captureFileStoreProvider).delete(item.filePath);
    }
  }

  void setNotes(String notes) {
    state = CaptureState(items: state.items, notes: notes);
    _persist();
  }

  /// Clears the session after a Studio job was created from it.
  Future<void> clear() async {
    final store = ref.read(captureFileStoreProvider);
    for (final i in state.items) {
      _engine.remove(i.localId);
      await store.delete(i.filePath);
    }
    state = const CaptureState();
    _persist();
  }
}

final captureControllerProvider =
    NotifierProvider<CaptureController, CaptureState>(CaptureController.new);
