import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/errors/api_error.dart';
import '../../../core/l10n/formatters.dart';
import '../../../core/l10n/gen/app_localizations.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens.g.dart';
import '../../../design/widgets/state_views.dart';
import '../data/intelligence_api.dart';

/// CGN-001 results for a published post: reach (from the channel or typed in
/// by the seller), chats and orders it brought, sales and margin. No plan
/// needed. "Add results" copies numbers from the app's own insights.
class PostResultsSection extends ConsumerWidget {
  const PostResultsSection({super.key, required this.postId});

  final String postId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final res = ref.watch(postResultsProvider(postId));
    if (res.hasError) return const SizedBox.shrink();
    final r = res.valueOrNull;
    return Column(
      key: Key('post-results-$postId'),
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (r != null) PostResultsView(results: r),
        Align(
          alignment: AlignmentDirectional.centerStart,
          child: TextButton.icon(
            key: Key('post-add-results-$postId'),
            onPressed: () => showAddResultsSheet(context, postId),
            icon: const Icon(Icons.add, size: 18),
            label: Text(l.prAdd),
          ),
        ),
      ],
    );
  }
}

String _orders(double v) =>
    v == v.roundToDouble() ? v.toInt().toString() : v.toStringAsFixed(1);

class PostResultsView extends StatelessWidget {
  const PostResultsView({super.key, required this.results});

  final PostResults results;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final p = AppPalette.of(context);
    final lang = Localizations.localeOf(context).languageCode;
    final r = results;
    String money(int v) => Formatters.money(v, r.currency, lang);
    String n(int v) => Formatters.integer(v, lang);
    final reach = [
      if (r.views != null) l.prViews(n(r.views!)),
      if (r.engagements != null) l.prEngagements(n(r.engagements!)),
      if (r.clicks != null) l.prClicks(n(r.clicks!)),
    ];
    final muted = theme.textTheme.bodySmall?.copyWith(color: p.muted);
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(top: AppSpace.s2),
      padding: const EdgeInsets.all(AppSpace.s3),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerLow,
        borderRadius: BorderRadius.circular(AppRadius.md),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            l.prTitle(r.windowDays.toString()),
            style: theme.textTheme.titleSmall,
          ),
          if (!r.windowComplete)
            Text(l.prWindowOpen(r.windowDays.toString()), style: muted),
          const SizedBox(height: AppSpace.s1),
          Text(
            [
              l.prChats(n(r.inquiries)),
              l.prOrders(_orders(r.orders)),
              l.prRevenue(money(r.revenueMinor)),
            ].join(' · '),
            key: Key('post-results-commerce-${r.postId}'),
            style: theme.textTheme.bodyMedium,
          ),
          Text(
            r.contributionMinor == null
                ? l.prCostNotSet
                : l.prMargin(money(r.contributionMinor!)),
            style: muted,
          ),
          const SizedBox(height: AppSpace.s1),
          if (reach.isEmpty)
            Text(l.prNoNumbers, style: muted)
          else ...[
            Text(reach.join(' · '), style: theme.textTheme.bodySmall),
            Text(
              r.source == 'manual' ? l.prSourceManual : l.prSourceChannel,
              style: muted,
            ),
          ],
        ],
      ),
    );
  }
}

Future<void> showAddResultsSheet(BuildContext context, String postId) =>
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (_) => AddResultsSheet(postId: postId),
    );

class AddResultsSheet extends ConsumerStatefulWidget {
  const AddResultsSheet({super.key, required this.postId});

  final String postId;

  @override
  ConsumerState<AddResultsSheet> createState() => _AddResultsSheetState();
}

class _AddResultsSheetState extends ConsumerState<AddResultsSheet> {
  static const _fields = [
    'views',
    'likes',
    'comments',
    'shares',
    'saves',
    'clicks',
  ];
  final _c = {for (final f in _fields) f: TextEditingController()};
  final _form = GlobalKey<FormState>();
  bool _busy = false;
  ApiError? _error;
  bool _empty = false;

  @override
  void dispose() {
    for (final c in _c.values) {
      c.dispose();
    }
    super.dispose();
  }

  String _label(AppLocalizations l, String f) => switch (f) {
    'views' => l.prFieldViews,
    'likes' => l.prFieldLikes,
    'comments' => l.prFieldComments,
    'shares' => l.prFieldShares,
    'saves' => l.prFieldSaves,
    _ => l.prFieldClicks,
  };

  Future<void> _save() async {
    if (!(_form.currentState?.validate() ?? false)) return;
    final counts = <String, int>{
      for (final f in _fields)
        if (_c[f]!.text.trim().isNotEmpty) f: int.parse(_c[f]!.text.trim()),
    };
    if (counts.isEmpty) {
      setState(() => _empty = true);
      return;
    }
    final l = AppLocalizations.of(context);
    setState(() {
      _busy = true;
      _error = null;
      _empty = false;
    });
    try {
      await ref
          .read(intelligenceApiProvider)
          .addPostResults(widget.postId, counts);
      if (!mounted) return;
      ref.invalidate(postResultsProvider(widget.postId));
      Navigator.of(context).pop();
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(l.prSaved)));
    } on Object catch (e) {
      if (mounted) setState(() => _error = asApiError(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final p = AppPalette.of(context);
    return Padding(
      padding: EdgeInsets.only(
        left: AppSpace.s4,
        right: AppSpace.s4,
        bottom: MediaQuery.viewInsetsOf(context).bottom + AppSpace.s4,
      ),
      child: Form(
        key: _form,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(l.prAddTitle, style: theme.textTheme.titleMedium),
              const SizedBox(height: AppSpace.s1),
              Text(
                l.prAddHint,
                style: theme.textTheme.bodySmall?.copyWith(color: p.muted),
              ),
              const SizedBox(height: AppSpace.s3),
              Wrap(
                spacing: AppSpace.s3,
                runSpacing: AppSpace.s3,
                children: [
                  for (final f in _fields)
                    SizedBox(
                      width: 140,
                      child: TextFormField(
                        key: Key('results-$f'),
                        controller: _c[f],
                        enabled: !_busy,
                        keyboardType: TextInputType.number,
                        inputFormatters: [
                          FilteringTextInputFormatter.allow(RegExp(r'[0-9]')),
                        ],
                        decoration: InputDecoration(labelText: _label(l, f)),
                        validator: (v) {
                          final t = (v ?? '').trim();
                          if (t.isEmpty) return null;
                          final x = int.tryParse(t);
                          return x == null || x < 0 || x > 1000000000
                              ? l.prInvalid
                              : null;
                        },
                      ),
                    ),
                ],
              ),
              if (_empty) ...[
                const SizedBox(height: AppSpace.s2),
                Text(
                  l.prNeedOne,
                  key: const Key('results-need-one'),
                  style: theme.textTheme.bodySmall?.copyWith(color: p.danger),
                ),
              ],
              if (_error != null) ...[
                const SizedBox(height: AppSpace.s2),
                InlineError(error: _error!),
              ],
              const SizedBox(height: AppSpace.s4),
              FilledButton(
                key: const Key('results-save'),
                onPressed: _busy ? null : _save,
                child: Text(l.prSave),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
