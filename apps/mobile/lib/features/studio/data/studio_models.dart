import 'package:flutter/foundation.dart';

List<String> _strings(Object? v) => ((v as List<Object?>?) ?? const [])
    .whereType<String>()
    .toList(growable: false);

double _d(Object? v) => v is num ? v.toDouble() : 0;

@immutable
class DraftAttribute {
  const DraftAttribute({
    required this.key,
    required this.value,
    required this.confidence,
  });

  factory DraftAttribute.fromJson(Map<String, Object?> j) => DraftAttribute(
    key: (j['key'] as String?) ?? '',
    value: (j['value'] as String?) ?? '',
    confidence: _d(j['confidence']),
  );

  final String key;
  final String value;
  final double confidence;
}

@immutable
class DraftOption {
  const DraftOption({required this.name, required this.values});

  factory DraftOption.fromJson(Map<String, Object?> j) => DraftOption(
    name: (j['name'] as String?) ?? '',
    values: _strings(j['values']),
  );

  final String name;
  final List<String> values;
}

/// Studio job `draft` (AI output, schema-validated server-side). Contains no
/// commercial facts: prices, stock and delivery come from the seller.
@immutable
class StudioDraft {
  const StudioDraft({
    this.titleEn = '',
    this.titleNe = '',
    this.descriptionEn = '',
    this.descriptionNe = '',
    this.bulletsEn = const [],
    this.attributes = const [],
    this.categoryPath = const [],
    this.categoryConfidence = 0,
    this.suggestedOptions = const [],
    this.hashtags = const [],
    this.captions = const {},
    this.needsSellerInput = const [],
    this.isProductPhoto = true,
  });

  factory StudioDraft.fromJson(Map<String, Object?> j) {
    final cat = (j['category'] as Map<String, Object?>?) ?? const {};
    final caps = (j['captions'] as Map<String, Object?>?) ?? const {};
    return StudioDraft(
      titleEn: (j['title_en'] as String?) ?? '',
      titleNe: (j['title_ne'] as String?) ?? '',
      descriptionEn: (j['description_en'] as String?) ?? '',
      descriptionNe: (j['description_ne'] as String?) ?? '',
      bulletsEn: _strings(j['bullets_en']),
      attributes: ((j['attributes'] as List<Object?>?) ?? const [])
          .whereType<Map<String, Object?>>()
          .map(DraftAttribute.fromJson)
          .where((a) => a.key.isNotEmpty && a.value.isNotEmpty)
          .toList(growable: false),
      categoryPath: _strings(cat['path']),
      categoryConfidence: _d(cat['confidence']),
      suggestedOptions: ((j['suggested_options'] as List<Object?>?) ?? const [])
          .whereType<Map<String, Object?>>()
          .map(DraftOption.fromJson)
          .where((o) => o.name.isNotEmpty)
          .toList(growable: false),
      hashtags: _strings(j['hashtags']),
      captions: {
        for (final e in caps.entries)
          if (e.value is String) e.key: e.value! as String,
      },
      needsSellerInput: _strings(j['needs_seller_input']),
      isProductPhoto: (j['is_product_photo'] as bool?) ?? true,
    );
  }

  final String titleEn;
  final String titleNe;
  final String descriptionEn;
  final String descriptionNe;
  final List<String> bulletsEn;
  final List<DraftAttribute> attributes;
  final List<String> categoryPath;
  final double categoryConfidence;
  final List<DraftOption> suggestedOptions;
  final List<String> hashtags;
  final Map<String, String> captions;
  final List<String> needsSellerInput;
  final bool isProductPhoto;
}

@immutable
class DraftIssue {
  const DraftIssue({required this.field, required this.kind, this.excerpt});

  factory DraftIssue.fromJson(Map<String, Object?> j) => DraftIssue(
    field: (j['field'] as String?) ?? '',
    kind: (j['kind'] as String?) ?? '',
    excerpt: j['excerpt'] as String?,
  );

  final String field;

  /// `unsupported_claim:<price|discount|stock|delivery|warranty|authenticity>`,
  /// `not_a_product_photo` or `too_long`.
  final String kind;
  final String? excerpt;

  /// e.g. "price" for `unsupported_claim:price`, else null.
  String? get claim =>
      kind.startsWith('unsupported_claim:') ? kind.split(':').last : null;
}

enum JobStatus { queued, running, ready, failed, applied, discarded, unknown }

@immutable
class StudioJob {
  const StudioJob({
    required this.id,
    required this.status,
    this.assetIds = const [],
    this.locale = 'ne',
    this.draft,
    this.confidence,
    this.needsReview = false,
    this.issues = const [],
    this.errorCode,
    this.productId,
    this.createdAt,
  });

  factory StudioJob.fromJson(Map<String, Object?> j) => StudioJob(
    id: j['id']! as String,
    status: JobStatus.values.firstWhere(
      (s) => s.name == j['status'],
      orElse: () => JobStatus.unknown,
    ),
    assetIds: _strings(j['asset_ids']),
    locale: (j['locale'] as String?) ?? 'ne',
    draft:
        j['draft'] is Map<String, Object?>
            ? StudioDraft.fromJson(j['draft']! as Map<String, Object?>)
            : null,
    confidence: (j['confidence'] as num?)?.toDouble(),
    needsReview: (j['needs_review'] as bool?) ?? false,
    issues: ((j['issues'] as List<Object?>?) ?? const [])
        .whereType<Map<String, Object?>>()
        .map(DraftIssue.fromJson)
        .toList(growable: false),
    errorCode: j['error_code'] as String?,
    productId: j['product_id'] as String?,
    createdAt:
        j['created_at'] is String
            ? DateTime.tryParse(j['created_at']! as String)
            : null,
  );

  final String id;
  final JobStatus status;
  final List<String> assetIds;
  final String locale;
  final StudioDraft? draft;
  final double? confidence;
  final bool needsReview;
  final List<DraftIssue> issues;
  final String? errorCode;
  final String? productId;
  final DateTime? createdAt;

  bool get isTerminal =>
      status != JobStatus.queued && status != JobStatus.running;
}
