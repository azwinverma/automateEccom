import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../../core/config/web_links.dart';
import '../../../core/l10n/gen/app_localizations.dart';
import '../../../design/tokens.g.dart';

/// Channel OAuth runs on the web dashboard for now; this sheet hands the
/// seller a link to it.
Future<void> showReconnectSheet(
  BuildContext context, {
  String? connectionId,
  String? channelName,
}) {
  final l = AppLocalizations.of(context);
  final url = channelsSettingsUrl(connectionId: connectionId);
  return showModalBottomSheet<void>(
    context: context,
    showDragHandle: true,
    builder: (ctx) {
      final theme = Theme.of(ctx);
      return SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(
            AppSpace.s4,
            0,
            AppSpace.s4,
            AppSpace.s4,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                l.reconnectTitle(channelName ?? l.reconnectChannelGeneric),
                style: theme.textTheme.titleLarge,
              ),
              const SizedBox(height: AppSpace.s2),
              Text(l.reconnectBody, style: theme.textTheme.bodyMedium),
              const SizedBox(height: AppSpace.s3),
              SelectableText(url, style: theme.textTheme.bodySmall),
              const SizedBox(height: AppSpace.s4),
              FilledButton.icon(
                style: FilledButton.styleFrom(
                  minimumSize: const Size.fromHeight(52),
                ),
                onPressed: () async {
                  await Clipboard.setData(ClipboardData(text: url));
                  if (!ctx.mounted) return;
                  Navigator.pop(ctx);
                  ScaffoldMessenger.of(
                    context,
                  ).showSnackBar(SnackBar(content: Text(l.reconnectCopied)));
                },
                icon: const Icon(Icons.copy),
                label: Text(l.actionCopyLink),
              ),
            ],
          ),
        ),
      );
    },
  );
}
