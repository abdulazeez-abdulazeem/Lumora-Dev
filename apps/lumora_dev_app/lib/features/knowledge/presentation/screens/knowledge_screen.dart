
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/network/lumora_api.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/widgets/glass_card.dart';

class KnowledgeScreen extends ConsumerStatefulWidget {
  const KnowledgeScreen({super.key});
  @override
  ConsumerState<KnowledgeScreen> createState() => _S();
}
class _S extends ConsumerState<KnowledgeScreen> {
  final q = TextEditingController();
  bool loading = false; Map? result; String? error;
  Future<void> search() async {
    if (q.text.trim().isEmpty) return;
    setState(() { loading = true; error = null; });
    try { result = await ref.read(lumoraApiProvider).knowledgeSearch(q.text.trim()); setState(() => loading = false); }
    catch (e) { setState(() { error = '$e'; loading = false; }); }
  }
  @override
  Widget build(BuildContext context) {
    final results = (result?['results'] as List?) ?? [];
    final cites = (result?['citations'] as List?) ?? [];
    return Scaffold(
      appBar: AppBar(title: const Text('Knowledge'), actions: [IconButton(icon: const Icon(Icons.sync), onPressed: () => ref.read(lumoraApiProvider).knowledgeReindex())]),
      body: Column(children: [
        Padding(padding: const EdgeInsets.all(16), child: Row(children: [
          Expanded(child: TextField(controller: q, decoration: const InputDecoration(hintText: 'Search docs…'), onSubmitted: (_) => search())),
          const SizedBox(width: 8), ElevatedButton(onPressed: loading ? null : search, child: const Text('Search')),
        ])),
        if (loading) const LinearProgressIndicator(color: AppColors.purple, minHeight: 2),
        if (error != null) Text(error!, style: const TextStyle(color: AppColors.error)),
        Expanded(child: results.isEmpty ? const EmptyState(icon: Icons.menu_book_outlined, message: 'Search the knowledge base') : ListView(
          padding: const EdgeInsets.all(16),
          children: [
            for (final r in results) Padding(padding: const EdgeInsets.only(bottom: 8), child: GlassCard(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              Row(children: [Expanded(child: Text('${r['title'] ?? r['source']}', style: const TextStyle(fontWeight: FontWeight.w600))), StatusChip(label: '${r['score'] ?? ''}', color: AppColors.violet)]),
              const SizedBox(height: 6), Text('${r['text'] ?? ''}', maxLines: 4, overflow: TextOverflow.ellipsis),
            ]))),
            if (cites.isNotEmpty) const SectionHeader('Citations'),
            for (final c in cites) ListTile(dense: true, leading: CircleAvatar(radius: 12, child: Text('${c['index']}', style: const TextStyle(fontSize: 11))), title: Text('${c['title']}')),
          ],
        )),
      ]),
    );
  }
}
