import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/auth/session_controller.dart';
import '../../../core/l10n/formatters.dart';
import '../../../core/l10n/gen/app_localizations.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens.g.dart';
import '../../../design/widgets/state_views.dart';
import '../data/studio_api.dart';
import '../data/studio_models.dart';

final draftsProvider = FutureProvider.autoDispose<List<StudioJob>>((ref) {
  ref.watch(activeMerchantIdProvider);
  return ref.watch(studioApiProvider).listJobs(limit: 50);
});

/// Recent AI drafts (also the entry for "Generate content").
class DraftsScreen extends ConsumerWidget {
  const DraftsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final palette = AppPalette.of(context);
    final lang = Localizations.localeOf(context).languageCode;
    return Scaffold(
      appBar: AppBar(title: Text(l.draftsTitle)),
      floatingActionButton: FloatingActionButton.extended(
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(AppRadius.md),
        ),
        onPressed: () => context.push('/studio/capture'),
        icon: const Icon(Icons.photo_camera_outlined),
        label: Text(l.draftsNew),
      ),
      body: RefreshIndicator(
        onRefresh: () => ref.refresh(draftsProvider.future),
        child: ListView(
          padding: const EdgeInsets.only(bottom: 96),
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(
                AppSpace.s4,
                0,
                AppSpace.s4,
                AppSpace.s3,
              ),
              child: Text(
                l.draftsIntro,
                style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              ),
            ),
            AsyncValueView<List<StudioJob>>(
              value: ref.watch(draftsProvider),
              onRetry: () => ref.invalidate(draftsProvider),
              isEmpty: (j) => j.isEmpty,
              empty: EmptyState(
                icon: Icons.photo_library_outlined,
                title: l.draftsEmpty,
              ),
              data:
                  (jobs) => Column(
                    children: [
                      for (final j in jobs) ...[
                        ListTile(
                          tileColor: theme.colorScheme.surface,
                          shape: const RoundedRectangleBorder(),
                          title: Text(
                            _title(j, lang).isEmpty
                                ? l.draftUntitled
                                : _title(j, lang),
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                          subtitle: Text(
                            [
                              _status(l, j.status),
                              if (j.createdAt != null)
                                Formatters.dateTime(j.createdAt!, lang),
                            ].join(' · '),
                            style: TextStyle(
                              color:
                                  j.status == JobStatus.failed
                                      ? palette.danger
                                      : j.status == JobStatus.ready
                                      ? palette.automation
                                      : null,
                            ),
                          ),
                          trailing: const Icon(Icons.chevron_right),
                          onTap:
                              () =>
                                  j.status == JobStatus.applied &&
                                          j.productId != null
                                      ? context.push(
                                        '/products/${j.productId}?job=${j.id}',
                                      )
                                      : context.push('/studio/jobs/${j.id}'),
                        ),
                        const Divider(height: 1),
                      ],
                    ],
                  ),
            ),
          ],
        ),
      ),
    );
  }

  static String _title(StudioJob j, String lang) {
    final d = j.draft;
    if (d == null) return '';
    return lang == 'ne' && d.titleNe.isNotEmpty ? d.titleNe : d.titleEn;
  }

  static String _status(AppLocalizations l, JobStatus s) => switch (s) {
    JobStatus.queued ||
    JobStatus.running ||
    JobStatus.unknown => l.draftStatusWorking,
    JobStatus.ready => l.draftStatusReady,
    JobStatus.failed => l.draftStatusFailed,
    JobStatus.applied => l.draftStatusApplied,
    JobStatus.discarded => l.draftStatusDiscarded,
  };
}
