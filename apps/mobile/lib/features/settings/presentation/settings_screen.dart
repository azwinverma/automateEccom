import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../core/api/providers.dart';
import '../../../core/auth/session_controller.dart';
import '../../../core/l10n/gen/app_localizations.dart';
import '../../../core/l10n/locale_controller.dart';
import '../../../design/app_theme.dart';
import '../../../design/theme_controller.dart';
import '../../../design/tokens.g.dart';
import '../../../design/widgets/section_header.dart';

class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  Future<void> _pickLanguage(BuildContext context, WidgetRef ref) async {
    final l = AppLocalizations.of(context);
    final current = ref.read(localeControllerProvider);
    final choice = await showModalBottomSheet<String>(
      context: context,
      showDragHandle: true,
      builder:
          (context) => SafeArea(
            child: RadioGroupList(
              current: current?.languageCode ?? 'system',
              options: {
                'system': l.languageSystem,
                'ne': l.languageNepali,
                'en': l.languageEnglish,
              },
            ),
          ),
    );
    if (choice == null) return;
    final locale = choice == 'system' ? null : Locale(choice);
    await ref.read(localeControllerProvider.notifier).set(locale);
    if (locale != null) {
      // Best effort: keep the account's preferred locale in sync so server
      // messages (email, receipts) follow. Local choice wins regardless.
      unawaited(
        ref
            .read(authApiProvider)
            .updateLocale(locale.languageCode)
            .then<void>((_) {}, onError: (Object _) {}),
      );
    }
  }

  Future<void> _pickTheme(BuildContext context, WidgetRef ref) async {
    final l = AppLocalizations.of(context);
    final choice = await showModalBottomSheet<String>(
      context: context,
      showDragHandle: true,
      builder:
          (context) => SafeArea(
            child: RadioGroupList(
              current: ref.read(themeControllerProvider).name,
              options: {
                'light': l.themeLight,
                'dark': l.themeDark,
                'system': l.themeSystem,
              },
            ),
          ),
    );
    if (choice == null) return;
    await ref
        .read(themeControllerProvider.notifier)
        .set(ThemeMode.values.byName(choice));
  }

  Future<void> _logout(BuildContext context, WidgetRef ref) async {
    final l = AppLocalizations.of(context);
    final ok = await showDialog<bool>(
      context: context,
      builder:
          (context) => AlertDialog(
            title: Text(l.logoutConfirmTitle),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(context, false),
                child: Text(l.actionCancel),
              ),
              FilledButton(
                onPressed: () => Navigator.pop(context, true),
                child: Text(l.settingsLogout),
              ),
            ],
          ),
    );
    if (ok ?? false) {
      await ref.read(sessionControllerProvider.notifier).logout();
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final palette = AppPalette.of(context);
    final session = ref.watch(sessionControllerProvider);
    final explicit = ref.watch(localeControllerProvider);
    final signedIn = session is SessionSignedIn ? session : null;
    final user = signedIn?.me.user;

    final languageName = switch (explicit?.languageCode) {
      null => l.languageSystem,
      'ne' => l.languageNepali,
      _ => l.languageEnglish,
    };

    return Scaffold(
      appBar: AppBar(title: Text(l.settingsTitle)),
      body: ListView(
        padding: const EdgeInsets.only(bottom: AppSpace.s8),
        children: [
          SectionHeader(l.settingsProfile),
          if (user != null)
            Container(
              color: theme.colorScheme.surface,
              padding: const EdgeInsets.all(AppSpace.s4),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(user.fullName, style: theme.textTheme.titleMedium),
                  Text(
                    user.email,
                    style: theme.textTheme.bodyMedium?.copyWith(
                      color: theme.colorScheme.onSurfaceVariant,
                    ),
                  ),
                  const SizedBox(height: AppSpace.s2),
                  Wrap(
                    spacing: AppSpace.s3,
                    children: [
                      if (!user.emailVerified)
                        Text(
                          l.emailUnverified,
                          style: theme.textTheme.labelMedium?.copyWith(
                            color: palette.warning,
                          ),
                        ),
                      Text(
                        user.mfaEnabled ? l.mfaOn : l.mfaOff,
                        style: theme.textTheme.labelMedium?.copyWith(
                          color:
                              user.mfaEnabled
                                  ? palette.success
                                  : theme.colorScheme.onSurfaceVariant,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          if (signedIn?.merchant != null) ...[
            SectionHeader(l.settingsShop),
            ListTile(
              tileColor: theme.colorScheme.surface,
              leading: const Icon(Icons.storefront_outlined),
              title: Text(signedIn!.merchant!.name),
              subtitle:
                  signedIn.merchant!.slug == null
                      ? null
                      : Text(signedIn.merchant!.slug!),
            ),
          ],
          const SizedBox(height: AppSpace.s6),
          const Divider(),
          _NavRow(
            icon: Icons.translate,
            title: l.settingsLanguage,
            value: languageName,
            onTap: () => _pickLanguage(context, ref),
          ),
          const Divider(),
          _NavRow(
            icon: Icons.contrast,
            title: l.settingsTheme,
            value: switch (ref.watch(themeControllerProvider)) {
              ThemeMode.dark => l.themeDark,
              ThemeMode.system => l.themeSystem,
              ThemeMode.light => l.themeLight,
            },
            onTap: () => _pickTheme(context, ref),
          ),
          const Divider(),
          _NavRow(
            icon: Icons.shield_outlined,
            title: l.settingsSecurity,
            onTap: () => context.push('/settings/security'),
          ),
          const Divider(),
          _NavRow(
            icon: Icons.data_usage_outlined,
            title: l.settingsPlan,
            onTap: () => context.push('/settings/plan'),
          ),
          const Divider(),
          _NavRow(
            key: const Key('settings-learned'),
            icon: Icons.lightbulb_outline,
            title: l.settingsLearned,
            onTap: () => context.push('/learned'),
          ),
          const Divider(),
          const SizedBox(height: AppSpace.s8),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: AppSpace.s4),
            child: OutlinedButton.icon(
              style: OutlinedButton.styleFrom(
                foregroundColor: palette.danger,
                minimumSize: const Size.fromHeight(52),
              ),
              onPressed: () => _logout(context, ref),
              icon: const Icon(Icons.logout),
              label: Text(l.settingsLogout),
            ),
          ),
        ],
      ),
    );
  }
}

class _NavRow extends StatelessWidget {
  const _NavRow({
    super.key,
    required this.icon,
    required this.title,
    required this.onTap,
    this.value,
  });

  final IconData icon;
  final String title;
  final String? value;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return ListTile(
      tileColor: theme.colorScheme.surface,
      shape: const RoundedRectangleBorder(),
      leading: Icon(icon),
      title: Text(title),
      trailing: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (value != null)
            Text(
              value!,
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
          const Icon(Icons.chevron_right),
        ],
      ),
      onTap: onTap,
    );
  }
}

/// Single-choice list for bottom sheets; pops with the chosen key.
class RadioGroupList extends StatelessWidget {
  const RadioGroupList({
    super.key,
    required this.current,
    required this.options,
  });

  final String current;
  final Map<String, String> options;

  @override
  Widget build(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        for (final e in options.entries)
          ListTile(
            title: Text(e.value),
            trailing:
                e.key == current
                    ? Icon(
                      Icons.check,
                      color: Theme.of(context).colorScheme.primary,
                    )
                    : null,
            selected: e.key == current,
            onTap: () => Navigator.pop(context, e.key),
          ),
        const SizedBox(height: AppSpace.s4),
      ],
    );
  }
}
