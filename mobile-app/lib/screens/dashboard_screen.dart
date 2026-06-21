import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/auth_service.dart';
import '../core/theme.dart';
import '../widgets/common.dart';
import 'api_list_screen.dart';
import 'apply_leave_screen.dart';
import 'attendance_screen.dart';
import 'employee_detail_screen.dart';

class DashboardScreen extends StatelessWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthService>();
    return Scaffold(
      appBar: AppBar(
        titleSpacing: 16,
        title: Row(
          children: [
            Avatar(url: auth.employeeProfile, name: auth.employeeName ?? '?', size: 38),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Text('Welcome back',
                      style: TextStyle(
                          fontSize: 12, color: Color(0xFF64748B), fontWeight: FontWeight.w400)),
                  Text(auth.employeeName ?? 'Employee',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
                ],
              ),
            ),
          ],
        ),
        actions: [
          IconButton(
            tooltip: 'Logout',
            icon: const Icon(Icons.logout),
            onPressed: () => context.read<AuthService>().logout(),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // hero card
          Container(
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                  colors: [Color(0xFF2563EB), Color(0xFF1D4ED8)]),
              borderRadius: BorderRadius.circular(16),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('Mark your attendance',
                    style: TextStyle(
                        color: Colors.white,
                        fontSize: 16,
                        fontWeight: FontWeight.w700)),
                const SizedBox(height: 4),
                const Text('Check in / out with location & photo',
                    style: TextStyle(color: Colors.white70, fontSize: 13)),
                const SizedBox(height: 14),
                FilledButton.icon(
                  style: FilledButton.styleFrom(
                      backgroundColor: Colors.white,
                      foregroundColor: AppTheme.brand,
                      minimumSize: const Size(160, 44)),
                  onPressed: () => Navigator.push(context,
                      MaterialPageRoute(builder: (_) => const AttendanceScreen())),
                  icon: const Icon(Icons.touch_app_outlined),
                  label: const Text('Go to Attendance'),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),
          const SectionTitle('Quick actions'),
          GridView.count(
            crossAxisCount: 3,
            shrinkWrap: true,
            physics: const NeverScrollableScrollPhysics(),
            mainAxisSpacing: 12,
            crossAxisSpacing: 12,
            childAspectRatio: 0.95,
            children: [
              _QuickTile(
                  icon: Icons.event_available_outlined,
                  label: 'My Leave',
                  onTap: () => Navigator.push(
                      context,
                      MaterialPageRoute(
                          builder: (_) => ApiListScreen(
                                title: 'My Leave',
                                endpoint: '/leave/user-request/',
                                titleField: 'leave_type_id',
                                subtitleField: 'start_date',
                                statusField: 'status',
                                actionLabel: 'Apply',
                                actionScreen: (_) => const ApplyLeaveScreen(),
                              )))),
              _QuickTile(
                  icon: Icons.receipt_long_outlined,
                  label: 'Payslips',
                  onTap: () => _open(context, 'Payslips', '/payroll/payslip/',
                      titleField: 'group_name', subtitleField: 'start_date', statusField: 'status')),
              _QuickTile(
                  icon: Icons.person_outline,
                  label: 'My Profile',
                  onTap: () {
                    if (auth.employeeId != null) {
                      Navigator.push(
                          context,
                          MaterialPageRoute(
                              builder: (_) => EmployeeDetailScreen(
                                  employeeId: auth.employeeId!,
                                  name: auth.employeeName ?? '')));
                    }
                  }),
              _QuickTile(
                  icon: Icons.flag_outlined,
                  label: 'Objectives',
                  onTap: () => _open(context, 'Objectives', '/pms/objective/',
                      titleField: 'objective', subtitleField: 'managers', statusField: 'status')),
              _QuickTile(
                  icon: Icons.payments_outlined,
                  label: 'Loans',
                  onTap: () => _open(context, 'Loans', '/payroll/loan-account/',
                      titleField: 'title', subtitleField: 'amount', statusField: 'status')),
              _QuickTile(
                  icon: Icons.support_agent_outlined,
                  label: 'Helpdesk',
                  onTap: () => _open(context, 'Tickets', '/helpdesk/ticket/',
                      titleField: 'title', subtitleField: 'status', statusField: 'status')),
            ],
          ),
        ],
      ),
    );
  }

  void _open(BuildContext context, String title, String endpoint,
      {String? titleField, String? subtitleField, String? statusField}) {
    Navigator.push(
        context,
        MaterialPageRoute(
            builder: (_) => ApiListScreen(
                  title: title,
                  endpoint: endpoint,
                  titleField: titleField,
                  subtitleField: subtitleField,
                  statusField: statusField,
                )));
  }
}

class _QuickTile extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback onTap;
  const _QuickTile(
      {required this.icon, required this.label, required this.onTap});
  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(14),
      child: Container(
        decoration: BoxDecoration(
            color: Colors.white,
            borderRadius: BorderRadius.circular(14),
            border: Border.all(color: const Color(0xFFE2E8F0))),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, color: AppTheme.brand, size: 28),
            const SizedBox(height: 8),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 4),
              child: Text(label,
                  textAlign: TextAlign.center,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(
                      fontSize: 12, fontWeight: FontWeight.w600)),
            ),
          ],
        ),
      ),
    );
  }
}
