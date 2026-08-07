class AppConstants {
  AppConstants._();
  static const appName = 'Lumora Dev';
  static const appVersion = '1.0.0';
  static const backendDefaultUrl = 'http://127.0.0.1:8000';
  static const secureKeyBackendUrl = 'backend_url';
  static const secureKeyApiToken = 'api_token';
  static const hiveBoxCache = 'lumora_cache';
  static const hiveBoxSettings = 'lumora_settings';
  static const hiveBoxChat = 'lumora_chat';
}

class ApiPaths {
  ApiPaths._();
  static const health = '/health';
  static const chat = '/chat';
  static const files = '/files';
  static const git = '/git';
  static const browser = '/browser';
  static const vision = '/vision';
  static const knowledge = '/knowledge';
  static const multiagent = '/multiagent';
  static const deployment = '/deployment';
  static const system = '/system';
  static const memory = '/memory';
}
