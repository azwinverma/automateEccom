/// Exact rupee → paisa conversion for seller-entered prices. Never uses
/// floating point: "1,250.5" → 125050.
library;

enum PriceInputError { empty, invalid, tooManyDecimals, zero, tooLarge }

/// Upper bound accepted by the catalog API (`price_minor ≤ 10_000_000_000`).
const maxPriceMinor = 10000000000;

const _devanagariDigits = '०१२३४५६७८९';

/// Result of parsing; exactly one of [paisa] / [error] is non-null.
typedef PriceParse = ({int? paisa, PriceInputError? error});

/// Accepts Latin or Devanagari digits, optional thousands separators
/// (`,` or spaces), an optional "Rs"/"रू" prefix and up to 2 decimals.
PriceParse parseRupeesToPaisa(String raw) {
  var s = raw.trim();
  if (s.isEmpty) return (paisa: null, error: PriceInputError.empty);
  final buf = StringBuffer();
  for (final ch in s.split('')) {
    final i = _devanagariDigits.indexOf(ch);
    buf.write(i >= 0 ? '$i' : ch);
  }
  s = buf
      .toString()
      .replaceFirst(
        RegExp(r'^(rs\.?|npr|रू|रु\.?)\s*', caseSensitive: false),
        '',
      )
      .replaceAll(RegExp(r'[,\s ]'), '');
  final m = RegExp(r'^(\d+)(?:\.(\d*))?$').firstMatch(s);
  if (m == null) return (paisa: null, error: PriceInputError.invalid);
  final whole = m.group(1)!;
  final frac = m.group(2) ?? '';
  if (frac.length > 2) {
    return (paisa: null, error: PriceInputError.tooManyDecimals);
  }
  // Guard length before int.parse to avoid overflow on absurd input.
  if (whole.replaceFirst(RegExp(r'^0+'), '').length > 9) {
    return (paisa: null, error: PriceInputError.tooLarge);
  }
  final paisa = int.parse(whole) * 100 + int.parse(frac.padRight(2, '0'));
  if (paisa == 0) return (paisa: null, error: PriceInputError.zero);
  if (paisa > maxPriceMinor) {
    return (paisa: null, error: PriceInputError.tooLarge);
  }
  return (paisa: paisa, error: null);
}

/// Inverse for pre-filling an edit field: 125050 → "1250.50", 125000 → "1250".
String paisaToRupeeInput(int paisa) {
  final r = paisa ~/ 100;
  final p = paisa % 100;
  return p == 0 ? '$r' : '$r.${p.toString().padLeft(2, '0')}';
}
