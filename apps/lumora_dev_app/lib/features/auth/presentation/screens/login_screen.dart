import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../../core/auth/auth_service.dart';
import '../../../../core/constants/app_constants.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/widgets/glass_card.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});
  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _url = TextEditingController(text: AppConstants.backendDefaultUrl);
  final _token = TextEditingController();
  final _profile = TextEditingController(text: 'default');
  bool _obscure = true;

  @override
  Widget build(BuildContext context) {
    final auth = ref.watch(authStateProvider);
    return Scaffold(
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 420),
              child: Column(
                children: [
                  Container(
                    width: 72, height: 72,
                    decoration: BoxDecoration(gradient: AppColors.brandGradient, borderRadius: BorderRadius.circular(20)),
                    child: const Icon(Icons.auto_awesome, color: Colors.white, size: 36),
                  ),
                  const SizedBox(height: 20),
                  const Text('Lumora Dev', style: TextStyle(fontSize: 28, fontWeight: FontWeight.w800)),
                  const SizedBox(height: 6),
                  const Text('Connect to your Lumora backend', style: TextStyle(color: AppColors.textSecondaryDark)),
                  const SizedBox(height: 28),
                  GlassCard(child: Column(children: [
                    TextField(controller: _profile, decoration: const InputDecoration(labelText: 'Profile name')),
                    const SizedBox(height: 12),
                    TextField(controller: _url, decoration: const InputDecoration(labelText: 'Backend URL', hintText: 'http://127.0.0.1:8000')),
                    const SizedBox(height: 12),
                    TextField(
                      controller: _token, obscureText: _obscure,
                      decoration: InputDecoration(
                        labelText: 'API Token (optional)',
                        suffixIcon: IconButton(
                          icon: Icon(_obscure ? Icons.visibility : Icons.visibility_off),
                          onPressed: () => setState(() => _obscure = !_obscure),
                        ),
                      ),
                    ),
                    if (auth.error != null) ...[
                      const SizedBox(height: 8),
                      Text(auth.error!, style: const TextStyle(color: AppColors.error, fontSize: 12)),
                    ],
                    const SizedBox(height: 16),
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton(
                        onPressed: auth.isLoading ? null : () async {
                          await ref.read(authStateProvider.notifier).login(
                            _url.text.trim(),
                            token: _token.text.trim().isEmpty ? null : _token.text.trim(),
                            profile: _profile.text.trim().isEmpty ? 'default' : _profile.text.trim(),
                          );
                          if (ref.read(authStateProvider).isAuthenticated && context.mounted) {
                            context.go('/home');
                          }
                        },
                        child: auth.isLoading
                            ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                            : const Text('Connect'),
                      ),
                    ),
                  ])),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
