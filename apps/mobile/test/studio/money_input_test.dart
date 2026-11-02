import 'package:commerce_os_seller/core/l10n/money_input.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  int? paisa(String s) => parseRupeesToPaisa(s).paisa;
  PriceInputError? err(String s) => parseRupeesToPaisa(s).error;

  test('whole rupees and paisa convert exactly', () {
    expect(paisa('1250'), 125000);
    expect(paisa('1250.5'), 125050);
    expect(paisa('1250.50'), 125050);
    expect(paisa('1250.05'), 125005);
    expect(paisa('0.01'), 1);
    expect(paisa('.5'), null); // needs a whole part
    expect(paisa('1.'), 100);
  });

  test('no floating point drift on classic cases', () {
    // 0.1 + 0.2 style values and 19.99 * 100 = 1998.9999… in doubles.
    expect(paisa('19.99'), 1999);
    expect(paisa('0.29'), 29);
    expect(paisa('1.15'), 115);
    expect(paisa('4.35'), 435);
    expect(paisa('99999999.99'), 9999999999);
  });

  test('separators, prefixes and Devanagari digits', () {
    expect(paisa('1,250'), 125000);
    expect(paisa('1,25,000'), 12500000);
    expect(paisa(' Rs 1,250.50 '), 125050);
    expect(paisa('रू १,२५०'), 125000);
    expect(paisa('१२५०.५०'), 125050);
    expect(paisa('NPR 500'), 50000);
  });

  test('rejections', () {
    expect(err(''), PriceInputError.empty);
    expect(err('   '), PriceInputError.empty);
    expect(err('0'), PriceInputError.zero);
    expect(err('0.00'), PriceInputError.zero);
    expect(err('-5'), PriceInputError.invalid);
    expect(err('12abc'), PriceInputError.invalid);
    expect(err('1.2.3'), PriceInputError.invalid);
    expect(err('1.234'), PriceInputError.tooManyDecimals);
    expect(err('100000001'), PriceInputError.tooLarge); // > 10_000_000_000 paisa
    expect(err('99999999999999999999'), PriceInputError.tooLarge);
  });

  test('upper bound is the catalog API limit', () {
    expect(paisa('100000000'), maxPriceMinor);
  });

  test('paisa back to an editable string', () {
    expect(paisaToRupeeInput(125000), '1250');
    expect(paisaToRupeeInput(125050), '1250.50');
    expect(paisaToRupeeInput(5), '0.05');
    for (final v in [1, 99, 100, 125005, 9999999999]) {
      expect(paisa(paisaToRupeeInput(v)), v);
    }
  });
}
