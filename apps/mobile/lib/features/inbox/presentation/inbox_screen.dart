import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/l10n/formatters.dart';
import '../../../core/l10n/gen/app_localizations.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens.g.dart';
import '../../../design/widgets/state_views.dart';
import '../data/inbox_api.dart';

/// Open customer chats, newest first. "Needs you" marks chats the AI handed
/// over; the unread count is what the seller hasn't opened yet.
class InboxScreen extends ConsumerWidget {
  const InboxScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final chats = ref.watch(conversationsProvider);
    return Scaffold(
      appBar: AppBar(title: Text(l.inboxTitle)),
      body: RefreshIndicator(
        onRefresh: () => ref.refresh(conversationsProvider.future),
        child: ListView(
          padding: const EdgeInsets.only(bottom: AppSpace.s8),
          children: [
            AsyncValueView<List<ConversationSummary>>(
              value: chats,
              onRetry: () => ref.invalidate(conversationsProvider),
              isEmpty: (c) => c.isEmpty,
              empty: EmptyState(
                icon: Icons.chat_bubble_outline,
                title: l.inboxEmpty,
                body: l.inboxEmptyBody,
              ),
              data:
                  (items) => Column(
                    children: [
                      for (final c in items) ...[
                        ConversationTile(conversation: c),
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

class ConversationTile extends ConsumerWidget {
  const ConversationTile({super.key, required this.conversation});

  final ConversationSummary conversation;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final palette = AppPalette.of(context);
    final lang = Localizations.localeOf(context).languageCode;
    final c = conversation;
    final last = c.lastMessageText ?? '';
    final preview = c.lastMessageDirection == 'out' ? l.inboxYou(last) : last;
    final unread = c.unreadCount > 0;
    return ListTile(
      key: Key('conversation-${c.id}'),
      minVerticalPadding: AppSpace.s3,
      title: Row(
        children: [
          Expanded(
            child: Text(
              c.customerName ?? c.customerPhone ?? l.inboxCustomer,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style:
                  unread ? const TextStyle(fontWeight: FontWeight.w700) : null,
            ),
          ),
          if (c.escalated) ...[
            const SizedBox(width: AppSpace.s2),
            Container(
              key: const Key('needs-you'),
              padding: const EdgeInsets.symmetric(
                horizontal: AppSpace.s2,
                vertical: 2,
              ),
              decoration: BoxDecoration(
                color: palette.dangerSoft,
                borderRadius: BorderRadius.circular(AppRadius.sm),
              ),
              child: Text(
                l.inboxNeedsYou,
                style: theme.textTheme.labelSmall?.copyWith(
                  color: palette.danger,
                ),
              ),
            ),
          ],
        ],
      ),
      subtitle: Text(preview, maxLines: 2, overflow: TextOverflow.ellipsis),
      trailing: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        crossAxisAlignment: CrossAxisAlignment.end,
        children: [
          if (c.lastMessageAt != null)
            Text(
              Formatters.date(c.lastMessageAt!, lang),
              style: theme.textTheme.labelSmall?.copyWith(color: palette.muted),
            ),
          if (unread) ...[
            const SizedBox(height: AppSpace.s1),
            Badge(
              key: const Key('unread'),
              label: Text(Formatters.integer(c.unreadCount, lang)),
            ),
          ],
        ],
      ),
      onTap: () async {
        await context.push('/inbox/${c.id}');
        ref.invalidate(conversationsProvider);
      },
    );
  }
}
