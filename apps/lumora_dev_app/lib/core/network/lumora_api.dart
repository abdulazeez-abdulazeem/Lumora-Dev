import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../constants/app_constants.dart';
import 'api_client.dart';

final lumoraApiProvider = Provider<LumoraApi>((ref) => LumoraApi(ref.watch(apiClientProvider)));

class LumoraApi {
  LumoraApi(this._c);
  final ApiClient _c;
  Map<String, dynamic> _m(dynamic d) => Map<String, dynamic>.from(d as Map? ?? {});

  Future<Map<String, dynamic>> health() async => _m((await _c.get(ApiPaths.health)).data);
  Future<Map<String, dynamic>> systemHealth() async => _m((await _c.get('${ApiPaths.system}/health')).data);
  Future<Map<String, dynamic>> systemStatus() async => _m((await _c.get('${ApiPaths.system}/status')).data);
  Future<Map<String, dynamic>> systemMetrics() async => _m((await _c.get('${ApiPaths.system}/metrics')).data);
  Future<Map<String, dynamic>> systemDiagnostics() async => _m((await _c.get('${ApiPaths.system}/diagnostics')).data);
  Future<Map<String, dynamic>> chat(String message, {String? threadId}) async =>
      _m((await _c.post(ApiPaths.chat, data: {'message': message, if (threadId != null) 'thread_id': threadId})).data);
  Future<Map<String, dynamic>> knowledgeSearch(String q, {int topK = 8}) async =>
      _m((await _c.post('${ApiPaths.knowledge}/search', data: {'query': q, 'top_k': topK})).data);
  Future<Map<String, dynamic>> knowledgeStatus() async => _m((await _c.get('${ApiPaths.knowledge}/status')).data);
  Future<Map<String, dynamic>> knowledgeReindex() async => _m((await _c.post('${ApiPaths.knowledge}/reindex')).data);
  Future<Map<String, dynamic>> multiagentStart(String goal) async =>
      _m((await _c.post('${ApiPaths.multiagent}/start', data: {'goal': goal, 'auto_run': true})).data);
  Future<Map<String, dynamic>> multiagentStatus() async => _m((await _c.get('${ApiPaths.multiagent}/status')).data);
  Future<Map<String, dynamic>> multiagentAgents() async => _m((await _c.get('${ApiPaths.multiagent}/agents')).data);
  Future<Map<String, dynamic>> multiagentTasks() async => _m((await _c.get('${ApiPaths.multiagent}/tasks')).data);
  Future<Map<String, dynamic>> multiagentMessages() async => _m((await _c.get('${ApiPaths.multiagent}/messages')).data);
  Future<Map<String, dynamic>> deploymentPlatforms() async => _m((await _c.get('${ApiPaths.deployment}/platforms')).data);
  Future<Map<String, dynamic>> deploymentBuild() async => _m((await _c.post('${ApiPaths.deployment}/build', data: {'project_dir': '.'})).data);
  Future<Map<String, dynamic>> deploymentDeploy({String platform = 'static'}) async =>
      _m((await _c.post('${ApiPaths.deployment}/deploy', data: {'platform': platform, 'project_dir': '.', 'build_first': true})).data);
  Future<Map<String, dynamic>> deploymentHistory() async => _m((await _c.get('${ApiPaths.deployment}/history')).data);
  Future<Map<String, dynamic>> deploymentStatus() async => _m((await _c.get('${ApiPaths.deployment}/status')).data);
  Future<Map<String, dynamic>> browserStatus() async => _m((await _c.get('${ApiPaths.browser}/status')).data);
  Future<Map<String, dynamic>> browserLaunch() async => _m((await _c.post('${ApiPaths.browser}/launch', data: {'headless': true})).data);
  Future<Map<String, dynamic>> browserGoto(String url) async => _m((await _c.post('${ApiPaths.browser}/goto', data: {'url': url})).data);
  Future<Map<String, dynamic>> browserScreenshot() async => _m((await _c.post('${ApiPaths.browser}/screenshot', data: {'full_page': false})).data);
  Future<Map<String, dynamic>> browserClose() async => _m((await _c.post('${ApiPaths.browser}/close')).data);
  Future<Map<String, dynamic>> visionAnalyze(String screenshot) async =>
      _m((await _c.post('${ApiPaths.vision}/analyze', data: {'screenshot': screenshot})).data);
  Future<Map<String, dynamic>> visionStatus() async => _m((await _c.get('${ApiPaths.vision}/status')).data);
  Future<Map<String, dynamic>> filesList({String path = '.'}) async =>
      _m((await _c.get('${ApiPaths.files}/list', query: {'path': path})).data);
  Future<Map<String, dynamic>> filesRead(String path) async =>
      _m((await _c.get('${ApiPaths.files}/read', query: {'path': path})).data);
  Future<Map<String, dynamic>> filesWrite(String path, String content) async =>
      _m((await _c.post('${ApiPaths.files}/write', data: {'path': path, 'content': content})).data);
  Future<Map<String, dynamic>> memoryList() async {
    try { return _m((await _c.get('${ApiPaths.memory}/list')).data); } catch (_) { return {'notes': []}; }
  }
  Future<Map<String, dynamic>> memoryRemember(String note) async =>
      _m((await _c.post('${ApiPaths.memory}/remember', data: {'note': note, 'kind': 'note'})).data);
}
