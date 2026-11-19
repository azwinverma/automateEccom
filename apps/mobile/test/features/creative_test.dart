import 'package:commerce_os_seller/design/widgets/state_views.dart';
import 'package:commerce_os_seller/features/intelligence/data/intelligence_api.dart';
import 'package:commerce_os_seller/features/intelligence/presentation/creative_genome_card.dart';
import 'package:commerce_os_seller/features/intelligence/presentation/post_results.dart';
import 'package:commerce_os_seller/features/intelligence/presentation/recommendations_section.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import '../helpers/fake_adapter.dart';
import '../helpers/test_app.dart';

Map<String, Object?> _pref(
  String attribute,
  String value, {
  double lift = 0.4,
  int n = 12,
  String confidence = 'high',
  bool recommended = true,
  bool engagementOnly = false,
}) => {
  'attribute': attribute,
  'value': value,
  'n': n,
  'lift': lift,
  'confidence': confidence,
  'recommended': recommended,
  'engagement_only': engagementOnly,
};

Map<String, Object?> _genome({bool ready = true}) => {
  'version': ready ? 3 : null,
  'status': ready ? 'ready' : 'learning',
  'posts': ready ? 24 : 6,
  'measured_posts': ready ? 24 : 6,
  'min_posts': 20,
  'baseline': ready ? {'outcome': 'orders', 'mean': 1.2} : null,
  'preferences':
      ready
          ? [
            _pref('language_mix', 'ne_en_mixed', lift: 0.62),
            _pref(
              'posting_window',
              'evening',
              lift: 0.02,
              confidence: 'low',
              recommended: false,
              engagementOnly: true,
            ),
            _pref(
              'language_mix',
              'en',
              lift: -0.3,
              confidence: 'high',
              recommended: false,
            ),
          ]
          : <Object?>[],
};

Map<String, Object?> _post({
  bool cost = true,
  String? source = 'manual',
  String? currency,
}) => {
  'post_id': 'post1',
  if (currency != null) 'currency': currency,
  'metrics': {
    'window_days': 7,
    'window_complete': false,
    'views': source == null ? null : 1500,
    'engagements': source == null ? null : 90,
    'clicks': null,
    'source': source,
    'inquiries': 2,
    'orders': 1.3,
    'revenue_minor': 318500,
    'contribution_minor': cost ? 188500 : null,
  },
};

Future<void> _pump(WidgetTester tester, Widget child, FakeAdapter adapter) =>
    pumpRouted(
      tester,
      initialLocation: '/',
      routes: [
        GoRoute(
          path: '/',
          builder:
              (_, __) => Scaffold(body: SingleChildScrollView(child: child)),
        ),
        GoRoute(
          path: '/what-sells',
          builder: (_, __) => const CreativeGenomeScreen(),
        ),
      ],
      adapter: adapter,
    );

FakeAdapter _forbidden() =>
    FakeAdapter((_) => FakeResponse(403, errorBody('feature_not_in_plan')));

