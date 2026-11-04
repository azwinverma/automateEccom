import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/errors/api_error.dart';
import '../../../core/errors/error_messages.dart';
import '../../../core/l10n/gen/app_localizations.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens.g.dart';
import '../../../design/widgets/state_views.dart';
import '../data/inbox_api.dart';

/// How often an open chat refreshes. Overridden in tests.
final threadPollIntervalProvider = Provider<Duration>(
  (ref) => const Duration(seconds: 5),
);

String draftFieldLabel(AppLocalizations l, String? field) => switch (field) {
  'product' => l.draftFieldProduct,
  'variant' => l.draftFieldVariant,
  'quantity' => l.draftFieldQuantity,
  'name' => l.draftFieldName,
  'phone' => l.draftFieldPhone,
  'district' => l.draftFieldDistrict,
  'municipality' => l.draftFieldMunicipality,
  'ward' => l.draftFieldWard,
  'area' => l.draftFieldArea,
  'payment' => l.draftFieldPayment,
  _ => field ?? '',
};

/// One chat. AI suggestions wait for the seller (Send / Edit / Discard); a
/// seller reply pauses the AI until it's handed back.
class ThreadScreen extends ConsumerStatefulWidget {
  const ThreadScreen({super.key, required this.conversationId});

  final String conversationId;

  @override
  ConsumerState<ThreadScreen> createState() => _ThreadScreenState();
}

class _ThreadScreenState extends ConsumerState<ThreadScreen> {
  final _text = TextEditingController();
  Timer? _poll;
  bool _busy = false;
  ApiError? _error;

  String get _id => widget.conversationId;

  @override
  void initState() {
    super.initState();
    _poll = Timer.periodic(ref.read(threadPollIntervalProvider), (_) {
      if (!mounted) return;
      ref
        ..invalidate(messagesProvider(_id))
        ..invalidate(conversationProvider(_id));
    });
    // Opening the chat clears its unread count (best effort).
    unawaited(ref.read(inboxApiProvider).markRead(_id).catchError((_) {}));
  }

  @override
  void dispose() {
    _poll?.cancel();
    _text.dispose();
    super.dispose();
  }

