
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/network/lumora_api.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/widgets/glass_card.dart';

class SystemScreen extends ConsumerStatefulWidget {
  const SystemScreen({super.key});
  @override
  ConsumerState<SystemScreen> createState() => _S();
}
class _S extends ConsumerState<SystemScreen> {
  Map? health, metrics, diag; bool loading = false; String? error;
  Future<void> load() async {
    setState(() { loading = true; error = null; });
    try {
      final api = ref.read(lumoraApiProvider);
      health = await api.systemHealth(); metrics = await api.systemMetrics(); diag = await api.systemDiagnostics();
      setState(() => loading = false);
    } catch (e) { setState(() { error = '$e'; loading = false; }); }
  }
  @override
  void initState() { super.initState(); load(); }
  @override
  Widget build(BuildContext context) {
    final components = (health?['components'] as List?) ?? [];
    return Scaffold(
      appBar: AppBar(title: const Text('System'), actions: [IconButton(icon: const Icon(Icons.refresh), onPressed: load)]),
      body: loading ? const LoadingView() : ListView(padding: const EdgeInsets.all(16), children: [
        if (error != null) Text(error!, style: const TextStyle(color: AppColors.error)),
        GlassCard(child: Row(children: [const Text('Overall', style: TextStyle(fontWeight: FontWeight.w600)), const Spacer(),
          StatusChip(label: '${health?['overall'] ?? 'unknown'}', color: health?['overall'] == 'healthy' ? AppColors.success : AppColors.warning)])),
        const SectionHeader('Components'),
        for (final c in components) ListTile(title: Text('${c['name']}'), subtitle: Text('${c['message']} · ${c['latency_ms']}ms'),
          trailing: StatusChip(label: '${c['status']}', color: c['status'] == 'healthy' ? AppColors.success : AppColors.warning)),
        const SectionHeader('Metrics'),
        if (metrics != null) GlassCard(child: Text('$metrics', style: const TextStyle(fontSize: 11))),
        const SectionHeader('Diagnostics'),
        if (diag != null) GlassCard(child: Text('Suggestions: ${(diag!['suggestions'] as List?)?.join('; ')}\nRecovery: ${(diag!['recovery_actions'] as List?)?.join('; ')}')),
      ]),
    );
  }
}
