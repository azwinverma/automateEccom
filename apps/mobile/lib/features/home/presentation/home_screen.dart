import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/auth/session_controller.dart';
import '../../../core/l10n/formatters.dart';
import '../../../core/l10n/gen/app_localizations.dart';
import '../../../design/tokens.g.dart';
import '../../../design/widgets/nivaro_brand.dart';
import '../../../design/widgets/section_header.dart';
import '../../../design/widgets/state_views.dart';
import '../../automation/data/automation_api.dart';
import '../../automation/presentation/control_center.dart';
import '../../channels/presentation/reconnect_sheet.dart';
import '../../exceptions/data/exception_routing.dart';
import '../../exceptions/data/exceptions_api.dart';
import '../../exceptions/presentation/exception_mapping.dart';
import '../../fulfillment/data/fulfillment_api.dart';
import '../../fulfillment/presentation/cod_screen.dart';
import '../../returns/data/returns_api.dart';
import '../../returns/presentation/returns_list_screen.dart';
import 'widgets/autopilot_status_strip.dart';
import 'widgets/exception_list.dart';
import 'widgets/quick_actions.dart';
import 'widgets/today_metrics.dart';

/// Home, ordered by seller priority: what needs me → act fast → today's
/// numbers. Exceptions are live (`GET /exceptions`); orders/revenue still
/// have no backend domain, so those stay honest empty states.
class HomeScreen extends ConsumerWidget {
  const HomeScreen({super.key});

  Future<void> _open(
    BuildContext context,
    WidgetRef ref,
    ApiException e,
  ) async {
    switch (resolveExceptionAction(e)) {
      case OpenRoute(:final location):
        await context.push(location);
        ref.invalidate(exceptionsProvider);
      case ReconnectChannel(:final connectionId):
        await showReconnectSheet(
          context,
          connectionId: connectionId,
          channelName: e.details['name'] as String?,
        );
      case DismissLocally(:final exceptionId):
        await ref
            .read(dismissedExceptionsProvider.notifier)
            .dismiss(exceptionId);
      case NoAction():
        break;
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final lang = Localizations.localeOf(context).languageCode;
    final session = ref.watch(sessionControllerProvider);
    final signedIn = session is SessionSignedIn ? session : null;
    final firstName = (signedIn?.me.user.fullName ?? '').split(' ').first;
    final shopName = signedIn?.merchant?.name ?? '';
    final exceptions = ref.watch(exceptionsProvider);
    final mode = ref.watch(automationModeProvider).valueOrNull;
    final count = exceptions.valueOrNull?.length;

    final autopilot =
        mode == null || count == null
            ? null
            : AutopilotStatus(
              mode: switch (mode) {
                'smart' => AutopilotMode.smart,
                'autopilot' => AutopilotMode.autopilot,
                _ => AutopilotMode.assisted,
              },
              // No automation-run metric exists yet; shown only when it does.
              automatedCount: null,
              needsAttentionCount: count,
            );

    return Scaffold(
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: () async {
            ref
              ..invalidate(exceptionsProvider)
              ..invalidate(automationModeProvider)
              ..invalidate(controlCenterProvider)
              ..invalidate(codOverviewProvider)
              ..invalidate(returnsPageProvider('to_decide'));
            await Future.wait<Object?>([
              ref.read(sessionControllerProvider.notifier).refreshMe(),
              ref
                  .read(exceptionsProvider.future)
                  .catchError((Object _) => <ApiException>[]),
            ]);
          },
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
                    Row(
                      children: [
                        NivaroMark(size: 18, semanticLabel: l.appName),
                        const SizedBox(width: AppSpace.s2),
                        Expanded(
                          child: Text(
                            shopName,
                            overflow: TextOverflow.ellipsis,
                            style: theme.textTheme.labelMedium?.copyWith(
                              color: theme.colorScheme.onSurfaceVariant,
                            ),
                          ),
                        ),
                      ],
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
              const ControlCenterCard(),
              // The Control Center replaces the strip once its summary has loaded.
              if (!ref.watch(controlCenterProvider).hasValue)
                AutopilotStatusStrip(status: autopilot),
              const CodHomeCard(),
              const ReturnsHomeCard(),
              SectionHeader(
                l.homeSectionNeedsYou,
                trailing:
                    count == null || count == 0
                        ? null
                        : Text(l.exceptionsCount(count)),
              ),
              AsyncValueView<List<ApiException>>(
                value: exceptions,
                onRetry: () => ref.invalidate(exceptionsProvider),
                loading: const SkeletonList(rows: 2),
                data: (items) {
                  final byId = {for (final e in items) e.id: e};
                  return ExceptionList(
                    items: toExceptionItems(l, items),
                    onTap: (item) {
                      final e = byId[item.id];
                      if (e != null) _open(context, ref, e);
                    },
                  );
                },
              ),
              SectionHeader(l.quickActionsTitle),
              QuickActionsGrid(
                onSelected:
                    (a) =>
                        a.isTab ? context.go(a.route) : context.push(a.route),
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
