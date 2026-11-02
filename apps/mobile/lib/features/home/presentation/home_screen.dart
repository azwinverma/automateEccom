import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/auth/session_controller.dart';
import '../../../core/l10n/formatters.dart';
import '../../../core/l10n/gen/app_localizations.dart';
import '../../../design/tokens.g.dart';
import '../../../design/widgets/section_header.dart';
import 'widgets/autopilot_status_strip.dart';
import 'widgets/exception_list.dart';
import 'widgets/quick_actions.dart';
import 'widgets/today_metrics.dart';

/// Home, ordered by seller priority: what needs me → act fast → today's
/// numbers. Phase 0 has no order/inbox/automation domains, so those regions
/// render honest empty states.
class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final lang = Localizations.localeOf(context).languageCode;
    final session = ref.watch(sessionControllerProvider);
    final signedIn = session is SessionSignedIn ? session : null;
    final firstName = (signedIn?.me.user.fullName ?? '').split(' ').first;
    final shopName = signedIn?.merchant?.name ?? '';

    // Real sources arrive with the orders/inbox/automation domains.
    const exceptions = <ExceptionItem>[];
    const AutopilotStatus? autopilot = null;

    return Scaffold(
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: () =>
              ref.read(sessionControllerProvider.notifier).refreshMe(),
          child: ListView(
            padding: const EdgeInsets.only(bottom: AppSpace.s8),
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(
                  AppSpace.s4,
                  AppSpace.s4,
                  AppSpace.s4,
                  AppSpace.s3,
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      shopName,
                      style: theme.textTheme.labelMedium?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                    Text(
                      l.homeGreeting(firstName),
                      style: theme.textTheme.headlineSmall,
                    ),
                    Text(
                      Formatters.dayHeading(DateTime.now(), lang),
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ],
                ),
              ),
              const AutopilotStatusStrip(status: autopilot),
              SectionHeader(
                l.homeSectionNeedsYou,
                trailing: exceptions.isEmpty
                    ? null
                    : Text(l.exceptionsCount(exceptions.length)),
              ),
              const ExceptionList(items: exceptions),
              SectionHeader(l.quickActionsTitle),
              QuickActionsGrid(
                onSelected: (a) => context.push('/soon/${a.slug}'),
              ),
              SectionHeader(l.homeSectionToday),
              const TodayMetrics(),
            ],
          ),
        ),
      ),
    );
  }
}
