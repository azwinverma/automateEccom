import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/api/providers.dart';
import '../../../core/errors/api_error.dart';
import '../../../core/l10n/gen/app_localizations.dart';
import '../../../design/tokens.g.dart';
import '../../../design/widgets/state_views.dart';
import 'auth_layout.dart';
import 'validators.dart';

/// Asks the API to email a reset link (QA-001). The link opens the web reset page.
class ForgotPasswordScreen extends ConsumerStatefulWidget {
  const ForgotPasswordScreen({super.key});

  @override
  ConsumerState<ForgotPasswordScreen> createState() =>
      _ForgotPasswordScreenState();
}

class _ForgotPasswordScreenState extends ConsumerState<ForgotPasswordScreen> {
  final _formKey = GlobalKey<FormState>();
  final _email = TextEditingController();
  bool _busy = false;
  bool _sent = false;
  ApiError? _error;

  @override
  void dispose() {
    _email.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!(_formKey.currentState?.validate() ?? false)) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await ref.read(authApiProvider).requestPasswordReset(_email.text.trim());
      if (mounted) setState(() => _sent = true);
    } on Object catch (e) {
      if (mounted) setState(() => _error = asApiError(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    if (_sent) {
      return AuthLayout(
        title: l.forgotSentTitle,
        subtitle: l.forgotSentBody,
        child: TextButton(
          onPressed: () => context.go('/login'),
          child: Text(l.forgotBack),
        ),
      );
    }
    return AuthLayout(
      title: l.forgotTitle,
      subtitle: l.forgotSubtitle,
      child: Form(
        key: _formKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            TextFormField(
              key: const Key('forgot-email'),
              controller: _email,
              keyboardType: TextInputType.emailAddress,
              autofillHints: const [AutofillHints.email],
              autocorrect: false,
              textInputAction: TextInputAction.done,
              onFieldSubmitted: (_) => _submit(),
              decoration: InputDecoration(labelText: l.fieldEmail),
              validator: (v) => Validators.email(l, v),
            ),
            const SizedBox(height: AppSpace.s4),
            if (_error != null) ...[
              InlineError(error: _error!),
              const SizedBox(height: AppSpace.s4),
            ],
            SubmitButton(
              key: const Key('forgot-submit'),
              label: l.forgotAction,
              busy: _busy,
              onPressed: _submit,
            ),
            const SizedBox(height: AppSpace.s2),
            TextButton(
              onPressed: _busy ? null : () => context.go('/login'),
              child: Text(l.forgotBack),
            ),
          ],
        ),
      ),
    );
  }
}
