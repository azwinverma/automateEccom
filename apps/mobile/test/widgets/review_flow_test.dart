import 'dart:convert';

import 'package:commerce_os_seller/features/studio/presentation/job_screen.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';

import '../helpers/fake_adapter.dart';
import '../helpers/test_app.dart';

const _readyJob = {
  'id': 'j1',
  'status': 'ready',
  'asset_ids': ['a1'],
  'locale': 'ne',
  'needs_review': true,
  'confidence': 0.7,
  'issues': [
    {'field': 'captions.instagram', 'kind': 'unsupported_claim:price', 'excerpt': 'Rs 999 matra'},
  ],
  'draft': {
    'title_en': 'Pashmina shawl',
    'title_ne': 'पश्मिना सल',
    'description_en': 'Soft and warm.',
    'description_ne': 'नरम र न्यानो।',
    'bullets_en': <String>[],
    'attributes': [
      {'key': 'material', 'value': 'Pashmina', 'confidence': 0.95},
      {'key': 'origin', 'value': 'Kathmandu', 'confidence': 0.55},
    ],
    'category': {'path': ['Clothing', 'Shawls'], 'confidence': 0.88},
    'suggested_options': <Object?>[],
    'hashtags': ['pashmina'],
    'captions': {'instagram': 'Rs 999 matra', 'facebook': 'f', 'tiktok': 't'},
    'needs_seller_input': ['Size in cm'],
    'is_product_photo': true,
  },
};

void main() {
  late FakeAdapter adapter;

  setUp(() {
    adapter = FakeAdapter((o) {
      if (o.path == '/studio/jobs/j1' && o.method == 'GET') {
        return const FakeResponse(200, _readyJob);
      }
      if (o.path == '/studio/jobs/j1/apply') {
        return const FakeResponse(201, {'id': 'p1', 'status': 'draft', 'version': 1});
      }
      return FakeResponse(404, errorBody('not_found'));
    });
  });

  Future<void> pump(WidgetTester tester, Locale locale) => pumpRouted(
        tester,
        initialLocation: '/studio/jobs/j1',
        adapter: adapter,
        locale: locale,
        height: 2000,
        routes: [
          GoRoute(path: '/studio/jobs/:id', builder: (_, s) => JobScreen(jobId: s.pathParameters['id']!)),
          stubRoute('/products/:id'),
        ],
      );

  testWidgets('en: validation blocks save until price + low-confidence check',
      (tester) async {
    await pump(tester, const Locale('en'));
    expect(find.text('Check your listing'), findsOneWidget);
    // Grounding issue rendered as a plain warning.
    expect(find.text('The text mentions a price. Prices come from you; please check.'), findsOneWidget);
    expect(find.text('Please check'), findsOneWidget);
    // English title comes first in English.
    expect(
      tester.getTopLeft(find.byKey(const Key('title-en'))).dy,
      lessThan(tester.getTopLeft(find.byKey(const Key('title-ne'))).dy),
    );

    await tester.tap(find.byKey(const Key('review-save')));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key('review-fix-problems')), findsOneWidget);
    expect(find.byKey(const Key('attr-unchecked-error')), findsOneWidget);
    expect(find.text('Enter a price'), findsOneWidget);
    expect(adapter.countPath('/studio/jobs/j1/apply'), 0);

    await tester.enterText(find.byKey(const Key('price-field')), '2,450.50');
    await tester.tap(find.byKey(const Key('attr-accept-origin')));
    await tester.pumpAndSettle();
    expect(find.text('Checked'), findsOneWidget);

    await tester.tap(find.byKey(const Key('review-save')));
    await tester.pumpAndSettle();

    final apply = adapter.requests.singleWhere((r) => r.path == '/studio/jobs/j1/apply');
    final body = jsonDecode(jsonEncode(apply.data)) as Map<String, Object?>;
    expect(body['accepted_attribute_keys'], ['material', 'origin']);
    expect(body['category_path'], ['Clothing', 'Shawls']);
    final product = body['product']! as Map<String, Object?>;
    expect(product['title'], 'Pashmina shawl');
    expect(product['title_ne'], 'पश्मिना सल');
    expect(product['variants'], [
      {'options': <String, Object?>{}, 'price_minor': 245050},
    ]);
    expect(find.text('STUB /products/p1?job=j1'), findsOneWidget);
  });

  testWidgets('ne: Nepali first, Nepali copy, no overflow at 360dp', (tester) async {
    await pump(tester, const Locale('ne'));
    expect(find.text('विवरण जाँच्नुहोस्'), findsOneWidget);
    expect(
      tester.getTopLeft(find.byKey(const Key('title-ne'))).dy,
      lessThan(tester.getTopLeft(find.byKey(const Key('title-en'))).dy),
    );
    expect(find.text('लेखाइमा मूल्य उल्लेख छ। मूल्य तपाईंले नै राख्ने हो, कृपया जाँच्नुहोस्।'), findsOneWidget);
    expect(find.text('कृपया जाँच्नुहोस्'), findsWidgets);
    await tester.tap(find.byKey(const Key('review-save')));
    await tester.pumpAndSettle();
    expect(find.text('मूल्य हाल्नुहोस्'), findsOneWidget);
    // Devanagari digits are accepted in the price field.
    await tester.enterText(find.byKey(const Key('price-field')), '१२००');
    await tester.pumpAndSettle();
    expect(find.text('मूल्य हाल्नुहोस्'), findsNothing);
  });
}
