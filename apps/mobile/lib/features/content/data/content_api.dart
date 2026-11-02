import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/api_call.dart';
import '../../../core/api/providers.dart';
import '../../studio/data/studio_models.dart';

@immutable
class ContentPost {
  const ContentPost({
    required this.id,
    required this.connectionId,
    required this.caption,
    required this.status,
    required this.version,
    this.source,
    this.issues = const [],
    this.scheduledAt,
    this.lastErrorCode,
    this.rejectionNote,
  });

  factory ContentPost.fromJson(Map<String, Object?> j) => ContentPost(
    id: j['id']! as String,
    connectionId: (j['connection_id'] as String?) ?? '',
    caption: (j['caption'] as String?) ?? '',
    status: (j['status'] as String?) ?? 'draft',
    version: (j['version'] as num?)?.toInt() ?? 1,
    source: j['source'] as String?,
    issues: ((j['issues'] as List<Object?>?) ?? const [])
        .whereType<Map<String, Object?>>()
        .map(DraftIssue.fromJson)
        .toList(growable: false),
    scheduledAt:
        j['scheduled_at'] is String
            ? DateTime.tryParse(j['scheduled_at']! as String)
            : null,
    lastErrorCode: j['last_error_code'] as String?,
    rejectionNote: j['rejection_note'] as String?,
  );

  final String id;
  final String connectionId;
  final String caption;

  /// draft | pending_approval | approved | scheduled | publishing |
  /// published | failed | cancelled
  final String status;
  final int version;
  final String? source;
  final List<DraftIssue> issues;
  final DateTime? scheduledAt;
  final String? lastErrorCode;
  final String? rejectionNote;
}

class ContentApi {
  ContentApi(this._dio);

  final Dio _dio;

  Future<List<ContentPost>> fromStudio(
    String jobId,
    List<String> connectionIds,
  ) => apiCall(() async {
    final r = await _dio.post<Map<String, Object?>>(
      '/content/posts/from-studio',
      data: {'job_id': jobId, 'connection_ids': connectionIds},
    );
    return itemsOf(r.data).map(ContentPost.fromJson).toList();
  });

  /// There is no `GET /content/posts/{id}`; the calendar list is filtered
  /// client-side (see docs/mobile/README.md → API gaps).
  Future<List<ContentPost>> list({String? status}) => apiCall(() async {
    final r = await _dio.get<Map<String, Object?>>(
      '/content/posts',
      queryParameters: {if (status != null) 'status': status},
    );
    return itemsOf(r.data).map(ContentPost.fromJson).toList();
  });

  Future<ContentPost> updateCaption(String id, String caption, int version) =>
      _post(
        () => _dio.patch<Map<String, Object?>>(
          '/content/posts/$id',
          data: {'caption': caption, 'version': version},
        ),
      );

  Future<ContentPost> submit(String id) =>
      _post(() => _dio.post<Map<String, Object?>>('/content/posts/$id/submit'));

  Future<ContentPost> approve(String id) => _post(
    () => _dio.post<Map<String, Object?>>('/content/posts/$id/approve'),
  );

  /// [at] null = publish now.
  Future<ContentPost> schedule(String id, {DateTime? at}) => _post(
    () => _dio.post<Map<String, Object?>>(
      '/content/posts/$id/schedule',
      data: {if (at != null) 'at': at.toUtc().toIso8601String()},
    ),
  );

  Future<ContentPost> _post(
    Future<Response<Map<String, Object?>>> Function() run,
  ) => apiCall(() async => ContentPost.fromJson((await run()).data!));
}

final contentApiProvider = Provider<ContentApi>(
  (ref) => ContentApi(ref.watch(dioProvider)),
);
