import 'package:flutter/foundation.dart';

@immutable
class TokenPair {
  const TokenPair({
    required this.accessToken,
    required this.refreshToken,
    this.expiresIn,
    this.sessionId,
  });

  factory TokenPair.fromJson(Map<String, Object?> json) => TokenPair(
    accessToken: json['access_token']! as String,
    refreshToken: json['refresh_token']! as String,
    expiresIn: (json['expires_in'] as num?)?.toInt(),
    sessionId: json['session_id'] as String?,
  );

  final String accessToken;
  final String refreshToken;
  final int? expiresIn;
  final String? sessionId;
}
