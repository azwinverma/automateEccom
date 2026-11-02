import 'package:flutter/material.dart';

import '../../../../core/l10n/gen/app_localizations.dart';
import '../../../../design/tokens.g.dart';
import 'usage_meter.dart';

/// Signature meter: premium video has a monthly quota *and* a daily burst
/// cap (billing spec), shown as two separate bars.
class VideoCreditMeter extends StatelessWidget {
  const VideoCreditMeter({
    super.key,
    required this.monthlyUsed,
    required this.monthlyLimit,
    this.monthlyReserved = 0,
    this.monthlyAlertLevel,
    required this.dailyUsed,
    required this.dailyLimit,
  });

  final int monthlyUsed;
  final int? monthlyLimit;
  final int monthlyReserved;
  final String? monthlyAlertLevel;
  final int dailyUsed;

  /// `null` = no daily cap.
  final int? dailyLimit;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final daily = dailyLimit;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(
            AppSpace.s4,
            AppSpace.s3,
            AppSpace.s4,
            0,
          ),
          child: Row(
            children: [
              Icon(
                Icons.movie_creation_outlined,
                size: 20,
                color: theme.colorScheme.primary,
              ),
              const SizedBox(width: AppSpace.s2),
              Text(l.videoMeterTitle, style: theme.textTheme.titleSmall),
            ],
          ),
        ),
        UsageMeter(
          key: const Key('video-monthly'),
          label: l.videoMeterMonthly,
          used: monthlyUsed,
          limit: monthlyLimit,
          reserved: monthlyReserved,
          alertLevel: monthlyAlertLevel,
        ),
        if (daily == null)
          Padding(
            padding: const EdgeInsets.symmetric(
              horizontal: AppSpace.s4,
              vertical: AppSpace.s2,
            ),
            child: Row(
              children: [
                Expanded(
                  child: Text(
                    l.videoMeterDaily,
                    style: theme.textTheme.titleSmall,
                  ),
                ),
                Text(l.videoMeterNoDailyCap, style: theme.textTheme.bodyMedium),
              ],
            ),
          )
        else
          UsageMeter(
            key: const Key('video-daily'),
            label: l.videoMeterDaily,
            used: dailyUsed,
            limit: daily,
            reachedText: l.videoMeterDailyReached,
          ),
        Padding(
          padding: const EdgeInsets.fromLTRB(
            AppSpace.s4,
            AppSpace.s1,
            AppSpace.s4,
            AppSpace.s3,
          ),
          child: Text(
            l.videoMeterHelp,
            style: theme.textTheme.bodySmall?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
        ),
      ],
    );
  }
}
