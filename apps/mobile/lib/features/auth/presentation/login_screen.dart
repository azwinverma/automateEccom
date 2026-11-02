import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/auth/session_controller.dart';
import '../../../core/errors/api_error.dart';
import '../../../core/errors/error_messages.dart';
import '../../../core/l10n/gen/app_localizations.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens.g.dart';
import '../../../design/widgets/state_views.dart';
import 'auth_layout.dart';
import 'validators.dart';

/// Email/password, then an in-place MFA step when the server answers
/// `mfa_required`.
class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _mfaKey = GlobalKey<FormState>();
  final _email = TextEditingController();
  final _password = TextEditingController();
  final _code = TextEditingController();
  String? _mfaToken;
  bool _busy = false;
  ApiError? _error;

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    _code.dispose();
    super.dispose();
  }

  Future<void> _run(Future<void> Function() action) async {
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      await action();
    } on Object catch (e) {
      if (mounted) setState(() => _error = asApiError(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _submitCredentials() async {
    if (!(_formKey.currentState?.validate() ?? false)) return;
    TextInput.finishAutofillContext();
    await _run(() async {
      final token = await ref
          .read(sessionControllerProvider.notifier)
          .login(email: _email.text.trim(), password: _password.text);
      if (token != null && mounted) setState(() => _mfaToken = token);
    });
  }

  Future<void> _submitCode() async {
    if (!(_mfaKey.currentState?.validate() ?? false)) return;
    await _run(
      () => ref
          .read(sessionControllerProvider.notifier)
          .verifyMfa(
            mfaToken: _mfaToken!,
            code: _code.text.trim().replaceAll(' ', ''),
          ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final session = ref.watch(sessionControllerProvider);
    final reason = session is SessionSignedOut ? session.reason : null;
    final notice = sessionEndedMessage(l, reason);

    if (_mfaToken != null) {
      return AuthLayout(
        title: l.mfaTitle,
        subtitle: l.mfaSubtitle,
        child: Form(
          key: _mfaKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              TextFormField(
                key: const Key('mfa-code-field'),
                controller: _code,
                autofocus: true,
                keyboardType: TextInputType.visiblePassword,
                autofillHints: const [AutofillHints.oneTimeCode],
                textInputAction: TextInputAction.done,
                onFieldSubmitted: (_) => _submitCode(),
                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                  fontFamily: AppTheme.latinFamily,
                  letterSpacing: 4,
                ),
                decoration: InputDecoration(labelText: l.fieldMfaCode),
                validator: (v) => Validators.code(l, v),
              ),
              const SizedBox(height: AppSpace.s4),
              if (_error != null) ...[
                InlineError(error: _error!),
                const SizedBox(height: AppSpace.s4),
              ],
              SubmitButton(
                label: l.mfaVerifyAction,
                busy: _busy,
                onPressed: _submitCode,
              ),
              const SizedBox(height: AppSpace.s2),
              TextButton(
                onPressed:
                    _busy
                        ? null
                        : () => setState(() {
                          _mfaToken = null;
                          _code.clear();
                          _error = null;
                        }),
                child: Text(l.mfaUseDifferentAccount),
              ),
            ],
          ),
        ),
      );
    }

    return AuthLayout(
      title: l.loginTitle,
      subtitle: l.loginSubtitle,
      child: AutofillGroup(
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (notice != null && _error == null) ...[
                _Notice(text: notice),
                const SizedBox(height: AppSpace.s4),
              ],
              TextFormField(
                key: const Key('email-field'),
                controller: _email,
                keyboardType: TextInputType.emailAddress,
                autofillHints: const [AutofillHints.email],
                textInputAction: TextInputAction.next,
                autocorrect: false,
                decoration: InputDecoration(labelText: l.fieldEmail),
                validator: (v) => Validators.email(l, v),
              ),
              const SizedBox(height: AppSpace.s3),
              PasswordField(
                controller: _password,
                validator: (v) => Validators.loginPassword(l, v),
                onSubmitted: (_) => _submitCredentials(),
              ),
              const SizedBox(height: AppSpace.s4),
              if (_error != null) ...[
                InlineError(error: _error!),
                const SizedBox(height: AppSpace.s4),
              ],
              SubmitButton(
                key: const Key('login-submit'),
                label: l.loginAction,
                busy: _busy,
                onPressed: _submitCredentials,
              ),
              const SizedBox(height: AppSpace.s2),
              TextButton(
                onPressed: _busy ? null : () => context.go('/register'),
                child: Text(l.loginNoAccount),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _Notice extends StatelessWidget {
  const _Notice({required this.text});

  final String text;

  @override
  Widget build(BuildContext context) {
    final palette = AppPalette.of(context);
    return Semantics(
      liveRegion: true,
      child: Container(
        padding: const EdgeInsets.all(AppSpace.s3),
        decoration: BoxDecoration(
          color: palette.warningSoft,
          borderRadius: BorderRadius.circular(AppRadius.md),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(Icons.shield_outlined, size: 20, color: palette.warning),
            const SizedBox(width: AppSpace.s2),
            Expanded(
              child: Text(text, style: Theme.of(context).textTheme.bodyMedium),
            ),
          ],
        ),
      ),
    );
  }
}
