
import 'package:flutter_test/flutter_test.dart';
import 'package:lumora_dev_app/core/constants/app_constants.dart';

void main() {
  test('default url is localhost API', () {
    expect(AppConstants.backendDefaultUrl, 'http://127.0.0.1:8000');
  });
  test('app version format', () {
    expect(AppConstants.appVersion.split('.').length, greaterThanOrEqualTo(2));
  });
}
