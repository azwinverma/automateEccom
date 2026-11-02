import 'package:commerce_os_seller/core/l10n/formatters.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:intl/date_symbol_data_local.dart';

void main() {
  setUpAll(() async {
    await initializeDateFormatting('en');
    await initializeDateFormatting('ne');
  });

  group('money (NPR)', () {
    test('English uses Rs, lakh grouping, no paisa when whole', () {
      expect(Formatters.money(125000, 'NPR', 'en'), 'Rs 1,250');
      expect(Formatters.money(12500000, 'NPR', 'en'), 'Rs 1,25,000');
      expect(Formatters.money(125050, 'NPR', 'en'), 'Rs 1,250.50');
      expect(Formatters.money(0, 'NPR', 'en'), 'Rs 0');
      expect(Formatters.money(-5000, 'NPR', 'en'), '-Rs 50');
    });

    test('Nepali uses रू and Devanagari digits', () {
      expect(Formatters.money(125000, 'NPR', 'ne'), 'रू १,२५०');
      expect(Formatters.money(12500000, 'NPR', 'ne'), 'रू १,२५,०००');
      expect(Formatters.money(125050, 'NPR', 'ne'), 'रू १,२५०.५०');
    });

    test('other currencies show their code', () {
      expect(Formatters.money(1000, 'USD', 'en'), 'USD 10');
    });
  });

  test('integers follow locale digits', () {
    expect(Formatters.integer(120000, 'en'), '1,20,000');
    expect(Formatters.integer(120, 'ne'), '१२०');
  });

  test('dates are localized', () {
    final d = DateTime(2026, 11, 2, 12);
    expect(Formatters.date(d, 'en'), 'Nov 2, 2026');
    expect(Formatters.date(d, 'ne'), contains('२०२६'));
  });
}
