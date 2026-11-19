import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/errors/api_error.dart';
import '../../../core/errors/error_messages.dart';
import '../../../core/l10n/gen/app_localizations.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens.g.dart';
import '../../../design/widgets/state_views.dart';
import '../data/intelligence_api.dart';
import 'intelligence_labels.dart';

/// UX-021 Commerce Memory: what Nivaro has learned, with confirm / reject.
/// (Correcting a value is web-only for now.)
class MemoryScreen extends ConsumerWidget {
  const MemoryScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final facts = ref.watch(memoryFactsProvider);
    return Scaffold(
      appBar: AppBar(title: Text(l.memTitle)),
      body: RefreshIndicator(
        onRefresh: () => ref.refresh(memoryFactsProvider.future),
        child: AsyncValueView<List<MemoryFact>>(
          value: facts,
          onRetry: () => ref.invalidate(memoryFactsProvider),
          data:
              (items) => ListView(
                padding: const EdgeInsets.all(AppSpace.s4),
                children: [
                  Text(l.memIntro, style: theme.textTheme.bodySmall),
                  const SizedBox(height: AppSpace.s3),
                  if (items.isEmpty)
                    Text(
                      l.memEmpty,
                      key: const Key('memory-empty'),
                      style: theme.textTheme.bodyMedium,
                    ),
                  for (final f in items) MemoryFactTile(fact: f),
                ],
              ),
        ),
      ),
    );
  }
}

class MemoryFactTile extends ConsumerStatefulWidget {
  const MemoryFactTile({super.key, required this.fact});

  final MemoryFact fact;

  @override
  ConsumerState<MemoryFactTile> createState() => _MemoryFactTileState();
}

class _MemoryFactTileState extends ConsumerState<MemoryFactTile> {
  bool _busy = false;
  String? _error;

  Future<void> _run(Future<void> Function() call) async {
    final l = AppLocalizations.of(context);
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await call();
      if (!mounted) return;
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(l.memDone)));
      ref.invalidate(memoryFactsProvider);
    } on ApiError catch (e) {
      if (!mounted) return;
      setState(() {
        _busy = false;
        _error =
            e.statusCode == 403
                ? l.memManagersOnly
                : localizedErrorMessage(l, e);
      });
    }
  }

  Future<void> _reject() async {
    final note = await showDialog<String>(
      context: context,
      builder: (_) => const _RejectDialog(),
    );
    if (note == null || note.length < 3) return;
    await _run(
      () => ref.read(intelligenceApiProvider).rejectFact(widget.fact.id, note),
    );
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final p = AppPalette.of(context);
    final f = widget.fact;
    final window =
        f.evidence.map((e) => e['window_days']).whereType<num>().firstOrNull;
    final muted = theme.textTheme.bodySmall?.copyWith(color: p.muted);
    return Padding(
      key: Key('fact-${f.id}'),
      padding: const EdgeInsets.only(bottom: AppSpace.s3),
      child: Card(
        margin: EdgeInsets.zero,
        child: Padding(
          padding: const EdgeInsets.all(AppSpace.s3),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(memoryFactLabel(l, f), style: theme.textTheme.bodyMedium),
              const SizedBox(height: AppSpace.s1),
              Text(
                [
                  if (f.source == 'merchant')
                    l.memSellerVersion
                  else
                    l.memConfidence((f.confidence * 100).round().toString()),
                  if (window != null) l.memWindow(window.toInt().toString()),
                  l.memVersion(f.version),
                ].join(' · '),
                style: muted,
              ),
              if (f.confirmed)
                Text(
                  l.memConfirmed,
                  key: Key('fact-confirmed-${f.id}'),
                  style: theme.textTheme.bodySmall?.copyWith(color: p.success),
                ),
              if (_error != null)
                Text(
                  _error!,
                  key: Key('fact-error-${f.id}'),
                  style: theme.textTheme.bodySmall?.copyWith(color: p.danger),
                ),
              const SizedBox(height: AppSpace.s2),
              Wrap(
                spacing: AppSpace.s2,
                runSpacing: AppSpace.s2,
                children: [
                  if (!f.confirmed)
                    FilledButton(
                      key: Key('fact-confirm-${f.id}'),
                      onPressed:
                          _busy
                              ? null
                              : () => _run(
                                () => ref
                                    .read(intelligenceApiProvider)
                                    .confirmFact(f.id),
                              ),
                      child: Text(l.memConfirm),
                    ),
                  OutlinedButton(
                    key: Key('fact-reject-${f.id}'),
                    onPressed: _busy ? null : _reject,
                    child: Text(l.memReject),
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

class _RejectDialog extends StatefulWidget {
  const _RejectDialog();

  @override
  State<_RejectDialog> createState() => _RejectDialogState();
}

class _RejectDialogState extends State<_RejectDialog> {
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
      title: Text(l.memRejectTitle),
      content: TextField(
        key: const Key('fact-reason'),
        controller: _c,
        maxLength: 300,
        decoration: InputDecoration(labelText: l.memRejectNote),
        onChanged: (_) => setState(() {}),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: Text(l.memCancel),
        ),
        FilledButton(
          key: const Key('fact-reject-confirm'),
          onPressed:
              _c.text.trim().length >= 3
                  ? () => Navigator.pop(context, _c.text.trim())
                  : null,
          child: Text(l.memReject),
        ),
      ],
    );
  }
}
