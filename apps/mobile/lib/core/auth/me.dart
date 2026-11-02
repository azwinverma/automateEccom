import 'package:flutter/foundation.dart';

@immutable
class AppUser {
  const AppUser({
    required this.id,
    required this.email,
    required this.fullName,
    this.phone,
    this.locale,
    this.emailVerified = false,
    this.mfaEnabled = false,
  });

  factory AppUser.fromJson(Map<String, Object?> json) => AppUser(
    id: json['id']! as String,
    email: json['email']! as String,
    fullName: (json['full_name'] as String?) ?? '',
    phone: json['phone'] as String?,
    locale: json['locale'] as String?,
    emailVerified: (json['email_verified'] as bool?) ?? false,
    mfaEnabled: (json['mfa_enabled'] as bool?) ?? false,
  );

  final String id;
  final String email;
  final String fullName;
  final String? phone;
  final String? locale;
  final bool emailVerified;
  final bool mfaEnabled;
}

@immutable
class MerchantSummary {
  const MerchantSummary({required this.id, required this.name, this.slug});

  factory MerchantSummary.fromJson(Map<String, Object?> json) =>
      MerchantSummary(
        id: json['id']! as String,
        name: (json['name'] as String?) ?? '',
        slug: json['slug'] as String?,
      );

  final String id;
  final String name;
  final String? slug;
}

@immutable
class Membership {
  const Membership({
    required this.merchant,
    required this.role,
    required this.status,
  });

  factory Membership.fromJson(Map<String, Object?> json) => Membership(
    merchant: MerchantSummary.fromJson(
      json['merchant']! as Map<String, Object?>,
    ),
    role: (json['role'] as String?) ?? 'viewer',
    status: (json['status'] as String?) ?? 'active',
  );

  final MerchantSummary merchant;
  final String role;
  final String status;

  bool get isActive => status == 'active';
}

/// `GET /me`.
@immutable
class Me {
  const Me({required this.user, required this.memberships});

  factory Me.fromJson(Map<String, Object?> json) => Me(
    user: AppUser.fromJson(json['user']! as Map<String, Object?>),
    memberships: ((json['memberships'] as List<Object?>?) ?? const [])
        .whereType<Map<String, Object?>>()
        .map(Membership.fromJson)
        .toList(growable: false),
  );

  final AppUser user;
  final List<Membership> memberships;

  List<Membership> get activeMemberships =>
      memberships.where((m) => m.isActive).toList(growable: false);
}
