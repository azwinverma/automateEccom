import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/errors/api_error.dart';
import '../../../core/errors/error_messages.dart';
import '../../../core/l10n/gen/app_localizations.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens.g.dart';
import '../../../design/widgets/state_views.dart';
import '../../fulfillment/presentation/fulfillment_labels.dart';
import '../data/automation_api.dart';
import 'automation_labels.dart';

/// Workflows at a glance; switch them on or off. Building/editing is on the web.
class WorkflowsScreen extends ConsumerStatefulWidget {
  const WorkflowsScreen({super.key});

  @override
  ConsumerState<WorkflowsScreen> createState() => _WorkflowsScreenState();
}

class _WorkflowsScreenState extends ConsumerState<WorkflowsScreen> {
  String? _busy;
  String? _error;

  Future<void> _toggle(WorkflowSummary w) async {
    final l = AppLocalizations.of(context);
    setState(() {
      _busy = w.id;
      _error = null;
    });
    try {
      await ref
          .read(automationApiProvider)
          .setStatus(w.id, w.status == 'active' ? 'paused' : 'active');
      ref.invalidate(workflowsProvider);
    } on ApiError catch (e) {
      if (mounted) {
        setState(
          () =>
              _error =
                  e.statusCode == 403
                      ? l.wfManagersOnly
                      : localizedErrorMessage(l, e),
        );
      }
    } finally {
      if (mounted) setState(() => _busy = null);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final palette = AppPalette.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(l.workflowsTitle)),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(workflowsProvider);
          await ref.read(workflowsProvider.future);
        },
        child: ListView(
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(
                AppSpace.s4,
                AppSpace.s3,
                AppSpace.s4,
                0,
              ),
              child: Text(
                l.wfEditOnWeb,
                style: theme.textTheme.bodySmall?.copyWith(
                  color: palette.muted,
                ),
              ),
            ),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.fromLTRB(
                  AppSpace.s4,
                  AppSpace.s2,
                  AppSpace.s4,
                  0,
                ),
                child: Text(
                  _error!,
                  key: const Key('workflows-error'),
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: palette.danger,
                  ),
                ),
              ),
            AsyncValueView<List<WorkflowSummary>>(
              value: ref.watch(workflowsProvider),
              onRetry: () => ref.invalidate(workflowsProvider),
              loading: const SkeletonList(rows: 3),
              isEmpty: (items) => items.isEmpty,
              empty: Padding(
                padding: const EdgeInsets.all(AppSpace.s4),
                child: Text(
                  l.workflowsEmpty,
                  key: const Key('workflows-empty'),
                  style: TextStyle(color: palette.muted),
                ),
              ),
              data:
                  (items) => Column(
                    children: [
                      for (final w in items)
                        ListTile(
                          key: Key('workflow-${w.id}'),
                          title: Text(w.name),
                          subtitle: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              const SizedBox(height: AppSpace.s1),
                              StatusChip(
                                key: Key('workflow-status-${w.id}'),
                                label: workflowStatusLabel(l, w),
                                colors: workflowStatusColors(context, w),
                              ),
                              const SizedBox(height: AppSpace.s1),
                              Text(
                                l.wfRuns(
                                  w.completedRuns,
                                  w.waitingRuns,
                                  w.failedRuns,
                                ),
                              ),
                            ],
                          ),
                          trailing: TextButton(
                            key: Key('workflow-toggle-${w.id}'),
                            onPressed: _busy == w.id ? null : () => _toggle(w),
                            child: Text(
                              w.status == 'active' ? l.wfTurnOff : l.wfTurnOn,
                            ),
                          ),
                        ),
                    ],
                  ),
            ),
          ],
        ),
      ),
    );
  }
}
