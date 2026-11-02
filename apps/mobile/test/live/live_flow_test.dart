// Opt-in end-to-end check against a running backend:
//   flutter test test/live --dart-define=LIVE_API=http://localhost:8095 \
//     --dart-define=LIVE_PHOTO=/abs/path/to/photo.jpg
// Skipped when LIVE_API is not set, so the normal suite stays offline.
// ignore_for_file: avoid_print
import 'dart:io';

import 'package:commerce_os_seller/core/api/api_client.dart';
import 'package:commerce_os_seller/core/api/request_context_interceptor.dart';
import 'package:commerce_os_seller/core/auth/auth_api.dart';
import 'package:commerce_os_seller/core/auth/token_store.dart';
import 'package:commerce_os_seller/core/config/app_config.dart';
import 'package:commerce_os_seller/core/errors/api_error.dart';
import 'package:commerce_os_seller/core/storage/key_value_store.dart';
import 'package:commerce_os_seller/features/catalog/data/catalog_api.dart';
import 'package:commerce_os_seller/features/channels/data/channels_api.dart';
import 'package:commerce_os_seller/features/content/data/content_api.dart';
import 'package:commerce_os_seller/features/exceptions/data/exception_routing.dart';
import 'package:commerce_os_seller/features/exceptions/data/exceptions_api.dart';
import 'package:commerce_os_seller/features/studio/data/job_poller.dart';
import 'package:commerce_os_seller/features/studio/data/media_api.dart';
import 'package:commerce_os_seller/features/studio/data/review_form.dart';
import 'package:commerce_os_seller/features/studio/data/studio_api.dart';
import 'package:commerce_os_seller/features/studio/data/studio_models.dart';
import 'package:commerce_os_seller/features/studio/data/upload_engine.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:uuid/uuid.dart';

const _api = String.fromEnvironment('LIVE_API');
const _photo = String.fromEnvironment('LIVE_PHOTO');

