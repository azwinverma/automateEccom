import 'exceptions_api.dart';

/// Where tapping an exception takes the seller.
sealed class ExceptionTarget {
  const ExceptionTarget();
}

final class OpenRoute extends ExceptionTarget {
  const OpenRoute(this.location);
  final String location;
}

/// OAuth reconnect happens on the web dashboard for now.
final class ReconnectChannel extends ExceptionTarget {
  const ReconnectChannel({this.connectionId, this.provider});
  final String? connectionId;
  final String? provider;
}

final class DismissLocally extends ExceptionTarget {
  const DismissLocally(this.exceptionId);
  final String exceptionId;
}

final class NoAction extends ExceptionTarget {
  const NoAction();
}

/// Maps an exception's server `action` (+ resource) to a navigation target.
ExceptionTarget resolveExceptionAction(ApiException e) {
  final id = e.resourceId;
  String? detail(String k) {
    final v = e.details[k];
    return v is String && v.isNotEmpty ? v : null;
  }

  switch (e.action) {
    case 'review_draft':
    case 'retry_draft':
      return e.resourceType == 'studio_job'
          ? OpenRoute('/studio/jobs/$id')
          : const NoAction();
    case 'retry_publish':
    case 'confirm_attributes':
      return e.resourceType == 'product'
          ? OpenRoute('/products/$id')
          : const NoAction();
    case 'review_post':
    case 'reschedule':
      return e.resourceType == 'content_post'
          ? OpenRoute('/posts/$id')
          : const NoAction();
    case 'reconnect':
      return ReconnectChannel(
        connectionId:
            e.resourceType == 'channel_connection'
                ? id
                : detail('connection_id'),
        provider: detail('provider'),
      );
    case 'dismiss':
      return DismissLocally(e.id);
  }
  return const NoAction();
}
