import 'dart:async';
import 'dart:math' as math;

import 'package:flutter/foundation.dart';

import '../../../core/errors/api_error.dart';
import 'media_api.dart';
import 'media_models.dart';

/// Per-photo upload lifecycle.
///
/// queued → uploading → completing → processing → ready | rejected
///        ↘ waitingRetry (network gave out; resumes on retry/online)
///        ↘ failed (not retryable: quota, too large, unsupported, no access)
enum UploadPhase {
  queued,
  uploading,
  completing,
  processing,
  ready,
  rejected,
  waitingRetry,
  failed,
}

@immutable
class UploadItem {
  const UploadItem({
    required this.localId,
    required this.filePath,
    required this.fileName,
    required this.contentType,
    required this.sizeBytes,
    this.phase = UploadPhase.queued,
    this.progress = 0,
    this.assetId,
    this.ticket,
    this.attempts = 0,
    this.errorCode,
    this.requestId,
    this.qualityFlags = const [],
    this.rejectionReason,
    this.pausedFrom,
  });

  factory UploadItem.fromJson(Map<String, Object?> j) {
    final t = j['ticket'];
    return UploadItem(
      localId: j['local_id']! as String,
      filePath: j['file_path']! as String,
      fileName: j['file_name']! as String,
      contentType: j['content_type']! as String,
      sizeBytes: (j['size_bytes']! as num).toInt(),
      phase: UploadPhase.values.firstWhere(
        (p) => p.name == j['phase'],
        orElse: () => UploadPhase.queued,
      ),
      assetId: j['asset_id'] as String?,
      ticket:
          t is Map<String, Object?>
              ? UploadTicket(
                assetId: t['asset_id']! as String,
                url: t['url']! as String,
                headers: ((t['headers'] as Map<String, Object?>?) ?? const {})
                    .map((k, v) => MapEntry(k, '$v')),
                expiresAt:
                    t['expires_at'] is String
                        ? DateTime.tryParse(t['expires_at']! as String)
                        : null,
              )
              : null,
      attempts: (j['attempts'] as num?)?.toInt() ?? 0,
      errorCode: j['error_code'] as String?,
      requestId: j['request_id'] as String?,
      qualityFlags: ((j['quality_flags'] as List<Object?>?) ?? const [])
          .whereType<String>()
          .toList(growable: false),
      rejectionReason: j['rejection_reason'] as String?,
      pausedFrom:
          UploadPhase.values
              .where((p) => p.name == j['paused_from'])
              .firstOrNull,
    );
  }

  final String localId;

  /// Copy in app storage (survives the OS clearing picker temp files).
  final String filePath;
  final String fileName;
  final String contentType;
  final int sizeBytes;
  final UploadPhase phase;

  /// 0..1 for the PUT; meaningful in [UploadPhase.uploading].
  final double progress;
  final String? assetId;
  final UploadTicket? ticket;
  final int attempts;
  final String? errorCode;
  final String? requestId;
  final List<String> qualityFlags;
  final String? rejectionReason;

  /// Step to resume from when a [UploadPhase.waitingRetry] item is retried.
  final UploadPhase? pausedFrom;

  bool get isTerminal =>
      phase == UploadPhase.ready ||
      phase == UploadPhase.rejected ||
      phase == UploadPhase.failed;

  bool get isActive => !isTerminal && phase != UploadPhase.waitingRetry;

  UploadItem copyWith({
    UploadPhase? phase,
    double? progress,
    String? Function()? assetId,
    UploadTicket? Function()? ticket,
    int? attempts,
    String? Function()? errorCode,
    String? Function()? requestId,
    List<String>? qualityFlags,
    String? Function()? rejectionReason,
    UploadPhase? Function()? pausedFrom,
  }) => UploadItem(
    localId: localId,
    filePath: filePath,
    fileName: fileName,
    contentType: contentType,
    sizeBytes: sizeBytes,
    phase: phase ?? this.phase,
    progress: progress ?? this.progress,
    assetId: assetId != null ? assetId() : this.assetId,
    ticket: ticket != null ? ticket() : this.ticket,
    attempts: attempts ?? this.attempts,
    errorCode: errorCode != null ? errorCode() : this.errorCode,
    requestId: requestId != null ? requestId() : this.requestId,
    qualityFlags: qualityFlags ?? this.qualityFlags,
    rejectionReason:
        rejectionReason != null ? rejectionReason() : this.rejectionReason,
    pausedFrom: pausedFrom != null ? pausedFrom() : this.pausedFrom,
  );

  Map<String, Object?> toJson() => {
    'local_id': localId,
    'file_path': filePath,
    'file_name': fileName,
    'content_type': contentType,
    'size_bytes': sizeBytes,
    // An interrupted PUT/complete is resumed from its last durable step.
    'phase': phase.name,
    'asset_id': assetId,
    if (ticket != null)
      'ticket': {
        'asset_id': ticket!.assetId,
        'url': ticket!.url,
        'headers': ticket!.headers,
        'expires_at': ticket!.expiresAt?.toIso8601String(),
      },
    'attempts': attempts,
    'error_code': errorCode,
    'request_id': requestId,
    'quality_flags': qualityFlags,
    'rejection_reason': rejectionReason,
    'paused_from': pausedFrom?.name,
  };
}

