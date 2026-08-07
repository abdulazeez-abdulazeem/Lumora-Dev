import 'package:connectivity_plus/connectivity_plus.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

final connectivityProvider = StreamProvider<bool>((ref) {
  return Connectivity().onConnectivityChanged.map((r) => r.isNotEmpty && !r.every((x) => x == ConnectivityResult.none));
});
final isOnlineProvider = Provider<bool>((ref) => ref.watch(connectivityProvider).maybeWhen(data: (v) => v, orElse: () => true));
