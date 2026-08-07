
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/network/lumora_api.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/widgets/glass_card.dart';

class MemoryScreen extends ConsumerStatefulWidget {
  const MemoryScreen({super.key});
  @override
  ConsumerState<MemoryScreen> createState() => _S();
}
class _S extends ConsumerState<MemoryScreen> {
  final note = TextEditingController(); List notes = []; bool loading = false;
  Future<void> load() async {
    setState(() => loading = true);
    try {
      final r = await ref.read(lumoraApiProvider).memoryList();
      notes = (r['notes'] as List?) ?? (r['items'] as List?) ?? [];
      setState(() => loading = false);
    } catch (_) { setState(() => loading = false); }
  }
  @override
  void initState() { super.initState(); load(); }
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Memory'), actions: [IconButton(icon: const Icon(Icons.refresh), onPressed: load)]),
    body: Column(children: [
      Padding(padding: const EdgeInsets.all(16), child: Row(children: [
        Expanded(child: TextField(controller: note, decoration: const InputDecoration(hintText: 'Remember…'))),
        IconButton(icon: const Icon(Icons.add), onPressed: () async {
          if (note.text.trim().isEmpty) return;
          await ref.read(lumoraApiProvider).memoryRemember(note.text.trim()); note.clear(); await load();
        }),
      ])),
      if (loading) const LinearProgressIndicator(color: AppColors.purple, minHeight: 2),
      Expanded(child: notes.isEmpty ? const EmptyState(icon: Icons.psychology_outlined, message: 'No memory notes') : ListView.builder(
        padding: const EdgeInsets.symmetric(horizontal: 16), itemCount: notes.length,
        itemBuilder: (_, i) {
          final n = notes[i];
          final text = n is Map ? (n['text'] ?? n['note'] ?? n.toString()) : n.toString();
          return Padding(padding: const EdgeInsets.only(bottom: 8), child: GlassCard(child: Text('$text')));
        },
      )),
    ]),
  );
}
