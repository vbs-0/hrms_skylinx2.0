import 'package:flutter_test/flutter_test.dart';
import 'package:skylinx_hrms/config/app_config.dart';

void main() {
  test('startUrl is built from the configured server', () {
    expect(AppConfig.startUrl.startsWith('http'), isTrue);
    expect(AppConfig.serverHost.isNotEmpty, isTrue);
  });
}
