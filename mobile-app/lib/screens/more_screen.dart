import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../core/auth_service.dart';
import '../core/theme.dart';
import 'api_list_screen.dart';

class _Module {
  final IconData icon;
  final String label;
  final String title;
  final String endpoint;
  final String? titleField;
  final String? subtitleField;
  final String? statusField;
  final bool adminOnly; // management modules — hidden from regular employees
  const _Module(this.icon, this.label, this.title, this.endpoint,
      {this.titleField,
      this.subtitleField,
      this.statusField,
      this.adminOnly = false});
}

class MoreScreen extends StatelessWidget {
  const MoreScreen({super.key});

  static const _modules = <_Module>[
    _Module(Icons.event_available_outlined, 'Leave', 'My Leave',
        '/leave/user-request/',
        titleField: 'leave_type_id', subtitleField: 'start_date', statusField: 'status'),
    _Module(Icons.beach_access_outlined, 'Leave Balance', 'Leave Balance',
        '/leave/available-leave/',
        titleField: 'leave_type_id', subtitleField: 'available_days'),
    _Module(Icons.receipt_long_outlined, 'Payslips', 'Payslips',
        '/payroll/payslip/',
        titleField: 'group_name', subtitleField: 'start_date', statusField: 'status'),
    _Module(Icons.payments_outlined, 'Loans', 'Loans',
        '/payroll/loan-account/',
        titleField: 'title', subtitleField: 'amount', statusField: 'status'),
    _Module(Icons.account_balance_wallet_outlined, 'Reimbursement',
        'Reimbursements', '/payroll/reimbusement/',
        titleField: 'title', subtitleField: 'amount', statusField: 'status'),
    _Module(Icons.flag_outlined, 'Objectives', 'Objectives',
        '/pms/objective/',
        titleField: 'title', subtitleField: 'description'),
    _Module(Icons.track_changes_outlined, 'Key Results', 'Key Results',
        '/pms/key-result/', titleField: 'title', subtitleField: 'progress_type'),
    _Module(Icons.work_outline, 'Recruitment', 'Recruitments',
        '/recruitment/recruitment/',
        titleField: 'title', statusField: 'closed', adminOnly: true),
    _Module(Icons.person_search_outlined, 'Candidates', 'Candidates',
        '/recruitment/candidate/',
        titleField: 'name',
        subtitleField: 'email',
        statusField: 'hired',
        adminOnly: true),
    _Module(Icons.support_agent_outlined, 'Helpdesk', 'Tickets',
        '/helpdesk/ticket/', titleField: 'title', statusField: 'status'),
    _Module(Icons.help_outline, 'FAQ', 'FAQs', '/helpdesk/faq/',
        titleField: 'question'),
    _Module(Icons.folder_outlined, 'Projects', 'Projects',
        '/project/project/', titleField: 'title', statusField: 'status'),
    _Module(Icons.checklist_outlined, 'Tasks', 'Tasks', '/project/task/',
        titleField: 'title', statusField: 'status'),
    _Module(Icons.login_outlined, 'Onboarding', 'Onboarding Tasks',
        '/onboarding/candidate-task/',
        titleField: 'onboarding_task_id', statusField: 'status', adminOnly: true),
    _Module(Icons.logout_outlined, 'Offboarding', 'Offboarding',
        '/offboarding/offboarding/',
        titleField: 'title', statusField: 'status', adminOnly: true),
    _Module(Icons.devices_other_outlined, 'Assets', 'Assets',
        '/asset/assets/', titleField: 'asset_name', statusField: 'asset_status'),
    _Module(Icons.notifications_outlined, 'Notifications', 'Notifications',
        '/notifications/notifications/list/all',
        titleField: 'verb', subtitleField: 'level'),
  ];

  @override
  Widget build(BuildContext context) {
    final auth = context.read<AuthService>();
    final modules = _modules
        .where((m) => !m.adminOnly || auth.isAdmin || auth.isManager)
        .toList();
    return Scaffold(
      appBar: AppBar(
        title: const Text('More'),
        actions: [
          IconButton(
            icon: const Icon(Icons.logout),
            tooltip: 'Logout',
            onPressed: () => auth.logout(),
          ),
        ],
      ),
      body: GridView.count(
        crossAxisCount: 3,
        padding: const EdgeInsets.all(16),
        mainAxisSpacing: 12,
        crossAxisSpacing: 12,
        childAspectRatio: 0.92,
        children: modules.map((mod) {
          return InkWell(
            onTap: () => Navigator.push(
              context,
              MaterialPageRoute(
                builder: (_) => ApiListScreen(
                  title: mod.title,
                  endpoint: mod.endpoint,
                  titleField: mod.titleField,
                  subtitleField: mod.subtitleField,
                  statusField: mod.statusField,
                ),
              ),
            ),
            borderRadius: BorderRadius.circular(14),
            child: Container(
              decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: const Color(0xFFE2E8F0)),
              ),
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(mod.icon, color: AppTheme.brand, size: 28),
                  const SizedBox(height: 8),
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 4),
                    child: Text(mod.label,
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
        }).toList(),
      ),
    );
  }
}
