import '../../../core/l10n/gen/app_localizations.dart';

/// Contract password policy: ≥ 10 chars, not equal to email. The common
/// password list is enforced server-side.
const minPasswordLength = 10;

final _email = RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$');
final _phone = RegExp(r'^\+?[0-9]{7,15}$');

abstract final class Validators {
  static String? email(AppLocalizations l, String? v) {
    final value = v?.trim() ?? '';
    if (value.isEmpty) return l.validationEmailRequired;
    if (!_email.hasMatch(value)) return l.validationEmailInvalid;
    return null;
  }

  static String? loginPassword(AppLocalizations l, String? v) =>
      (v ?? '').isEmpty ? l.validationPasswordRequired : null;

  static String? newPassword(AppLocalizations l, String? v, String email) {
    final value = v ?? '';
    if (value.isEmpty) return l.validationPasswordRequired;
    if (value.length < minPasswordLength) {
      return l.validationPasswordTooShort(minPasswordLength);
    }
    if (value.trim().toLowerCase() == email.trim().toLowerCase()) {
      return l.validationPasswordEqualsEmail;
    }
    return null;
  }

  static String? name(AppLocalizations l, String? v) =>
      (v?.trim() ?? '').isEmpty ? l.validationNameRequired : null;

  static String? optionalPhone(AppLocalizations l, String? v) {
    final value = (v ?? '').replaceAll(RegExp(r'[\s-]'), '');
    if (value.isEmpty) return null;
    return _phone.hasMatch(value) ? null : l.validationPhoneInvalid;
  }

  static String? code(AppLocalizations l, String? v) =>
      (v?.trim() ?? '').isEmpty ? l.validationCodeRequired : null;
}
