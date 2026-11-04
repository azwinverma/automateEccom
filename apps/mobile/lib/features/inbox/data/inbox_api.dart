import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/api_call.dart';
import '../../../core/api/providers.dart';

DateTime? _date(Object? v) => v is String ? DateTime.tryParse(v) : null;

@immutable
class ConversationSummary {
  const ConversationSummary({
    required this.id,
    required this.provider,
    required this.status,
    required this.unreadCount,
    required this.escalated,
    required this.humanHandoff,
    this.customerName,
    this.customerPhone,
    this.escalationReason,
    this.lastIntent,
    this.lastMessageText,
    this.lastMessageDirection,
    this.lastMessageAt,
    this.orderDraftStatus,
    this.orderDraftAwaiting,
    this.orderDraftOrderId,
  });

  factory ConversationSummary.fromJson(Map<String, Object?> j) {
    final c = j['customer'] as Map<String, Object?>?;
    final last = j['last_message'] as Map<String, Object?>?;
    final draft = j['order_draft'] as Map<String, Object?>?;
    return ConversationSummary(
      id: j['id']! as String,
      provider: (j['provider'] as String?) ?? '',
      status: (j['status'] as String?) ?? 'open',
      unreadCount: (j['unread_count'] as num?)?.toInt() ?? 0,
      escalated: (j['escalated'] as bool?) ?? false,
      humanHandoff: (j['human_handoff'] as bool?) ?? false,
      customerName: c?['display_name'] as String?,
      customerPhone: c?['phone'] as String?,
      escalationReason: j['escalation_reason'] as String?,
      lastIntent: j['last_intent'] as String?,
      lastMessageText: last?['text'] as String?,
      lastMessageDirection: last?['direction'] as String?,
      lastMessageAt: _date(j['last_message_at']),
      orderDraftStatus: draft?['status'] as String?,
      orderDraftAwaiting: draft?['awaiting_field'] as String?,
      orderDraftOrderId: draft?['order_id'] as String?,
    );
  }

  final String id;
  final String provider;
  final String status;
  final int unreadCount;
  final bool escalated;
  final bool humanHandoff;
  final String? customerName;
  final String? customerPhone;
  final String? escalationReason;
  final String? lastIntent;
  final String? lastMessageText;
  final String? lastMessageDirection;
  final DateTime? lastMessageAt;

  /// Only in the detail response: the chat-to-order draft, if any.
  final String? orderDraftStatus;
  final String? orderDraftAwaiting;
  final String? orderDraftOrderId;
}

@immutable
class ChatMessage {
  const ChatMessage({
    required this.id,
    required this.direction,
    required this.authorType,
    required this.text,
    required this.status,
    this.errorCode,
    this.createdAt,
    this.grounding = const {},
  });

  factory ChatMessage.fromJson(Map<String, Object?> j) => ChatMessage(
    id: j['id']! as String,
    direction: (j['direction'] as String?) ?? 'in',
    authorType: (j['author_type'] as String?) ?? 'customer',
    text: (j['text'] as String?) ?? '',
    status: (j['status'] as String?) ?? 'received',
    errorCode: j['error_code'] as String?,
    createdAt: _date(j['created_at']),
    grounding: (j['grounding'] as Map<String, Object?>?) ?? const {},
  );

  final String id;

  /// in | out
  final String direction;

  /// customer | seller | ai | system
  final String authorType;
  final String text;

  /// received | suggested | queued | sent | failed | discarded
  final String status;
  final String? errorCode;
  final DateTime? createdAt;
  final Map<String, Object?> grounding;

  bool get isSuggestion => status == 'suggested';
  bool get isInbound => direction == 'in';
}

class InboxApi {
  InboxApi(this._dio);

  final Dio _dio;

  Future<List<ConversationSummary>> conversations() => apiCall(() async {
    final r = await _dio.get<Map<String, Object?>>(
      '/conversations',
      queryParameters: {'status': 'open'},
    );
    return itemsOf(r.data).map(ConversationSummary.fromJson).toList();
  });

  Future<ConversationSummary> conversation(String id) => apiCall(() async {
    final r = await _dio.get<Map<String, Object?>>('/conversations/$id');
    return ConversationSummary.fromJson(r.data!);
  });

  Future<List<ChatMessage>> messages(String id) => apiCall(() async {
    final r = await _dio.get<Map<String, Object?>>(
      '/conversations/$id/messages',
    );
    return itemsOf(r.data).map(ChatMessage.fromJson).toList();
  });

  Future<ChatMessage> reply(String conversationId, String text) => _message(
    () => _dio.post<Map<String, Object?>>(
      '/conversations/$conversationId/messages',
      data: {'text': text},
    ),
  );

  /// Sends an AI suggestion, optionally edited by the seller first.
  Future<ChatMessage> approve(String messageId, {String? text}) => _message(
    () => _dio.post<Map<String, Object?>>(
      '/messages/$messageId/approve',
      data: {if (text != null) 'text': text},
    ),
  );

  Future<void> discard(String messageId) =>
      apiCall(() => _dio.post<void>('/messages/$messageId/discard'));

  Future<ChatMessage> retry(String messageId) => _message(
    () => _dio.post<Map<String, Object?>>('/messages/$messageId/retry'),
  );

  Future<void> handBackToAi(String conversationId) => apiCall(
    () => _dio.patch<Map<String, Object?>>(
      '/conversations/$conversationId',
      data: {'human_handoff': false},
    ),
  );

  Future<void> markRead(String conversationId) => apiCall(
    () =>
        _dio.post<Map<String, Object?>>('/conversations/$conversationId/read'),
  );

  Future<ChatMessage> _message(
    Future<Response<Map<String, Object?>>> Function() run,
  ) => apiCall(() async => ChatMessage.fromJson((await run()).data!));
}

final inboxApiProvider = Provider<InboxApi>(
  (ref) => InboxApi(ref.watch(dioProvider)),
);

final conversationsProvider =
    FutureProvider.autoDispose<List<ConversationSummary>>(
      (ref) => ref.watch(inboxApiProvider).conversations(),
    );

final conversationProvider = FutureProvider.autoDispose
    .family<ConversationSummary, String>(
      (ref, id) => ref.watch(inboxApiProvider).conversation(id),
    );

final messagesProvider = FutureProvider.autoDispose
    .family<List<ChatMessage>, String>(
      (ref, id) => ref.watch(inboxApiProvider).messages(id),
    );
