import '../l10n/gen/app_localizations.dart';
import 'api_error.dart';

/// Maps contract error codes to localized, user-facing copy. The server's
/// `message` is a developer fallback and is never shown.
String localizedErrorMessage(AppLocalizations l, ApiError error) {
  switch (error.code) {
    case 'validation_error':
      return l.errValidation;
    case 'not_authenticated':
    case 'token_expired':
    case 'invalid_token':
      return l.errNotAuthenticated;
    case 'invalid_credentials':
      return l.errInvalidCredentials;
    case 'mfa_invalid_code':
      return l.errMfaInvalidCode;
    case 'permission_denied':
      return l.errPermissionDenied;
    case 'feature_not_in_plan':
      return l.errFeatureNotInPlan;
    case 'not_found':
      return l.errNotFound;
    case 'conflict':
      return l.errConflict;
    case 'idempotency_in_progress':
      return l.errIdempotencyInProgress;
    case 'idempotency_key_reused':
      return l.errIdempotencyKeyReused;
    case 'slug_taken':
      return l.errSlugTaken;
    case 'email_taken':
      return l.errEmailTaken;
    case 'usage_limit_reached':
      return error.details['resource'] == 'storage_mb'
          ? l.errStorageFull
          : l.errUsageLimitReached;
    case 'invalid_state_transition':
      return l.errInvalidStateTransition;
    case 'rate_limited':
      return l.errRateLimited;
    case 'dependency_unavailable':
      return l.errDependencyUnavailable;
    case 'refresh_token_reused':
      return l.errSessionReused;
    case 'session_revoked':
      return l.errSessionRevoked;
    // Phase 1: media, studio, catalog, channels, content.
    case 'file_too_large':
      return l.errFileTooLarge;
    case 'unsupported_media_type':
      return l.errUnsupportedMediaType;
    case 'file_unreadable':
      return l.errFileUnreadable;
    case 'upload_missing':
      return l.errUploadMissing;
    case 'upload_expired':
    case 'invalid_signature':
      return l.errUploadExpired;
    case 'media_not_ready':
      return l.errMediaNotReady;
    case 'media_not_found':
      return l.errMediaNotFound;
    case 'media_in_use':
      return l.errConflict;
    case 'draft_not_ready':
      return l.errDraftNotReady;
    case 'invalid_photo_count':
      return l.errInvalidPhotoCount;
    case 'not_failed':
      return l.errNotFailed;
    case 'not_publishable':
      return l.errNotPublishable;
    case 'product_not_active':
      return l.errProductNotActive;
    case 'capability_not_supported':
      return l.errCapabilityNotSupported;
    case 'version_conflict':
      return l.errVersionConflict;
    case 'post_locked':
      return l.errPostLocked;
    case 'reconnect_required':
      return l.errReconnectRequired;
    case 'schedule_in_past':
      return l.errScheduleInPast;
    case 'schedule_too_far':
      return l.errScheduleTooFar;
    case 'caption_required':
      return l.errCaptionRequired;
    case 'caption_too_long':
      return l.errCaptionTooLong;
    case 'connection_not_found':
      return l.errNotFound;
    case ClientErrorCodes.sessionEnded:
      return l.errSessionEnded;
    case ClientErrorCodes.network:
      return l.errNetwork;
    case ClientErrorCodes.timeout:
      return l.errTimeout;
    case ClientErrorCodes.server:
      return l.errServer;
  }
  if (error.kind == ApiErrorKind.sessionEnded) return l.errSessionEnded;
  if ((error.statusCode ?? 0) >= 500) return l.errServer;
  return l.errUnknown;
}

/// Copy for a forced sign-out reason shown on the login screen.
String? sessionEndedMessage(AppLocalizations l, String? reason) =>
    switch (reason) {
      null => null,
      'refresh_token_reused' => l.errSessionReused,
      'session_revoked' => l.errSessionRevoked,
      _ => l.errSessionEnded,
    };
