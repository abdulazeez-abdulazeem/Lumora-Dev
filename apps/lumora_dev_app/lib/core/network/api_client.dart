import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pretty_dio_logger/pretty_dio_logger.dart';
import '../constants/app_constants.dart';
import '../storage/secure_storage_service.dart';

final apiClientProvider = Provider<ApiClient>((ref) => ApiClient(ref.watch(secureStorageProvider)));

class ApiClient {
  ApiClient(this._storage) {
    _dio = Dio(BaseOptions(
      baseUrl: AppConstants.backendDefaultUrl,
      connectTimeout: const Duration(seconds: 20),
      receiveTimeout: const Duration(seconds: 60),
      headers: {'Content-Type': 'application/json', 'Accept': 'application/json'},
    ));
    _dio.interceptors.add(InterceptorsWrapper(onRequest: (o, h) async {
      final token = await _storage.read(AppConstants.secureKeyApiToken);
      if (token != null && token.isNotEmpty) o.headers['X-Lumora-Token'] = token;
      final url = await _storage.read(AppConstants.secureKeyBackendUrl);
      if (url != null && url.isNotEmpty) o.baseUrl = url;
      h.next(o);
    }));
    _dio.interceptors.add(PrettyDioLogger(requestHeader: false, requestBody: false, responseBody: false, compact: true));
  }
  final SecureStorageService _storage;
  late final Dio _dio;
  Dio get dio => _dio;
  Future<void> setBaseUrl(String url) async {
    await _storage.write(AppConstants.secureKeyBackendUrl, url);
    _dio.options.baseUrl = url;
  }
  Future<Response<T>> get<T>(String path, {Map<String, dynamic>? query}) => _dio.get<T>(path, queryParameters: query);
  Future<Response<T>> post<T>(String path, {dynamic data}) => _dio.post<T>(path, data: data);
}
