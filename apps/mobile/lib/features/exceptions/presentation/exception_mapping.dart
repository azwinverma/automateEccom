import '../../../core/l10n/gen/app_localizations.dart';
import '../../home/presentation/widgets/exception_list.dart';
import '../data/exceptions_api.dart';

String exceptionActionLabel(AppLocalizations l, String action) =>
    switch (action) {
      'reconnect' => l.exActionReconnect,
      'retry_publish' => l.exActionRetryPublish,
      'reschedule' => l.exActionReschedule,
      'review_post' => l.exActionReviewPost,
      'review_draft' => l.exActionReviewDraft,
      'retry_draft' => l.exActionRetryDraft,
      'resolve_drift' => l.exActionResolveDrift,
      'confirm_attributes' => l.exActionConfirmAttributes,
      'dismiss' => l.exActionDismiss,
      _ => '',
    };

String exceptionSubject(AppLocalizations l, ApiException e) {
  String? d(String k) {
    final v = e.details[k];
    return v is String && v.isNotEmpty ? v : null;
  }

  return switch (e.resourceType) {
    'channel_connection' =>
      d('name') ?? d('provider') ?? l.reconnectChannelGeneric,
    'product' => d('product_title') ?? l.exSubjectProduct,
    'content_post' => l.exSubjectPost,
    'studio_job' => l.exSubjectDraft,
    'media' => d('file_name') ?? l.exSubjectProduct,
    _ => e.resourceType,
  };
}

/// API exceptions → list items. Unknown types are dropped (logged in
/// debug) rather than rendered with a wrong label.
List<ExceptionItem> toExceptionItems(
  AppLocalizations l,
  List<ApiException> items,
) => [
  for (final e in items)
    if (ExceptionType.fromCode(e.type) case final type?)
      ExceptionItem(
        id: e.id,
        type: type,
        subject: exceptionSubject(l, e),
        occurredAt: e.occurredAt ?? DateTime.fromMillisecondsSinceEpoch(0),
        severity: ExceptionSeverity.fromCode(e.severity),
        actionLabel:
            exceptionActionLabel(l, e.action).isEmpty
                ? null
                : exceptionActionLabel(l, e.action),
      ),
];
