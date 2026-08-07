import 'dart:async';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../../core/network/lumora_api.dart';
import '../../../../core/theme/app_colors.dart';

class EditorScreen extends ConsumerStatefulWidget {
  const EditorScreen({super.key, this.path});
  final String? path;
  @override
  ConsumerState<EditorScreen> createState() => _EditorScreenState();
}

class _EditorScreenState extends ConsumerState<EditorScreen> {
  late final TextEditingController c;
  bool loading = false, saving = false, dirty = false;
  String? error;
  Timer? _autoSave;

  @override
  void initState() {
    super.initState();
    c = TextEditingController();
    c.addListener(() {
      dirty = true;
      _autoSave?.cancel();
      _autoSave = Timer(const Duration(seconds: 2), () {
        if (dirty && widget.path != null) save(silent: true);
      });
    });
    if (widget.path != null) load();
  }

  @override
  void dispose() {
    _autoSave?.cancel();
    c.dispose();
    super.dispose();
  }

  Future<void> load() async {
    setState(() => loading = true);
    try {
      final r = await ref.read(lumoraApiProvider).filesRead(widget.path!);
      c.text = r['content']?.toString() ?? r['text']?.toString() ?? '';
      dirty = false;
      setState(() => loading = false);
    } catch (e) {
      setState(() { error = '$e'; loading = false; });
    }
  }

  Future<void> save({bool silent = false}) async {
    if (widget.path == null) return;
    setState(() => saving = true);
    try {
      await ref.read(lumoraApiProvider).filesWrite(widget.path!, c.text);
      dirty = false;
      setState(() => saving = false);
      if (!silent && mounted) {
        ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Saved')));
      }
    } catch (e) {
      setState(() { error = '$e'; saving = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text('${widget.path ?? 'Editor'}${dirty ? ' •' : ''}'),
        actions: [
          if (saving) const Padding(padding: EdgeInsets.all(12), child: SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2))),
          IconButton(icon: const Icon(Icons.save), onPressed: () => save()),
        ],
      ),
      body: loading
          ? const Center(child: CircularProgressIndicator())
          : Column(children: [
              if (error != null) Text(error!, style: const TextStyle(color: AppColors.error)),
              Expanded(
                child: TextField(
                  controller: c,
                  maxLines: null,
                  expands: true,
                  style: const TextStyle(fontFamily: 'monospace', fontSize: 13),
                  decoration: const InputDecoration(border: InputBorder.none, contentPadding: EdgeInsets.all(16), hintText: 'Code…'),
                ),
              ),
            ]),
    );
  }
}
