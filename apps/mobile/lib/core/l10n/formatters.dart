import 'package:intl/intl.dart';

/// Locale-aware formatting for Nepal sellers.
///
/// - NPR uses "रू" in Nepali and "Rs" in English, South Asian digit grouping
///   (1,25,000), and paisa only when non-zero.
/// - Nepali uses Devanagari digits (intl's `ne` number symbols).
abstract final class Formatters {
  static String _numberLocale(String languageCode) =>
      languageCode == 'ne' ? 'ne' : 'en_IN';

  /// [amountMinor] is the contract's `amount_minor` (paisa for NPR).
  static String money(int amountMinor, String currency, String languageCode) {
    final locale = _numberLocale(languageCode);
    final negative = amountMinor < 0;
    final abs = amountMinor.abs();
    final hasFraction = abs % 100 != 0;
    final pattern = hasFraction ? '#,##,##0.00' : '#,##,##0';
    final number = NumberFormat(pattern, locale).format(abs / 100);
    final symbol = switch (currency.toUpperCase()) {
      'NPR' => languageCode == 'ne' ? 'रू' : 'Rs',
      final other => other,
    };
    return '${negative ? '-' : ''}$symbol $number';
  }

  static String integer(int value, String languageCode) =>
      NumberFormat('#,##,##0', _numberLocale(languageCode)).format(value);

  static String percent(double ratio, String languageCode) =>
      NumberFormat.percentPattern(_numberLocale(languageCode)).format(ratio);

  /// e.g. "2 Nov 2026" / "नोभेम्बर २, २०२६"
  static String date(DateTime value, String languageCode) =>
      DateFormat.yMMMd(languageCode).format(value.toLocal());

  /// e.g. "Monday, 2 November"
  static String dayHeading(DateTime value, String languageCode) =>
      DateFormat.MMMMEEEEd(languageCode).format(value.toLocal());

  static String dateTime(DateTime value, String languageCode) =>
      DateFormat.yMMMd(languageCode).add_jm().format(value.toLocal());
}
