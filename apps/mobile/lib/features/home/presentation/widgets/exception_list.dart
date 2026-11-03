import 'package:flutter/material.dart';

import '../../../../core/l10n/formatters.dart';
import '../../../../core/l10n/gen/app_localizations.dart';
import '../../../../design/app_theme.dart';
import '../../../../design/tokens.g.dart';
import '../../../../design/widgets/state_views.dart';

/// Exception kinds that need a human. Codes match backend `type` strings.
enum ExceptionType {
  paymentMismatch('payment_mismatch'),
  lowConfidenceAi('low_confidence_ai'),
  refundAboveThreshold('refund_above_threshold'),
  courierFailed('courier_failed'),
  channelExpired('channel_expired'),
  inventoryMismatch('inventory_mismatch'),
  publishFailed('publish_failed'),
  listingDrift('listing_drift'),
  ambiguousVariant('ambiguous_variant'),
  customerEscalation('customer_escalation'),
  providerFailure('provider_failure');

  const ExceptionType(this.code);
  final String code;

  static ExceptionType? fromCode(String code) {
    for (final t in values) {
      if (t.code == code) return t;
    }
    return null;
  }

  /// Money and customer-facing failures are urgent; the rest are warnings.
  bool get isUrgent => switch (this) {
    paymentMismatch ||
    refundAboveThreshold ||
    courierFailed ||
    customerEscalation => true,
    _ => false,
  };

  IconData get icon => switch (this) {
    paymentMismatch => Icons.payments_outlined,
    lowConfidenceAi => Icons.help_outline,
    refundAboveThreshold => Icons.undo_outlined,
    courierFailed => Icons.local_shipping_outlined,
    channelExpired => Icons.link_off_outlined,
    inventoryMismatch => Icons.inventory_2_outlined,
    publishFailed => Icons.cloud_off_outlined,
    listingDrift => Icons.sync_problem_outlined,
    ambiguousVariant => Icons.straighten_outlined,
    customerEscalation => Icons.support_agent_outlined,
    providerFailure => Icons.report_problem_outlined,
  };

  String label(AppLocalizations l) => switch (this) {
    paymentMismatch => l.exPaymentMismatch,
    lowConfidenceAi => l.exLowConfidenceAi,
    refundAboveThreshold => l.exRefundAboveThreshold,
    courierFailed => l.exCourierFailed,
    channelExpired => l.exChannelExpired,
    inventoryMismatch => l.exInventoryMismatch,
    publishFailed => l.exPublishFailed,
    listingDrift => l.exListingDrift,
    ambiguousVariant => l.exAmbiguousVariant,
    customerEscalation => l.exCustomerEscalation,
    providerFailure => l.exProviderFailure,
  };
}

enum ExceptionSeverity {
  urgent,
  high,
  normal;

  static ExceptionSeverity? fromCode(String? code) =>
      values.where((s) => s.name == code).firstOrNull;
}

@immutable
class ExceptionItem {
  const ExceptionItem({
    required this.id,
    required this.type,
    required this.subject,
    required this.occurredAt,
    ExceptionSeverity? severity,
    this.actionLabel,
  }) : _severity = severity;

  final String id;
  final ExceptionType type;
  final ExceptionSeverity? _severity;

  /// Short label for what fixes it, e.g. "Reconnect".
  final String? actionLabel;

  /// Server severity when known; otherwise derived from the type.
  ExceptionSeverity get severity =>
      _severity ??
      (type.isUrgent ? ExceptionSeverity.urgent : ExceptionSeverity.normal);

  bool get isUrgent => severity != ExceptionSeverity.normal;

  /// Server-provided reference, e.g. order number or customer name.
  final String subject;
  final DateTime occurredAt;
}

/// Exception Inbox: what needs the seller now, urgent first. Rows are
/// separated by hairlines, not wrapped in cards.
class ExceptionList extends StatelessWidget {
  const ExceptionList({super.key, required this.items, this.onTap});

  final List<ExceptionItem> items;
  final ValueChanged<ExceptionItem>? onTap;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    if (items.isEmpty) {
      return EmptyState(
        icon: Icons.task_alt,
        title: l.exceptionsEmptyTitle,
        body: l.exceptionsEmptyBody,
      );
    }
    final sorted = [...items]..sort((a, b) {
      if (a.type.isUrgent != b.type.isUrgent) {
        return a.type.isUrgent ? -1 : 1;
      }
      return b.occurredAt.compareTo(a.occurredAt);
    });
    return Column(
      children: [
        for (var i = 0; i < sorted.length; i++) ...[
          if (i > 0) const Divider(indent: AppSpace.s4 + 24 + AppSpace.s3),
          _ExceptionRow(item: sorted[i], onTap: onTap),
        ],
      ],
    );
  }
}

class _ExceptionRow extends StatelessWidget {
  const _ExceptionRow({required this.item, this.onTap});

  final ExceptionItem item;
  final ValueChanged<ExceptionItem>? onTap;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final palette = AppPalette.of(context);
    final lang = Localizations.localeOf(context).languageCode;
    final tone = switch (item.severity) {
      ExceptionSeverity.urgent => palette.danger,
      ExceptionSeverity.high => palette.warning,
      ExceptionSeverity.normal => palette.automation,
    };
    return InkWell(
      onTap: onTap == null ? null : () => onTap!(item),
      child: ConstrainedBox(
        constraints: const BoxConstraints(minHeight: 56),
        child: Padding(
          padding: const EdgeInsets.symmetric(
            horizontal: AppSpace.s4,
            vertical: AppSpace.s3,
          ),
          child: Row(
            children: [
              // A 3px tone rail carries urgency without a coloured blob.
              Container(width: 3, height: 32, color: tone),
              const SizedBox(width: AppSpace.s3),
              Icon(item.type.icon, color: tone, size: 24),
              const SizedBox(width: AppSpace.s3),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(item.type.label(l), style: theme.textTheme.titleSmall),
                    Text(
                      [
                        item.subject,
                        if (item.actionLabel != null) item.actionLabel!,
                      ].join(' · '),
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ],
                ),
              ),
              Text(
                Formatters.dateTime(item.occurredAt, lang),
                style: theme.textTheme.labelSmall?.copyWith(
                  color: palette.muted,
                ),
              ),
              if (onTap != null)
                Icon(
                  Icons.chevron_right,
                  color: theme.colorScheme.onSurfaceVariant,
                ),
            ],
          ),
        ),
      ),
    );
  }
}
