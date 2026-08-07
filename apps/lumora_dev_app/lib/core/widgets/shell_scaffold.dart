import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../theme/app_colors.dart';
import '../network/connectivity_service.dart';

class ShellScaffold extends ConsumerWidget {
  const ShellScaffold({super.key, required this.child});
  final Widget child;
  static const tabs = [
    ('/home', 'Home', Icons.home_rounded),
    ('/projects', 'Projects', Icons.folder_rounded),
    ('/chat', 'Chat', Icons.auto_awesome),
    ('/tasks', 'Tasks', Icons.checklist_rounded),
    ('/settings', 'Settings', Icons.settings_rounded),
  ];
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final loc = GoRouterState.of(context).uri.toString();
    final online = ref.watch(isOnlineProvider);
    var index = 0;
    for (var i = 0; i < tabs.length; i++) {
      if (loc.startsWith(tabs[i].$1)) index = i;
    }
    return Scaffold(
      drawer: Drawer(
        backgroundColor: AppColors.surfaceDark,
        child: SafeArea(child: ListView(children: [
          const DrawerHeader(child: Text('Lumora Dev', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w800))),
          for (final i in [
            ('Knowledge', '/knowledge', Icons.menu_book_rounded),
            ('Memory', '/memory', Icons.psychology_rounded),
            ('Browser', '/browser', Icons.language_rounded),
            ('Vision', '/vision', Icons.visibility_rounded),
            ('Multi-Agent', '/multiagent', Icons.groups_rounded),
            ('Deployment', '/deployment', Icons.rocket_launch_rounded),
            ('System', '/system', Icons.monitor_heart_rounded),
            ('Files', '/files', Icons.folder_open_rounded),
            ('Editor', '/editor', Icons.code_rounded),
          ])
            ListTile(leading: Icon(i.$3, color: AppColors.violet), title: Text(i.$1), onTap: () { Navigator.pop(context); context.go(i.$2); }),
        ])),
      ),
      body: Column(children: [
        if (!online) MaterialBanner(content: const Text('Offline'), actions: [TextButton(onPressed: () {}, child: const Text('OK'))]),
        Expanded(child: child),
      ]),
      bottomNavigationBar: NavigationBar(
        selectedIndex: index,
        onDestinationSelected: (i) => context.go(tabs[i].$1),
        destinations: [for (final t in tabs) NavigationDestination(icon: Icon(t.$3), label: t.$2)],
      ),
    );
  }
}
