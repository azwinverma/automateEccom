import 'package:flutter/foundation.dart';

/// `GET /media/{id}` (subset used by the app).
@immutable
class MediaAsset {
  const MediaAsset({
    required this.id,
    required this.status,
    this.qualityFlags = const [],
    this.rejectionReason,
    this.derivatives = const {},
  });

  factory MediaAsset.fromJson(Map<String, Object?> json) {
    final d = (json['derivatives'] as Map<String, Object?>?) ?? const {};
    return MediaAsset(
      id: json['id']! as String,
      status: (json['status'] as String?) ?? 'pending_upload',
      qualityFlags: ((json['quality_flags'] as List<Object?>?) ?? const [])
          .whereType<String>()
          .toList(growable: false),
      rejectionReason: json['rejection_reason'] as String?,
      derivatives: {
        for (final e in d.entries)
          if (e.value is Map<String, Object?> &&
              (e.value! as Map<String, Object?>)['url'] is String)
            e.key: (e.value! as Map<String, Object?>)['url']! as String,
      },
    );
  }

  final String id;

  /// pending_upload | uploaded | processing | ready | rejected | deleted
  final String status;

  /// Subset of low_resolution | blurry | too_dark | overexposed.
  final List<String> qualityFlags;

  /// not_an_image | image_too_large | unsupported_format | malware_detected
  final String? rejectionReason;

  /// kind → signed URL (expires in ~5 min; refetch, never cache).
  final Map<String, String> derivatives;

  bool get isTerminal => status == 'ready' || status == 'rejected';
}

@immutable
class UploadTicket {
  const UploadTicket({
    required this.assetId,
    required this.url,
    required this.headers,
    this.expiresAt,
  });

  factory UploadTicket.fromJson(Map<String, Object?> json) {
    final u = json['upload']! as Map<String, Object?>;
    return UploadTicket(
      assetId: json['asset_id']! as String,
      url: u['url']! as String,
      headers: ((u['headers'] as Map<String, Object?>?) ?? const {}).map(
        (k, v) => MapEntry(k, '$v'),
      ),
      expiresAt:
          u['expires_at'] is String
              ? DateTime.tryParse(u['expires_at']! as String)
              : null,
    );
  }

  final String assetId;
  final String url;
  final Map<String, String> headers;
  final DateTime? expiresAt;
}
