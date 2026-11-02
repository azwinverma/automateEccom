import 'package:commerce_os_seller/design/widgets/nivaro_brand.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('logo renders the approved artwork in light and dark', (
    tester,
  ) async {
    for (final brightness in Brightness.values) {
      await tester.pumpWidget(
        MaterialApp(
          theme: ThemeData(brightness: brightness),
          home: const Scaffold(
            body: Column(
              children: [
                NivaroLogo(height: 24),
                NivaroMark(
                  size: 32,
                  monoColor: Colors.white,
                  semanticLabel: 'Nivaro',
                ),
              ],
            ),
          ),
        ),
      );
      expect(tester.takeException(), isNull);
      expect(find.bySemanticsLabel('Nivaro'), findsNWidgets(2));
      final logo = tester.getSize(find.byType(NivaroLogo));
      expect(logo.height, 24);
      expect(
        logo.width,
        closeTo(
          24 * NivaroAssets.markRatio +
              24 * 0.3 +
              24 * 0.6 * NivaroAssets.wordRatio,
          0.5,
        ),
      );
      final images = tester
          .widgetList<Image>(find.byType(Image))
          .map((i) => (i.image as AssetImage).assetName);
      expect(
        images,
        containsAll([
          NivaroAssets.mark,
          NivaroAssets.wordmark,
          NivaroAssets.markMono,
        ]),
      );
    }
  });
}
