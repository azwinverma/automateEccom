import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/errors/api_error.dart';
import '../../../core/errors/error_messages.dart';
import '../../../core/l10n/gen/app_localizations.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens.g.dart';
import '../../../design/widgets/section_header.dart';
import '../data/intelligence_api.dart';
import 'intelligence_labels.dart';

/// COD delivery risk for an order (CODI). Hidden for prepaid orders and when
/// there's no assessment or the plan doesn't include it (404/403).
class CodRiskCard extends ConsumerWidget {
  const CodRiskCard({
    super.key,
    required this.orderId,
    required this.paymentMethod,
  });

  final String orderId;
  final String paymentMethod;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    if (paymentMethod != 'cod') return const SizedBox.shrink();
    final risk = ref.watch(codRiskProvider(orderId)).valueOrNull;
    if (risk == null) return const SizedBox.shrink();
    return CodRiskView(risk: risk);
  }
}

class CodRiskView extends ConsumerStatefulWidget {
  const CodRiskView({super.key, required this.risk});

  final CodRisk risk;

  @override
  ConsumerState<CodRiskView> createState() => _CodRiskViewState();
}

class _CodRiskViewState extends ConsumerState<CodRiskView> {
  late CodRisk _risk = widget.risk;
  String? _error;

  @override
  void didUpdateWidget(covariant CodRiskView old) {
    super.didUpdateWidget(old);
    if (old.risk != widget.risk) _risk = widget.risk;
  }

  Future<void> _save(Future<CodRisk> Function() call) async {
    final l = AppLocalizations.of(context);
    setState(() => _error = null);
    try {
      final next = await call();
      if (!mounted) return;
      setState(() => _risk = next);
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(l.riskUpdated)));
    } on ApiError catch (e) {
      if (mounted) setState(() => _error = localizedErrorMessage(l, e));
    }
  }

  Future<void> _override() async {
    final res = await showDialog<(String, String)>(
      context: context,
      builder: (_) => _OverrideDialog(current: _risk.level),
    );
    if (res == null) return;
    await _save(
      () => ref
          .read(intelligenceApiProvider)
          .override(_risk.orderId, res.$1, res.$2),
    );
  }

  Future<void> _dispute() async {
    final note = await showDialog<String>(
      context: context,
      builder: (_) => const _DisputeDialog(),
    );
    if (note == null) return;
    await _save(
      () => ref.read(intelligenceApiProvider).dispute(_risk.orderId, note),
    );
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final p = AppPalette.of(context);
    final r = _risk;
    final (fg, bg) = switch (r.level) {
      'HIGHER' => (p.danger, p.dangerSoft),
      'MEDIUM' => (p.warning, p.warningSoft),
      _ => (p.success, p.successSoft),
    };
    const pad = EdgeInsets.symmetric(horizontal: AppSpace.s4);
    return Column(
      key: const Key('cod-risk'),
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SectionHeader(l.riskTitle),
        Padding(
          padding: pad,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                key: Key('cod-risk-level-${r.level}'),
                padding: const EdgeInsets.symmetric(
                  horizontal: AppSpace.s2,
                  vertical: 2,
                ),
                decoration: BoxDecoration(
                  color: bg,
                  borderRadius: BorderRadius.circular(AppRadius.md),
                ),
                child: Text(
                  riskLevelLabel(l, r.level),
                  style: theme.textTheme.labelMedium?.copyWith(color: fg),
                ),
              ),
              const SizedBox(height: AppSpace.s1),
              Text(
                riskActionLabel(l, r.recommendedAction),
                style: theme.textTheme.titleSmall,
              ),
              for (final f in r.factors)
                if (riskFactorLabel(l, f) case final text?)
                  Text('• $text', style: theme.textTheme.bodySmall),
              if (r.overridden && (r.overrideReason ?? '').isNotEmpty)
                Text(
                  l.riskOverridden(r.overrideReason!),
                  style: theme.textTheme.bodySmall,
                ),
              if (r.disputed && (r.disputeNote ?? '').isNotEmpty)
                Text(
                  l.riskDisputed(r.disputeNote!),
                  style: theme.textTheme.bodySmall,
                ),
              const SizedBox(height: AppSpace.s1),
              Text(
                l.riskFairness,
                style: theme.textTheme.bodySmall?.copyWith(color: p.muted),
              ),
              if (_error != null)
                Text(
                  _error!,
                  key: const Key('cod-risk-error'),
                  style: theme.textTheme.bodySmall?.copyWith(color: p.danger),
                ),
              Wrap(
                spacing: AppSpace.s2,
                children: [
                  TextButton(
                    key: const Key('cod-risk-override'),
                    onPressed: _override,
                    child: Text(l.riskOverride),
                  ),
                  TextButton(
                    key: const Key('cod-risk-dispute'),
                    onPressed: _dispute,
                    child: Text(l.riskDispute),
                  ),
                ],
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _OverrideDialog extends StatefulWidget {
  const _OverrideDialog({required this.current});

  final String current;

  @override
  State<_OverrideDialog> createState() => _OverrideDialogState();
}

class _OverrideDialogState extends State<_OverrideDialog> {
  late String _level = widget.current;
  final _reason = TextEditingController();

  @override
  void dispose() {
    _reason.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final ok = _reason.text.trim().length >= 3;
    return AlertDialog(
      title: Text(l.riskOverrideTitle),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          for (final lv in const ['LOW', 'MEDIUM', 'HIGHER'])
            ListTile(
              key: Key('cod-risk-choose-$lv'),
              contentPadding: EdgeInsets.zero,
              leading: Icon(
                _level == lv
                    ? Icons.radio_button_checked
                    : Icons.radio_button_unchecked,
              ),
              title: Text(riskLevelLabel(l, lv)),
              onTap: () => setState(() => _level = lv),
            ),
          TextField(
            key: const Key('cod-risk-reason'),
            controller: _reason,
            maxLength: 300,
            decoration: InputDecoration(labelText: l.riskOverrideReason),
            onChanged: (_) => setState(() {}),
          ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: Text(l.riskCancel),
        ),
        FilledButton(
          key: const Key('cod-risk-save'),
          onPressed:
              ok
                  ? () => Navigator.pop(context, (_level, _reason.text.trim()))
                  : null,
          child: Text(l.riskSave),
        ),
      ],
    );
  }
}

class _DisputeDialog extends StatefulWidget {
  const _DisputeDialog();

  @override
  State<_DisputeDialog> createState() => _DisputeDialogState();
}

class _DisputeDialogState extends State<_DisputeDialog> {
  final _note = TextEditingController();

  @override
  void dispose() {
    _note.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return AlertDialog(
      title: Text(l.riskDisputeTitle),
      content: TextField(
        key: const Key('cod-risk-note'),
        controller: _note,
        maxLength: 500,
        decoration: InputDecoration(labelText: l.riskDisputeNote),
        onChanged: (_) => setState(() {}),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: Text(l.riskCancel),
        ),
        FilledButton(
          key: const Key('cod-risk-dispute-save'),
          onPressed:
              _note.text.trim().length >= 3
                  ? () => Navigator.pop(context, _note.text.trim())
                  : null,
          child: Text(l.riskSave),
        ),
      ],
    );
  }
}
