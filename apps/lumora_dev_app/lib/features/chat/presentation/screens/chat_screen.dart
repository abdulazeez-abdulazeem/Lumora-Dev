import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_markdown/flutter_markdown.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:uuid/uuid.dart';
import '../../../../core/network/lumora_api.dart';
import '../../../../core/storage/secure_storage_service.dart';
import '../../../../core/theme/app_colors.dart';

class ChatMessage {
  ChatMessage({required this.id, required this.role, required this.content, this.pinned = false});
  final String id;
  final String role;
  String content;
  bool pinned;
  Map<String, dynamic> toJson() => {'id': id, 'role': role, 'content': content, 'pinned': pinned};
  factory ChatMessage.fromJson(Map m) => ChatMessage(
    id: m['id']?.toString() ?? const Uuid().v4(),
    role: m['role']?.toString() ?? 'user',
    content: m['content']?.toString() ?? '',
    pinned: m['pinned'] == true,
  );
}

class ChatScreen extends ConsumerStatefulWidget {
  const ChatScreen({super.key});
  @override
  ConsumerState<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends ConsumerState<ChatScreen> {
  final _c = TextEditingController();
  final _search = TextEditingController();
  final _scroll = ScrollController();
  final _messages = <ChatMessage>[];
  bool _sending = false;
  bool _searchOpen = false;
  String? _editingId;
  String? _lastUserPrompt;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final box = ref.read(secureStorageProvider).chat;
      final raw = box.get('messages') as List?;
      if (raw != null) {
        for (final m in raw) {
          if (m is Map) _messages.add(ChatMessage.fromJson(Map<String, dynamic>.from(m)));
        }
        setState(() {});
      }
    } catch (_) {}
  }

  Future<void> _persist() async {
    try {
      final box = ref.read(secureStorageProvider).chat;
      await box.put('messages', _messages.map((m) => m.toJson()).toList());
    } catch (_) {}
  }

  List<ChatMessage> get _visible {
    final q = _search.text.trim().toLowerCase();
    if (q.isEmpty) return _messages;
    return _messages.where((m) => m.content.toLowerCase().contains(q)).toList();
  }

  Future<void> _send([String? override]) async {
    final text = (override ?? _c.text).trim();
    if (text.isEmpty || _sending) return;
    _lastUserPrompt = text;
    if (_editingId != null) {
      final idx = _messages.indexWhere((m) => m.id == _editingId);
      if (idx >= 0) _messages[idx].content = text;
      _editingId = null;
    } else {
      _messages.add(ChatMessage(id: const Uuid().v4(), role: 'user', content: text));
    }
    setState(() { _sending = true; _c.clear(); });
    _scrollEnd();
    try {
      final res = await ref.read(lumoraApiProvider).chat(text);
      final reply = res['response']?.toString() ?? res['message']?.toString() ?? res['content']?.toString() ?? res.toString();
      setState(() {
        _messages.add(ChatMessage(id: const Uuid().v4(), role: 'assistant', content: reply));
        _sending = false;
      });
      await _persist();
    } catch (e) {
      setState(() {
        _messages.add(ChatMessage(id: const Uuid().v4(), role: 'assistant', content: 'Backend error: $e'));
        _sending = false;
      });
    }
    _scrollEnd();
  }

  void _scrollEnd() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scroll.hasClients) _scroll.jumpTo(_scroll.position.maxScrollExtent);
    });
  }

  Future<void> _export() async {
    final buf = StringBuffer('# Lumora Chat Export\n\n');
    for (final m in _messages) {
      buf.writeln('**${m.role}**: ${m.content}\n');
    }
    await Clipboard.setData(ClipboardData(text: buf.toString()));
    if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Conversation copied')));
  }

  @override
  Widget build(BuildContext context) {
    final list = _visible;
    return Scaffold(
      appBar: AppBar(
        title: _searchOpen
            ? TextField(
                controller: _search,
                autofocus: true,
                decoration: const InputDecoration(hintText: 'Search messages…', border: InputBorder.none),
                onChanged: (_) => setState(() {}),
              )
            : const Text('AI Assistant'),
        actions: [
          IconButton(icon: Icon(_searchOpen ? Icons.close : Icons.search), onPressed: () => setState(() {
            _searchOpen = !_searchOpen;
            if (!_searchOpen) _search.clear();
          })),
          IconButton(icon: const Icon(Icons.ios_share), onPressed: _export),
          IconButton(icon: const Icon(Icons.delete_outline), onPressed: () async {
            setState(() => _messages.clear());
            await _persist();
          }),
        ],
      ),
      body: Column(children: [
        Expanded(
          child: list.isEmpty
              ? const Center(child: Text('Ask Lumora to plan, code, test, or deploy.'))
              : ListView.builder(
                  controller: _scroll,
                  padding: const EdgeInsets.all(16),
                  itemCount: list.length,
                  itemBuilder: (_, i) {
                    final m = list[i];
                    final isUser = m.role == 'user';
                    return Align(
                      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
                      child: Container(
                        margin: const EdgeInsets.only(bottom: 10),
                        padding: const EdgeInsets.all(14),
                        constraints: BoxConstraints(maxWidth: MediaQuery.sizeOf(context).width * 0.85),
                        decoration: BoxDecoration(
                          color: isUser ? AppColors.purple.withValues(alpha: 0.25) : AppColors.cardDark,
                          borderRadius: BorderRadius.circular(16),
                          border: Border.all(
                            color: m.pinned ? AppColors.violet : AppColors.borderDark,
                            width: m.pinned ? 1.5 : 0.5,
                          ),
                        ),
                        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                          MarkdownBody(data: m.content, selectable: true),
                          Row(mainAxisAlignment: MainAxisAlignment.end, children: [
                            if (!isUser) ...[
                              IconButton(
                                tooltip: 'Regenerate',
                                icon: const Icon(Icons.refresh, size: 16),
                                onPressed: _lastUserPrompt == null || _sending ? null : () {
                                  // remove last assistant and resend
                                  if (_messages.isNotEmpty && _messages.last.role == 'assistant') {
                                    setState(() => _messages.removeLast());
                                  }
                                  _send(_lastUserPrompt);
                                },
                              ),
                              IconButton(
                                tooltip: 'Copy',
                                icon: const Icon(Icons.copy, size: 16),
                                onPressed: () => Clipboard.setData(ClipboardData(text: m.content)),
                              ),
                            ],
                            if (isUser)
                              IconButton(
                                tooltip: 'Edit',
                                icon: const Icon(Icons.edit, size: 16),
                                onPressed: () {
                                  setState(() {
                                    _editingId = m.id;
                                    _c.text = m.content;
                                  });
                                },
                              ),
                            IconButton(
                              tooltip: m.pinned ? 'Unpin' : 'Pin',
                              icon: Icon(m.pinned ? Icons.push_pin : Icons.push_pin_outlined, size: 16),
                              onPressed: () async {
                                setState(() => m.pinned = !m.pinned);
                                await _persist();
                              },
                            ),
                          ]),
                        ]),
                      ),
                    );
                  },
                ),
        ),
        if (_sending) const LinearProgressIndicator(color: AppColors.purple, minHeight: 2),
        if (_editingId != null)
          MaterialBanner(
            content: const Text('Editing message'),
            actions: [TextButton(onPressed: () => setState(() { _editingId = null; _c.clear(); }), child: const Text('Cancel'))],
          ),
        SafeArea(child: Padding(
          padding: const EdgeInsets.all(12),
          child: Row(children: [
            Expanded(child: TextField(
              controller: _c, minLines: 1, maxLines: 5,
              decoration: InputDecoration(hintText: _editingId != null ? 'Edit message…' : 'Message Lumora…'),
              onSubmitted: (_) => _send(),
            )),
            const SizedBox(width: 8),
            IconButton.filled(
              onPressed: _sending ? null : () => _send(),
              icon: const Icon(Icons.send_rounded),
              style: IconButton.styleFrom(backgroundColor: AppColors.purple),
            ),
          ]),
        )),
      ]),
    );
  }
}
