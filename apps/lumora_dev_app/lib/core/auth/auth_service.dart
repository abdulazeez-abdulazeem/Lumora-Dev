import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../constants/app_constants.dart';
import '../network/api_client.dart';
import '../storage/secure_storage_service.dart';

final authServiceProvider = Provider<AuthService>((ref) {
  return AuthService(ref.watch(secureStorageProvider), ref.watch(apiClientProvider));
});

final authStateProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  return AuthNotifier(ref.watch(authServiceProvider));
});

class AuthState {
  const AuthState({
    this.isAuthenticated = false,
    this.isLoading = false,
    this.backendUrl = AppConstants.backendDefaultUrl,
    this.profileName = 'default',
    this.error,
  });
  final bool isAuthenticated;
  final bool isLoading;
  final String backendUrl;
  final String profileName;
  final String? error;

  AuthState copyWith({
    bool? isAuthenticated,
    bool? isLoading,
    String? backendUrl,
    String? profileName,
    String? error,
  }) =>
      AuthState(
        isAuthenticated: isAuthenticated ?? this.isAuthenticated,
        isLoading: isLoading ?? this.isLoading,
        backendUrl: backendUrl ?? this.backendUrl,
        profileName: profileName ?? this.profileName,
        error: error,
      );
}

class AuthService {
  AuthService(this._storage, this._client);
  final SecureStorageService _storage;
  final ApiClient _client;

  static const _keyProfiles = 'backend_profiles';
  static const _keyActiveProfile = 'active_profile';
  static const _keySession = 'session_active';

  Future<bool> hasSession() async {
    final active = await _storage.read(_keySession);
    final token = await _storage.read(AppConstants.secureKeyApiToken);
    return active == '1' || (token != null && token.isNotEmpty);
  }

  Future<void> login({
    required String backendUrl,
    String? token,
    String profileName = 'default',
  }) async {
    final url = backendUrl.trim().replaceAll(RegExp(r'/+$'), '');
    await _client.setBaseUrl(url);
    if (token != null && token.isNotEmpty) {
      await _storage.write(AppConstants.secureKeyApiToken, token);
    }
    await _storage.write(AppConstants.secureKeyBackendUrl, url);
    await _storage.write(_keyActiveProfile, profileName);
    await _storage.write(_keySession, '1');
    await _saveProfile(profileName, url, token ?? '');
    // Verify connectivity
    try {
      await _client.get(ApiPaths.health);
    } catch (_) {
      // Allow offline login with stored credentials
    }
  }

  Future<void> logout() async {
    await _storage.write(_keySession, '0');
    // Keep profiles and optional token for convenience; clear session flag
  }

  Future<void> clearSessionFully() async {
    await _storage.delete(AppConstants.secureKeyApiToken);
    await _storage.write(_keySession, '0');
  }

  Future<List<Map<String, String>>> listProfiles() async {
    final raw = await _storage.read(_keyProfiles);
    if (raw == null || raw.isEmpty) return [];
    try {
      // simple encoding: name|url|token;name|url|token
      return raw.split(';;').where((e) => e.isNotEmpty).map((e) {
        final p = e.split('|');
        return {
          'name': p.isNotEmpty ? p[0] : 'default',
          'url': p.length > 1 ? p[1] : '',
          'token': p.length > 2 ? p[2] : '',
        };
      }).toList();
    } catch (_) {
      return [];
    }
  }

  Future<void> _saveProfile(String name, String url, String token) async {
    final profiles = await listProfiles();
    profiles.removeWhere((p) => p['name'] == name);
    profiles.add({'name': name, 'url': url, 'token': token});
    final encoded = profiles.map((p) => '${p['name']}|${p['url']}|${p['token']}').join(';;');
    await _storage.write(_keyProfiles, encoded);
  }

  Future<void> restoreSession() async {
    final url = await _storage.read(AppConstants.secureKeyBackendUrl);
    if (url != null && url.isNotEmpty) {
      await _client.setBaseUrl(url);
    }
  }
}

class AuthNotifier extends StateNotifier<AuthState> {
  AuthNotifier(this._service) : super(const AuthState()) {
    _bootstrap();
  }
  final AuthService _service;

  Future<void> _bootstrap() async {
    state = state.copyWith(isLoading: true);
    await _service.restoreSession();
    final has = await _service.hasSession();
    final url = await _service._storage.read(AppConstants.secureKeyBackendUrl);
    final profile = await _service._storage.read(AuthService._keyActiveProfile);
    state = state.copyWith(
      isAuthenticated: has,
      isLoading: false,
      backendUrl: url ?? AppConstants.backendDefaultUrl,
      profileName: profile ?? 'default',
    );
  }

  Future<void> login(String url, {String? token, String profile = 'default'}) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      await _service.login(backendUrl: url, token: token, profileName: profile);
      state = state.copyWith(
        isAuthenticated: true,
        isLoading: false,
        backendUrl: url,
        profileName: profile,
      );
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  Future<void> logout() async {
    await _service.logout();
    state = state.copyWith(isAuthenticated: false);
  }
}
