import 'package:commerce_os_seller/design/app_theme.dart';
import 'package:commerce_os_seller/design/widgets/meter_bar.dart';
import 'package:commerce_os_seller/features/settings/presentation/widgets/usage_meter.dart';
import 'package:commerce_os_seller/features/settings/presentation/widgets/video_credit_meter.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import '../helpers/pump.dart';

Color _barColor(WidgetTester tester) {
  final boxes = tester
      .widgetList<ColoredBox>(
        find.descendant(
          of: find.byType(FractionallySizedBox),
          matching: find.byType(ColoredBox),
        ),
      )
      .toList();
  return boxes.single.color;
}

void main() {
  test('threshold boundaries', () {
    expect(usageLevelFor(0.69), UsageLevel.normal);
    expect(usageLevelFor(0.70), UsageLevel.notice);
    expect(usageLevelFor(0.849), UsageLevel.notice);
    expect(usageLevelFor(0.85), UsageLevel.warning);
    expect(usageLevelFor(0.999), UsageLevel.warning);
    expect(usageLevelFor(1.0), UsageLevel.reached);
    expect(usageLevelFor(1.3), UsageLevel.reached);
  });

  final cases = <(int, UsageLevel, String?)>[
    (50, UsageLevel.normal, null),
    (70, UsageLevel.notice, 'Over 70% used'),
    (85, UsageLevel.warning, 'Almost at the limit'),
    (100, UsageLevel.reached, 'Limit reached. Buy credits or upgrade to keep going.'),
  ];

  for (final (used, level, text) in cases) {
    testWidgets('$used/100 renders ${level.name} state', (tester) async {
      await pumpLocalized(
        tester,
        UsageMeter(label: 'AI writing', used: used, limit: 100),
      );
      expect(find.text('$used of 100'), findsOneWidget);
      if (text == null) {
        expect(find.byKey(Key('usage-level-${level.name}')), findsNothing);
      } else {
        expect(find.text(text), findsOneWidget);
      }
      const palette = AppPalette.light;
      final expected = switch (level) {
        UsageLevel.normal => AppTheme.light().colorScheme.primary,
        UsageLevel.notice => palette.accentSun,
        UsageLevel.warning => palette.warning,
        UsageLevel.reached => palette.danger,
      };
      expect(_barColor(tester), expected);
    });
  }

  testWidgets('reserved usage counts toward the threshold', (tester) async {
    await pumpLocalized(
      tester,
      const UsageMeter(label: 'AI images', used: 80, reserved: 6, limit: 100),
    );
    expect(find.text('Almost at the limit'), findsOneWidget);
    expect(find.text('6 in progress'), findsOneWidget);
  });

  testWidgets('server alert level wins when stricter', (tester) async {
    await pumpLocalized(
      tester,
      const UsageMeter(label: 'x', used: 10, limit: 100, alertLevel: '85'),
    );
    expect(find.text('Almost at the limit'), findsOneWidget);
  });

  testWidgets('unlimited shows no bar', (tester) async {
    await pumpLocalized(
      tester,
      const UsageMeter(label: 'Products', used: 12, limit: null),
    );
    expect(find.text('Unlimited'), findsOneWidget);
    expect(find.byType(MeterBar), findsNothing);
  });

  testWidgets('Nepali uses Devanagari digits', (tester) async {
    await pumpLocalized(
      tester,
      const UsageMeter(label: 'AI लेखन', used: 120, limit: 500),
      locale: const Locale('ne'),
    );
    expect(find.text('५०० मध्ये १२०'), findsOneWidget);
  });

  group('VideoCreditMeter', () {
    testWidgets('shows monthly quota and daily burst separately',
        (tester) async {
      await pumpLocalized(
        tester,
        const VideoCreditMeter(
          monthlyUsed: 12,
          monthlyLimit: 20,
          dailyUsed: 4,
          dailyLimit: 4,
        ),
      );
      expect(find.text('Video credits'), findsOneWidget);
      expect(find.byKey(const Key('video-monthly')), findsOneWidget);
      expect(find.byKey(const Key('video-daily')), findsOneWidget);
      expect(find.text('12 of 20'), findsOneWidget);
      expect(find.text('4 of 4'), findsOneWidget);
      // Daily cap reached, monthly is not: copy says it resets tomorrow.
      expect(find.text("Today's cap reached. It resets tomorrow."),
          findsOneWidget);
      expect(find.text('Limit reached. Buy credits or upgrade to keep going.'),
          findsNothing);
    });

    testWidgets('no daily cap', (tester) async {
      await pumpLocalized(
        tester,
        const VideoCreditMeter(
          monthlyUsed: 2,
          monthlyLimit: 60,
          dailyUsed: 0,
          dailyLimit: null,
        ),
      );
      expect(find.text('No daily cap'), findsOneWidget);
      expect(find.byKey(const Key('video-daily')), findsNothing);
    });
  });
}
