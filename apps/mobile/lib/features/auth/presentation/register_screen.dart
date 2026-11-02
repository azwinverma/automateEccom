import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/auth/session_controller.dart';
import '../../../core/errors/api_error.dart';
import '../../../core/l10n/gen/app_localizations.dart';
import '../../../design/tokens.g.dart';
import '../../../design/widgets/state_views.dart';
import 'auth_layout.dart';
import 'validators.dart';

class RegisterScreen extends ConsumerStatefulWidget {
  const RegisterScreen({super.key});

  @override
  ConsumerState<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends ConsumerState<RegisterScreen> {
  final _formKey = GlobalKey<FormState>();
  final _name = TextEditingController();
  final _email = TextEditingController();
  final _phone = TextEditingController();
  final _password = TextEditingController();
  bool _busy = false;
  ApiError? _error;

  @override
  void dispose() {
    _name.dispose();
    _email.dispose();
    _phone.dispose();
    _password.dispose();
    super.dispose();
  }

  String? _serverFieldError(String field) {
    final e = _error;
    if (e == null || e.code != 'validation_error') return null;
    return e.fieldErrors.containsKey(field)
        ? AppLocalizations.of(context).errFieldInvalid
        : null;
  }

  Future<void> _submit() async {
    if (!(_formKey.currentState?.validate() ?? false)) return;
    TextInput.finishAutofillContext();
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final mfa = await ref.read(sessionControllerProvider.notifier).register(
            email: _email.text.trim(),
            password: _password.text,
            fullName: _name.text.trim(),
            phone: _phone.text.replaceAll(RegExp(r'[\s-]'), ''),
            locale: Localizations.localeOf(context).languageCode,
          );
      // A brand-new account shouldn't need MFA; if it does, finish on login.
      if (mfa != null && mounted) context.go('/login');
    } on Object catch (e) {
      if (mounted) setState(() => _error = asApiError(e));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return AuthLayout(
      title: l.registerTitle,
      subtitle: l.registerSubtitle,
      child: AutofillGroup(
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              TextFormField(
                controller: _name,
                textCapitalization: TextCapitalization.words,
                autofillHints: const [AutofillHints.name],
                textInputAction: TextInputAction.next,
                decoration: InputDecoration(
                  labelText: l.fieldFullName,
                  errorText: _serverFieldError('full_name'),
                ),
                validator: (v) => Validators.name(l, v),
              ),
              const SizedBox(height: AppSpace.s3),
              TextFormField(
                controller: _email,
                keyboardType: TextInputType.emailAddress,
                autofillHints: const [AutofillHints.email],
                textInputAction: TextInputAction.next,
                autocorrect: false,
                decoration: InputDecoration(
                  labelText: l.fieldEmail,
                  errorText: _serverFieldError('email'),
                ),
                validator: (v) => Validators.email(l, v),
              ),
              const SizedBox(height: AppSpace.s3),
              TextFormField(
                controller: _phone,
                keyboardType: TextInputType.phone,
                autofillHints: const [AutofillHints.telephoneNumber],
                textInputAction: TextInputAction.next,
                decoration: InputDecoration(
                  labelText: l.fieldPhone,
                  errorText: _serverFieldError('phone'),
                ),
                validator: (v) => Validators.optionalPhone(l, v),
              ),
              const SizedBox(height: AppSpace.s3),
              PasswordField(
                controller: _password,
                autofillHints: const [AutofillHints.newPassword],
                helperText: l.passwordHint(minPasswordLength),
                errorText: _serverFieldError('password'),
                validator: (v) => Validators.newPassword(l, v, _email.text),
                onSubmitted: (_) => _submit(),
              ),
              const SizedBox(height: AppSpace.s4),
              if (_error != null) ...[
                InlineError(error: _error!),
                const SizedBox(height: AppSpace.s4),
              ],
              SubmitButton(
                label: l.registerAction,
                busy: _busy,
                onPressed: _submit,
              ),
              const SizedBox(height: AppSpace.s2),
              TextButton(
                onPressed: _busy ? null : () => context.go('/login'),
                child: Text(l.registerHaveAccount),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
