import 'dart:convert';

import 'package:commerce_os_seller/features/inbox/presentation/inbox_screen.dart';
import 'package:commerce_os_seller/features/inbox/presentation/thread_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import '../helpers/fake_adapter.dart';
import '../helpers/test_app.dart';

Map<String, Object?> conv({
  bool handoff = false,
  bool escalated = false,
  String? draft,
}) => {
  'id': 'cv1',
  'provider': 'sandbox_channel',
  'status': 'open',
  'customer': {'id': 'c1', 'display_name': 'Bikash Rai', 'phone': null},
  'unread_count': 2,
  'escalated': escalated,
  'escalation_reason': escalated ? 'complaint' : null,
  'human_handoff': handoff,
  'last_message_at': '2026-11-03T08:00:00Z',
  'last_message': {
    'text': 'Dhaka kurta XL cha?',
    'direction': 'in',
    'status': 'received',
  },
  'order_draft':
      draft == null
          ? null
          : {
            'id': 'd1',
            'status': draft,
            'fields': <String, Object?>{},
            'awaiting_field': 'phone',
            'order_id': null,
          },
};

Map<String, Object?> msg(
  String id,
  String text, {
  String dir = 'in',
  String author = 'customer',
  String status = 'received',
  String? error,
}) => {
  'id': id,
  'direction': dir,
  'author_type': author,
  'text': text,
  'status': status,
  'error_code': error,
  'grounding': <String, Object?>{},
  'created_at': '2026-11-03T08:00:00Z',
};

Map<String, Object?> _body(Object? data) =>
    (data is String ? jsonDecode(data) : data) as Map<String, Object?>? ??
    const {};

List<GoRoute> _routes() => [
  GoRoute(path: '/inbox', builder: (_, __) => const InboxScreen()),
  GoRoute(
    path: '/inbox/:id',
    builder: (_, s) => ThreadScreen(conversationId: s.pathParameters['id']!),
  ),
];

final _noPoll = threadPollIntervalProvider.overrideWithValue(
  const Duration(hours: 1),
);

