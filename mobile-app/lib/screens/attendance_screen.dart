import 'package:flutter/material.dart';
import 'package:intl/intl.dart';

import '../core/api_client.dart';
import '../core/theme.dart';
import '../widgets/common.dart';

class AttendanceScreen extends StatefulWidget {
  const AttendanceScreen({super.key});
  @override
  State<AttendanceScreen> createState() => _AttendanceScreenState();
}

class _AttendanceScreenState extends State<AttendanceScreen> {
  bool _busy = false;
  int _reloadKey = 0;

  Future<void> _punch(String action) async {
    setState(() => _busy = true);
    String msg;
    try {
      final r = await ApiClient.I.dio.post('/attendance/$action/');
      final d = r.data;
      msg = (d is Map && d['message'] != null)
          ? d['message'].toString()
          : (r.statusCode == 200 || r.statusCode == 201
              ? 'Done'
              : 'Failed (${r.statusCode})');
    } catch (e) {
      msg = 'Could not reach server';
    }
    if (!mounted) return;
    setState(() {
      _busy = false;
      _reloadKey++; // refresh history
    });
    ScaffoldMessenger.of(context)
        .showSnackBar(SnackBar(content: Text(msg)));
  }

  String _fmtRow(Map m) {
    final d = m['attendance_date'] ?? m['date'] ?? '';
    return d.toString();
  }

  String _fmtTimes(Map m) {
    final ci = m['attendance_clock_in'] ?? m['clock_in'] ?? '';
    final co = m['attendance_clock_out'] ?? m['clock_out'] ?? '';
    return 'In: ${ci.toString().isEmpty ? '—' : ci}   Out: ${co.toString().isEmpty ? '—' : co}';
  }

  @override
  Widget build(BuildContext context) {
    final now = DateFormat('EEE, d MMM yyyy').format(DateTime.now());
    return Scaffold(
      appBar: AppBar(title: const Text('Attendance')),
      body: Column(
        children: [
          Container(
            margin: const EdgeInsets.all(16),
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: const Color(0xFFE2E8F0)),
            ),
            child: Column(
              children: [
                Text(now,
                    style: const TextStyle(
                        color: Color(0xFF64748B), fontSize: 13)),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: FilledButton.icon(
                        style: FilledButton.styleFrom(
                            backgroundColor: const Color(0xFF16A34A)),
                        onPressed: _busy ? null : () => _punch('clock-in'),
                        icon: const Icon(Icons.login),
                        label: const Text('Check In'),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: FilledButton.icon(
                        style: FilledButton.styleFrom(
                            backgroundColor: const Color(0xFFDC2626)),
                        onPressed: _busy ? null : () => _punch('clock-out'),
                        icon: const Icon(Icons.logout),
                        label: const Text('Check Out'),
                      ),
                    ),
                  ],
                ),
                if (_busy)
                  const Padding(
                    padding: EdgeInsets.only(top: 14),
                    child: LinearProgressIndicator(),
                  ),
              ],
            ),
          ),
          const Padding(
            padding: EdgeInsets.symmetric(horizontal: 16),
            child: Align(
                alignment: Alignment.centerLeft,
                child: SectionTitle('My attendance')),
          ),
          Expanded(
            child: AsyncListView<Map<String, dynamic>>(
              key: ValueKey(_reloadKey),
              emptyText: 'No attendance records yet.',
              loader: () => ApiClient.I.getList('/attendance/my-attendance/'),
              itemBuilder: (c, m) => Card(
                child: ListTile(
                  leading: const Icon(Icons.event_note_outlined,
                      color: AppTheme.brand),
                  title: Text(_fmtRow(m)),
                  subtitle: Text(_fmtTimes(m)),
                  trailing: m['attendance_overtime_approve'] == true
                      ? const StatusChip('OT')
                      : null,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
