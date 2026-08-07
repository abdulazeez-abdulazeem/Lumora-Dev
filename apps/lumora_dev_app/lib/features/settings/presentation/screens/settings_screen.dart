import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../../core/auth/auth_service.dart';
import '../../../../core/constants/app_constants.dart';
import '../../../../core/network/api_client.dart';
import '../../../../core/storage/secure_storage_service.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/widgets/glass_card.dart';

final themeModeProvider = StateProvider<ThemeMode>((ref) => ThemeMode.dark);
final fontScaleProvider = StateProvider<double>((ref) => 1.0);
final accentColorProvider = StateProvider<Color>((ref) => AppColors.purple);

class SettingsScreen extends ConsumerStatefulWidget {
  const SettingsScreen({super.key});
  @override
  ConsumerState<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends ConsumerState<SettingsScreen> {
  final _url = TextEditingController(text: AppConstants.backendDefaultUrl);
  final _token = TextEditingController();
  bool _obscure = true;
  List<Map<String, String>> _profiles = [];

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final s = ref.read(secureStorageProvider);
    final url = await s.read(AppConstants.secureKeyBackendUrl);
    final token = await s.read(AppConstants.secureKeyApiToken);
    if (url != null) _url.text = url;
    if (token != null) _token.text = token;
    _profiles = await ref.read(authServiceProvider).listProfiles();
    setState(() {});
  }

  Future<void> _saveBackend() async {
    await ref.read(apiClientProvider).setBaseUrl(_url.text.trim());
    await ref.read(secureStorageProvider).write(AppConstants.secureKeyApiToken, _token.text.trim());
    if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Saved securely')));
  }

  Future<void> _clearCache() async {
    try {
      final s = ref.read(secureStorageProvider);
      await s.cache.clear();
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Cache cleared')));
    } catch (e) {
      if (mounted) ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Error: $e')));
    }
  }

  @override
  Widget build(BuildContext context) {
    final themeMode = ref.watch(themeModeProvider);
    final fontScale = ref.watch(fontScaleProvider);
    final auth = ref.watch(authStateProvider);

    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: ListView(padding: const EdgeInsets.all(16), children: [
        const SectionHeader('Session'),
        GlassCard(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('Profile: ${auth.profileName}', style: const TextStyle(fontWeight: FontWeight.w600)),
          Text(auth.backendUrl, style: const TextStyle(fontSize: 12, color: AppColors.textSecondaryDark)),
          const SizedBox(height: 8),
          Row(children: [
            ElevatedButton(
              onPressed: () async {
                await ref.read(authStateProvider.notifier).logout();
                if (context.mounted) context.go('/login');
              },
              child: const Text('Logout'),
            ),
          ]),
        ])),
        const SectionHeader('Backend'),
        GlassCard(child: Column(children: [
          TextField(controller: _url, decoration: const InputDecoration(labelText: 'Backend URL')),
          const SizedBox(height: 12),
          TextField(
            controller: _token, obscureText: _obscure,
            decoration: InputDecoration(
              labelText: 'API Token',
              suffixIcon: IconButton(
                icon: Icon(_obscure ? Icons.visibility : Icons.visibility_off),
                onPressed: () => setState(() => _obscure = !_obscure),
              ),
            ),
          ),
          const SizedBox(height: 12),
          Align(alignment: Alignment.centerRight, child: ElevatedButton(onPressed: _saveBackend, child: const Text('Save'))),
        ])),
        if (_profiles.isNotEmpty) ...[
          const SectionHeader('Saved Profiles'),
          for (final p in _profiles)
            ListTile(
              title: Text(p['name'] ?? ''),
              subtitle: Text(p['url'] ?? ''),
              trailing: TextButton(
                child: const Text('Use'),
                onPressed: () async {
                  await ref.read(authStateProvider.notifier).login(
                    p['url'] ?? AppConstants.backendDefaultUrl,
                    token: (p['token'] ?? '').isEmpty ? null : p['token'],
                    profile: p['name'] ?? 'default',
                  );
                  await _load();
                },
              ),
            ),
        ],
        const SectionHeader('Appearance'),
        GlassCard(child: Column(children: [
          for (final m in [(ThemeMode.dark, 'Dark'), (ThemeMode.light, 'Light'), (ThemeMode.system, 'System')])
            RadioListTile<ThemeMode>(
              title: Text(m.$2), value: m.$1, groupValue: themeMode,
              onChanged: (v) => ref.read(themeModeProvider.notifier).state = v!,
            ),
          ListTile(
            title: const Text('Font size'),
            subtitle: Slider(
              value: fontScale, min: 0.85, max: 1.3, divisions: 9,
              onChanged: (v) => ref.read(fontScaleProvider.notifier).state = v,
            ),
            trailing: Text('${(fontScale * 100).round()}%'),
          ),
        ])),
        const SectionHeader('Data'),
        GlassCard(child: ListTile(
          leading: const Icon(Icons.cleaning_services_outlined),
          title: const Text('Clear cache'),
          onTap: _clearCache,
        )),
        const SectionHeader('About'),
        const GlassCard(child: Text('Lumora Dev App v1.1.0\nClient for Lumora Dev v4.0\nAuth · Realtime · Production polish')),
      ]),
    );
  }
}
