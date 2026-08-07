import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../../core/storage/secure_storage_service.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/widgets/glass_card.dart';

class ProjectsScreen extends ConsumerStatefulWidget {
  const ProjectsScreen({super.key});
  @override
  ConsumerState<ProjectsScreen> createState() => _ProjectsScreenState();
}

class _ProjectsScreenState extends ConsumerState<ProjectsScreen> {
  final items = <Map<String, dynamic>>[];
  String q = '';
  String filter = 'all'; // all | favorites | recent

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final box = ref.read(secureStorageProvider).settings;
      final raw = box.get('projects') as List?;
      if (raw != null) {
        items.clear();
        for (final p in raw) {
          if (p is Map) items.add(Map<String, dynamic>.from(p));
        }
      }
      if (items.isEmpty) items.add({'name': 'Lumora Dev', 'path': '.', 'favorite': true, 'recent': true});
      setState(() {});
    } catch (_) {
      if (items.isEmpty) items.add({'name': 'Lumora Dev', 'path': '.', 'favorite': true, 'recent': true});
    }
  }

  Future<void> _persist() async {
    try {
      final box = ref.read(secureStorageProvider).settings;
      await box.put('projects', items);
    } catch (_) {}
  }

  List<Map<String, dynamic>> get filtered {
    var list = items.where((p) => p['name'].toString().toLowerCase().contains(q.toLowerCase())).toList();
    if (filter == 'favorites') list = list.where((p) => p['favorite'] == true).toList();
    if (filter == 'recent') list = list.where((p) => p['recent'] == true).toList();
    return list;
  }

  @override
  Widget build(BuildContext context) {
    final f = filtered;
    return Scaffold(
      appBar: AppBar(title: const Text('Projects')),
      floatingActionButton: FloatingActionButton(
        backgroundColor: AppColors.purple,
        onPressed: () async {
          final c = TextEditingController();
          final name = await showDialog<String>(
            context: context,
            builder: (ctx) => AlertDialog(
              title: const Text('New Project'),
              content: TextField(controller: c, decoration: const InputDecoration(hintText: 'Name')),
              actions: [
                TextButton(onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
                ElevatedButton(onPressed: () => Navigator.pop(ctx, c.text.trim()), child: const Text('Create')),
              ],
            ),
          );
          if (name != null && name.isNotEmpty) {
            setState(() => items.add({'name': name, 'path': name, 'favorite': false, 'recent': true}));
            await _persist();
          }
        },
        child: const Icon(Icons.add),
      ),
      body: Column(children: [
        Padding(padding: const EdgeInsets.fromLTRB(16, 16, 16, 8), child: TextField(
          decoration: const InputDecoration(prefixIcon: Icon(Icons.search), hintText: 'Search projects'),
          onChanged: (v) => setState(() => q = v),
        )),
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Row(children: [
            for (final chip in [('all', 'All'), ('favorites', 'Favorites'), ('recent', 'Recent')])
              Padding(
                padding: const EdgeInsets.only(right: 8),
                child: FilterChip(
                  label: Text(chip.$2),
                  selected: filter == chip.$1,
                  onSelected: (_) => setState(() => filter = chip.$1),
                ),
              ),
          ]),
        ),
        Expanded(
          child: f.isEmpty
              ? const EmptyState(icon: Icons.folder_off, message: 'No projects match')
              : ListView.builder(
                  padding: const EdgeInsets.all(16),
                  itemCount: f.length,
                  itemBuilder: (_, i) {
                    final p = f[i];
                    return Dismissible(
                      key: ValueKey(p['name']),
                      background: Container(color: AppColors.error, alignment: Alignment.centerRight, padding: const EdgeInsets.only(right: 16), child: const Icon(Icons.delete, color: Colors.white)),
                      direction: DismissDirection.endToStart,
                      onDismissed: (_) async {
                        items.removeWhere((x) => x['name'] == p['name']);
                        await _persist();
                        setState(() {});
                      },
                      child: Padding(
                        padding: const EdgeInsets.only(bottom: 8),
                        child: GlassCard(
                          onTap: () {
                            p['recent'] = true;
                            _persist();
                            context.go('/files');
                          },
                          child: Row(children: [
                            IconButton(
                              icon: Icon(p['favorite'] == true ? Icons.star_rounded : Icons.star_outline, color: AppColors.violet),
                              onPressed: () async {
                                setState(() => p['favorite'] = !(p['favorite'] == true));
                                await _persist();
                              },
                            ),
                            Expanded(child: Text('${p['name']}', style: const TextStyle(fontWeight: FontWeight.w600))),
                            PopupMenuButton<String>(
                              onSelected: (v) async {
                                if (v == 'duplicate') {
                                  setState(() => items.add({...p, 'name': '${p['name']} copy', 'favorite': false}));
                                  await _persist();
                                } else if (v == 'rename') {
                                  final c = TextEditingController(text: p['name']?.toString());
                                  final name = await showDialog<String>(context: context, builder: (ctx) => AlertDialog(
                                    title: const Text('Rename'), content: TextField(controller: c),
                                    actions: [ElevatedButton(onPressed: () => Navigator.pop(ctx, c.text.trim()), child: const Text('OK'))],
                                  ));
                                  if (name != null && name.isNotEmpty) {
                                    setState(() => p['name'] = name);
                                    await _persist();
                                  }
                                }
                              },
                              itemBuilder: (_) => const [
                                PopupMenuItem(value: 'duplicate', child: Text('Duplicate')),
                                PopupMenuItem(value: 'rename', child: Text('Rename')),
                              ],
                            ),
                          ]),
                        ),
                      ),
                    );
                  },
                ),
        ),
      ]),
    );
  }
}
