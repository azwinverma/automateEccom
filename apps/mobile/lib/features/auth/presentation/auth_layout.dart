import 'package:flutter/material.dart';

import '../../../core/l10n/gen/app_localizations.dart';
import '../../../design/tokens.g.dart';

/// Shared single-column layout for auth/onboarding: wordmark, title,
/// subtitle, then content. No hero art, no gradient.
class AuthLayout extends StatelessWidget {
  const AuthLayout({
    super.key,
    required this.title,
    required this.subtitle,
    required this.child,
    this.leading,
  });

  final String title;
  final String subtitle;
  final Widget child;
  final Widget? leading;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l = AppLocalizations.of(context);
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 480),
            child: ListView(
              padding: const EdgeInsets.fromLTRB(
                AppSpace.s4,
                AppSpace.s6,
                AppSpace.s4,
                AppSpace.s8,
              ),
              children: [
                if (leading != null) leading!,
                Row(
                  children: [
                    Container(
                      width: 4,
                      height: 18,
                      color: theme.colorScheme.primary,
                    ),
                    const SizedBox(width: AppSpace.s2),
                    Text(
                      l.appName,
                      style: theme.textTheme.titleSmall?.copyWith(
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: AppSpace.s8),
                Semantics(
                  header: true,
                  child: Text(title, style: theme.textTheme.headlineMedium),
                ),
                const SizedBox(height: AppSpace.s2),
                Text(
                  subtitle,
                  style: theme.textTheme.bodyLarge?.copyWith(
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                ),
                const SizedBox(height: AppSpace.s6),
                child,
              ],
            ),
          ),
        ),
      ),
    );
  }
}

/// Full-width primary action that shows progress while [busy].
class SubmitButton extends StatelessWidget {
  const SubmitButton({
    super.key,
    required this.label,
    required this.busy,
    required this.onPressed,
  });

  final String label;
  final bool busy;

  /// Null disables the button.
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      height: 52,
      child: FilledButton(
        onPressed: busy ? null : onPressed,
        child:
            busy
                ? SizedBox.square(
                  dimension: 20,
                  child: CircularProgressIndicator(
                    strokeWidth: 2,
                    semanticsLabel: AppLocalizations.of(context).loadingLabel,
                  ),
                )
                : Text(label),
      ),
    );
  }
}

/// Password field with a show/hide toggle.
class PasswordField extends StatefulWidget {
  const PasswordField({
    super.key,
    required this.controller,
    required this.validator,
    this.helperText,
    this.errorText,
    this.autofillHints = const [AutofillHints.password],
    this.textInputAction = TextInputAction.done,
    this.onSubmitted,
  });

  final TextEditingController controller;
  final FormFieldValidator<String> validator;
  final String? helperText;
  final String? errorText;
  final Iterable<String> autofillHints;
  final TextInputAction textInputAction;
  final ValueChanged<String>? onSubmitted;

  @override
  State<PasswordField> createState() => _PasswordFieldState();
}

class _PasswordFieldState extends State<PasswordField> {
  bool _obscure = true;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    return TextFormField(
      key: const Key('password-field'),
      controller: widget.controller,
      obscureText: _obscure,
      autofillHints: widget.autofillHints,
      textInputAction: widget.textInputAction,
      onFieldSubmitted: widget.onSubmitted,
      validator: widget.validator,
      decoration: InputDecoration(
        labelText: l.fieldPassword,
        helperText: widget.helperText,
        errorText: widget.errorText,
        suffixIcon: IconButton(
          tooltip: _obscure ? l.showPassword : l.hidePassword,
          icon: Icon(
            _obscure
                ? Icons.visibility_outlined
                : Icons.visibility_off_outlined,
          ),
          onPressed: () => setState(() => _obscure = !_obscure),
        ),
      ),
    );
  }
}
