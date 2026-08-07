import 'dart:async';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../network/lumora_api.dart';

/// Polling-based realtime updates with graceful degradation.
/// WebSocket/SSE can be plugged in later without changing consumers.
final realtimeServiceProvider = Provider<RealtimeService>((ref) {
  final svc = RealtimeService(ref.watch(lumoraApiProvider));
  ref.onDispose(svc.dispose);
  return svc;
});

final liveSystemHealthProvider = StreamProvider<Map<String, dynamic>>((ref) {
  return ref.watch(realtimeServiceProvider).systemHealthStream;
});

final liveMultiAgentProvider = StreamProvider<Map<String, dynamic>>((ref) {
  return ref.watch(realtimeServiceProvider).multiAgentStream;
});

final liveDeploymentProvider = StreamProvider<Map<String, dynamic>>((ref) {
  return ref.watch(realtimeServiceProvider).deploymentStream;
});

final liveTasksProvider = StreamProvider<List>((ref) {
  return ref.watch(realtimeServiceProvider).tasksStream;
});

class RealtimeService {
  RealtimeService(this._api);
  final LumoraApi _api;

  final _systemCtrl = StreamController<Map<String, dynamic>>.broadcast();
  final _agentCtrl = StreamController<Map<String, dynamic>>.broadcast();
  final _deployCtrl = StreamController<Map<String, dynamic>>.broadcast();
  final _tasksCtrl = StreamController<List>.broadcast();

  Timer? _timer;
  bool _running = false;
  Duration interval = const Duration(seconds: 8);

  Stream<Map<String, dynamic>> get systemHealthStream => _systemCtrl.stream;
  Stream<Map<String, dynamic>> get multiAgentStream => _agentCtrl.stream;
  Stream<Map<String, dynamic>> get deploymentStream => _deployCtrl.stream;
  Stream<List> get tasksStream => _tasksCtrl.stream;

  void start() {
    if (_running) return;
    _running = true;
    _tick();
    _timer = Timer.periodic(interval, (_) => _tick());
  }

  void stop() {
    _running = false;
    _timer?.cancel();
    _timer = null;
  }

  Future<void> _tick() async {
    try {
      final h = await _api.systemHealth();
      if (!_systemCtrl.isClosed) _systemCtrl.add(h);
    } catch (_) {}
    try {
      final a = await _api.multiagentStatus();
      if (!_agentCtrl.isClosed) _agentCtrl.add(a);
    } catch (_) {}
    try {
      final d = await _api.deploymentStatus();
      if (!_deployCtrl.isClosed) _deployCtrl.add(d);
    } catch (_) {}
    try {
      final t = await _api.multiagentTasks();
      if (!_tasksCtrl.isClosed) _tasksCtrl.add((t['tasks'] as List?) ?? []);
    } catch (_) {}
  }

  void dispose() {
    stop();
    _systemCtrl.close();
    _agentCtrl.close();
    _deployCtrl.close();
    _tasksCtrl.close();
  }
}
