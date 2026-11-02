import 'dart:ui';

import 'package:commerce_os_seller/core/l10n/gen/app_localizations.dart';
import 'package:commerce_os_seller/features/auth/presentation/validators.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  final l = lookupAppLocalizations(const Locale('en'));

  test('new password policy mirrors the contract', () {
    expect(Validators.newPassword(l, '', 'a@b.np'), l.validationPasswordRequired);
    expect(Validators.newPassword(l, 'short', 'a@b.np'),
        'Use at least 10 characters');
    expect(Validators.newPassword(l, 'sita@thamel.np', 'Sita@Thamel.np'),
        l.validationPasswordEqualsEmail);
    expect(Validators.newPassword(l, 'momo-and-chiya-42', 'a@b.np'), isNull);
  });

  test('phone is optional but validated when present', () {
    expect(Validators.optionalPhone(l, ''), isNull);
    expect(Validators.optionalPhone(l, '98-4123 4567'), isNull);
    expect(Validators.optionalPhone(l, '+9779841234567'), isNull);
    expect(Validators.optionalPhone(l, 'abc'), l.validationPhoneInvalid);
  });
}
