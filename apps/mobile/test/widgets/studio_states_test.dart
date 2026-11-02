import 'dart:async';

import 'package:commerce_os_seller/features/catalog/presentation/product_screen.dart';
import 'package:commerce_os_seller/features/studio/data/studio_models.dart';
import 'package:commerce_os_seller/features/studio/presentation/job_screen.dart';
import 'package:commerce_os_seller/features/studio/presentation/widgets/issue_list.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import '../helpers/fake_adapter.dart';
import '../helpers/pump.dart';
import '../helpers/test_app.dart';

const _issues = [
  DraftIssue(field: 'captions.instagram', kind: 'unsupported_claim:price', excerpt: 'Rs 999'),
  DraftIssue(field: 'description_en', kind: 'unsupported_claim:authenticity'),
  DraftIssue(field: 'photos', kind: 'not_a_product_photo'),
  DraftIssue(field: 'title_en', kind: 'too_long'),
  DraftIssue(field: 'bullets_en[0]', kind: 'unsupported_claim:teleport'),
];

void main() {
  testWidgets('issues: every kind has seller copy (en)', (tester) async {
    tester.view.physicalSize = const Size(1080, 2220);
    tester.view.devicePixelRatio = 3;
    addTearDown(tester.view.reset);
    await pumpLocalized(tester, const IssueList(issues: _issues));
    expect(find.text('The text mentions a price. Prices come from you; please check.'), findsOneWidget);
    expect(find.text('In: Caption · Instagram'), findsOneWidget);
    expect(find.text('“Rs 999”'), findsOneWidget);
    expect(find.textContaining('original or genuine'), findsOneWidget);
    expect(find.textContaining('may not show a product'), findsOneWidget);
    expect(find.textContaining('shortened'), findsOneWidget);
    expect(find.textContaining("couldn't verify"), findsOneWidget);
  });

  testWidgets('issues: Nepali at 360dp', (tester) async {
    tester.view.physicalSize = const Size(1080, 2220);
    tester.view.devicePixelRatio = 3;
    addTearDown(tester.view.reset);
    await pumpLocalized(tester, const IssueList(issues: _issues), locale: const Locale('ne'));
    expect(find.text('लेखाइमा मूल्य उल्लेख छ। मूल्य तपाईंले नै राख्ने हो, कृपया जाँच्नुहोस्।'), findsOneWidget);
    expect(find.text('ठाउँ: क्याप्सन · Instagram'), findsOneWidget);
  });

  for (final locale in const [Locale('en'), Locale('ne')]) {
    testWidgets('job queued → calm progress, no percentage (${locale.languageCode})', (tester) async {
      final adapter = FakeAdapter(
        (o) => const FakeResponse(200, {'id': 'j1', 'status': 'queued'}),
      );
      await pumpRouted(
        tester,
        initialLocation: '/studio/jobs/j1',
        adapter: adapter,
        locale: locale,
        settle: false,
        // Never resolves: keeps the screen in its waiting state.
        overrides: [jobPollDelayProvider.overrideWithValue((_) => Completer<void>().future)],
        routes: [GoRoute(path: '/studio/jobs/:id', builder: (_, s) => JobScreen(jobId: s.pathParameters['id']!))],
      );
      await tester.pump(const Duration(milliseconds: 100));
      expect(find.byKey(const Key('job-status')), findsOneWidget);
      expect(find.textContaining('%'), findsNothing);
      expect(
        find.text(locale.languageCode == 'ne'
            ? "यो स्क्रिन छोड्न सक्नुहुन्छ, काम चलिरहन्छ। पछि 'ड्राफ्ट' मा भेटिन्छ।"
            : "You can leave this screen; we'll keep working. Find it later under Drafts."),
        findsOneWidget,
      );
    });
  }

  testWidgets('job failed → retry posts and re-polls', (tester) async {
    var retried = false;
    final adapter = FakeAdapter((o) {
      if (o.path == '/studio/jobs/j1/retry') {
        retried = true;
        return const FakeResponse(202, {'id': 'j1', 'status': 'queued'});
      }
      return FakeResponse(200, {'id': 'j1', 'status': retried ? 'ready' : 'failed', 'error_code': 'ai_unavailable'});
    });
    await pumpRouted(
      tester,
      initialLocation: '/studio/jobs/j1',
      adapter: adapter,
      overrides: [jobPollDelayProvider.overrideWithValue((_) async {})],
      routes: [GoRoute(path: '/studio/jobs/:id', builder: (_, s) => JobScreen(jobId: s.pathParameters['id']!))],
    );
    expect(find.text('Our writing service is busy. Try again in a few minutes.'), findsOneWidget);
    await tester.tap(find.byKey(const Key('job-retry')));
    await tester.pumpAndSettle();
    expect(adapter.countPath('/studio/jobs/j1/retry'), 1);
    expect(find.text('Check your listing'), findsOneWidget);
  });

  testWidgets('job 403 feature_not_in_plan → plan upgrade state', (tester) async {
    final adapter = FakeAdapter((o) => FakeResponse(403, errorBody('feature_not_in_plan')));
    await pumpRouted(
      tester,
      initialLocation: '/studio/jobs/j1',
      adapter: adapter,
      routes: [GoRoute(path: '/studio/jobs/:id', builder: (_, s) => JobScreen(jobId: s.pathParameters['id']!))],
    );
    expect(find.text('Not in your current plan'), findsOneWidget);
  });

  for (final locale in const [Locale('en'), Locale('ne')]) {
    testWidgets('go live → not_publishable problems link to fixes (${locale.languageCode})', (tester) async {
      final adapter = FakeAdapter((o) {
        switch (o.path) {
          case '/catalog/products/p1':
            return const FakeResponse(200, {
              'id': 'p1',
              'title': 'Pashmina shawl',
              'title_ne': 'पश्मिना सल',
              'status': 'draft',
              'version': 3,
              'variants': [
                {'id': 'v1', 'options': <String, String>{}, 'price': {'amount_minor': 0, 'currency': 'NPR'}, 'status': 'active'},
              ],
              'attributes': [
                {'key': 'origin', 'value': 'Kathmandu', 'confidence': 0.55, 'confirmed': false, 'source': 'ai'},
              ],
            });
          case '/catalog/products/p1/status':
            return const FakeResponse(400, {
              'error': {
                'code': 'not_publishable',
                'message': 'x',
                'details': {'problems': ['price_required', 'unconfirmed_ai_attributes']},
                'request_id': 'r1',
              },
            });
          case '/catalog/products/p1/listings':
            return const FakeResponse(200, {'items': <Object?>[]});
          case '/channels':
            return const FakeResponse(200, {
              'items': [
                {'id': 'c1', 'provider': 'instagram', 'display_name': 'Thamel IG', 'status': 'connected', 'capabilities': ['product_listing', 'content_publish'], 'needs_reconnect': false},
                {'id': 'c2', 'provider': 'facebook', 'display_name': 'Thamel FB', 'status': 'expired', 'capabilities': ['product_listing'], 'needs_reconnect': true},
                {'id': 'c3', 'provider': 'tiktok', 'display_name': 'No listings', 'status': 'connected', 'capabilities': ['messages'], 'needs_reconnect': false},
              ],
            });
        }
        return FakeResponse(404, errorBody('not_found'));
      });
      await pumpRouted(
        tester,
        initialLocation: '/products/p1?job=j1',
        adapter: adapter,
        locale: locale,
        height: 1600,
        routes: [
          GoRoute(
            path: '/products/:id',
            builder: (_, s) => ProductScreen(productId: s.pathParameters['id']!, jobId: s.uri.queryParameters['job']),
          ),
        ],
      );
      final ne = locale.languageCode == 'ne';
      expect(find.text(ne ? 'पश्मिना सल' : 'Pashmina shawl'), findsOneWidget);
      // Channels: listing-capable connected + expired-with-reconnect; others hidden.
      expect(find.text('Thamel IG'), findsNWidgets(2)); // publish + posts
      expect(find.text(ne ? 'फेरि जोड्नुहोस्' : 'Reconnect'), findsOneWidget);
      expect(find.text('No listings'), findsNothing);

      await tester.tap(find.byKey(const Key('go-live')));
      await tester.pumpAndSettle();
      final status = adapter.requests.singleWhere((r) => r.path == '/catalog/products/p1/status');
      expect(status.data, {'status': 'active', 'version': 3});
      expect(find.byKey(const Key('problem-price_required')), findsOneWidget);
      expect(find.byKey(const Key('problem-unconfirmed_ai_attributes')), findsOneWidget);
      expect(find.text(ne ? 'मिलाउनुहोस्' : 'Fix'), findsNWidgets(2));

      // "Fix" on price opens the price editor for the zero-price variant.
      await tester.tap(find.text(ne ? 'मिलाउनुहोस्' : 'Fix').first);
      await tester.pumpAndSettle();
      expect(find.byType(AlertDialog), findsOneWidget);
    });
  }
}
