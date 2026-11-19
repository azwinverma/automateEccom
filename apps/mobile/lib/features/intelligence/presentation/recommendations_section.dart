import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/errors/api_error.dart';
import '../../../core/errors/error_messages.dart';
import '../../../core/l10n/gen/app_localizations.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens.g.dart';
import '../../../design/widgets/section_header.dart';
import '../../automation/data/automation_api.dart';
import '../data/intelligence_api.dart';
import 'intelligence_labels.dart';

/// Evidence-backed suggestions (REC). Hidden when there are none or they can't load.
class RecommendationsSection extends ConsumerWidget {
  const RecommendationsSection({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final items = ref.watch(recommendationsProvider).valueOrNull;
    if (items == null || items.isEmpty) return const SizedBox.shrink();
    final l = AppLocalizations.of(context);
    return Column(
      key: const Key('recommendations'),
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SectionHeader(l.recsTitle),
        for (final r in items) RecommendationTile(item: r),
      ],
    );
  }
}

class RecommendationTile extends ConsumerStatefulWidget {
  const RecommendationTile({super.key, required this.item});

  final Recommendation item;

  @override
  ConsumerState<RecommendationTile> createState() => _RecommendationTileState();
}

class _RecommendationTileState extends ConsumerState<RecommendationTile> {
  bool _busy = false;
  String? _error;

  Future<void> _run(Future<void> Function() call, String done) async {
    final l = AppLocalizations.of(context);
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await call();
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(done)));
      ref
        ..invalidate(recommendationsProvider)
        ..invalidate(autopilotScoreProvider)
        ..invalidate(controlCenterProvider);
    } on ApiError catch (e) {
      if (!mounted) return;
      setState(() {
        _busy = false;
        _error =
            e.statusCode == 403
                ? l.recManagersOnly
                : localizedErrorMessage(l, e);
      });
    }
  }

  Future<void> _dismiss() async {
    final l = AppLocalizations.of(context);
    final reason = await showDialog<String>(
      context: context,
      builder: (_) => const _ReasonDialog(),
    );
    if (reason == null || reason.length < 3) return;
    await _run(
      () => ref.read(intelligenceApiProvider).reject(widget.item.id, reason),
      l.recDismissed,
    );
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final palette = AppPalette.of(context);
    final r = widget.item;
    final why = recommendationWhy(l, r);
    final impact = recommendationImpact(l, r);
    final canApply = r.actionType != 'none' && r.actionType != 'plan_upgrade';
    return Padding(
      key: Key('rec-${r.id}'),
      padding: const EdgeInsets.fromLTRB(
        AppSpace.s4,
        0,
        AppSpace.s4,
        AppSpace.s3,
      ),
      child: Card(
        margin: EdgeInsets.zero,
        child: Padding(
          padding: const EdgeInsets.all(AppSpace.s3),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(recommendationWhat(l, r), style: theme.textTheme.titleSmall),
              if (why != null) Text(why, style: theme.textTheme.bodySmall),
              const SizedBox(height: AppSpace.s1),
              Text(
                [
                  r.confidence >= 0.8
                      ? l.recConfidenceHigh
                      : l.recConfidenceMedium,
                  if (impact != null) impact,
                ].join(' · '),
                style: theme.textTheme.bodySmall?.copyWith(
                  color: palette.muted,
                ),
              ),
              if (_error != null)
                Padding(
                  padding: const EdgeInsets.only(top: AppSpace.s1),
                  child: Text(
                    _error!,
                    key: Key('rec-error-${r.id}'),
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: palette.danger,
                    ),
                  ),
                ),
              const SizedBox(height: AppSpace.s2),
              Row(
                children: [
                  if (canApply) ...[
                    FilledButton(
                      key: Key('rec-accept-${r.id}'),
                      onPressed:
                          _busy
                              ? null
                              : () => _run(
                                () => ref
                                    .read(intelligenceApiProvider)
                                    .accept(r.id),
                                l.recApplied,
                              ),
                      child: Text(l.recAccept),
                    ),
                    const SizedBox(width: AppSpace.s2),
                  ],
                  OutlinedButton(
                    key: Key('rec-dismiss-${r.id}'),
                    onPressed: _busy ? null : _dismiss,
                    child: Text(l.recDismiss),
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

class _ReasonDialog extends StatefulWidget {
  const _ReasonDialog();

  @override
  State<_ReasonDialog> createState() => _ReasonDialogState();
}

class _ReasonDialogState extends State<_ReasonDialog> {
  final _c = TextEditingController();

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return AlertDialog(
      title: Text(l.recDismissTitle),
      content: TextField(
        key: const Key('rec-reason'),
        controller: _c,
        maxLength: 300,
        decoration: InputDecoration(labelText: l.recDismissReason),
        onChanged: (_) => setState(() {}),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: Text(l.recCancel),
        ),
        FilledButton(
          key: const Key('rec-dismiss-confirm'),
          onPressed:
              _c.text.trim().length >= 3
                  ? () => Navigator.pop(context, _c.text.trim())
                  : null,
          child: Text(l.recDismiss),
        ),
      ],
    );
  }
}