/// Client-side size cap mirrors the server's 20 MB limit.
const maxUploadBytes = 20 * 1024 * 1024;

const _nonRetryable = {
  'usage_limit_reached',
  'file_too_large',
  'unsupported_media_type',
  'permission_denied',
  'feature_not_in_plan',
  'not_found',
  'validation_error',
};

/// Drives every [UploadItem] through its lifecycle with bounded concurrency,
/// automatic backoff on flaky networks and resumable steps.
class UploadEngine {
  UploadEngine({
    required this.api,
    required this.readFile,
    required this.onChanged,
    Future<void> Function(Duration)? delay,
    DateTime Function()? now,
    this.maxAutoRetries = 4,
    this.concurrency = 2,
    this.pollCap = const Duration(seconds: 8),
  }) : _delay = delay ?? Future<void>.delayed,
       _now = now ?? DateTime.now;

  final MediaGateway api;
  final Future<Uint8List> Function(String path) readFile;
  final void Function(List<UploadItem> items) onChanged;
  final int maxAutoRetries;
  final int concurrency;
  final Duration pollCap;
  final Future<void> Function(Duration) _delay;
  final DateTime Function() _now;

  final List<UploadItem> _items = [];
  final Set<String> _running = {};
  final Set<String> _removed = {};

  /// Items whose ticket was issued during this run: trusted even if the
  /// device clock says it's expired (clock skew). The server's signature
  /// check is authoritative and its rejection is retried with backoff.
  final Set<String> _freshTicket = {};
  final List<Completer<void>> _idleWaiters = [];
  bool _disposed = false;

  List<UploadItem> get items => List.unmodifiable(_items);

  /// Restores persisted items; anything mid-flight is resumed.
  void restore(Iterable<UploadItem> items) {
    _items
      ..clear()
      ..addAll(items);
    _emit();
    _pump();
  }

  void add(Iterable<UploadItem> items) {
    for (final i in items) {
      if (i.sizeBytes > maxUploadBytes) {
        _items.add(
          i.copyWith(
            phase: UploadPhase.failed,
            errorCode: () => 'file_too_large',
          ),
        );
      } else {
        _items.add(i);
      }
    }
    _emit();
    _pump();
  }

  void remove(String localId) {
    _removed.add(localId);
    _items.removeWhere((i) => i.localId == localId);
    _emit();
    _pump();
  }

  /// Retries one item (or all paused/failed-retryable items when null).
  void retry([String? localId]) {
    for (var n = 0; n < _items.length; n++) {
      final i = _items[n];
      if (localId != null && i.localId != localId) continue;
      if (i.phase == UploadPhase.waitingRetry) {
        _items[n] = i.copyWith(
          phase: i.pausedFrom ?? UploadPhase.queued,
          pausedFrom: () => null,
          attempts: 0,
          errorCode: () => null,
        );
      } else if (i.phase == UploadPhase.failed &&
          localId != null &&
          i.errorCode != 'file_too_large') {
        _items[n] = _restart(i).copyWith(attempts: 0, errorCode: () => null);
      }
    }
    _emit();
    _pump();
  }

  /// Completes when nothing is running (tests / graceful shutdown).
  Future<void> idle() {
    if (_running.isEmpty) return Future.value();
    final c = Completer<void>();
    _idleWaiters.add(c);
    return c.future;
  }

  void dispose() => _disposed = true;

  void _emit() {
    if (!_disposed) onChanged(items);
  }

  int _indexOf(String id) => _items.indexWhere((i) => i.localId == id);

  UploadItem? _get(String id) {
    final n = _indexOf(id);
    return n < 0 ? null : _items[n];
  }

  void _set(UploadItem item) {
    final n = _indexOf(item.localId);
    if (n < 0) return;
    _items[n] = item;
    _emit();
  }

  void _pump() {
    if (_disposed) return;
    for (final i in _items) {
      if (_running.length >= concurrency) break;
      if (!i.isActive || _running.contains(i.localId)) continue;
      _running.add(i.localId);
      unawaited(
        _run(i.localId).whenComplete(() {
          _running.remove(i.localId);
          _pump();
          if (_running.isEmpty) {
            for (final w in _idleWaiters) {
              w.complete();
            }
            _idleWaiters.clear();
          }
        }),
      );
    }
  }

  bool _ticketUsable(UploadItem i) {
    final t = i.ticket;
    if (t == null) return false;
    final exp = t.expiresAt;
    return exp == null || exp.isAfter(_now().add(const Duration(seconds: 30)));
  }

