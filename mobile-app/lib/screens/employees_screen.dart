import 'package:flutter/material.dart';

import '../core/api_client.dart';
import '../widgets/common.dart';
import 'employee_detail_screen.dart';

class EmployeesScreen extends StatefulWidget {
  const EmployeesScreen({super.key});
  @override
  State<EmployeesScreen> createState() => _EmployeesScreenState();
}

class _EmployeesScreenState extends State<EmployeesScreen> {
  String _q = '';
  final _ctrl = TextEditingController();

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  String _name(Map m) =>
      '${m['employee_first_name'] ?? ''} ${m['employee_last_name'] ?? ''}'.trim();

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Directory')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
            child: TextField(
              controller: _ctrl,
              textInputAction: TextInputAction.search,
              onSubmitted: (v) => setState(() => _q = v.trim()),
              decoration: InputDecoration(
                hintText: 'Search employees…',
                prefixIcon: const Icon(Icons.search),
                suffixIcon: _q.isEmpty
                    ? null
                    : IconButton(
                        icon: const Icon(Icons.clear),
                        onPressed: () {
                          _ctrl.clear();
                          setState(() => _q = '');
                        }),
              ),
            ),
          ),
          Expanded(
            child: AsyncListView<Map<String, dynamic>>(
              key: ValueKey(_q),
              emptyText: 'No employees found.',
              loader: () => ApiClient.I.getList('/employee/list/employees/',
                  query: _q.isEmpty ? null : {'search': _q}),
              itemBuilder: (c, m) => Card(
                child: ListTile(
                  leading: Avatar(url: m['employee_profile'], name: _name(m)),
                  title: Text(_name(m).isEmpty ? '—' : _name(m),
                      maxLines: 1, overflow: TextOverflow.ellipsis),
                  subtitle: Text(
                    [m['job_position_name'], m['email']]
                        .where((e) => e != null && '$e'.isNotEmpty)
                        .join(' · '),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () => Navigator.push(
                    c,
                    MaterialPageRoute(
                      builder: (_) => EmployeeDetailScreen(
                          employeeId: m['id'] as int, name: _name(m)),
                    ),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
