import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/providers.dart';
import '../../../core/errors/api_error.dart';
import 'media_models.dart';

/// Port used by the upload engine (faked in tests).
abstract interface class MediaGateway {
  Future<UploadTicket> createUpload({
    required String fileName,
    required String contentType,
    required int sizeBytes,
  });

  /// PUTs bytes to the signed URL with exactly the given headers and no
  /// Authorization header.
  Future<void> putBytes(
    UploadTicket ticket,
    Uint8List bytes, {
    void Function(int sent, int total)? onProgress,
  });

  Future<void> complete(String assetId);

  Future<MediaAsset> get(String assetId);
}

class MediaApi implements MediaGateway {
  MediaApi(this._dio, this._objectStore);

  final Dio _dio;

  /// Bare client for signed object-store URLs (no auth/tenant headers).
  final Dio _objectStore;

  Future<T> _call<T>(Future<T> Function() run) async {
    try {
      return await run();
    } on DioException catch (e) {
      throw ApiError.fromDio(e);
    }
  }

  @override
  Future<UploadTicket> createUpload({
    required String fileName,
    required String contentType,
    required int sizeBytes,
  }) => _call(() async {
    final res = await _dio.post<Map<String, Object?>>(
      '/media/uploads',
      data: {
        'file_name': fileName,
        'content_type': contentType,
        'size_bytes': sizeBytes,
        'purpose': 'product',
      },
    );
    return UploadTicket.fromJson(res.data!);
  });

  @override
  Future<void> putBytes(
    UploadTicket ticket,
    Uint8List bytes, {
    void Function(int sent, int total)? onProgress,
  }) => _call(() async {
    await _objectStore.put<Object?>(
      ticket.url,
      data: Stream<List<int>>.value(bytes),
      options: Options(
        headers: {...ticket.headers, Headers.contentLengthHeader: bytes.length},
        responseType: ResponseType.plain,
      ),
      onSendProgress: onProgress,
    );
  });

  @override
  Future<void> complete(String assetId) => _call(() async {
    await _dio.post<Object?>('/media/$assetId/complete');
  });

  @override
  Future<MediaAsset> get(String assetId) => _call(() async {
    final res = await _dio.get<Map<String, Object?>>('/media/$assetId');
    return MediaAsset.fromJson(res.data!);
  });
}

final objectStoreDioProvider = Provider<Dio>((ref) {
  final config = ref.watch(appConfigProvider);
  final dio = Dio(
    BaseOptions(
      connectTimeout: config.connectTimeout,
      // Large photos on 3G: give the body time.
      sendTimeout: const Duration(seconds: 90),
      receiveTimeout: config.receiveTimeout,
    ),
  );
  final adapter = ref.watch(httpClientAdapterProvider);
  if (adapter != null) dio.httpClientAdapter = adapter;
  ref.onDispose(dio.close);
  return dio;
});

final mediaApiProvider = Provider<MediaGateway>(
  (ref) => MediaApi(ref.watch(dioProvider), ref.watch(objectStoreDioProvider)),
);
