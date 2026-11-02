import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/errors/api_error.dart';
import '../../../core/l10n/formatters.dart';
import '../../../core/l10n/gen/app_localizations.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens.g.dart';
import '../../../design/widgets/state_views.dart';
import '../../channels/data/channels_api.dart';
import '../../channels/presentation/reconnect_sheet.dart';
import '../../studio/presentation/widgets/issue_list.dart';
import '../data/content_api.dart';

/// Loads posts by id. No single-post endpoint exists, so the calendar list
/// is fetched and filtered (API gap).
final postsByIdsProvider = FutureProvider.autoDispose
    .family<List<ContentPost>, String>((ref, key) async {
      final ids = key.split(',').where((s) => s.isNotEmpty).toSet();
      final all = await ref.watch(contentApiProvider).list();
      return all.where((p) => ids.contains(p.id)).toList(growable: false);
    });

String postStatusLabel(AppLocalizations l, ContentPost p, String lang) =>
    switch (p.status) {
      'draft' => l.postStatusDraft,
      'pending_approval' => l.postStatusPendingApproval,
      'approved' => l.postStatusApproved,
      'scheduled' => l.postStatusScheduled(
        p.scheduledAt == null ? '' : Formatters.dateTime(p.scheduledAt!, lang),
      ),
      'publishing' => l.postStatusPublishing,
      'published' => l.postStatusPublished,
      'failed' => l.postStatusFailed,
      'cancelled' => l.postStatusCancelled,
      _ => p.status,
    };

/// Per-channel post drafts: edit caption → submit → (approve) → publish now
/// or schedule.
class PostsScreen extends ConsumerWidget {
  const PostsScreen({super.key, required this.postIds});

