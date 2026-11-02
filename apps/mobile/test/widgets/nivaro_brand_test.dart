import 'package:commerce_os_seller/design/brand_geometry.g.dart';
import 'package:commerce_os_seller/design/widgets/nivaro_brand.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  testWidgets('logo paints colour and mono marks and exposes one label', (tester) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: Column(
            children: [
              NivaroLogo(height: 24),
              NivaroMark(size: 32, monoColor: Colors.white, semanticLabel: 'Nivaro'),
            ],
          ),
        ),
      ),
    );
    expect(tester.takeException(), isNull);
    expect(find.bySemanticsLabel('Nivaro'), findsNWidgets(2));
    final logo = tester.getSize(find.byType(NivaroLogo));
    // mark (24) + gap + wordmark (0.72 × 24 high at 150:46).
    expect(logo.height, 24);
    expect(logo.width, closeTo(24 + 24 * 0.42 + 24 * 0.72 * 150 / 46, 0.5));
  });

  test('generated geometry matches the shared brand source', () {
    expect(NivaroMarkGeometry.diagonal, [24, 16, 40, 48]);
    expect(NivaroMarkGeometry.ribbon, 12);
    expect(NivaroWordmarkGeometry.circles.length, 2);
  });
}
