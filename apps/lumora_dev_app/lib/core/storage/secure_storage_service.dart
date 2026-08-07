import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:hive_flutter/hive_flutter.dart';
import '../constants/app_constants.dart';

final secureStorageProvider = Provider<SecureStorageService>((ref) => SecureStorageService());

class SecureStorageService {
  SecureStorageService() : _secure = const FlutterSecureStorage(aOptions: AndroidOptions(encryptedSharedPreferences: true));
  final FlutterSecureStorage _secure;
  Future<void> write(String key, String value) => _secure.write(key: key, value: value);
  Future<String?> read(String key) => _secure.read(key: key);
  Future<void> delete(String key) => _secure.delete(key: key);
  Future<void> initHive() async {
    await Hive.initFlutter();
    await Hive.openBox(AppConstants.hiveBoxCache);
    await Hive.openBox(AppConstants.hiveBoxSettings);
    await Hive.openBox(AppConstants.hiveBoxChat);
  }
  Box get cache => Hive.box(AppConstants.hiveBoxCache);
  Box get settings => Hive.box(AppConstants.hiveBoxSettings);
  Box get chat => Hive.box(AppConstants.hiveBoxChat);
}
