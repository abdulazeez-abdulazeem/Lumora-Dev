
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/network/lumora_api.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/widgets/glass_card.dart';

class BrowserScreen extends ConsumerStatefulWidget {
  const BrowserScreen({super.key});
  @override
  ConsumerState<BrowserScreen> createState() => _S();
}
class _S extends ConsumerState<BrowserScreen> {
  final url = TextEditingController(text: 'https://example.com');
  Map? status; String? error; bool loading = false;
  Future<void> refresh() async {
    setState(() => loading = true);
    try { status = await ref.read(lumoraApiProvider).browserStatus(); setState(() => loading = false); }
    catch (e) { setState(() { error = '$e'; loading = false; }); }
  }
  @override
  void initState() { super.initState(); refresh(); }
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Browser'), actions: [IconButton(icon: const Icon(Icons.refresh), onPressed: refresh)]),
    body: ListView(padding: const EdgeInsets.all(16), children: [
      Row(children: [Expanded(child: TextField(controller: url, decoration: const InputDecoration(hintText: 'URL'))),
        IconButton(icon: const Icon(Icons.navigation), onPressed: () async {
          setState(() => loading = true);
          try { await ref.read(lumoraApiProvider).browserGoto(url.text.trim()); await refresh(); }
          catch (e) { setState(() { error = '$e'; loading = false; }); }
        })]),
      const SizedBox(height: 12),
      Wrap(spacing: 8, children: [
        ElevatedButton(onPressed: () async { await ref.read(lumoraApiProvider).browserLaunch(); await refresh(); }, child: const Text('Launch')),
        ElevatedButton(onPressed: () async { await ref.read(lumoraApiProvider).browserScreenshot(); }, child: const Text('Screenshot')),
        ElevatedButton(onPressed: () async { await ref.read(lumoraApiProvider).browserClose(); await refresh(); }, child: const Text('Close')),
      ]),
      if (error != null) Text(error!, style: const TextStyle(color: AppColors.error)),
      if (loading) const LinearProgressIndicator(color: AppColors.purple, minHeight: 2),
      const SectionHeader('Status'), GlassCard(child: Text('${status ?? '—'}')),
    ]),
  );
}
