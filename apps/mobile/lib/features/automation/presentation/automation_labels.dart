import 'package:flutter/material.dart';

import '../../../core/l10n/gen/app_localizations.dart';
import '../../../design/app_theme.dart';
import '../data/automation_api.dart';

String actionLabel(
  AppLocalizations l,
  String? action, {
  String kind = 'action',
}) {
  if (kind == 'approval') return l.autoActionContinue;
  return switch (action) {
    'notify_seller' => l.autoActionNotifySeller,
    'add_order_note' => l.autoActionAddOrderNote,
    'send_customer_message' => l.autoActionSendCustomerMessage,
    'send_review_request' => l.autoActionSendReviewRequest,
    'book_courier' => l.autoActionBookCourier,
    'request_pickup' => l.autoActionRequestPickup,
    'request_reattempt' => l.autoActionRequestReattempt,
    'approve_return' => l.autoActionApproveReturn,
    'send_ai_reply' => l.autoActionSendAiReply,
    'issue_refund' => l.autoActionIssueRefund,
    _ => l.autoActionOther,
  };
}

/// Why something waits for a person (the Decision Policy rule that decided).
String waitingReason(AppLocalizations l, String? rule) => switch (rule) {
  'assisted_mode' => l.ruleAssisted,
  'r2_not_enabled' => l.ruleR2Off,
  'above_threshold' => l.ruleAboveLimit,
  'below_confidence_threshold' || 'low_confidence' => l.ruleNotSure,
  'high_risk' => l.ruleHighRisk,
  'missing_entitlement' ||
  'missing_capability' ||
  'prohibited' => l.ruleBlocked,
  _ => l.ruleApprovalStep,
};

/// Why something ran on its own.
String ranReason(AppLocalizations l, String rule) {
  if (rule == 'informational') return l.ruleNotice;
  if (rule.endsWith('_r2_enabled')) return l.ruleRanEnabled;
  if (rule.startsWith('autopilot')) return l.ruleRanAutopilot;
  return l.ruleRanSmart;
}

String modeLabel(AppLocalizations l, String mode) => switch (mode) {
  'smart' => l.ccModeSmart,
  'autopilot' => l.ccModeAutopilot,
  _ => l.ccModeAssisted,
};

String workflowStatusLabel(AppLocalizations l, WorkflowSummary w) {
  if (w.brokeRepeatedly) return l.wfBroke;
  return switch (w.status) {
    'active' => l.wfStatusActive,
    'paused' => l.wfStatusPaused,
    _ => l.wfStatusDraft,
  };
}

(Color, Color) workflowStatusColors(BuildContext context, WorkflowSummary w) {
  final p = AppPalette.of(context);
  if (w.brokeRepeatedly) return (p.danger, p.dangerSoft);
  return switch (w.status) {
    'active' => (p.success, p.successSoft),
    'paused' => (p.warning, p.warningSoft),
    _ => (p.muted, p.line),
  };
}