void main() {
  test('capture → AI draft → review → create → go live → publish → posts',
      () async {
    const config = AppConfig(apiBaseUrl: _api, getRetries: 0);
    final tokens = TokenStore(InMemoryKeyValueStore());
    String? merchant;
    final dio = buildApiDio(
      config: config,
      tokenStore: tokens,
      merchantId: () => merchant,
      languageCode: () => 'ne',
      onSessionEnded: (r) => fail('session ended: $r'),
    );
    final auth = AuthApi(dio);
    final email = 'mobile-e2e-${const Uuid().v4().substring(0, 8)}@example.np';
    const password = 'momo-chiya-dal-bhat-42';

    await auth.register(email: email, password: password, fullName: 'Sita Rai', locale: 'ne');
    final login = await auth.login(email: email, password: password, deviceName: 'e2e');
    await tokens.save((login as LoginSucceeded).tokens);
    final m = await dio.post<Map<String, Object?>>(
      '/merchants',
      data: {
        'name': 'Thamel Handloom E2E',
        'country': 'NP',
        'currency': 'NPR',
        'timezone': 'Asia/Kathmandu',
        'default_locale': 'ne',
      },
      options: Options(extra: {ApiExtra.tenant: false, ApiExtra.idempotent: true}),
    );
    merchant = ((m.data!['merchant'] ?? m.data) as Map<String, Object?>)['id']! as String;
    print('merchant $merchant');

    // 1. Signed upload via the real engine.
    final media = MediaApi(dio, Dio());
    final file = File(_photo);
    final engine = UploadEngine(
      api: media,
      readFile: (p) => File(p).readAsBytes(),
      onChanged: (_) {},
    )..add([
        UploadItem(
          localId: 'l1',
          filePath: file.path,
          fileName: 'shawl.jpg',
          contentType: 'image/jpeg',
          sizeBytes: file.lengthSync(),
        ),
      ]);
    await engine.idle().timeout(const Duration(minutes: 2));
    final up = engine.items.single;
    print('upload ${up.phase} flags=${up.qualityFlags} err=${up.errorCode}');
    expect(up.phase, UploadPhase.ready);
    final asset = await media.get(up.assetId!);
    print('derivatives ${asset.derivatives.keys.toList()}');

    // 2. AI draft.
    final studio = StudioApi(dio);
    final created = await studio.createJob(
      assetIds: [up.assetId!],
      locale: 'ne',
      sellerNotes: 'Pure pashmina, made in Kathmandu',
      idempotencyKey: const Uuid().v4(),
    );
    StudioJob? job;
    await for (final j in pollJob(fetch: () => studio.getJob(created.id))
        .timeout(const Duration(minutes: 3))) {
      print('job ${j.status.name}');
      job = j;
    }
    expect(job!.status, JobStatus.ready, reason: 'error_code=${job.errorCode}');
    print('draft title_ne="${job.draft!.titleNe}" attrs=${job.draft!.attributes.length} '
        'issues=${job.issues.map((i) => i.kind).toList()} needs_review=${job.needsReview}');

    // 3. Review (seller price, acknowledge low-confidence attributes) → apply.
    final form = ReviewForm.fromDraft(job.draft!)..price = '2,450.50';
    for (final a in form.uncheckedAttributes) {
      a.decision = AttributeDecision.accepted;
    }
    expect(form.validate(), isEmpty);
    final payload = form.toApply();
    final detail = await studio.apply(
      job.id,
      product: payload.product,
      categoryPath: payload.categoryPath,
      acceptedAttributeKeys: payload.acceptedKeys,
    );
    final productId = detail['id']! as String;
    final catalog = CatalogApi(dio);
    var product = await catalog.product(productId);
    print('product ${product.status} v${product.version} '
        'prices=${product.activeVariants.map((v) => v.priceMinor).toList()} '
        'unconfirmed=${product.unconfirmed.map((a) => a.key).toList()}');
    expect(product.activeVariants.every((v) => v.priceMinor > 0), isTrue);

    // 4. Go live (confirm any remaining AI attributes first).
    if (product.unconfirmed.isNotEmpty) {
      product = await catalog.confirmAttributes(
        productId,
        [for (final a in product.unconfirmed) a.key],
      );
    }
    product = await catalog.setStatus(productId, 'active', product.version);
    print('status ${product.status}');
    expect(product.status, 'active');

    // 5. Test setup only (the web app owns OAuth): connect the dev sandbox
    // channel through its consent screen so publish/posts paths run.
    final start = await dio.post<Map<String, Object?>>(
      '/channels/connect',
      data: {'provider': 'sandbox_channel', 'redirect_uri': 'http://localhost/cb'},
    );
    final authorize = Uri.parse(start.data!['authorize_url']! as String);
    final consent = await Dio(BaseOptions(followRedirects: false, validateStatus: (_) => true))
        .getUri<Object?>(authorize.hasScheme ? authorize : Uri.parse('$_api$authorize'));
    final cb = Uri.parse(consent.headers.value('location')!);
    await dio.post<Object?>(
      '/channels/oauth/callback',
      data: {
        'provider': 'sandbox_channel',
        'state': cb.queryParameters['state'],
        'code': cb.queryParameters['code'],
      },
    );

    // Channels → publish → listings; posts from studio.
    final channels = await ChannelsApi(dio).list();
    print('channels ${channels.map((c) => '${c.provider}:${c.status}:${c.capabilities}').toList()}');
    final listable = channels.where((c) => c.isConnected && c.supports('product_listing')).toList();
    if (listable.isNotEmpty) {
      await catalog.publish(productId, [for (final c in listable) c.id]);
      for (var i = 0; i < 20; i++) {
        final l = await catalog.listings(productId);
        print('listings ${l.map((x) => '${x.provider}:${x.status}:${x.lastErrorCode}').toList()}');
        if (!l.any((x) => x.inFlight)) break;
        await Future<void>.delayed(const Duration(seconds: 2));
      }
    }
    final postable = channels.where((c) => c.isConnected && c.supports('content_publish')).toList();
    if (postable.isNotEmpty) {
      final content = ContentApi(dio);
      final posts = await content.fromStudio(job.id, [for (final c in postable) c.id]);
      for (final p in posts) {
        var cur = await content.submit(p.id);
        print('post ${p.id} submitted → ${cur.status} issues=${cur.issues.length}');
        if (cur.status == 'pending_approval') cur = await content.approve(p.id);
        cur = await content.schedule(p.id);
        print('post → ${cur.status}');
      }
    }

    // 6. Exceptions parse and route.
    final ex = await ExceptionsApi(dio).list();
    for (final e in ex) {
      print('exception ${e.type}/${e.severity}/${e.action} → ${resolveExceptionAction(e).runtimeType}');
    }

    // Error envelope sanity: 404 is typed.
    try {
      await catalog.product('00000000-0000-0000-0000-000000000000');
    } on ApiError catch (e) {
      print('404 → ${e.code} req=${e.requestId}');
      expect(e.code, 'not_found');
    }
  }, skip: _api.isEmpty ? 'set --dart-define=LIVE_API to run' : false,
      timeout: const Timeout(Duration(minutes: 8)));
}
