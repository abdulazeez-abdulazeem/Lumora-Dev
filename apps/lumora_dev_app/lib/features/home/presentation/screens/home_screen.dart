import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../../../core/network/lumora_api.dart';
import '../../../../core/realtime/realtime_service.dart';
import '../../../../core/theme/app_colors.dart';
import '../../../../core/widgets/glass_card.dart';

final homeDashboardProvider = FutureProvider<Map<String, dynamic>>((ref) async {
  final api = ref.watch(lumoraApiProvider);
  final out = <String, dynamic>{};
  try { out['system'] = await api.systemStatus(); } catch (_) { out['system'] = {}; }
  try { out['knowledge'] = await api.knowledgeStatus(); } catch (_) { out['knowledge'] = {}; }
  try { out['agents'] = await api.multiagentStatus(); } catch (_) { out['agents'] = {}; }
  try { out['deploy'] = await api.deploymentStatus(); } catch (_) { out['deploy'] = {}; }
  return out;
});

class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});
  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref.read(realtimeServiceProvider).start();
    });
  }

  @override
  Widget build(BuildContext context) {
    final dash = ref.watch(homeDashboardProvider);
    final liveHealth = ref.watch(liveSystemHealthProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Lumora', style: TextStyle(fontWeight: FontWeight.w800)),
        actions: [IconButton(icon: const Icon(Icons.refresh), onPressed: () => ref.invalidate(homeDashboardProvider))],
      ),
      body: RefreshIndicator(
        onRefresh: () async => ref.invalidate(homeDashboardProvider),
        child: dash.when(
          loading: () => const LoadingView(),
          error: (e, _) => ErrorView(message: '$e', onRetry: () => ref.invalidate(homeDashboardProvider)),
          data: (data) {
            final overall = liveHealth.maybeWhen(
              data: (h) => h['overall']?.toString(),
              orElse: () => (data['system'] as Map?)?['overall_health']?.toString(),
            ) ?? '—';
            return ListView(padding: const EdgeInsets.all(16), children: [
              Container(
                padding: const EdgeInsets.all(20),
                decoration: BoxDecoration(
                  gradient: AppColors.brandGradient,
                  borderRadius: BorderRadius.circular(20),
                  boxShadow: [BoxShadow(color: AppColors.purple.withValues(alpha: 0.35), blurRadius: 20, offset: const Offset(0, 8))],
                ),
                child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                  const Text('Autonomous Engineering', style: TextStyle(color: Colors.white70)),
                  const SizedBox(height: 6),
                  const Text('Build. Review. Deploy.', style: TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.w800)),
                  const SizedBox(height: 12),
                  FilledButton.tonal(
                    onPressed: () => context.go('/chat'),
                    style: FilledButton.styleFrom(backgroundColor: Colors.white24),
                    child: const Text('Open AI Assistant', style: TextStyle(color: Colors.white)),
                  ),
                ]),
              ),
              const SectionHeader('Live Status'),
              GridView.count(
                shrinkWrap: true, physics: const NeverScrollableScrollPhysics(),
                crossAxisCount: MediaQuery.sizeOf(context).width > 600 ? 4 : 2,
                childAspectRatio: 1.7, mainAxisSpacing: 8, crossAxisSpacing: 8,
                children: [
                  for (final t in [
                    ('Health', overall, overall == 'healthy' ? AppColors.success : AppColors.warning),
                    ('Knowledge', '${(data['knowledge'] as Map?)?['documents'] ?? (data['knowledge'] as Map?)?['chunks'] ?? '—'}', AppColors.violet),
                    ('Agents', '${((data['agents'] as Map?)?['agents'] as List?)?.length ?? '—'}', AppColors.electricBlue),
                    ('Deploy', '${(data['deploy'] as Map?)?['total'] ?? 0}', AppColors.cyan),
                  ])
                    GlassCard(child: Column(crossAxisAlignment: CrossAxisAlignment.start, mainAxisAlignment: MainAxisAlignment.center, children: [
                      Text(t.$1, style: const TextStyle(color: AppColors.textSecondaryDark, fontSize: 12)),
                      Text(t.$2, style: TextStyle(fontWeight: FontWeight.w700, color: t.$3)),
                    ])),
                ],
              ),
              const SectionHeader('Quick Actions'),
              Wrap(spacing: 8, runSpacing: 8, children: [
                for (final a in [
                  ('Chat', Icons.auto_awesome, '/chat'),
                  ('Agents', Icons.groups_rounded, '/multiagent'),
                  ('Deploy', Icons.rocket_launch_rounded, '/deployment'),
                  ('System', Icons.monitor_heart_rounded, '/system'),
                ])
                  ActionChip(avatar: Icon(a.$2, size: 18, color: AppColors.violet), label: Text(a.$1), onPressed: () => context.go(a.$3)),
              ]),
              const SectionHeader('Modules'),
              for (final m in [
                ('Knowledge', '/knowledge', Icons.menu_book_rounded),
                ('Multi-Agent', '/multiagent', Icons.groups_rounded),
                ('Deployment', '/deployment', Icons.rocket_launch_rounded),
                ('System', '/system', Icons.monitor_heart_rounded),
                ('Vision', '/vision', Icons.visibility_rounded),
                ('Browser', '/browser', Icons.language_rounded),
              ])
                Padding(padding: const EdgeInsets.only(bottom: 8), child: GlassCard(
                  onTap: () => context.go(m.$2),
                  child: Row(children: [
                    Icon(m.$3, color: AppColors.purple), const SizedBox(width: 12),
                    Expanded(child: Text(m.$1, style: const TextStyle(fontWeight: FontWeight.w600))),
                    const Icon(Icons.chevron_right, color: AppColors.textSecondaryDark),
                  ]),
                )),
            ]);
          },
        ),
      ),
    );
  }
}
