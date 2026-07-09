import 'dart:async';

import 'package:flutter/material.dart';
import 'package:location/location.dart';
import 'package:provider/provider.dart';

import '../core/api_client.dart';
import '../core/auth_service.dart';
import 'attendance_screen.dart';
import 'dashboard_screen.dart';
import 'employees_screen.dart';
import 'more_screen.dart';

class HomeShell extends StatefulWidget {
  const HomeShell({super.key});
  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _i = 0;
  Timer? _geoTimer;
  final _pages = const [
    DashboardScreen(),
    EmployeesScreen(),
    AttendanceScreen(),
    MoreScreen(),
  ];

  @override
  void initState() {
    super.initState();
    // Pings every 5 min while this screen tree is alive (app open/foreground
    // or briefly backgrounded by the OS). The server no-ops if the employee
    // isn't currently clocked in, so it's safe to just always ping — no
    // client-side attendance-state tracking needed. Does NOT run if the app
    // is force-closed; that needs a native background service, not built here.
    _geoTimer = Timer.periodic(const Duration(minutes: 5), (_) => _pingLocation());
  }

  Future<void> _pingLocation() async {
    final auth = context.read<AuthService>();
    if (!auth.geoFencing) return;
    try {
      final loc = Location();
      if (!await loc.serviceEnabled()) return;
      final perm = await loc.hasPermission();
      if (perm != PermissionStatus.granted &&
          perm != PermissionStatus.grantedLimited) {
        return;
      }
      final d = await loc.getLocation();
      if (d.latitude == null || d.longitude == null) return;
      await ApiClient.I.dio.post('/attendance/location/', data: {
        'latitude': d.latitude,
        'longitude': d.longitude,
        'accuracy': d.accuracy ?? 0,
        'gpsEnabled': true,
      });
    } catch (_) {
      // Best-effort — a missed ping just means a slightly later exit alert.
    }
  }

  @override
  void dispose() {
    _geoTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: IndexedStack(index: _i, children: _pages),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _i,
        onDestinationSelected: (v) => setState(() => _i = v),
        destinations: const [
          NavigationDestination(
              icon: Icon(Icons.dashboard_outlined),
              selectedIcon: Icon(Icons.dashboard),
              label: 'Home'),
          NavigationDestination(
              icon: Icon(Icons.people_outline),
              selectedIcon: Icon(Icons.people),
              label: 'Directory'),
          NavigationDestination(
              icon: Icon(Icons.access_time_outlined),
              selectedIcon: Icon(Icons.access_time_filled),
              label: 'Attendance'),
          NavigationDestination(
              icon: Icon(Icons.grid_view_outlined),
              selectedIcon: Icon(Icons.grid_view),
              label: 'More'),
        ],
      ),
    );
  }
}
