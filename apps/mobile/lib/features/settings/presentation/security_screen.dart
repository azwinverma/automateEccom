import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/providers.dart';
import '../../../core/auth/auth_api.dart';
import '../../../core/errors/api_error.dart';
import '../../../core/errors/error_messages.dart';
import '../../../core/l10n/formatters.dart';
import '../../../core/l10n/gen/app_localizations.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens.g.dart';
import '../../../design/widgets/section_header.dart';
import '../../../design/widgets/state_views.dart';
import '../data/sessions_providers.dart';

class SecurityScreen extends ConsumerWidget {
  const SecurityScreen({super.key});

  Future<void> _confirmAndRun(
    BuildContext context,
    WidgetRef ref, {
    required String title,
    String? body,
    required Future<void> Function() action,
  }) async {
    final l = AppLocalizations.of(context);
    final messenger = ScaffoldMessenger.of(context);
    final ok = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(title),
        content: body == null ? null : Text(body),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: Text(l.actionCancel),
          ),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            child: Text(l.sessionRevoke),
          ),
        ],
      ),
    );
    if (!(ok ?? false)) return;
    try {
      await action();
      messenger.showSnackBar(SnackBar(content: Text(l.sessionsRevokedToast)));
    } on ApiError catch (e) {
      messenger.showSnackBar(
        SnackBar(content: Text(localizedErrorMessage(l, e))),
      );
    }
    ref.invalidate(sessionsProvider);
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l = AppLocalizations.of(context);
    final sessions = ref.watch(sessionsProvider);
    final api = ref.read(authApiProvider);

    return Scaffold(
      appBar: AppBar(title: Text(l.securityTitle)),
      body: RefreshIndicator(
        onRefresh: () => ref.refresh(sessionsProvider.future),
        child: ListView(
          children: [
            SectionHeader(l.sessionsTitle),
            AsyncValueView<List<AuthSession>>(
              value: sessions,
              onRetry: () => ref.invalidate(sessionsProvider),
              data: (items) {
                final sorted = [...items]
                  ..sort((a, b) => a.current == b.current
                      ? (b.lastUsedAt ?? DateTime(0))
                          .compareTo(a.lastUsedAt ?? DateTime(0))
                      : (a.current ? -1 : 1));
                final others = sorted.where((s) => !s.current).length;
                return Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    for (final s in sorted) ...[
                      _SessionRow(
                        session: s,
                        onRevoke: s.current
                            ? null
                            : () => _confirmAndRun(
                                  context,
                                  ref,
                                  title: l.sessionRevokeConfirm(
                                    s.deviceName ?? l.sessionUnknownDevice,
                                  ),
                                  action: () => api.revokeSession(s.id),
                                ),
                      ),
                      const Divider(),
                    ],
                    if (others == 0)
                      EmptyState(title: l.sessionsOnlyThis)
                    else
                      Padding(
                        padding: const EdgeInsets.all(AppSpace.s4),
                        child: OutlinedButton(
                          style: OutlinedButton.styleFrom(
                            foregroundColor: AppPalette.of(context).danger,
                            minimumSize: const Size.fromHeight(52),
                          ),
                          onPressed: () => _confirmAndRun(
                            context,
                            ref,
                            title: l.sessionsRevokeOthers,
                            body: l.sessionsRevokeOthersConfirm,
                            action: api.revokeAllOtherSessions,
                          ),
                          child: Text(l.sessionsRevokeOthers),
                        ),
                      ),
                  ],
                );
              },
            ),
          ],
        ),
      ),
    );
  }
}

class _SessionRow extends StatelessWidget {
  const _SessionRow({required this.session, this.onRevoke});

  final AuthSession session;
  final VoidCallback? onRevoke;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final palette = AppPalette.of(context);
    final lang = Localizations.localeOf(context).languageCode;
    final lastUsed = session.lastUsedAt ?? session.createdAt;
    final subtitle = [
      if (lastUsed != null)
        l.sessionLastUsed(Formatters.dateTime(lastUsed, lang)),
      if (session.ip != null) session.ip!,
    ].join(' · ');
    return ListTile(
      tileColor: theme.colorScheme.surface,
      shape: const RoundedRectangleBorder(),
      leading: Icon(
        session.current ? Icons.smartphone : Icons.devices_other_outlined,
      ),
      title: Row(
        children: [
          Flexible(
            child: Text(
              session.deviceName ?? l.sessionUnknownDevice,
              overflow: TextOverflow.ellipsis,
            ),
          ),
          if (session.current) ...[
            const SizedBox(width: AppSpace.s2),
            Text(
              l.sessionThisDevice,
              style: theme.textTheme.labelSmall?.copyWith(
                color: palette.success,
              ),
            ),
          ],
        ],
      ),
      subtitle: subtitle.isEmpty ? null : Text(subtitle),
      trailing: onRevoke == null
          ? null
          : TextButton(onPressed: onRevoke, child: Text(l.sessionRevoke)),
    );
  }
}
