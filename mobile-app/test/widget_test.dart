import 'package:flutter_test/flutter_test.dart';
import 'package:skylinx_hrms/config/app_config.dart';

void main() {
  test('apiBase is built from the configured server', () {
    expect(AppConfig.apiBase.startsWith('http'), isTrue);
    expect(AppConfig.apiBase.endsWith('/api'), isTrue);
  });
}
