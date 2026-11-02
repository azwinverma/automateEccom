import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/providers.dart';
import '../../../core/auth/auth_api.dart';

final sessionsProvider = FutureProvider.autoDispose<List<AuthSession>>(
  (ref) => ref.watch(authApiProvider).sessions(),
);
