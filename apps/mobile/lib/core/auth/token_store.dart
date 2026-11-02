import '../storage/key_value_store.dart';
import 'token_pair.dart';

/// Holds tokens in memory for fast synchronous header injection and persists
/// them to secure storage only.
class TokenStore {
  TokenStore(this._store);

  static const _kAccess = 'auth.access_token';
  static const _kRefresh = 'auth.refresh_token';
  static const _kSession = 'auth.session_id';

  final KeyValueStore _store;
  String? _access;
  String? _refresh;
  String? _sessionId;
  bool _loaded = false;

  String? get accessToken => _access;
  String? get sessionId => _sessionId;
  bool get hasSession => _refresh != null;

  Future<void> load() async {
    if (_loaded) return;
    _access = await _store.read(_kAccess);
    _refresh = await _store.read(_kRefresh);
    _sessionId = await _store.read(_kSession);
    _loaded = true;
  }

  Future<String?> readRefreshToken() async {
    await load();
    return _refresh;
  }

  Future<void> save(TokenPair pair) async {
    _access = pair.accessToken;
    _refresh = pair.refreshToken;
    _sessionId = pair.sessionId ?? _sessionId;
    _loaded = true;
    await _store.write(_kAccess, pair.accessToken);
    await _store.write(_kRefresh, pair.refreshToken);
    if (_sessionId != null) await _store.write(_kSession, _sessionId!);
  }

  Future<void> clear() async {
    _access = null;
    _refresh = null;
    _sessionId = null;
    _loaded = true;
    await _store.delete(_kAccess);
    await _store.delete(_kRefresh);
    await _store.delete(_kSession);
  }
}
