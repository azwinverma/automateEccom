import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:uuid/uuid.dart';

import '../../../core/errors/api_error.dart';
import '../../../core/l10n/gen/app_localizations.dart';
import '../../../design/app_theme.dart';
import '../../../design/tokens.g.dart';
import '../../../design/widgets/state_views.dart';
import '../../auth/presentation/auth_layout.dart';
import '../data/capture_controller.dart';
import '../data/photo_picker.dart';
import '../data/studio_api.dart';
import 'widgets/upload_tile.dart';

/// Step 1: photos. Uploads start immediately and run in the background with
/// per-photo progress; the seller can keep adding photos or notes meanwhile.
class CaptureScreen extends ConsumerStatefulWidget {
  const CaptureScreen({super.key});

  @override
  ConsumerState<CaptureScreen> createState() => _CaptureScreenState();
}

class _CaptureScreenState extends ConsumerState<CaptureScreen> {
  late final TextEditingController _notes;
  bool _submitting = false;
  ApiError? _error;
  String? _jobKey;
  String? _jobKeyPayload;

  @override
  void initState() {
    super.initState();
    _notes = TextEditingController(
      text: ref.read(captureControllerProvider).notes,
    );
    WidgetsBinding.instance.addPostFrameCallback((_) => _recoverLost());
  }

  @override
  void dispose() {
    _notes.dispose();
    super.dispose();
  }

  Future<void> _recoverLost() async {
    try {
      final lost = await ref.read(photoPickerProvider).recoverLost();
      if (lost.isNotEmpty) await _add(lost);
    } on Object {
      // Nothing to recover.
    }
  }

  Future<void> _add(List<PickedPhoto> photos) async {
    final skipped = await ref
        .read(captureControllerProvider.notifier)
        .addFiles(photos);
    if (skipped > 0 && mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(AppLocalizations.of(context).captureSkipped(skipped)),
        ),
      );
    }
  }

  Future<void> _pick({required bool camera}) async {
    final picker = ref.read(photoPickerProvider);
    final room = ref.read(captureControllerProvider).remainingSlots;
    try {
      if (camera) {
        final p = await picker.camera();
        if (p != null) await _add([p]);
      } else {
        await _add(await picker.gallery(limit: room));
      }
    } on Object {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(AppLocalizations.of(context).capturePickerError),
        ),
      );
    }
  }

  Future<void> _createDraft() async {
    final capture = ref.read(captureControllerProvider);
    final ids = [for (final i in capture.ready) i.assetId!];
    final locale = Localizations.localeOf(context).languageCode;
    final payload = '${ids.join(',')}|$locale|${capture.notes.trim()}';
    if (_jobKey == null || _jobKeyPayload != payload) {
      _jobKey = const Uuid().v4();
      _jobKeyPayload = payload;
    }
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      final job = await ref
          .read(studioApiProvider)
          .createJob(
            assetIds: ids,
            locale: locale == 'ne' ? 'ne' : 'en',
            sellerNotes: capture.notes,
            idempotencyKey: _jobKey!,
          );
      await ref.read(captureControllerProvider.notifier).clear();
      if (mounted) context.pushReplacement('/studio/jobs/${job.id}');
    } on Object catch (e) {
      if (mounted) setState(() => _error = asApiError(e));
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final palette = AppPalette.of(context);
    final state = ref.watch(captureControllerProvider);
    final ctrl = ref.read(captureControllerProvider.notifier);
    final full = state.remainingSlots <= 0;
    final canSubmit = state.ready.isNotEmpty && !state.anyActive;

    return Scaffold(
      appBar: AppBar(title: Text(l.captureTitle)),
      body: ListView(
        padding: const EdgeInsets.only(bottom: AppSpace.s8),
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(
              AppSpace.s4,
              0,
              AppSpace.s4,
              AppSpace.s4,
            ),
            child: Text(
              l.captureIntro,
              style: theme.textTheme.bodyMedium?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: AppSpace.s4),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                FilledButton.icon(
                  key: const Key('capture-camera'),
                  style: FilledButton.styleFrom(
                    minimumSize: const Size.fromHeight(56),
                  ),
                  onPressed: full ? null : () => _pick(camera: true),
                  icon: const Icon(Icons.photo_camera_outlined),
                  label: Text(l.captureTakePhoto),
                ),
                const SizedBox(height: AppSpace.s2),
                OutlinedButton.icon(
                  key: const Key('capture-gallery'),
                  style: OutlinedButton.styleFrom(
                    minimumSize: const Size.fromHeight(52),
                  ),
                  onPressed: full ? null : () => _pick(camera: false),
                  icon: const Icon(Icons.photo_library_outlined),
                  label: Text(l.captureFromGallery),
                ),
              ],
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(
              AppSpace.s4,
              AppSpace.s5,
              AppSpace.s4,
              AppSpace.s1,
            ),
            child: Text(
              full
                  ? l.captureLimitReached
                  : l.capturePhotoCount(state.items.length, maxCapturePhotos),
              style: theme.textTheme.titleSmall,
            ),
          ),
          if (state.anyPaused)
            Container(
              margin: const EdgeInsets.symmetric(
                horizontal: AppSpace.s4,
                vertical: AppSpace.s2,
              ),
              padding: const EdgeInsets.all(AppSpace.s3),
              color: palette.warningSoft,
              child: Row(
                children: [
                  Icon(Icons.wifi_off_outlined, color: palette.warning),
                  const SizedBox(width: AppSpace.s2),
                  Expanded(child: Text(l.uploadPaused)),
                  TextButton(
                    onPressed: ctrl.retry,
                    child: Text(l.captureResumeAll),
                  ),
                ],
              ),
            ),
          for (final item in state.items) ...[
            UploadTile(
              key: ValueKey(item.localId),
              item: item,
              onRetry: () => ctrl.retry(item.localId),
              onRemove: () => ctrl.remove(item.localId),
            ),
            const Divider(indent: AppSpace.s4),
          ],
          if (state.items.isNotEmpty)
            Padding(
              padding: const EdgeInsets.symmetric(
                horizontal: AppSpace.s4,
                vertical: AppSpace.s2,
              ),
              child: Text(
                l.captureKeepsGoing,
                style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              ),
            ),
          Padding(
            padding: const EdgeInsets.all(AppSpace.s4),
            child: TextField(
              controller: _notes,
              maxLines: 3,
              minLines: 2,
              maxLength: 2000,
              onChanged: ctrl.setNotes,
              decoration: InputDecoration(
                labelText: l.captureNotesLabel,
                hintText: l.captureNotesHint,
                alignLabelWithHint: true,
              ),
            ),
          ),
        ],
      ),
      bottomNavigationBar: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(
            AppSpace.s4,
            AppSpace.s2,
            AppSpace.s4,
            AppSpace.s3,
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              if (_error != null) ...[
                InlineError(error: _error!),
                if (_error!.code == 'feature_not_in_plan')
                  TextButton(
                    onPressed: () => context.push('/settings/plan'),
                    child: Text(l.settingsPlan),
                  ),
                const SizedBox(height: AppSpace.s2),
              ] else if (!canSubmit)
                Padding(
                  padding: const EdgeInsets.only(bottom: AppSpace.s2),
                  child: Text(
                    state.anyActive
                        ? l.captureWaitForUploads
                        : l.captureNeedOneReady,
                    textAlign: TextAlign.center,
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: theme.colorScheme.onSurfaceVariant,
                    ),
                  ),
                ),
              SubmitButton(
                key: const Key('capture-submit'),
                label: l.captureMakeDraft,
                busy: _submitting,
                onPressed: canSubmit ? _createDraft : null,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
