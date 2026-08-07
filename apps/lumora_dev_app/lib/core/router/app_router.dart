import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../features/auth/presentation/screens/login_screen.dart';
import '../../features/home/presentation/screens/home_screen.dart';
import '../../features/chat/presentation/screens/chat_screen.dart';
import '../../features/projects/presentation/screens/projects_screen.dart';
import '../../features/tasks/presentation/screens/tasks_screen.dart';
import '../../features/settings/presentation/screens/settings_screen.dart';
import '../../features/knowledge/presentation/screens/knowledge_screen.dart';
import '../../features/memory/presentation/screens/memory_screen.dart';
import '../../features/browser/presentation/screens/browser_screen.dart';
import '../../features/vision/presentation/screens/vision_screen.dart';
import '../../features/multiagent/presentation/screens/multiagent_screen.dart';
import '../../features/deployment/presentation/screens/deployment_screen.dart';
import '../../features/system/presentation/screens/system_screen.dart';
import '../../features/files/presentation/screens/files_screen.dart';
import '../../features/editor/presentation/screens/editor_screen.dart';
import '../auth/auth_service.dart';
import '../widgets/shell_scaffold.dart';

final appRouterProvider = Provider<GoRouter>((ref) {
  final auth = ref.watch(authStateProvider);
  return GoRouter(
    initialLocation: auth.isAuthenticated ? '/home' : '/login',
    redirect: (context, state) {
      final loggingIn = state.matchedLocation == '/login';
      if (auth.isLoading) return null;
      if (!auth.isAuthenticated && !loggingIn) return '/login';
      if (auth.isAuthenticated && loggingIn) return '/home';
      return null;
    },
    routes: [
      GoRoute(path: '/login', builder: (_, __) => const LoginScreen()),
      ShellRoute(
        builder: (c, s, child) => ShellScaffold(child: child),
        routes: [
          GoRoute(path: '/home', builder: (_, __) => const HomeScreen()),
          GoRoute(path: '/projects', builder: (_, __) => const ProjectsScreen()),
          GoRoute(path: '/chat', builder: (_, __) => const ChatScreen()),
          GoRoute(path: '/tasks', builder: (_, __) => const TasksScreen()),
          GoRoute(path: '/settings', builder: (_, __) => const SettingsScreen()),
          GoRoute(path: '/knowledge', builder: (_, __) => const KnowledgeScreen()),
          GoRoute(path: '/memory', builder: (_, __) => const MemoryScreen()),
          GoRoute(path: '/browser', builder: (_, __) => const BrowserScreen()),
          GoRoute(path: '/vision', builder: (_, __) => const VisionScreen()),
          GoRoute(path: '/multiagent', builder: (_, __) => const MultiAgentScreen()),
          GoRoute(path: '/deployment', builder: (_, __) => const DeploymentScreen()),
          GoRoute(path: '/system', builder: (_, __) => const SystemScreen()),
          GoRoute(path: '/files', builder: (_, __) => const FilesScreen()),
          GoRoute(path: '/editor', builder: (_, s) => EditorScreen(path: s.uri.queryParameters['path'])),
        ],
      ),
    ],
  );
});
