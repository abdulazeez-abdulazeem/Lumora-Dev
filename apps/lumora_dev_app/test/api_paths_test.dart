
import 'package:flutter_test/flutter_test.dart';
import 'package:lumora_dev_app/core/constants/app_constants.dart';

void main() {
  group('ApiPaths', () {
    test('chat', () => expect(ApiPaths.chat, '/chat'));
    test('files', () => expect(ApiPaths.files, '/files'));
    test('git', () => expect(ApiPaths.git, '/git'));
    test('memory', () => expect(ApiPaths.memory, '/memory'));
    test('health', () => expect(ApiPaths.health, '/health'));
  });
  group('AppConstants', () {
    test('secure keys', () {
      expect(AppConstants.secureKeyBackendUrl, isNotEmpty);
      expect(AppConstants.secureKeyApiToken, isNotEmpty);
    });
    test('hive boxes', () {
      expect(AppConstants.hiveBoxCache, 'lumora_cache');
      expect(AppConstants.hiveBoxChat, 'lumora_chat');
    });
  });
}
