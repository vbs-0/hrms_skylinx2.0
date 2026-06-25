import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'api_client.dart';

/// Holds auth state (JWT + current employee) and persists it.
class AuthService extends ChangeNotifier {
  String? token;
  int? employeeId;
  String? employeeName;
  String? employeeProfile;
  int? companyId;
  bool faceDetection = false;
  bool geoFencing = false;
  bool isAdmin = false;
  bool isManager = false;
  bool loaded = false;

  bool get isAuthenticated => token != null && token!.isNotEmpty;

  Future<void> loadFromStorage() async {
    final p = await SharedPreferences.getInstance();
    token = p.getString('token');
    if (token != null && token!.isEmpty) token = null;
    employeeId = p.getInt('empId');
    employeeName = p.getString('empName');
    employeeProfile = p.getString('empProfile');
    companyId = p.getInt('companyId');
    faceDetection = p.getBool('faceDetection') ?? false;
    geoFencing = p.getBool('geoFencing') ?? false;
    isAdmin = p.getBool('isAdmin') ?? false;
    isManager = p.getBool('isManager') ?? false;
    ApiClient.I.token = token;
    loaded = true;
    notifyListeners();
  }

  /// Returns null on success, or an error message.
  Future<String?> login(String username, String password) async {
    try {
      final r = await ApiClient.I.dio.post('/auth/login/',
          data: {'username': username, 'password': password});
      if (r.statusCode != 200 || r.data is! Map || r.data['access'] == null) {
        return _extractError(r.data) ?? 'Invalid username or password.';
      }
      final d = Map<String, dynamic>.from(r.data as Map);
      token = d['access'] as String?;
      final emp = d['employee'] is Map ? d['employee'] as Map : null;
      employeeId = emp?['id'] as int?;
      employeeName = emp?['full_name'] as String?;
      employeeProfile = emp?['employee_profile'] as String?;
      companyId = d['company_id'] as int?;
      faceDetection = d['face_detection'] == true;
      geoFencing = d['geo_fencing'] == true;
      isAdmin = d['is_admin'] == true;
      isManager = d['is_manager'] == true;
      ApiClient.I.token = token;

      final p = await SharedPreferences.getInstance();
      await p.setString('token', token ?? '');
      await p.setInt('empId', employeeId ?? 0);
      await p.setString('empName', employeeName ?? '');
      await p.setString('empProfile', employeeProfile ?? '');
      await p.setInt('companyId', companyId ?? 0);
      await p.setBool('faceDetection', faceDetection);
      await p.setBool('geoFencing', geoFencing);
      notifyListeners();
      return null;
    } on DioException catch (e) {
      return 'Could not reach server: ${e.message ?? 'network error'}';
    } catch (e) {
      return 'Login failed: $e';
    }
  }

  Future<void> logout() async {
    token = null;
    employeeId = null;
    employeeName = null;
    employeeProfile = null;
    companyId = null;
    ApiClient.I.token = null;
    final p = await SharedPreferences.getInstance();
    await p.clear();
    notifyListeners();
  }

  String? _extractError(dynamic data) {
    if (data is Map) {
      for (final k in ['detail', 'error', 'message', 'non_field_errors']) {
        if (data[k] != null) return data[k].toString();
      }
    }
    return null;
  }
}
