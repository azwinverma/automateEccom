import 'dart:async';

import '../../../core/errors/api_error.dart';
import 'studio_models.dart';

/// Backoff schedule for polling a Studio job: 2s, 3s, 4.5s … capped at 10s.
Duration jobPollDelay(
  int attempt, {
  Duration initial = const Duration(seconds: 2),
  Duration cap = const Duration(seconds: 10),
}) {
  var ms = initial.inMilliseconds.toDouble();
  for (var i = 0; i < attempt; i++) {
    ms *= 1.5;
    if (ms >= cap.inMilliseconds) return cap;
  }
  return Duration(milliseconds: ms.round());
}

/// Polls `GET /studio/jobs/{id}` until a terminal status, emitting every
/// observed job. Transient errors (offline, 5xx) keep polling at the capped
/// delay; other errors are emitted as stream errors and stop polling.
Stream<StudioJob> pollJob({
  required Future<StudioJob> Function() fetch,
  Future<void> Function(Duration)? delay,
  int maxTransientErrors = 30,
}) async* {
  final wait = delay ?? Future<void>.delayed;
  var attempt = 0;
  var transient = 0;
  while (true) {
    try {
      final job = await fetch();
      transient = 0;
      yield job;
      if (job.isTerminal) return;
      await wait(jobPollDelay(attempt++));
    } on ApiError catch (e) {
      final retryable =
          e.isOffline || (e.statusCode ?? 0) >= 500 || e.code == 'rate_limited';
      if (!retryable || ++transient > maxTransientErrors) rethrow;
      await wait(e.retryAfter ?? jobPollDelay(99));
    }
  }
}
