/// Web dashboard base URL for flows the app hands off (e.g. channel OAuth).
/// Override with `--dart-define=WEB_BASE_URL=https://app.example.np`.
const webBaseUrl = String.fromEnvironment(
  'WEB_BASE_URL',
  defaultValue: 'http://localhost:3010',
);

String channelsSettingsUrl({String? connectionId}) =>
    '${webBaseUrl.replaceAll(RegExp(r'/+$'), '')}/settings/channels'
    '${connectionId == null ? '' : '?reconnect=$connectionId'}';
