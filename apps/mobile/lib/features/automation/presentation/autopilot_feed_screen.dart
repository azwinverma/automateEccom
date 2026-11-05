import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/l10n/formatters.dart';
import '../../../core/l10n/gen/app_localizations.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens.g.dart';
import '../../../design/widgets/state_views.dart';
import '../data/automation_api.dart';
import 'automation_labels.dart';

/// What automation did on its own in the last 7 days, and why it was allowed.
class AutopilotFeedScreen extends ConsumerWidget {
  const AutopilotFeedScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final palette = AppPalette.of(context);
    final lang = Localizations.localeOf(context).languageCode;
    return Scaffold(
      appBar: AppBar(title: Text(l.feedTitle)),
      body: ListView(
        children: [
          AsyncValueView<ControlCenter>(
            value: ref.watch(controlCenterProvider),
            onRetry: () => ref.invalidate(controlCenterProvider),
            loading: const SkeletonList(rows: 4),
            isEmpty: (cc) => cc.feed.isEmpty,
            empty: Padding(
              padding: const EdgeInsets.all(AppSpace.s4),
              child: Text(
                l.feedEmpty,
                key: const Key('feed-empty'),
                style: TextStyle(color: palette.muted),
              ),
            ),
            data:
                (cc) => Column(
                  children: [
                    for (final d in cc.feed)
                      ListTile(
                        key: Key('feed-${d.id}'),
                        leading: const Icon(Icons.bolt_outlined),
                        title: Text(actionLabel(l, d.action)),
                        subtitle: Text(
                          '${ranReason(l, d.rule)} · ${Formatters.dateTime(d.createdAt, lang)}',
                        ),
                        trailing:
                            d.impactMinor == null
                                ? null
                                : Text(
                                  Formatters.money(
                                    d.impactMinor!,
                                    d.currency ?? cc.currency,
                                    lang,
                                  ),
                                ),
                      ),
                  ],
                ),
          ),
        ],
      ),
    );
  }
}
