import 'package:flutter/material.dart';

import '../core/api_client.dart';
import '../widgets/common.dart';

class EmployeeDetailScreen extends StatefulWidget {
  final int employeeId;
  final String name;
  const EmployeeDetailScreen(
      {super.key, required this.employeeId, required this.name});

  @override
  State<EmployeeDetailScreen> createState() => _EmployeeDetailScreenState();
}

class _EmployeeDetailScreenState extends State<EmployeeDetailScreen> {
  late Future<Map<String, dynamic>> _future;

  @override
  void initState() {
    super.initState();
    _future = _load();
  }

  Future<Map<String, dynamic>> _load() async {
    // try detail endpoint; fall back to empty on failure
    try {
      return await ApiClient.I.getMap('/employee/employees/${widget.employeeId}/');
    } catch (_) {
      return {};
    }
  }

  String _s(dynamic v) {
    if (v == null) return '';
    if (v is Map) {
      for (final k in ['name', 'title', 'full_name']) {
        if (v[k] != null) return v[k].toString();
      }
      return '';
    }
    return v.toString();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.name.isEmpty ? 'Employee' : widget.name)),
      body: FutureBuilder<Map<String, dynamic>>(
        future: _future,
        builder: (context, snap) {
          if (snap.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          final m = snap.data ?? {};
          final name = _s(m['employee_first_name']).isNotEmpty
              ? '${_s(m['employee_first_name'])} ${_s(m['employee_last_name'])}'.trim()
              : widget.name;
          // curated fields shown first when present
          final curated = <String, String>{
            'Email': _s(m['email']),
            'Phone': _s(m['phone']),
            'Badge ID': _s(m['badge_id']),
            'Gender': _s(m['gender']),
            'Date of birth': _s(m['dob']),
            'Job position': _s(m['job_position_id'] ?? m['job_position_name']),
            'Department': _s(m['department_id'] ?? m['department_name']),
            'Work type': _s(m['work_type_id']),
            'Shift': _s(m['shift_id']),
            'Date joining': _s(m['date_joining']),
          }..removeWhere((k, v) => v.isEmpty);

          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Center(
                child: Column(
                  children: [
                    Avatar(
                        url: m['employee_profile'],
                        name: name.isEmpty ? widget.name : name,
                        size: 88),
                    const SizedBox(height: 12),
                    Text(name.isEmpty ? widget.name : name,
                        style: const TextStyle(
                            fontSize: 20, fontWeight: FontWeight.w700)),
                    if (_s(m['job_position_id'] ?? m['job_position_name'])
                        .isNotEmpty)
                      Padding(
                        padding: const EdgeInsets.only(top: 4),
                        child: Text(
                            _s(m['job_position_id'] ?? m['job_position_name']),
                            style: const TextStyle(color: Color(0xFF64748B))),
                      ),
                  ],
                ),
              ),
              const SizedBox(height: 20),
              if (curated.isEmpty)
                const Card(
                  child: Padding(
                    padding: EdgeInsets.all(16),
                    child: Text(
                        'Details are not available for this employee via the API.',
                        style: TextStyle(color: Color(0xFF64748B))),
                  ),
                )
              else
                Card(
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                    child: Column(
                      children: curated.entries
                          .map((e) => InfoRow(e.key, e.value))
                          .toList(),
                    ),
                  ),
                ),
            ],
          );
        },
      ),
    );
  }
}
