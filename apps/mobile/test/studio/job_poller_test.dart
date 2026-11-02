import 'package:commerce_os_seller/core/errors/api_error.dart';
import 'package:commerce_os_seller/features/studio/data/job_poller.dart';
import 'package:commerce_os_seller/features/studio/data/studio_models.dart';
import 'package:flutter_test/flutter_test.dart';

StudioJob _job(String status) => StudioJob.fromJson({'id': 'j1', 'status': status});

void main() {
  test('backoff: 2s → ×1.5 → capped at 10s', () {
    expect(
      [for (var i = 0; i < 7; i++) jobPollDelay(i).inMilliseconds],
      [2000, 3000, 4500, 6750, 10000, 10000, 10000],
    );
  });

  Future<(List<String>, List<Duration>)> run(List<Object> script) async {
    final waits = <Duration>[];
    final seen = <String>[];
    var i = 0;
    await for (final j in pollJob(
      fetch: () async {
        final next = script[i++];
        if (next is ApiError) throw next;
        return _job(next as String);
      },
      delay: (d) async => waits.add(d),
    )) {
      seen.add(j.status.name);
    }
    return (seen, waits);
  }

  test('polls queued → running → ready and stops', () async {
    final (seen, waits) = await run(['queued', 'running', 'running', 'ready']);
    expect(seen, ['queued', 'running', 'running', 'ready']);
    expect(waits, [
      const Duration(seconds: 2),
      const Duration(seconds: 3),
      const Duration(milliseconds: 4500),
    ]);
  });

  test('failed, applied and discarded are terminal', () async {
    for (final t in ['failed', 'applied', 'discarded']) {
      final (seen, waits) = await run(['running', t, 'running']);
      expect(seen, ['running', t]);
      expect(waits, hasLength(1));
    }
  });

  test('offline blips keep polling at the capped delay', () async {
    const offline = ApiError(kind: ApiErrorKind.network, code: 'network_unreachable');
    final (seen, waits) = await run(['queued', offline, offline, 'ready']);
    expect(seen, ['queued', 'ready']);
    expect(waits, [
      const Duration(seconds: 2),
      const Duration(seconds: 10),
      const Duration(seconds: 10),
    ]);
  });

  test('non-retryable errors (e.g. 403 feature_not_in_plan) surface', () async {
    const denied = ApiError(
      kind: ApiErrorKind.http,
      code: 'feature_not_in_plan',
      statusCode: 403,
    );
    await expectLater(run(['queued', denied]), throwsA(denied));
  });

  test('parses a ready job draft and issues', () {
    final j = StudioJob.fromJson({
      'id': 'j1',
      'status': 'ready',
      'needs_review': true,
      'confidence': 0.71,
      'issues': [
        {'field': 'captions.instagram', 'kind': 'unsupported_claim:price', 'excerpt': 'Rs 999 only'},
      ],
      'draft': {
        'title_en': 'Pashmina shawl',
        'title_ne': 'पश्मिना सल',
        'attributes': [
          {'key': 'material', 'value': 'Pashmina', 'confidence': 0.62},
        ],
        'category': {'path': ['Clothing', 'Shawls'], 'confidence': 0.9},
        'suggested_options': [
          {'name': 'Colour', 'values': ['Maroon', 'Cream']},
        ],
        'captions': {'instagram': 'x', 'facebook': 'y', 'tiktok': 'z'},
        'needs_seller_input': ['Size in cm'],
        'is_product_photo': true,
      },
    });
    expect(j.isTerminal, isTrue);
    expect(j.issues.single.claim, 'price');
    expect(j.draft!.attributes.single.confidence, 0.62);
    expect(j.draft!.categoryPath, ['Clothing', 'Shawls']);
    expect(j.draft!.captions['tiktok'], 'z');
  });
}
