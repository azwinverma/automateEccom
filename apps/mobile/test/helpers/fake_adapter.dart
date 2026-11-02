import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';

typedef FakeHandler = FutureOr<FakeResponse> Function(RequestOptions options);

class FakeResponse {
  const FakeResponse(this.status, [this.body, this.headers = const {}]);

  /// Simulates a dropped connection.
  const FakeResponse.networkError()
      : status = -1,
        body = null,
        headers = const {};

  final int status;
  final Object? body;
  final Map<String, String> headers;
}

Map<String, Object?> errorBody(String code, {String requestId = 'req-1'}) => {
      'error': {
        'code': code,
        'message': code,
        'details': <String, Object?>{},
        'request_id': requestId,
      },
    };

/// Routes requests to [handler] and records every request it sees.
class FakeAdapter implements HttpClientAdapter {
  FakeAdapter(this.handler);

  final FakeHandler handler;
  final List<RequestOptions> requests = [];

  /// Header snapshots per call (RequestOptions are mutated on retry).
  final List<({String path, Map<String, Object?> headers})> log = [];

  int countPath(String path) => requests.where((r) => r.path == path).length;

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    requests.add(options);
    log.add((path: options.path, headers: Map.of(options.headers)));
    final r = await handler(options);
    if (r.status == -1) {
      throw DioException.connectionError(
        requestOptions: options,
        reason: 'fake network down',
      );
    }
    return ResponseBody.fromString(
      r.body == null ? '' : jsonEncode(r.body),
      r.status,
      headers: {
        Headers.contentTypeHeader: [Headers.jsonContentType],
        for (final e in r.headers.entries) e.key: [e.value],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}
