import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../core/api_client.dart';
import '../core/auth_service.dart';

class ApplyLeaveScreen extends StatefulWidget {
  const ApplyLeaveScreen({super.key});
  @override
  State<ApplyLeaveScreen> createState() => _ApplyLeaveScreenState();
}

class _ApplyLeaveScreenState extends State<ApplyLeaveScreen> {
  final _fmt = DateFormat('yyyy-MM-dd');
  List<Map<String, dynamic>> _types = [];
  int? _typeId;
  DateTime? _start;
  DateTime? _end;
  final _desc = TextEditingController();
  bool _loading = true;
  bool _busy = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadTypes();
  }

  @override
  void dispose() {
    _desc.dispose();
    super.dispose();
  }

  Future<void> _loadTypes() async {
    try {
      final t = await ApiClient.I.getList('/leave/leave-type/');
      setState(() {
        _types = t;
        _loading = false;
      });
    } catch (_) {
      setState(() => _loading = false);
    }
  }

  Future<void> _pick(bool start) async {
    final d = await showDatePicker(
      context: context,
      initialDate: DateTime.now(),
      firstDate: DateTime.now().subtract(const Duration(days: 30)),
      lastDate: DateTime.now().add(const Duration(days: 365)),
    );
    if (d == null) return;
    setState(() {
      if (start) {
        _start = d;
        if (_end == null || _end!.isBefore(d)) _end = d;
      } else {
        _end = d;
      }
    });
  }

  Future<void> _submit() async {
    if (_typeId == null || _start == null || _end == null) {
      setState(() => _error = 'Pick a leave type and dates.');
      return;
    }
    setState(() {
      _busy = true;
      _error = null;
    });
    final auth = context.read<AuthService>();
    try {
      final r = await ApiClient.I.dio.post('/leave/user-request/', data: {
        'employee_id': auth.employeeId,
        'leave_type_id': _typeId,
        'start_date': _fmt.format(_start!),
        'end_date': _fmt.format(_end!),
        'start_date_breakdown': 'full_day',
        'end_date_breakdown': 'full_day',
        'description': _desc.text,
      });
      if (!mounted) return;
      if (r.statusCode != null && r.statusCode! < 300) {
        Navigator.pop(context);
        ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Leave request submitted.')));
      } else {
        setState(() {
          _busy = false;
          _error = _err(r.data) ?? 'Failed (${r.statusCode}).';
        });
      }
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _busy = false;
        _error = 'Could not submit: $e';
      });
    }
  }

  String? _err(dynamic d) {
    if (d is Map) {
      final parts = <String>[];
      d.forEach((k, v) => parts.add('$k: ${v is List ? v.join(', ') : v}'));
      return parts.isEmpty ? null : parts.join('\n');
    }
    return null;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Apply for Leave')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                const Text('Leave type',
                    style: TextStyle(fontWeight: FontWeight.w600)),
                const SizedBox(height: 6),
                DropdownButtonFormField<int>(
                  value: _typeId,
                  isExpanded: true,
                  hint: const Text('Select leave type'),
                  items: _types
                      .map((t) => DropdownMenuItem<int>(
                            value: t['id'] as int?,
                            child: Text(
                                (t['name'] ?? t['leave_type_name'] ?? 'Type')
                                    .toString()),
                          ))
                      .toList(),
                  onChanged: (v) => setState(() => _typeId = v),
                ),
                const SizedBox(height: 16),
                Row(
                  children: [
                    Expanded(
                        child: _DateField(
                            label: 'Start date',
                            value: _start == null ? null : _fmt.format(_start!),
                            onTap: () => _pick(true))),
                    const SizedBox(width: 12),
                    Expanded(
                        child: _DateField(
                            label: 'End date',
                            value: _end == null ? null : _fmt.format(_end!),
                            onTap: () => _pick(false))),
                  ],
                ),
                const SizedBox(height: 16),
                const Text('Reason',
                    style: TextStyle(fontWeight: FontWeight.w600)),
                const SizedBox(height: 6),
                TextField(
                  controller: _desc,
                  maxLines: 3,
                  decoration:
                      const InputDecoration(hintText: 'Reason for leave…'),
                ),
                if (_error != null) ...[
                  const SizedBox(height: 14),
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                        color: const Color(0xFFFEE2E2),
                        borderRadius: BorderRadius.circular(8)),
                    child: Text(_error!,
                        style: const TextStyle(
                            color: Color(0xFFB91C1C), fontSize: 13)),
                  ),
                ],
                const SizedBox(height: 20),
                FilledButton(
                  onPressed: _busy ? null : _submit,
                  child: _busy
                      ? const SizedBox(
                          height: 22,
                          width: 22,
                          child: CircularProgressIndicator(
                              strokeWidth: 2.5, color: Colors.white))
                      : const Text('Submit request'),
                ),
              ],
            ),
    );
  }
}

class _DateField extends StatelessWidget {
  final String label;
  final String? value;
  final VoidCallback onTap;
  const _DateField({required this.label, this.value, required this.onTap});
  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      child: InputDecorator(
        decoration: InputDecoration(labelText: label),
        child: Text(value ?? 'Select',
            style: TextStyle(
                color: value == null ? Colors.grey : Colors.black87)),
      ),
    );
  }
}
