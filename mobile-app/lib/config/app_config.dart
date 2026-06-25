// ============================================================================
//  APP CONFIG — SET YOUR SERVER HERE
// ============================================================================
//  One place to point the app at your HRMS server. Edit `_defaultServerUrl`,
//  or override at build time:
//     flutter run --dart-define=SERVER_URL=https://your-domain.com
// ============================================================================

class AppConfig {
  /// 👉 CHANGE THIS to your server.
  static const String _defaultServerUrl = 'https://skylinxhrms.qzz.io';

  static const String serverUrl = String.fromEnvironment(
    'SERVER_URL',
    defaultValue: _defaultServerUrl,
  );

  static const String appName = 'Skylinx HRMS';

  /// Base URL for the DRF API (skylinx_api mounted at /api/).
  static String get apiBase =>
      '${serverUrl.replaceAll(RegExp(r'/+$'), '')}/api';

  /// Server origin (for building media/image URLs returned as relative paths).
  static String mediaUrl(String? path) {
    if (path == null || path.isEmpty) return '';
    if (path.startsWith('http')) return path;
    return serverUrl.replaceAll(RegExp(r'/+$'), '') + path;
  }
}
