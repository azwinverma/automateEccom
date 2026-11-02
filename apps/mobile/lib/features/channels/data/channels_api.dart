import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/api_call.dart';
import '../../../core/api/providers.dart';
import '../../../core/auth/session_controller.dart';

@immutable
class ChannelConnection {
  const ChannelConnection({
    required this.id,
    required this.provider,
    required this.displayName,
    required this.status,
    this.capabilities = const [],
    this.needsReconnect = false,
  });

  factory ChannelConnection.fromJson(Map<String, Object?> j) =>
      ChannelConnection(
        id: j['id']! as String,
        provider: (j['provider'] as String?) ?? '',
        displayName: (j['display_name'] as String?) ?? '',
        status: (j['status'] as String?) ?? '',
        capabilities: ((j['capabilities'] as List<Object?>?) ?? const [])
            .whereType<String>()
            .toList(growable: false),
        needsReconnect: (j['needs_reconnect'] as bool?) ?? false,
      );

  final String id;
  final String provider;
  final String displayName;
  final String status;
  final List<String> capabilities;
  final bool needsReconnect;

  bool get isConnected => status == 'connected';
  bool supports(String capability) => capabilities.contains(capability);

  String get label => displayName.isNotEmpty ? displayName : provider;
}

class ChannelsApi {
  ChannelsApi(this._dio);

  final Dio _dio;

  Future<List<ChannelConnection>> list() => apiCall(() async {
    final r = await _dio.get<Map<String, Object?>>('/channels');
    return itemsOf(r.data).map(ChannelConnection.fromJson).toList();
  });
}

final channelsApiProvider = Provider<ChannelsApi>(
  (ref) => ChannelsApi(ref.watch(dioProvider)),
);

final channelsProvider = FutureProvider.autoDispose<List<ChannelConnection>>((
  ref,
) {
  ref.watch(activeMerchantIdProvider);
  return ref.watch(channelsApiProvider).list();
});
