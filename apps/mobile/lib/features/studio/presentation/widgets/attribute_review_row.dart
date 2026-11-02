import 'package:flutter/material.dart';

import '../../../../core/l10n/formatters.dart';
import '../../../../core/l10n/gen/app_localizations.dart';
import '../../../../design/app_theme.dart';
import '../../../../design/tokens.g.dart';
import '../../data/review_form.dart';

String humaniseKey(String key) {
  final s = key.replaceAll('_', ' ').trim();
  return s.isEmpty ? key : '${s[0].toUpperCase()}${s.substring(1)}';
}

/// One AI attribute. Low-confidence values carry a brand-blue "Please check"
/// rail and need an explicit tap (accept or edit).
class AttributeReviewRow extends StatelessWidget {
  const AttributeReviewRow({
    super.key,
    required this.attribute,
    required this.onAccept,
    required this.onEdit,
    this.showError = false,
  });

  final EditableAttribute attribute;
  final VoidCallback onAccept;
  final VoidCallback onEdit;
  final bool showError;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final palette = AppPalette.of(context);
    final lang = Localizations.localeOf(context).languageCode;
    final a = attribute;
    final pending = !a.acknowledged;
    final rail =
        pending
            ? (showError ? palette.danger : palette.automation)
            : Colors.transparent;

    return Container(
      decoration: BoxDecoration(
        color: pending ? palette.automationSoft : null,
        border: Border(left: BorderSide(color: rail, width: 3)),
      ),
      padding: const EdgeInsets.fromLTRB(
        AppSpace.s4 - 3,
        AppSpace.s3,
        AppSpace.s4,
        AppSpace.s2,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      humaniseKey(a.source.key),
                      style: theme.textTheme.labelMedium?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                    Text(a.value, style: theme.textTheme.bodyLarge),
                  ],
                ),
              ),
              Text(
                l.confidenceLabel(
                  Formatters.percent(a.source.confidence, lang),
                ),
                style: theme.textTheme.labelSmall?.copyWith(
                  color: palette.automation,
                ),
              ),
            ],
          ),
          if (a.needsCheck)
            Wrap(
              crossAxisAlignment: WrapCrossAlignment.center,
              spacing: AppSpace.s2,
              children: [
                Text(
                  switch (a.decision) {
                    AttributeDecision.pending => l.attrPleaseCheck,
                    AttributeDecision.accepted => l.attrAccepted,
                    AttributeDecision.edited => l.attrEdited,
                  },
                  key: Key('attr-state-${a.source.key}'),
                  style: theme.textTheme.labelMedium?.copyWith(
                    color:
                        pending
                            ? (showError ? palette.danger : palette.automation)
                            : palette.success,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                if (a.decision != AttributeDecision.accepted)
                  TextButton(
                    key: Key('attr-accept-${a.source.key}'),
                    onPressed: onAccept,
                    child: Text(l.attrAccept),
                  ),
                TextButton(
                  key: Key('attr-edit-${a.source.key}'),
                  onPressed: onEdit,
                  child: Text(l.attrEdit),
                ),
              ],
            ),
        ],
      ),
    );
  }
}
