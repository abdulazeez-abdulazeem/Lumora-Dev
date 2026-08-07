
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:lumora_dev_app/core/theme/app_colors.dart';
import 'package:lumora_dev_app/core/constants/app_constants.dart';

void main() {
  test('AppColors brand values', () {
    expect(AppColors.purple.value, isNot(0));
    expect(AppColors.electricBlue.value, isNot(0));
  });
  test('AppConstants defaults', () {
    expect(AppConstants.appName, 'Lumora Dev');
    expect(AppConstants.backendDefaultUrl, contains('8000'));
    expect(AppConstants.appVersion, '1.0.0');
  });
  test('ApiPaths defined', () {
    expect(ApiPaths.system, '/system');
    expect(ApiPaths.knowledge, '/knowledge');
    expect(ApiPaths.multiagent, '/multiagent');
    expect(ApiPaths.deployment, '/deployment');
    expect(ApiPaths.vision, '/vision');
    expect(ApiPaths.browser, '/browser');
  });
}
