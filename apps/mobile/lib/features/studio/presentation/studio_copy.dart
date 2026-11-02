import '../../../core/l10n/gen/app_localizations.dart';
import '../data/studio_models.dart';

/// Seller-facing copy for a grounding/length issue.
String issueMessage(AppLocalizations l, DraftIssue issue) {
  switch (issue.claim) {
    case 'price':
      return l.issueClaimPrice;
    case 'discount':
      return l.issueClaimDiscount;
    case 'stock':
      return l.issueClaimStock;
    case 'delivery':
      return l.issueClaimDelivery;
    case 'warranty':
      return l.issueClaimWarranty;
    case 'authenticity':
      return l.issueClaimAuthenticity;
    case null:
      break;
    default:
      return l.issueClaimOther;
  }
  return switch (issue.kind) {
    'not_a_product_photo' => l.issueNotProductPhoto,
    'too_long' => l.issueTooLong,
    _ => l.issueClaimOther,
  };
}

/// Readable field name for an issue's `field` (e.g. `captions.instagram`).
String issueFieldLabel(AppLocalizations l, String field) {
  if (field.startsWith('title_ne')) return l.fieldTitleNe;
  if (field.startsWith('title_en')) return l.fieldTitleEn;
  if (field.startsWith('description_ne')) return l.fieldDescriptionNe;
  if (field.startsWith('description_en')) return l.fieldDescriptionEn;
  if (field.startsWith('caption')) {
    final ch = field.split('.').last;
    final name = switch (ch) {
      'instagram' => 'Instagram',
      'facebook' => 'Facebook',
      'tiktok' => 'TikTok',
      _ => '',
    };
    return name.isEmpty ? l.fieldCaption : '${l.fieldCaption} · $name';
  }
  if (field.startsWith('bullets_en')) return l.fieldDescriptionEn;
  return field;
}

/// Gentle retake tip for a media quality flag; null for unknown flags.
String? qualityTip(AppLocalizations l, String flag) => switch (flag) {
  'low_resolution' => l.tipLowResolution,
  'blurry' => l.tipBlurry,
  'too_dark' => l.tipTooDark,
  'overexposed' => l.tipOverexposed,
  _ => null,
};

String rejectionMessage(AppLocalizations l, String? reason) => switch (reason) {
  'not_an_image' => l.rejectNotAnImage,
  'image_too_large' => l.rejectTooLarge,
  'unsupported_format' => l.rejectUnsupported,
  'malware_detected' => l.rejectMalware,
  _ => l.uploadRejected,
};
