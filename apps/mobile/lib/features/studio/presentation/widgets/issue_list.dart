import 'package:flutter/material.dart';

import '../../../../core/l10n/gen/app_localizations.dart';
import '../../../../design/app_theme.dart';
import '../../../../design/tokens.g.dart';
import '../../data/studio_models.dart';
import '../studio_copy.dart';

/// Grounding / quality warnings as plain rows with a warning rail.
class IssueList extends StatelessWidget {
  const IssueList({super.key, required this.issues});

  final List<DraftIssue> issues;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final palette = AppPalette.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (final i in issues)
          Container(
            margin: const EdgeInsets.only(bottom: AppSpace.s2),
            padding: const EdgeInsets.all(AppSpace.s3),
            decoration: BoxDecoration(
              color: palette.warningSoft,
              border: Border(
                left: BorderSide(color: palette.warning, width: 3),
              ),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(Icons.report_outlined, size: 20, color: palette.warning),
                const SizedBox(width: AppSpace.s2),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        issueMessage(l, i),
                        style: theme.textTheme.bodyMedium?.copyWith(
                          color:
                              theme.brightness == Brightness.light
                                  ? AppColors.neutralInk
                                  : null,
                        ),
                      ),
                      if (i.field.isNotEmpty && i.field != 'photos')
                        Text(
                          l.issueInField(issueFieldLabel(l, i.field)),
                          style: theme.textTheme.labelSmall?.copyWith(
                            color: theme.colorScheme.onSurfaceVariant,
                          ),
                        ),
                      if (i.excerpt != null && i.excerpt!.isNotEmpty)
                        Text(
                          '“${i.excerpt}”',
                          style: theme.textTheme.bodySmall?.copyWith(
                            fontStyle: FontStyle.italic,
                          ),
                        ),
                    ],
                  ),
                ),
              ],
            ),
          ),
      ],
    );
  }
}
