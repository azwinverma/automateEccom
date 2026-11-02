import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/errors/api_error.dart';
import '../../../core/l10n/gen/app_localizations.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens.g.dart';
import '../../../design/widgets/state_views.dart';
import '../data/job_poller.dart';
import '../data/studio_api.dart';
import '../data/studio_models.dart';
import 'review_view.dart';

/// Overridable for tests (no real timers).
final jobPollDelayProvider = Provider<Future<void> Function(Duration)>(
  (ref) => Future<void>.delayed,
);

final studioJobProvider = StreamProvider.autoDispose.family<StudioJob, String>((
  ref,
  id,
) {
  final api = ref.watch(studioApiProvider);
  return pollJob(
    fetch: () => api.getJob(id),
    delay: ref.watch(jobPollDelayProvider),
  );
});

/// Step 2: waits for the AI draft (calm, no fake percentage), then hands
/// over to the review form. Leaving is fine: the job keeps running.
class JobScreen extends ConsumerWidget {
  const JobScreen({super.key, required this.jobId});

  final String jobId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final job = ref.watch(studioJobProvider(jobId));
    return job.when(
      skipLoadingOnRefresh: false,
      loading:
          () => _Shell(
            title: l.draftWorkingTitle,
            child: const SkeletonList(rows: 2),
          ),
      error:
          (e, _) => _Shell(
            title: l.draftWorkingTitle,
            child: ErrorStateView(
              error: e,
              onRetry: () => ref.invalidate(studioJobProvider(jobId)),
            ),
          ),
      data:
          (j) => switch (j.status) {
            JobStatus.ready => ReviewView(key: ValueKey(j.id), job: j),
            JobStatus.queued || JobStatus.running || JobStatus.unknown =>
              _Shell(title: l.draftWorkingTitle, child: _Working(job: j)),
            JobStatus.failed => _Shell(
              title: l.draftFailedTitle,
              child: _Failed(job: j),
            ),
            JobStatus.applied => _Shell(
              title: l.draftAppliedTitle,
              child: Padding(
                padding: const EdgeInsets.all(AppSpace.s4),
                child: FilledButton(
                  onPressed:
                      j.productId == null
                          ? null
                          : () => context.pushReplacement(
                            '/products/${j.productId}?job=${j.id}',
                          ),
                  child: Text(l.draftOpenProduct),
                ),
              ),
            ),
            JobStatus.discarded => _Shell(
              title: l.draftsTitle,
              child: EmptyState(title: l.draftDiscarded),
            ),
          },
    );
  }
}

class _Shell extends StatelessWidget {
  const _Shell({required this.title, required this.child});

  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: Text(title)),
    body: ListView(children: [child]),
  );
}

class _Working extends StatelessWidget {
  const _Working({required this.job});

  final StudioJob job;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final palette = AppPalette.of(context);
    final reduced = MediaQuery.maybeDisableAnimationsOf(context) ?? false;
    return Padding(
      padding: const EdgeInsets.all(AppSpace.s4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.edit_note, color: palette.automation),
              const SizedBox(width: AppSpace.s2),
              Text(
                job.status == JobStatus.queued ? l.draftQueued : l.draftRunning,
                key: const Key('job-status'),
                style: theme.textTheme.titleSmall?.copyWith(
                  color: palette.automation,
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpace.s3),
          // Indeterminate on purpose: we don't know the remaining time.
          if (!reduced)
            LinearProgressIndicator(
              color: palette.automation,
              backgroundColor: palette.automationSoft,
              semanticsLabel: l.loadingLabel,
            ),
          const SizedBox(height: AppSpace.s4),
          Text(l.draftWorkingBody, style: theme.textTheme.bodyMedium),
          const SizedBox(height: AppSpace.s4),
          Text(
            l.draftLeaveOk,
            style: theme.textTheme.bodySmall?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
        ],
      ),
    );
  }
}

class _Failed extends ConsumerStatefulWidget {
  const _Failed({required this.job});

  final StudioJob job;

  @override
  ConsumerState<_Failed> createState() => _FailedState();
}

class _FailedState extends ConsumerState<_Failed> {
  bool _busy = false;
  ApiError? _error;

  Future<void> _retry() async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await ref.read(studioApiProvider).retry(widget.job.id);
      ref.invalidate(studioJobProvider(widget.job.id));
    } on ApiError catch (e) {
      if (mounted) setState(() => _error = e);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final aiBusy = const {
      'ai_unavailable',
      'provider_unavailable',
      'stalled',
    }.contains(widget.job.errorCode);
    return Padding(
      padding: const EdgeInsets.all(AppSpace.s4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            aiBusy ? l.errAiUnavailable : l.draftFailedBody,
            style: theme.textTheme.bodyMedium,
          ),
          if (widget.job.errorCode != null)
            Padding(
              padding: const EdgeInsets.only(top: AppSpace.s1),
              child: SelectableText(
                l.requestIdLabel(widget.job.errorCode!),
                style: theme.textTheme.labelSmall?.copyWith(
                  color: AppPalette.of(context).muted,
                ),
              ),
            ),
          const SizedBox(height: AppSpace.s4),
          if (_error != null) ...[
            InlineError(error: _error!),
            const SizedBox(height: AppSpace.s3),
          ],
          FilledButton.icon(
            key: const Key('job-retry'),
            style: FilledButton.styleFrom(
              minimumSize: const Size.fromHeight(52),
            ),
            onPressed: _busy ? null : _retry,
            icon: const Icon(Icons.refresh),
            label: Text(l.actionRetry),
          ),
        ],
      ),
    );
  }
}