  Future<void> _run(String id) async {
    while (!_disposed && !_removed.contains(id)) {
      final item = _get(id);
      if (item == null || !item.isActive) return;
      try {
        switch (item.phase) {
          case UploadPhase.queued:
            final t = await api.createUpload(
              fileName: item.fileName,
              contentType: item.contentType,
              sizeBytes: item.sizeBytes,
            );
            _freshTicket.add(id);
            _set(
              item.copyWith(
                phase: UploadPhase.uploading,
                assetId: () => t.assetId,
                ticket: () => t,
                progress: 0,
                errorCode: () => null,
              ),
            );
          case UploadPhase.uploading:
            if (!_freshTicket.contains(id) && !_ticketUsable(item)) {
              // Signed URL expired: start a fresh upload slot.
              _set(_restart(item));
              continue;
            }
            final bytes = await readFile(item.filePath);
            await api.putBytes(
              item.ticket!,
              bytes,
              onProgress: (sent, total) {
                final cur = _get(id);
                if (cur == null || total <= 0) return;
                _set(cur.copyWith(progress: sent / total));
              },
            );
            _set(
              _get(id)!.copyWith(phase: UploadPhase.completing, progress: 1),
            );
          case UploadPhase.completing:
            await api.complete(item.assetId!);
            _set(item.copyWith(phase: UploadPhase.processing, attempts: 0));
          case UploadPhase.processing:
            if (await _poll(id)) continue;
            return;
          case UploadPhase.ready:
          case UploadPhase.rejected:
          case UploadPhase.waitingRetry:
          case UploadPhase.failed:
            return;
        }
      } on ApiError catch (e) {
        final cur = _get(id);
        if (cur == null) return;
        if (!await _handleError(cur, e)) return;
      } on Object {
        // File vanished or unreadable: cannot recover automatically.
        final cur = _get(id);
        if (cur == null) return;
        _set(
          cur.copyWith(
            phase: UploadPhase.failed,
            errorCode: () => 'file_unreadable',
          ),
        );
        return;
      }
    }
  }

  UploadItem _restart(UploadItem i) => i.copyWith(
    phase: UploadPhase.queued,
    assetId: () => null,
    ticket: () => null,
    progress: 0,
  );

  /// Returns true to continue the loop.
  Future<bool> _handleError(UploadItem item, ApiError e) async {
    switch (e.code) {
      case 'upload_missing':
        // Server never got the bytes: redo the PUT.
        _set(item.copyWith(phase: UploadPhase.uploading, progress: 0));
        return _backoff(item, e);
      case 'upload_expired':
      case 'invalid_signature':
        _set(_restart(item));
        return _backoff(item, e);
    }
    if (e.kind == ApiErrorKind.sessionEnded || _nonRetryable.contains(e.code)) {
      _set(
        item.copyWith(
          phase: UploadPhase.failed,
          errorCode: () => e.code,
          requestId: () => e.requestId,
        ),
      );
      return false;
    }
    // Network, timeout, 5xx, rate limit, dependency down → backoff.
    return _backoff(item, e);
  }

  Future<bool> _backoff(UploadItem item, ApiError e) async {
    final cur = _get(item.localId)!;
    final attempts = cur.attempts + 1;
    if (attempts > maxAutoRetries) {
      _set(
        cur.copyWith(
          phase: UploadPhase.waitingRetry,
          pausedFrom: () => cur.phase,
          attempts: attempts,
          errorCode: () => e.code,
          requestId: () => e.requestId,
        ),
      );
      return false;
    }
    _set(
      cur.copyWith(
        attempts: attempts,
        errorCode: () => e.code,
        requestId: () => e.requestId,
      ),
    );
    final wait =
        e.retryAfter ?? Duration(seconds: math.min(30, 1 << (attempts - 1)));
    await _delay(wait);
    return true;
  }

  /// Returns true when the main loop must continue (asset needs `complete`
  /// again), false when the item reached a terminal state.
  Future<bool> _poll(String id) async {
    var wait = const Duration(seconds: 1);
    while (!_disposed && !_removed.contains(id)) {
      final cur = _get(id);
      if (cur == null) return false;
      final asset = await api.get(cur.assetId!);
      if (asset.status == 'ready') {
        _set(
          cur.copyWith(
            phase: UploadPhase.ready,
            qualityFlags: asset.qualityFlags,
            errorCode: () => null,
            attempts: 0,
          ),
        );
        return false;
      }
      if (asset.status == 'rejected') {
        _set(
          cur.copyWith(
            phase: UploadPhase.rejected,
            rejectionReason: () => asset.rejectionReason,
          ),
        );
        return false;
      }
      if (asset.status == 'pending_upload') {
        // complete() didn't stick (e.g. app killed between PUT and complete).
        _set(cur.copyWith(phase: UploadPhase.completing));
        return true;
      }
      await _delay(wait);
      final next = wait * 1.5;
      wait = next > pollCap ? pollCap : next;
    }
    return false;
  }
}