void main() {
  testWidgets('list shows needs-you, unread and opens the chat', (
    tester,
  ) async {
    final adapter = FakeAdapter((o) {
      if (o.path == '/conversations') {
        return FakeResponse(200, {
          'items': [conv(escalated: true)],
          'next_cursor': null,
        });
      }
      if (o.path == '/conversations/cv1') {
        return FakeResponse(200, conv(escalated: true));
      }
      if (o.path == '/conversations/cv1/messages') {
        return FakeResponse(200, {
          'items': [msg('m1', 'Dhaka kurta XL cha?')],
          'next_cursor': null,
        });
      }
      if (o.path == '/conversations/cv1/read') return FakeResponse(200, conv());
      return const FakeResponse(404);
    });
    await pumpRouted(
      tester,
      initialLocation: '/inbox',
      routes: _routes(),
      adapter: adapter,
      overrides: [_noPoll],
    );
    expect(adapter.requests.first.queryParameters['status'], 'open');
    expect(find.byKey(const Key('needs-you')), findsOneWidget);
    expect(find.byKey(const Key('unread')), findsOneWidget);
    await tester.tap(find.byKey(const Key('conversation-cv1')));
    await tester.pumpAndSettle();
    expect(find.text('The AI handed this chat to you.'), findsOneWidget);
    expect(adapter.countPath('/conversations/cv1/read'), 1);
  });

  testWidgets('AI suggestion: send, edit then send, discard', (tester) async {
    var messages = [
      msg('m1', 'Dhaka kurta M kati?'),
      msg(
        's1',
        'Dhaka Kurta (M): Rs 2,450. In stock.',
        dir: 'out',
        author: 'ai',
        status: 'suggested',
      ),
      msg(
        's2',
        'Would you like to order?',
        dir: 'out',
        author: 'ai',
        status: 'suggested',
      ),
    ];
    final adapter = FakeAdapter((o) {
      if (o.path == '/conversations/cv1') {
        return FakeResponse(200, conv(draft: 'collecting'));
      }
      if (o.path == '/conversations/cv1/messages') {
        return FakeResponse(200, {'items': messages, 'next_cursor': null});
      }
      if (o.path == '/conversations/cv1/read') return FakeResponse(200, conv());
      if (o.path == '/messages/s1/approve') {
        final text =
            _body(o.data)['text'] as String? ??
            'Dhaka Kurta (M): Rs 2,450. In stock.';
        messages = [
          messages[0],
          msg('s1', text, dir: 'out', author: 'ai', status: 'queued'),
          messages[2],
        ];
        return FakeResponse(200, messages[1]);
      }
      if (o.path == '/messages/s2/discard') {
        messages = messages.where((m) => m['id'] != 's2').toList();
        return const FakeResponse(204);
      }
      return const FakeResponse(404);
    });
    await pumpRouted(
      tester,
      initialLocation: '/inbox/cv1',
      routes: _routes(),
      adapter: adapter,
      overrides: [_noPoll],
    );
    expect(
      find.text('Taking an order: waiting for phone number'),
      findsOneWidget,
    );
    expect(find.textContaining('AI suggestion'), findsNWidgets(2));

    await tester.tap(find.byKey(const Key('suggestion-edit-s1')));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const Key('edit-field')),
      'Rs 2,450. Free delivery in Pokhara!',
    );
    await tester.tap(find.byKey(const Key('edit-send')));
    await tester.pumpAndSettle();
    final approve = adapter.requests.singleWhere(
      (r) => r.path == '/messages/s1/approve',
    );
    expect(_body(approve.data)['text'], 'Rs 2,450. Free delivery in Pokhara!');
    expect(find.text('Rs 2,450. Free delivery in Pokhara!'), findsOneWidget);
    expect(find.textContaining('Sending'), findsOneWidget);

    await tester.tap(find.byKey(const Key('suggestion-discard-s2')));
    await tester.pumpAndSettle();
    expect(adapter.countPath('/messages/s2/discard'), 1);
    expect(find.text('Would you like to order?'), findsNothing);
  });

  testWidgets('seller reply, failed message retry, hand back to AI', (
    tester,
  ) async {
    var handoff = false;
    var messages = [
      msg('m1', 'hello?'),
      msg(
        'f1',
        'Hi! Which size?',
        dir: 'out',
        author: 'ai',
        status: 'failed',
        error: 'reconnect_required',
      ),
    ];
    final adapter = FakeAdapter((o) {
      if (o.path == '/conversations/cv1' && o.method == 'GET') {
        return FakeResponse(200, conv(handoff: handoff));
      }
      if (o.path == '/conversations/cv1' && o.method == 'PATCH') {
        expect(_body(o.data)['human_handoff'], false);
        handoff = false;
        return FakeResponse(200, conv());
      }
      if (o.path == '/conversations/cv1/messages' && o.method == 'GET') {
        return FakeResponse(200, {'items': messages, 'next_cursor': null});
      }
      if (o.path == '/conversations/cv1/messages' && o.method == 'POST') {
        handoff = true;
        final m = msg(
          'r1',
          _body(o.data)['text']! as String,
          dir: 'out',
          author: 'seller',
          status: 'queued',
        );
        messages = [...messages, m];
        return FakeResponse(201, m);
      }
      if (o.path == '/messages/f1/retry') {
        messages = [
          messages[0],
          msg(
            'f1',
            'Hi! Which size?',
            dir: 'out',
            author: 'ai',
            status: 'queued',
          ),
          ...messages.skip(2),
        ];
        return FakeResponse(200, messages[1]);
      }
      if (o.path == '/conversations/cv1/read') return FakeResponse(200, conv());
      return const FakeResponse(404);
    });
    await pumpRouted(
      tester,
      initialLocation: '/inbox/cv1',
      routes: _routes(),
      adapter: adapter,
      overrides: [_noPoll],
    );

    expect(find.textContaining('Not sent'), findsOneWidget);
    await tester.tap(find.byKey(const Key('message-retry-f1')));
    await tester.pumpAndSettle();
    expect(adapter.countPath('/messages/f1/retry'), 1);
    expect(find.textContaining('Not sent'), findsNothing);

    await tester.enterText(
      find.byKey(const Key('reply-field')),
      'Send me a photo please',
    );
    await tester.tap(find.byKey(const Key('reply-send')));
    await tester.pumpAndSettle();
    expect(find.text('Send me a photo please'), findsOneWidget);
    expect(
      find.text("You're handling this chat. The AI is paused."),
      findsOneWidget,
    );
    final field = tester.widget<TextField>(
      find.byKey(const Key('reply-field')),
    );
    expect(field.controller!.text, isEmpty);

    await tester.tap(find.byKey(const Key('hand-back')));
    await tester.pumpAndSettle();
    expect(find.text('The AI will answer new messages again.'), findsOneWidget);
    expect(find.byKey(const Key('hand-back')), findsNothing);
  });

  testWidgets('Nepali thread renders at 360dp without overflow', (
    tester,
  ) async {
    final adapter = FakeAdapter((o) {
      if (o.path == '/conversations/cv1') {
        return FakeResponse(200, conv(draft: 'awaiting_confirmation'));
      }
      if (o.path == '/conversations/cv1/messages') {
        return FakeResponse(200, {
          'items': [
            msg('m1', 'ढाका कुर्ता M को मूल्य कति हो?'),
            msg(
              's1',
              'ढाका कुर्ता (M): रु 2,450।',
              dir: 'out',
              author: 'ai',
              status: 'suggested',
            ),
          ],
          'next_cursor': null,
        });
      }
      if (o.path == '/conversations/cv1/read') return FakeResponse(200, conv());
      return const FakeResponse(404);
    });
    await pumpRouted(
      tester,
      initialLocation: '/inbox/cv1',
      routes: _routes(),
      adapter: adapter,
      locale: const Locale('ne'),
      overrides: [_noPoll],
    );
    expect(
      find.text("अर्डर विवरण पठाइयो। ग्राहकको 'हो' कुर्दै।"),
      findsOneWidget,
    );
    expect(find.text('हटाउनुहोस्'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });
}
