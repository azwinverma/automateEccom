import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/errors/api_error.dart';
import '../../../core/errors/error_messages.dart';
import '../../../core/l10n/gen/app_localizations.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens.g.dart';
import '../../../design/widgets/state_views.dart';
import '../data/automation_api.dart';
import 'automation_labels.dart';

/// Workflow steps the Decision Policy left for a person (AUT-009).
class ApprovalsScreen extends ConsumerWidget {
  const ApprovalsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final palette = AppPalette.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(l.approvalsTitle)),
      body: RefreshIndicator(
        onRefresh: () async {
          ref.invalidate(approvalsProvider);
          await ref.read(approvalsProvider.future);
        },
        child: ListView(
          children: [
            AsyncValueView<List<AutomationApproval>>(
              value: ref.watch(approvalsProvider),
              onRetry: () => ref.invalidate(approvalsProvider),
              loading: const SkeletonList(rows: 3),
              isEmpty: (items) => items.isEmpty,
              empty: Padding(
                padding: const EdgeInsets.all(AppSpace.s4),
                child: Text(
                  l.approvalsEmpty,
                  key: const Key('approvals-empty'),
                  style: TextStyle(color: palette.muted),
                ),
              ),
              data:
                  (items) => Column(
                    children: [for (final a in items) _ApprovalTile(item: a)],
                  ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ApprovalTile extends ConsumerStatefulWidget {
  const _ApprovalTile({required this.item});

  final AutomationApproval item;

  @override
  ConsumerState<_ApprovalTile> createState() => _ApprovalTileState();
}

class _ApprovalTileState extends ConsumerState<_ApprovalTile> {
  bool _busy = false;
  String? _error;

  Future<void> _resolve(bool approve, {String? note}) async {
    final l = AppLocalizations.of(context);
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await ref
          .read(automationApiProvider)
          .resolve(widget.item.id, approve: approve, note: note);
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(l.approvalsDone)));
      ref
        ..invalidate(approvalsProvider)
        ..invalidate(controlCenterProvider);
    } on ApiError catch (e) {
      if (!mounted) return;
      setState(() {
        _busy = false;
        _error =
            e.statusCode == 403
                ? l.approvalsManagersOnly
                : localizedErrorMessage(l, e);
      });
    }
  }

  Future<void> _reject() async {
    final note = await showDialog<String>(
      context: context,
      builder: (_) => const _RejectDialog(),
    );
    if (note != null) await _resolve(false, note: note.isEmpty ? null : note);
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final palette = AppPalette.of(context);
    final a = widget.item;
    return Padding(
      key: Key('approval-${a.id}'),
      padding: const EdgeInsets.fromLTRB(
        AppSpace.s4,
        AppSpace.s3,
        AppSpace.s4,
        0,
      ),
      child: Card(
        margin: EdgeInsets.zero,
        child: Padding(
          padding: const EdgeInsets.all(AppSpace.s3),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                actionLabel(l, a.action, kind: a.kind),
                style: theme.textTheme.titleSmall,
              ),
              if ((a.workflowName ?? '').isNotEmpty)
                Text(
                  a.workflowName!,
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: palette.muted,
                  ),
                ),
              const SizedBox(height: AppSpace.s1),
              Text(
                l.approvalsWhy(waitingReason(l, a.decision?.rule)),
                style: theme.textTheme.bodySmall,
              ),
              if (a.orderNumber != null && a.orderId != null)
                TextButton(
                  key: Key('approval-order-${a.id}'),
                  style: TextButton.styleFrom(padding: EdgeInsets.zero),
                  onPressed: () => context.push('/orders/${a.orderId}'),
                  child: Text(l.approvalsOrder(a.orderNumber!)),
                ),
              if (_error != null)
                Padding(
                  padding: const EdgeInsets.only(top: AppSpace.s1),
                  child: Text(
                    _error!,
                    key: Key('approval-error-${a.id}'),
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: palette.danger,
                    ),
                  ),
                ),
              const SizedBox(height: AppSpace.s2),
              Row(
                children: [
                  FilledButton(
                    key: Key('approval-approve-${a.id}'),
                    onPressed: _busy ? null : () => _resolve(true),
                    child: Text(l.approvalsApprove),
                  ),
                  const SizedBox(width: AppSpace.s2),
                  OutlinedButton(
                    key: Key('approval-reject-${a.id}'),
                    onPressed: _busy ? null : _reject,
                    child: Text(l.approvalsReject),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// Returns the (possibly empty) note when confirmed, null when cancelled.
class _RejectDialog extends StatefulWidget {
  const _RejectDialog();

  @override
  State<_RejectDialog> createState() => _RejectDialogState();
}

class _RejectDialogState extends State<_RejectDialog> {
  final _note = TextEditingController();

  @override
  void dispose() {
    _note.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return AlertDialog(
      title: Text(l.approvalsRejectTitle),
      content: TextField(
        key: const Key('approval-note'),
        controller: _note,
        maxLength: 300,
        decoration: InputDecoration(labelText: l.approvalsNote),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: Text(l.approvalsCancel),
        ),
        FilledButton(
          key: const Key('approval-reject-confirm'),
          onPressed: () => Navigator.pop(context, _note.text.trim()),
          child: Text(l.approvalsReject),
        ),
      ],
    );
  }
}
