import 'package:flutter_test/flutter_test.dart';
import 'package:lumora_dev_app/core/theme/app_colors.dart';

void main() {
  test('color purple', () => expect(AppColors.purple.alpha, greaterThan(0)));
  test('color violet', () => expect(AppColors.violet.alpha, greaterThan(0)));
  test('color electricBlue', () => expect(AppColors.electricBlue.alpha, greaterThan(0)));
  test('color cyan', () => expect(AppColors.cyan.alpha, greaterThan(0)));
  test('color success', () => expect(AppColors.success.alpha, greaterThan(0)));
  test('color warning', () => expect(AppColors.warning.alpha, greaterThan(0)));
  test('color error', () => expect(AppColors.error.alpha, greaterThan(0)));
  test('color black', () => expect(AppColors.black.alpha, greaterThan(0)));
  test('color surfaceDark', () => expect(AppColors.surfaceDark.alpha, greaterThan(0)));
  test('color cardDark', () => expect(AppColors.cardDark.alpha, greaterThan(0)));
}
