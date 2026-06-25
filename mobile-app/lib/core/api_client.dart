import 'package:dio/dio.dart';

import '../config/app_config.dart';

/// Single Dio client for the whole app. Holds the JWT and attaches it to every
/// request. Provides small helpers to unwrap DRF list/detail responses.
class ApiClient {
  ApiClient._() {
    dio = Dio(BaseOptions(
      baseUrl: AppConfig.apiBase,
      connectTimeout: const Duration(seconds: 20),
      receiveTimeout: const Duration(seconds: 30),
      headers: {'Content-Type': 'application/json'},
      // don't throw on 4xx so callers can inspect status
      validateStatus: (s) => s != null && s < 500,
    ));
    dio.interceptors.add(InterceptorsWrapper(onRequest: (options, handler) {
      if (token != null && token!.isNotEmpty) {
        options.headers['Authorization'] = 'Bearer $token';
      }
      handler.next(options);
    }));
  }

  static final ApiClient I = ApiClient._();
  late final Dio dio;
  String? token;

  /// GET a (possibly paginated) list endpoint -> list of maps.
  Future<List<Map<String, dynamic>>> getList(String path,
      {Map<String, dynamic>? query}) async {
    final r = await dio.get(path, queryParameters: query);
    final d = r.data;
    final List items;
    if (d is List) {
      items = d;
    } else if (d is Map && d['results'] is List) {
      items = d['results'] as List;
    } else {
      items = const [];
    }
    return items.map((e) => Map<String, dynamic>.from(e as Map)).toList();
  }

  /// GET an object endpoint -> map.
  Future<Map<String, dynamic>> getMap(String path,
      {Map<String, dynamic>? query}) async {
    final r = await dio.get(path, queryParameters: query);
    return (r.data is Map) ? Map<String, dynamic>.from(r.data) : {};
  }
}
