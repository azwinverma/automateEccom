import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/errors/api_error.dart';
import '../../core/errors/error_messages.dart';
import '../../core/l10n/gen/app_localizations.dart';
import '../app_theme.dart';
import '../tokens.g.dart';

/// Static (non-animated) placeholder block. No shimmer: the brand rules
/// forbid decorative infinite motion.
class SkeletonBlock extends StatelessWidget {
  const SkeletonBlock({super.key, this.height = 16, this.width});

  final double height;
  final double? width;

  @override
  Widget build(BuildContext context) => Container(
        height: height,
        width: width,
        decoration: BoxDecoration(
          color: Theme.of(context).colorScheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(AppRadius.sm),
        ),
      );
}

/// Skeleton rows approximating a list of settings/usage rows.
class SkeletonList extends StatelessWidget {
  const SkeletonList({super.key, this.rows = 4});

  final int rows;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: AppLocalizations.of(context).loadingLabel,
      liveRegion: true,
      child: ExcludeSemantics(
        child: Padding(
          padding: const EdgeInsets.all(AppSpace.s4),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              for (var i = 0; i < rows; i++) ...[
                const SkeletonBlock(height: 14, width: 140),
                const SizedBox(height: AppSpace.s2),
                const SkeletonBlock(height: 10),
                const SizedBox(height: AppSpace.s6),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

/// Plain, left-aligned empty state. Icon sits bare (never in a circle).
class EmptyState extends StatelessWidget {
  const EmptyState({
    super.key,
    required this.title,
    this.body,
    this.icon,
    this.action,
  });

  final String title;
  final String? body;
  final IconData? icon;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(
        horizontal: AppSpace.s4,
        vertical: AppSpace.s4,
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (icon != null) ...[
            Icon(icon, size: 24, color: theme.colorScheme.onSurfaceVariant),
            const SizedBox(width: AppSpace.s3),
          ],
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(title, style: theme.textTheme.titleSmall),
                if (body != null) ...[
                  const SizedBox(height: AppSpace.s1),
                  Text(
                    body!,
                    style: theme.textTheme.bodyMedium?.copyWith(
                      color: theme.colorScheme.onSurfaceVariant,
                    ),
                  ),
                ],
                if (action != null) ...[
                  const SizedBox(height: AppSpace.s3),
                  action!,
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// Error / offline / permission-denied state with retry and a tiny request id
/// support reference.
class ErrorStateView extends StatelessWidget {
  const ErrorStateView({super.key, required this.error, this.onRetry});

  final Object error;
  final VoidCallback? onRetry;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final palette = AppPalette.of(context);
    final e = asApiError(error);

    final (IconData icon, String title, String body, bool canRetry) =
        switch (e) {
      _ when e.code == 'feature_not_in_plan' => (
          Icons.lock_outline,
          l.featureNotInPlanTitle,
          l.featureNotInPlanBody,
          false,
        ),
      _ when e.code == 'permission_denied' => (
          Icons.lock_outline,
          l.permissionDeniedTitle,
          l.permissionDeniedBody,
          false,
        ),
      _ when e.isOffline => (
          Icons.wifi_off_outlined,
          l.offlineTitle,
          localizedErrorMessage(l, e),
          true,
        ),
      _ => (
          Icons.error_outline,
          l.errorTitle,
          localizedErrorMessage(l, e),
          true,
        ),
    };

    return Padding(
      padding: const EdgeInsets.all(AppSpace.s4),
      child: Semantics(
        liveRegion: true,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(
                  icon,
                  color: e.isPermissionDenied
                      ? theme.colorScheme.onSurfaceVariant
                      : palette.danger,
                ),
                const SizedBox(width: AppSpace.s3),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(title, style: theme.textTheme.titleSmall),
                      const SizedBox(height: AppSpace.s1),
                      Text(
                        body,
                        style: theme.textTheme.bodyMedium?.copyWith(
                          color: theme.colorScheme.onSurfaceVariant,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
            if (canRetry && onRetry != null) ...[
              const SizedBox(height: AppSpace.s3),
              OutlinedButton.icon(
                onPressed: onRetry,
                icon: const Icon(Icons.refresh, size: 18),
                label: Text(l.actionRetry),
              ),
            ],
            if (e.requestId != null) ...[
              const SizedBox(height: AppSpace.s2),
              SelectableText(
                l.requestIdLabel(e.requestId!),
                style: theme.textTheme.labelSmall?.copyWith(
                  color: palette.muted,
                  fontFamily: AppTheme.latinFamily,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

/// Renders loading (skeleton), error, empty and data for an [AsyncValue].
class AsyncValueView<T> extends StatelessWidget {
  const AsyncValueView({
    super.key,
    required this.value,
    required this.data,
    this.onRetry,
    this.isEmpty,
    this.empty,
    this.loading,
  });

  final AsyncValue<T> value;
  final Widget Function(T data) data;
  final VoidCallback? onRetry;
  final bool Function(T data)? isEmpty;
  final Widget? empty;
  final Widget? loading;

  @override
  Widget build(BuildContext context) {
    return value.when(
      skipLoadingOnRefresh: false,
      loading: () => loading ?? const SkeletonList(),
      error: (e, _) => ErrorStateView(error: e, onRetry: onRetry),
      data: (d) {
        if (empty != null && (isEmpty?.call(d) ?? false)) return empty!;
        return data(d);
      },
    );
  }
}

/// Inline form error banner (non-blocking), e.g. under a submit button.
class InlineError extends StatelessWidget {
  const InlineError({super.key, required this.error});

  final ApiError error;

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final palette = AppPalette.of(context);
    return Semantics(
      liveRegion: true,
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.all(AppSpace.s3),
        decoration: BoxDecoration(
          color: palette.dangerSoft,
          borderRadius: BorderRadius.circular(AppRadius.md),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              localizedErrorMessage(l, error),
              style: theme.textTheme.bodyMedium?.copyWith(
                color: palette.danger,
              ),
            ),
            if (error.requestId != null)
              Padding(
                padding: const EdgeInsets.only(top: AppSpace.s1),
                child: SelectableText(
                  l.requestIdLabel(error.requestId!),
                  style: theme.textTheme.labelSmall?.copyWith(
                    color: palette.muted,
                    fontFamily: AppTheme.latinFamily,
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}
