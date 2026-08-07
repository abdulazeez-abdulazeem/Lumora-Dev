
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/network/lumora_api.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/widgets/glass_card.dart';

class DeploymentScreen extends ConsumerStatefulWidget {
  const DeploymentScreen({super.key});
  @override
  ConsumerState<DeploymentScreen> createState() => _S();
}
class _S extends ConsumerState<DeploymentScreen> {
  String platform = 'static'; bool loading = false; List platforms = []; List history = []; Map? last; String? error;
  Future<void> load() async {
    setState(() => loading = true);
    try {
      final api = ref.read(lumoraApiProvider);
      platforms = ((await api.deploymentPlatforms())['platforms'] as List?) ?? [];
      history = ((await api.deploymentHistory())['history'] as List?) ?? [];
      setState(() => loading = false);
    } catch (e) { setState(() { error = '$e'; loading = false; }); }
  }
  Future<void> deploy() async {
    setState(() { loading = true; error = null; });
    try { last = await ref.read(lumoraApiProvider).deploymentDeploy(platform: platform); setState(() => loading = false); await load(); }
    catch (e) { setState(() { error = '$e'; loading = false; }); }
  }
  @override
  void initState() { super.initState(); load(); }
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Deployment'), actions: [IconButton(icon: const Icon(Icons.refresh), onPressed: load)]),
    body: ListView(padding: const EdgeInsets.all(16), children: [
      Row(children: [
        Expanded(child: DropdownButtonFormField<String>(value: platform, items: const [
          DropdownMenuItem(value: 'static', child: Text('static')), DropdownMenuItem(value: 'docker', child: Text('docker')),
          DropdownMenuItem(value: 'vercel', child: Text('vercel')), DropdownMenuItem(value: 'netlify', child: Text('netlify')),
          DropdownMenuItem(value: 'railway', child: Text('railway')), DropdownMenuItem(value: 'render', child: Text('render')),
        ], onChanged: (v) => setState(() => platform = v ?? 'static'), decoration: const InputDecoration(labelText: 'Platform'))),
        const SizedBox(width: 8), ElevatedButton(onPressed: loading ? null : deploy, child: const Text('Deploy')),
      ]),
      if (error != null) Text(error!, style: const TextStyle(color: AppColors.error)),
      if (last != null) ...[const SectionHeader('Last Result'), GlassCard(child: Text('$last'))],
      const SectionHeader('Platforms'),
      for (final p in platforms) ListTile(title: Text('${p['name']}'), subtitle: Text('${p['validation']}')),
      const SectionHeader('History'),
      for (final h in history) ListTile(title: Text('${h['deployment_id']} · ${h['platform']}'), trailing: StatusChip(label: '${h['status']}', color: AppColors.cyan)),
    ]),
  );
}