  Future<void> _run(Future<void> Function(InboxApi api) action) async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await action(ref.read(inboxApiProvider));
      ref
        ..invalidate(messagesProvider(_id))
        ..invalidate(conversationProvider(_id));
    } on Object catch (e) {
      if (mounted) setState(() => _error = asApiError(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _send() async {
    final text = _text.text.trim();
    if (text.isEmpty) return;
    await _run((api) => api.reply(_id, text));
    if (_error == null) _text.clear();
  }

  Future<void> _edit(ChatMessage m) async {
    final edited = await showDialog<String>(
      context: context,
      builder: (_) => _EditDialog(initial: m.text),
    );
    if (edited != null && edited.trim().isNotEmpty) {
      await _run((api) => api.approve(m.id, text: edited.trim()));
    }
  }

  Future<void> _handBack() async {
    await _run((api) => api.handBackToAi(_id));
    if (mounted && _error == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(AppLocalizations.of(context).threadHandedBack)),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final conv = ref.watch(conversationProvider(_id)).valueOrNull;
    final messages = ref.watch(messagesProvider(_id));
    return Scaffold(
      appBar: AppBar(
        title: Text(
          conv?.customerName ?? conv?.customerPhone ?? l.inboxCustomer,
          overflow: TextOverflow.ellipsis,
        ),
        actions: [
          if (conv?.humanHandoff ?? false)
            TextButton(
              key: const Key('hand-back'),
              onPressed: _busy ? null : _handBack,
              child: Text(l.threadHandBack),
            ),
        ],
      ),
      body: Column(
        children: [
          if (conv != null) _Banners(conversation: conv),
          Expanded(
            child: AsyncValueView<List<ChatMessage>>(
              value: messages,
              onRetry: () => ref.invalidate(messagesProvider(_id)),
              data:
                  (items) => ListView(
                    reverse: true,
                    padding: const EdgeInsets.all(AppSpace.s3),
                    children: [
                      for (final m in items.reversed)
                        _Bubble(
                          key: ValueKey(m.id),
                          message: m,
                          busy: _busy,
                          onSend: () => _run((api) => api.approve(m.id)),
                          onEdit: () => _edit(m),
                          onDiscard: () => _run((api) => api.discard(m.id)),
                          onRetry: () => _run((api) => api.retry(m.id)),
                        ),
                    ],
                  ),
            ),
          ),
          if (_error != null)
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: AppSpace.s3),
              child: InlineError(error: _error!),
            ),
          SafeArea(
            top: false,
            child: Padding(
              padding: const EdgeInsets.all(AppSpace.s2),
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      key: const Key('reply-field'),
                      controller: _text,
                      minLines: 1,
                      maxLines: 4,
                      maxLength: 4000,
                      textCapitalization: TextCapitalization.sentences,
                      decoration: InputDecoration(
                        hintText: l.threadReplyHint,
                        counterText: '',
                      ),
                    ),
                  ),
                  const SizedBox(width: AppSpace.s2),
                  IconButton.filled(
                    key: const Key('reply-send'),
                    tooltip: l.threadSend,
                    constraints: const BoxConstraints(
                      minWidth: 48,
                      minHeight: 48,
                    ),
                    onPressed: _busy ? null : _send,
                    icon: const Icon(Icons.send),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _Banners extends StatelessWidget {
  const _Banners({required this.conversation});

  final ConversationSummary conversation;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final palette = AppPalette.of(context);
    final c = conversation;
    final lines = <(String, Color, Widget?)>[
      if (c.escalated) (l.threadEscalatedBanner, palette.dangerSoft, null),
      if (c.humanHandoff && !c.escalated)
        (l.threadHumanBanner, palette.infoSoft, null),
      if (c.orderDraftStatus == 'collecting')
        (
          l.draftCollecting(draftFieldLabel(l, c.orderDraftAwaiting)),
          palette.automationSoft,
          null,
        ),
      if (c.orderDraftStatus == 'awaiting_confirmation')
        (l.draftAwaitingConfirmation, palette.automationSoft, null),
      if (c.orderDraftStatus == 'confirmed' && c.orderDraftOrderId != null)
        (
          l.draftConfirmed,
          palette.successSoft,
          TextButton(
            onPressed: () => context.push('/orders/${c.orderDraftOrderId}'),
            child: Text(l.exActionReviewOrder),
          ),
        ),
    ];
    return Column(
      children: [
        for (final (text, color, action) in lines)
          Container(
            key: Key('banner-$text'),
            width: double.infinity,
            color: color,
            padding: const EdgeInsets.symmetric(
              horizontal: AppSpace.s4,
              vertical: AppSpace.s2,
            ),
            child: Row(
              children: [
                Expanded(child: Text(text)),
                if (action != null) action,
              ],
            ),
          ),
      ],
    );
  }
}

class _Bubble extends StatelessWidget {
  const _Bubble({
    super.key,
    required this.message,
    required this.busy,
    required this.onSend,
    required this.onEdit,
    required this.onDiscard,
    required this.onRetry,
  });

  final ChatMessage message;
  final bool busy;
  final VoidCallback onSend;
  final VoidCallback onEdit;
  final VoidCallback onDiscard;
  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final palette = AppPalette.of(context);
    final m = message;
    final inbound = m.isInbound;
    final bg =
        inbound
            ? theme.colorScheme.surfaceContainerHighest
            : m.isSuggestion
            ? palette.automationSoft
            : theme.colorScheme.primaryContainer;
    final meta = [
      if (m.authorType == 'ai') l.threadByAi,
      if (m.isSuggestion) l.threadSuggestion,
      if (m.status == 'queued') l.threadSending,
      if (m.status == 'failed')
        '${l.threadFailed}${m.errorCode == null ? '' : ' · ${localizedErrorMessage(l, ApiError(kind: ApiErrorKind.http, code: m.errorCode!))}'}',
    ];
    return Align(
      alignment: inbound ? Alignment.centerLeft : Alignment.centerRight,
      child: ConstrainedBox(
        constraints: BoxConstraints(
          maxWidth: MediaQuery.sizeOf(context).width * 0.82,
        ),
        child: Container(
          key: Key('message-${m.id}'),
          margin: const EdgeInsets.symmetric(vertical: AppSpace.s1),
          padding: const EdgeInsets.all(AppSpace.s3),
          decoration: BoxDecoration(
            color: bg,
            borderRadius: BorderRadius.circular(AppRadius.lg),
            border:
                m.isSuggestion
                    ? Border.all(color: palette.automation)
                    : m.status == 'failed'
                    ? Border.all(color: palette.danger)
                    : null,
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(m.text),
              if (meta.isNotEmpty) ...[
                const SizedBox(height: AppSpace.s1),
                Text(
                  meta.join(' · '),
                  style: theme.textTheme.labelSmall?.copyWith(
                    color:
                        m.status == 'failed' ? palette.danger : palette.muted,
                  ),
                ),
              ],
              if (m.isSuggestion)
                Wrap(
                  spacing: AppSpace.s1,
                  children: [
                    TextButton(
                      key: Key('suggestion-send-${m.id}'),
                      onPressed: busy ? null : onSend,
                      child: Text(l.threadSuggestionSend),
                    ),
                    TextButton(
                      key: Key('suggestion-edit-${m.id}'),
                      onPressed: busy ? null : onEdit,
                      child: Text(l.threadSuggestionEdit),
                    ),
                    TextButton(
                      key: Key('suggestion-discard-${m.id}'),
                      onPressed: busy ? null : onDiscard,
                      child: Text(l.threadSuggestionDiscard),
                    ),
                  ],
                ),
              if (m.status == 'failed')
                TextButton(
                  key: Key('message-retry-${m.id}'),
                  onPressed: busy ? null : onRetry,
                  child: Text(l.threadRetry),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _EditDialog extends StatefulWidget {
  const _EditDialog({required this.initial});

  final String initial;

  @override
  State<_EditDialog> createState() => _EditDialogState();
}

class _EditDialogState extends State<_EditDialog> {
  late final _c = TextEditingController(text: widget.initial);

  @override
  void dispose() {
    _c.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return AlertDialog(
      title: Text(l.threadEditTitle),
      content: TextField(
        key: const Key('edit-field'),
        controller: _c,
        minLines: 3,
        maxLines: 8,
        maxLength: 4000,
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: Text(l.commonCancel),
        ),
        FilledButton(
          key: const Key('edit-send'),
          onPressed: () => Navigator.of(context).pop(_c.text),
          child: Text(l.threadSuggestionSend),
        ),
      ],
    );
  }
}
