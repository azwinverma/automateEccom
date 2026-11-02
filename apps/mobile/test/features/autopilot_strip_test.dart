import 'package:commerce_os_seller/features/home/presentation/widgets/autopilot_status_strip.dart';
import 'package:flutter_test/flutter_test.dart';

import '../helpers/pump.dart';

void main() {
  testWidgets('null status says automation is not active (no fake counts)',
      (tester) async {
    await pumpLocalized(tester, const AutopilotStatusStrip(status: null));
    expect(find.textContaining('Not active yet'), findsOneWidget);
    expect(find.textContaining('handled'), findsNothing);
  });

  testWidgets('shows mode and counts', (tester) async {
    await pumpLocalized(
      tester,
      const AutopilotStatusStrip(
        status: AutopilotStatus(
          mode: AutopilotMode.smart,
          automatedCount: 18,
          needsAttentionCount: 3,
        ),
      ),
    );
    expect(find.text('Smart'), findsOneWidget);
    expect(find.bySemanticsLabel('Autopilot: Smart'), findsOneWidget);
    expect(find.text('18 handled'), findsOneWidget);
    expect(find.text('3 need you'), findsOneWidget);
    expect(find.text('Routine work runs, risky work waits for you'),
        findsOneWidget);
  });
}
