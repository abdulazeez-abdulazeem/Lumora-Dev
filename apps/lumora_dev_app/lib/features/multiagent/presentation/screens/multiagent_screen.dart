
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/network/lumora_api.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/widgets/glass_card.dart';

class MultiAgentScreen extends ConsumerStatefulWidget {
  const MultiAgentScreen({super.key});
  @override
  ConsumerState<MultiAgentScreen> createState() => _S();
}
class _S extends ConsumerState<MultiAgentScreen> {
  final goal = TextEditingController();
  bool loading = false; List agents = []; List tasks = []; List messages = []; String? error;
  Future<void> refresh() async {
    setState(() { loading = true; error = null; });
    try {
      final api = ref.read(lumoraApiProvider);
      agents = ((await api.multiagentAgents())['agents'] as List?) ?? [];
      tasks = ((await api.multiagentTasks())['tasks'] as List?) ?? [];
      messages = ((await api.multiagentMessages())['messages'] as List?) ?? [];
      setState(() => loading = false);
    } catch (e) { setState(() { error = '$e'; loading = false; }); }
  }
  Future<void> start() async {
    if (goal.text.trim().isEmpty) return;
    setState(() => loading = true);
    try { await ref.read(lumoraApiProvider).multiagentStart(goal.text.trim()); await refresh(); }
    catch (e) { setState(() { error = '$e'; loading = false; }); }
  }
  @override
  void initState() { super.initState(); refresh(); }
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Multi-Agent'), actions: [IconButton(icon: const Icon(Icons.refresh), onPressed: refresh)]),
    body: ListView(padding: const EdgeInsets.all(16), children: [
      Row(children: [Expanded(child: TextField(controller: goal, decoration: const InputDecoration(hintText: 'Goal…'))), const SizedBox(width: 8), ElevatedButton(onPressed: loading ? null : start, child: const Text('Start'))]),
      if (error != null) Text(error!, style: const TextStyle(color: AppColors.error)),
      const SectionHeader('Agents'),
      for (final a in agents) Padding(padding: const EdgeInsets.only(bottom: 6), child: GlassCard(child: Row(children: [
        Icon(a['active'] == true ? Icons.circle : Icons.circle_outlined, size: 12, color: a['active'] == true ? AppColors.success : AppColors.textSecondaryDark),
        const SizedBox(width: 10), Expanded(child: Text('${a['role']}', style: const TextStyle(fontWeight: FontWeight.w600))),
      ]))),
      const SectionHeader('Tasks'),
      for (final t in tasks) ListTile(dense: true, title: Text('${t['title']}'), subtitle: Text('${t['role']} · ${t['status']}'), leading: StatusChip(label: '${t['status']}', color: AppColors.electricBlue)),
      const SectionHeader('Messages'),
      for (final m in messages.take(20)) ListTile(dense: true, title: Text('${m['from_agent']} → ${m['to_agent']}'), subtitle: Text('${m['body']}')),
    ]),
  );
}
