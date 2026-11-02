import '../../../../core/l10n/gen/app_localizations.dart';

/// Localized names for metered resources; unknown resources fall back to a
/// humanised code so new server resources still render.
String resourceLabel(AppLocalizations l, String resource) =>
    switch (resource) {
      'ai_text_generations' => l.resAiTextGenerations,
      'ai_inbox_replies' => l.resAiInboxReplies,
      'ai_images' || 'ai_image_generations' => l.resAiImages,
      'auto_reels' => l.resAutoReels,
      'premium_video_credits' ||
      'premium_video_seconds' ||
      'premium_video' =>
        l.resPremiumVideo,
      'products' => l.resProducts,
      'orders' => l.resOrders,
      'channels' => l.resChannels,
      'team_members' => l.resTeamMembers,
      'stores' => l.resStores,
      'storage_mb' || 'storage_bytes' || 'storage' => l.resStorage,
      'automation_runs' => l.resAutomationRuns,
      'api_calls' => l.resApiCalls,
      _ => _humanise(resource),
    };

String _humanise(String code) {
  final words = code.split('_').where((w) => w.isNotEmpty).toList();
  if (words.isEmpty) return code;
  final first = words.first;
  return [
    '${first[0].toUpperCase()}${first.substring(1)}',
    ...words.skip(1),
  ].join(' ');
}
