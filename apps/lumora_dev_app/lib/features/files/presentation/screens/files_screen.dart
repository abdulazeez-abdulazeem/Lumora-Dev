
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../../core/network/lumora_api.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/widgets/glass_card.dart';

class FilesScreen extends ConsumerStatefulWidget {
  const FilesScreen({super.key});
  @override
  ConsumerState<FilesScreen> createState() => _S();
}
class _S extends ConsumerState<FilesScreen> {
  String path = '.'; List files = []; bool loading = false; String? error;
  Future<void> load([String? p]) async {
    setState(() { loading = true; error = null; if (p != null) path = p; });
    try {
      final r = await ref.read(lumoraApiProvider).filesList(path: path);
      files = (r['files'] as List?) ?? (r['entries'] as List?) ?? (r['items'] as List?) ?? [];
      setState(() => loading = false);
    } catch (e) { setState(() { error = '$e'; loading = false; }); }
  }
  @override
  void initState() { super.initState(); load(); }
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: Text('Files · $path'), actions: [IconButton(icon: const Icon(Icons.refresh), onPressed: () => load())]),
    body: loading ? const LoadingView() : error != null ? ErrorView(message: error!, onRetry: () => load())
      : ListView.builder(padding: const EdgeInsets.all(16), itemCount: files.length, itemBuilder: (_, i) {
          final f = files[i];
          final name = f is Map ? (f['name'] ?? f['path'] ?? f.toString()) : f.toString();
          final isDir = f is Map && (f['is_dir'] == true || f['type'] == 'dir');
          return Padding(padding: const EdgeInsets.only(bottom: 6), child: GlassCard(
            onTap: () { if (isDir) load('$path/$name'); else context.go('/editor?path=${Uri.encodeComponent('$path/$name')}'); },
            child: Row(children: [Icon(isDir ? Icons.folder : Icons.insert_drive_file, color: AppColors.violet), const SizedBox(width: 12), Expanded(child: Text('$name'))]),
          ));
        }),
  );
}
