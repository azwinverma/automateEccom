import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../api/api_call.dart';
import '../api/providers.dart';

/// Effective permissions in the current shop (GET /permissions/me).
///
/// Used only to hide actions a person can't take; the server still enforces
/// every call. `null` while loading or if the list couldn't be fetched: callers
/// then show the action and rely on the server's 403 message.
final myPermissionsProvider = FutureProvider.autoDispose<Set<String>?>((
  ref,
) async {
  try {
    final data = await apiCall(() async {
      final r = await ref
          .watch(dioProvider)
          .get<Map<String, Object?>>('/permissions/me');
      return r.data;
    });
    final perms = data?['permissions'];
    return perms is List ? perms.whereType<String>().toSet() : null;
  } on Object {
    return null;
  }
});

/// True unless the permission list is known and lacks [permission].
bool mayDo(Set<String>? permissions, String permission) =>
    permissions == null || permissions.contains(permission);
