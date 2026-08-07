
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/network/lumora_api.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/widgets/glass_card.dart';

class TasksScreen extends ConsumerStatefulWidget {
  const TasksScreen({super.key});
  @override
  ConsumerState<TasksScreen> createState() => _S();
}
class _S extends ConsumerState<TasksScreen> {
  List tasks = []; bool loading = false; String? error;
  Future<void> load() async {
    setState(() { loading = true; error = null; });
    try { tasks = ((await ref.read(lumoraApiProvider).multiagentTasks())['tasks'] as List?) ?? []; setState(() => loading = false); }
    catch (e) { setState(() { error = '$e'; loading = false; }); }
  }
  @override
  void initState() { super.initState(); load(); }
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Tasks'), actions: [IconButton(icon: const Icon(Icons.refresh), onPressed: load)]),
    body: loading ? const LoadingView() : error != null ? ErrorView(message: error!, onRetry: load)
      : tasks.isEmpty ? const EmptyState(icon: Icons.checklist, message: 'No agent tasks — start a multi-agent goal')
      : ListView.builder(padding: const EdgeInsets.all(16), itemCount: tasks.length, itemBuilder: (_, i) {
          final t = tasks[i];
          return Padding(padding: const EdgeInsets.only(bottom: 8), child: GlassCard(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [Expanded(child: Text('${t['title']}', style: const TextStyle(fontWeight: FontWeight.w600))), StatusChip(label: '${t['status']}', color: AppColors.electricBlue)]),
            Text('${t['role']} · ${t['description'] ?? ''}', style: const TextStyle(fontSize: 12, color: AppColors.textSecondaryDark)),
          ])));
        }),
  );
}
