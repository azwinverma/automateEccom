import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:uuid/uuid.dart';

import '../../../core/auth/session_controller.dart';
import '../../../core/errors/api_error.dart';
import '../../../core/l10n/gen/app_localizations.dart';
import '../../../design/tokens.g.dart';
import '../../../design/widgets/state_views.dart';
import '../../auth/presentation/auth_layout.dart';
import '../data/merchant_api.dart';

/// Creates the merchant (tenant). Currency and timezone are fixed to NPR /
/// Asia/Kathmandu in Phase 0 and shown read-only.
class OnboardingScreen extends ConsumerStatefulWidget {
  const OnboardingScreen({super.key});

  @override
  ConsumerState<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends ConsumerState<OnboardingScreen> {
  final _formKey = GlobalKey<FormState>();
  final _name = TextEditingController();
  String? _language;
  bool _busy = false;
  ApiError? _error;

  /// One key per intended shop. Regenerated only when the payload changes,
  /// so retries after a dropped connection are replayed, not duplicated.
  String _idempotencyKey = const Uuid().v4();
  String? _keyPayload;

  @override
  void dispose() {
    _name.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!(_formKey.currentState?.validate() ?? false)) return;
    final language = _language ?? Localizations.localeOf(context).languageCode;
    final name = _name.text.trim();
    final payload = '$name|$language';
    if (_keyPayload != null && _keyPayload != payload) {
      _idempotencyKey = const Uuid().v4();
    }
    _keyPayload = payload;

    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final merchant = await ref
          .read(merchantApiProvider)
          .create(
            name: name,
            defaultLocale: language,
            idempotencyKey: _idempotencyKey,
          );
      await ref
          .read(sessionControllerProvider.notifier)
          .refreshMe(preferMerchantId: merchant.id);
    } on Object catch (e) {
      if (mounted) setState(() => _error = asApiError(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final language = _language ?? Localizations.localeOf(context).languageCode;

    Widget fixedRow(String label, String value) => Padding(
      padding: const EdgeInsets.symmetric(vertical: AppSpace.s3),
      child: Row(
        children: [
          Expanded(
            child: Text(
              label,
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
          ),
          Text(value, style: theme.textTheme.titleSmall),
        ],
      ),
    );

    return AuthLayout(
      title: l.onboardingTitle,
      subtitle: l.onboardingSubtitle,
      child: Form(
        key: _formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            TextFormField(
              key: const Key('business-name-field'),
              controller: _name,
              textCapitalization: TextCapitalization.words,
              textInputAction: TextInputAction.done,
              decoration: InputDecoration(
                labelText: l.fieldBusinessName,
                hintText: l.fieldBusinessNameHint,
              ),
              validator: (v) {
                final value = v?.trim() ?? '';
                if (value.isEmpty) return l.validationBusinessNameRequired;
                if (value.length < 2) return l.validationBusinessNameTooShort;
                return null;
              },
            ),
            const SizedBox(height: AppSpace.s5),
            Text(l.fieldDefaultLanguage, style: theme.textTheme.titleSmall),
            const SizedBox(height: AppSpace.s2),
            SegmentedButton<String>(
              showSelectedIcon: false,
              segments: [
                ButtonSegment(value: 'ne', label: Text(l.languageNepali)),
                ButtonSegment(value: 'en', label: Text(l.languageEnglish)),
              ],
              selected: {language},
              onSelectionChanged: (s) => setState(() => _language = s.first),
            ),
            const SizedBox(height: AppSpace.s5),
            const Divider(),
            fixedRow(l.fieldCurrency, l.currencyNpr),
            const Divider(),
            fixedRow(l.fieldTimezone, l.timezoneKathmandu),
            const Divider(),
            const SizedBox(height: AppSpace.s2),
            Text(
              l.onboardingFixedNote,
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: AppSpace.s6),
            if (_error != null) ...[
              InlineError(error: _error!),
              const SizedBox(height: AppSpace.s4),
            ],
            SubmitButton(
              label: l.onboardingAction,
              busy: _busy,
              onPressed: _submit,
            ),
            const SizedBox(height: AppSpace.s2),
            TextButton(
              onPressed:
                  _busy
                      ? null
                      : () =>
                          ref.read(sessionControllerProvider.notifier).logout(),
              child: Text(l.settingsLogout),
            ),
          ],
        ),
      ),
    );
  }
}
