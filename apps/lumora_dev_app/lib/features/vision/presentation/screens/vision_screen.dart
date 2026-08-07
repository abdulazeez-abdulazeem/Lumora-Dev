
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/network/lumora_api.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/widgets/glass_card.dart';

class VisionScreen extends ConsumerStatefulWidget {
  const VisionScreen({super.key});
  @override
  ConsumerState<VisionScreen> createState() => _S();
}
class _S extends ConsumerState<VisionScreen> {
  Map? status, result; bool loading = false; String? error;
  @override
  void initState() { super.initState(); ref.read(lumoraApiProvider).visionStatus().then((s) => setState(() => status = s)).catchError((e) => setState(() => error = '$e')); }
  Future<void> analyze() async {
    setState(() { loading = true; error = null; });
    try {
      final api = ref.read(lumoraApiProvider);
      final shot = await api.browserScreenshot();
      final path = shot['path']?.toString() ?? shot['screenshot']?.toString() ?? '';
      if (path.isEmpty) throw Exception('No screenshot from browser');
      result = await api.visionAnalyze(path);
      setState(() => loading = false);
    } catch (e) { setState(() { error = '$e'; loading = false; }); }
  }
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Vision')),
    body: ListView(padding: const EdgeInsets.all(16), children: [
      ElevatedButton(onPressed: loading ? null : analyze, child: const Text('Capture & Analyze')),
      if (loading) const LinearProgressIndicator(color: AppColors.purple, minHeight: 2),
      if (error != null) Text(error!, style: const TextStyle(color: AppColors.error)),
      const SectionHeader('Status'), GlassCard(child: Text('${status ?? '—'}')),
      const SectionHeader('Analysis'),
      if (result != null) GlassCard(child: Text('Confidence: ${result!['confidence']}\n${result!['message']}\nIssues: ${result!['issues']}')),
    ]),
  );
}