void main() {
  testWidgets('what sells: learning progress until enough posts', (
    tester,
  ) async {
    await _pump(
      tester,
      const CreativeGenomeCard(),
      FakeAdapter((_) => FakeResponse(200, _genome(ready: false))),
    );
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('cg-learning')), findsOneWidget);
    expect(find.textContaining('6 of 20 measured'), findsOneWidget);
    expect(find.byType(LinearProgressIndicator), findsOneWidget);
    expect(find.byKey(const Key('cg-see-all')), findsNothing);
  });

  testWidgets('what sells: patterns that bring orders; likes-only flagged', (
    tester,
  ) async {
    await _pump(
      tester,
      const CreativeGenomeCard(),
      FakeAdapter((_) => FakeResponse(200, _genome())),
    );
    await tester.pumpAndSettle();
    expect(find.text('Captions mixing Nepali and English'), findsOneWidget);
    expect(
      find.text('62% more orders per post · From 12 posts · high confidence'),
      findsOneWidget,
    );
    expect(
      find.text('Posting in the evening (6–9 PM): Gets likes, not orders'),
      findsOneWidget,
    );
    // Not recommended → not on the card.
    expect(find.text('Captions in English'), findsNothing);
    await tester.tap(find.byKey(const Key('cg-see-all')));
    await tester.pumpAndSettle();
    expect(find.text('Other patterns'), findsOneWidget);
    expect(find.text('Captions in English'), findsOneWidget);
  });

  testWidgets('what sells hides on 403', (tester) async {
    await _pump(tester, const CreativeGenomeCard(), _forbidden());
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('creative-genome-card')), findsNothing);
  });

  testWidgets('post results: commerce first, source and missing cost', (
    tester,
  ) async {
    await _pump(
      tester,
      Column(
        children: [
          PostResultsView(results: PostResults.fromJson(_post())),
          PostResultsView(
            results: PostResults.fromJson(_post(cost: false, source: null)),
          ),
        ],
      ),
      FakeAdapter((_) => const FakeResponse(404)),
    );
    await tester.pumpAndSettle();
    expect(find.text('Results (first 7 days)'), findsNWidgets(2));
    expect(
      find.text('Still counting: first 7 days not over yet'),
      findsNWidgets(2),
    );
    expect(
      find.textContaining('2 chats · 1.3 orders · Sales'),
      findsNWidgets(2),
    );
    expect(find.textContaining('Margin Rs'), findsOneWidget);
    expect(find.text('Margin: product cost not set'), findsOneWidget);
    expect(find.text('Numbers entered by you'), findsOneWidget);
    expect(find.text('No views or likes added yet'), findsOneWidget);
  });

  testWidgets('add results: validation, needs one number, posts counts', (
    tester,
  ) async {
    Object? sent;
    final adapter = FakeAdapter((o) {
      if (o.method == 'POST') {
        sent = o.data;
        return FakeResponse(201, _post());
      }
      return const FakeResponse(200, {'post_id': 'post1', 'metrics': null});
    });
    await _pump(tester, const PostResultsSection(postId: 'post1'), adapter);
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('post-add-results-post1')));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('results-save')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('results-need-one')), findsOneWidget);
    expect(sent, isNull);
    await tester.enterText(find.byKey(const Key('results-views')), '1500');
    await tester.enterText(find.byKey(const Key('results-likes')), '90');
    await tester.tap(find.byKey(const Key('results-save')));
    await tester.pumpAndSettle();
    expect(sent, {'views': 1500, 'likes': 90});
    expect(
      adapter.requests.any(
        (r) =>
            r.method == 'POST' &&
            r.path == '/intelligence/creative/posts/post1/metrics',
      ),
      isTrue,
    );
    expect(find.text('Results saved'), findsOneWidget);
  });

  testWidgets('add results: server error is shown in the sheet', (
    tester,
  ) async {
    final adapter = FakeAdapter((o) {
      if (o.method == 'POST') {
        return FakeResponse(409, errorBody('post_not_published'));
      }
      return const FakeResponse(200, {'post_id': 'post1', 'metrics': null});
    });
    await _pump(tester, const PostResultsSection(postId: 'post1'), adapter);
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key('post-add-results-post1')));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('results-views')), '5');
    await tester.tap(find.byKey(const Key('results-save')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('results-save')), findsOneWidget); // still open
    expect(find.byType(InlineError), findsOneWidget);
    expect(find.text('Results saved'), findsNothing);
  });

  testWidgets('creative tip reads as a plain sentence', (tester) async {
    final adapter = FakeAdapter(
      (_) => const FakeResponse(200, {
        'items': [
          {
            'id': 'r9',
            'type': 'creative_tip',
            'confidence': 0.8,
            'explanation': {
              'what': 'creative_price_timing',
              'why': 'creative_pattern',
              'vars': {
                'value': 'first_2s',
                'lift_pct': 85,
                'n': 14,
                'outcome': 'orders',
              },
            },
            'estimated_impact': {'lift': 0.85},
            'action': {'type': 'none'},
          },
        ],
      }),
    );
    await _pump(tester, const RecommendationsSection(), adapter);
    await tester.pumpAndSettle();
    expect(
      find.text('Do more of this: Price in the first 2 seconds'),
      findsOneWidget,
    );
    expect(
      find.text('85% more orders per post, from 14 posts'),
      findsOneWidget,
    );
  });

  testWidgets('360px: card and results sheet fit without overflow', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(360, 780);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.reset);
    final adapter = FakeAdapter((o) {
      if (o.path.endsWith('/genome')) return FakeResponse(200, _genome());
      return FakeResponse(200, _post());
    });
    await _pump(
      tester,
      const Column(
        children: [CreativeGenomeCard(), PostResultsSection(postId: 'post1')],
      ),
      adapter,
    );
    await tester.pumpAndSettle();
    expect(find.text('Captions mixing Nepali and English'), findsOneWidget);
    await tester.tap(find.byKey(const Key('post-add-results-post1')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('results-clicks')), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

  testWidgets('post results load from the per-post endpoint in its currency', (
    tester,
  ) async {
    final adapter = FakeAdapter(
      (_) => FakeResponse(200, _post(currency: 'INR')),
    );
    await _pump(tester, const PostResultsSection(postId: 'post1'), adapter);
    await tester.pumpAndSettle();
    expect(
      adapter.requests.map((r) => r.path),
      contains('/intelligence/creative/posts/post1'),
    );
    expect(find.textContaining('Rs'), findsNothing);
    expect(find.textContaining('Sales INR\u00a03,185'), findsOneWidget);
  });

  testWidgets('post results: no currency falls back to NPR', (tester) async {
    await _pump(
      tester,
      const PostResultsSection(postId: 'post1'),
      FakeAdapter((_) => FakeResponse(200, _post())),
    );
    await tester.pumpAndSettle();
    expect(find.textContaining('Sales Rs'), findsOneWidget);
  });

  testWidgets('post results hide when the post is not found', (tester) async {
    await _pump(
      tester,
      const PostResultsSection(postId: 'post1'),
      FakeAdapter((_) => FakeResponse(404, errorBody('post_not_found'))),
    );
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('post-add-results-post1')), findsNothing);
  });
}
