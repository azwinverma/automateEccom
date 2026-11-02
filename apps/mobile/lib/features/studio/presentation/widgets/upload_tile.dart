import 'dart:io';

import 'package:flutter/foundation.dart';

import 'package:flutter/material.dart';

import '../../../../core/errors/api_error.dart';
import '../../../../core/errors/error_messages.dart';
import '../../../../core/l10n/formatters.dart';
import '../../../../core/l10n/gen/app_localizations.dart';
import '../../../../design/app_theme.dart';
import '../../../../design/tokens.g.dart';
import '../../../../design/widgets/meter_bar.dart';
import '../../data/upload_engine.dart';
import '../studio_copy.dart';

/// One photo row: local thumbnail, status with progress, tips and actions.
/// Full-width rows (not a grid) keep text readable in Nepali at 360dp.
class UploadTile extends StatelessWidget {
  const UploadTile({
    super.key,
    required this.item,
    required this.onRetry,
    required this.onRemove,
  });

  final UploadItem item;
  final VoidCallback onRetry;
  final VoidCallback onRemove;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final palette = AppPalette.of(context);
    final lang = Localizations.localeOf(context).languageCode;

    final retrying = item.attempts > 0 && item.isActive;
    final (String status, Color color) = switch (item.phase) {
      UploadPhase.queued => (
        retrying ? l.uploadRetrying : l.uploadQueued,
        theme.colorScheme.onSurfaceVariant,
      ),
      UploadPhase.uploading => (
        retrying
            ? l.uploadRetrying
            : l.uploadUploading(Formatters.percent(item.progress, lang)),
        theme.colorScheme.primary,
      ),
      UploadPhase.completing ||
      UploadPhase.processing => (l.uploadProcessing, theme.colorScheme.primary),
      UploadPhase.ready => (l.uploadReady, palette.success),
      UploadPhase.waitingRetry => (l.uploadPaused, palette.warning),
      UploadPhase.rejected => (l.uploadRejected, palette.danger),
      UploadPhase.failed => (l.uploadFailed, palette.danger),
    };

    String? detail;
    if (item.phase == UploadPhase.rejected) {
      detail = rejectionMessage(l, item.rejectionReason);
    } else if (item.phase == UploadPhase.failed && item.errorCode != null) {
      detail = localizedErrorMessage(
        l,
        ApiError(
          kind: ApiErrorKind.http,
          code: item.errorCode!,
          details:
              item.errorCode == 'usage_limit_reached'
                  ? const {'resource': 'storage_mb'}
                  : const {},
        ),
      );
    }
    final tips =
        item.phase == UploadPhase.ready
            ? item.qualityFlags.map((f) => qualityTip(l, f)).whereType<String>()
            : const <String>[];
    final canRetry =
        item.phase == UploadPhase.waitingRetry ||
        (item.phase == UploadPhase.failed &&
            item.errorCode != 'file_too_large' &&
            item.errorCode != 'unsupported_media_type' &&
            item.errorCode != 'file_unreadable');

    return Padding(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpace.s4,
        vertical: AppSpace.s2,
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(AppRadius.sm),
            child: SizedBox.square(
              dimension: 64,
              // Web keeps the picker's blob URL; phones keep a file in app storage.
              child: (kIsWeb ? Image.network : _fileImage)(
                item.filePath,
                fit: BoxFit.cover,
                cacheWidth: 192,
                errorBuilder:
                    (_, __, ___) => ColoredBox(
                      color: theme.colorScheme.surfaceContainerHighest,
                      child: Icon(
                        Icons.image_outlined,
                        color: theme.colorScheme.onSurfaceVariant,
                      ),
                    ),
              ),
            ),
          ),
          const SizedBox(width: AppSpace.s3),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  status,
                  key: Key('upload-status-${item.localId}'),
                  style: theme.textTheme.titleSmall?.copyWith(color: color),
                ),
                if (item.phase == UploadPhase.uploading) ...[
                  const SizedBox(height: AppSpace.s1),
                  MeterBar(ratio: item.progress, level: UsageLevel.normal),
                ],
                if (detail != null)
                  Text(detail, style: theme.textTheme.bodySmall),
                for (final t in tips)
                  Padding(
                    padding: const EdgeInsets.only(top: AppSpace.s1),
                    child: Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Icon(
                          Icons.lightbulb_outline,
                          size: 16,
                          color: palette.warning,
                        ),
                        const SizedBox(width: AppSpace.s1),
                        Expanded(
                          child: Text(t, style: theme.textTheme.bodySmall),
                        ),
                      ],
                    ),
                  ),
                if (canRetry)
                  TextButton.icon(
                    style: TextButton.styleFrom(
                      padding: EdgeInsets.zero,
                      alignment: AlignmentDirectional.centerStart,
                    ),
                    onPressed: onRetry,
                    icon: const Icon(Icons.refresh, size: 18),
                    label: Text(l.uploadTapRetry),
                  ),
              ],
            ),
          ),
          IconButton(
            tooltip: l.captureRemovePhoto,
            onPressed: onRemove,
            icon: const Icon(Icons.close),
          ),
        ],
      ),
    );
  }
}

Image _fileImage(
  String path, {
  BoxFit? fit,
  int? cacheWidth,
  ImageErrorWidgetBuilder? errorBuilder,
}) => Image.file(
  File(path),
  fit: fit,
  cacheWidth: cacheWidth,
  errorBuilder: errorBuilder,
);