  final List<String> postIds;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final key = postIds.join(',');
    final posts = ref.watch(postsByIdsProvider(key));
    final channels = ref.watch(channelsProvider).valueOrNull ?? const [];
    return Scaffold(
      appBar: AppBar(title: Text(l.postsTitle)),
      body: RefreshIndicator(
        onRefresh: () => ref.refresh(postsByIdsProvider(key).future),
        child: ListView(
          padding: const EdgeInsets.only(bottom: AppSpace.s8),
          children: [
            AsyncValueView<List<ContentPost>>(
              value: posts,
              onRetry: () => ref.invalidate(postsByIdsProvider(key)),
              isEmpty: (p) => p.isEmpty,
              empty: EmptyState(
                title: postIds.length == 1 ? l.postNotFound : l.postsEmpty,
              ),
              data:
                  (items) => Column(
                    children: [
                      for (final p in items) ...[
                        PostCard(
                          key: ValueKey(p.id),
                          post: p,
                          channel:
                              channels
                                  .where((c) => c.id == p.connectionId)
                                  .firstOrNull,
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
}

class PostCard extends ConsumerStatefulWidget {
  const PostCard({super.key, required this.post, this.channel});

  final ContentPost post;
  final ChannelConnection? channel;

  @override
  ConsumerState<PostCard> createState() => _PostCardState();
}

class _PostCardState extends ConsumerState<PostCard> {
  late ContentPost _post = widget.post;
  late final TextEditingController _caption = TextEditingController(
    text: widget.post.caption,
  );
  bool _busy = false;
  ApiError? _error;

  @override
  void dispose() {
    _caption.dispose();
    super.dispose();
  }

  bool get _editable =>
      const {'draft', 'pending_approval', 'approved'}.contains(_post.status);
  bool get _dirty => _caption.text.trim() != _post.caption.trim();

  Future<void> _run(Future<ContentPost> Function(ContentApi api) action) async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final p = await action(ref.read(contentApiProvider));
      setState(() {
        _post = p;
        if (!_dirty || _caption.text.isEmpty) _caption.text = p.caption;
      });
    } on Object catch (e) {
      if (mounted) setState(() => _error = asApiError(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _saveCaption() async {
    await _run(
      (api) => api.updateCaption(_post.id, _caption.text.trim(), _post.version),
    );
    if (mounted && _error == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(AppLocalizations.of(context).postCaptionSaved)),
      );
    }
  }

  Future<void> _schedule() async {
    final now = DateTime.now();
    final date = await showDatePicker(
      context: context,
      firstDate: now,
      lastDate: now.add(const Duration(days: 90)),
      initialDate: now,
    );
    if (date == null || !mounted) return;
    final time = await showTimePicker(
      context: context,
      initialTime: TimeOfDay.fromDateTime(now.add(const Duration(hours: 1))),
    );
    if (time == null) return;
    final at = DateTime(
      date.year,
      date.month,
      date.day,
      time.hour,
      time.minute,
    );
    await _run((api) => api.schedule(_post.id, at: at));
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final palette = AppPalette.of(context);
    final lang = Localizations.localeOf(context).languageCode;
    final p = _post;
    final statusColor = switch (p.status) {
      'published' || 'approved' => palette.success,
      'failed' => palette.danger,
      'pending_approval' => palette.automation,
      _ => theme.colorScheme.onSurfaceVariant,
    };

    final actions = <Widget>[
      if (_editable && _dirty)
        OutlinedButton(
          onPressed: _busy ? null : _saveCaption,
          child: Text(l.postSaveCaption),
        ),
      if (p.status == 'draft' && !_dirty)
        FilledButton(
          key: Key('post-submit-${p.id}'),
          onPressed: _busy ? null : () => _run((api) => api.submit(p.id)),
          child: Text(l.postSubmit),
        ),
      if (p.status == 'pending_approval' && !_dirty)
        FilledButton(
          key: Key('post-approve-${p.id}'),
          onPressed: _busy ? null : () => _run((api) => api.approve(p.id)),
          child: Text(l.postApprove),
        ),
      if ((p.status == 'approved' || p.status == 'failed') && !_dirty) ...[
        FilledButton(
          key: Key('post-now-${p.id}'),
          onPressed: _busy ? null : () => _run((api) => api.schedule(p.id)),
          child: Text(l.postPublishNow),
        ),
        OutlinedButton(
          onPressed: _busy ? null : _schedule,
          child: Text(l.postSchedule),
        ),
      ],
    ];

    return Container(
      color: theme.colorScheme.surface,
      padding: const EdgeInsets.all(AppSpace.s4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  widget.channel?.label ?? '—',
                  style: theme.textTheme.titleSmall,
                ),
              ),
              Text(
                postStatusLabel(l, p, lang),
                key: Key('post-status-${p.id}'),
                style: theme.textTheme.labelMedium?.copyWith(
                  color: statusColor,
                ),
              ),
            ],
          ),
          if (p.status == 'pending_approval')
            Padding(
              padding: const EdgeInsets.only(top: AppSpace.s1),
              child: Text(
                l.postNeedsApprovalNote,
                style: theme.textTheme.bodySmall?.copyWith(
                  color: palette.automation,
                ),
              ),
            ),
          if (p.issues.isNotEmpty) ...[
            const SizedBox(height: AppSpace.s2),
            IssueList(issues: p.issues),
          ],
          const SizedBox(height: AppSpace.s3),
          TextField(
            controller: _caption,
            enabled: _editable && !_busy,
            minLines: 3,
            maxLines: 10,
            onChanged: (_) => setState(() {}),
            decoration: InputDecoration(
              labelText: l.fieldCaption,
              alignLabelWithHint: true,
            ),
          ),
          if (_error != null) ...[
            const SizedBox(height: AppSpace.s2),
            InlineError(error: _error!),
            if (_error!.code == 'permission_denied')
              Text(l.postNoApprovePermission, style: theme.textTheme.bodySmall),
            if (_error!.code == 'reconnect_required')
              TextButton(
                onPressed:
                    () => showReconnectSheet(
                      context,
                      connectionId: p.connectionId,
                      channelName: widget.channel?.label,
                    ),
                child: Text(l.channelReconnect),
              ),
          ],
          if (actions.isNotEmpty) ...[
            const SizedBox(height: AppSpace.s3),
            Wrap(
              spacing: AppSpace.s2,
              runSpacing: AppSpace.s2,
              children: actions,
            ),
          ],
        ],
      ),
    );
  }
}
