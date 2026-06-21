import 'package:flutter/material.dart';

import '../core/api_client.dart';
import '../widgets/common.dart';

/// Generic list screen for record-style modules (leave, payslips, assets,
/// tickets, objectives, ...). Pulls a DRF list endpoint and renders each row
/// using best-effort field extraction (handles scalars + nested FK maps).
class ApiListScreen extends StatelessWidget {
  final String title;
  final String endpoint;
  final String? titleField;
  final String? subtitleField;
  final String? statusField;

  const ApiListScreen({
    super.key,
    required this.title,
    required this.endpoint,
    this.titleField,
    this.subtitleField,
    this.statusField,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(title)),
      body: AsyncListView<Map<String, dynamic>>(
        emptyText: 'No $title yet.',
        loader: () => ApiClient.I.getList(endpoint),
        itemBuilder: (c, m) {
          final titleText = _display(m, titleField) ?? _firstText(m);
          final sub = _display(m, subtitleField);
          final status = _display(m, statusField);
          return Card(
            child: ListTile(
              title: Text(titleText,
                  maxLines: 1, overflow: TextOverflow.ellipsis),
              subtitle: sub == null ? null : Text(sub),
              trailing: status == null ? null : StatusChip(status),
              onTap: () => _showDetail(c, titleText, m),
            ),
          );
        },
      ),
    );
  }

  void _showDetail(BuildContext context, String t, Map<String, dynamic> m) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (_) => DraggableScrollableSheet(
        expand: false,
        initialChildSize: 0.6,
        maxChildSize: 0.9,
        builder: (c, ctrl) => ListView(
          controller: ctrl,
          padding: const EdgeInsets.all(20),
          children: [
            Text(t,
                style: const TextStyle(
                    fontSize: 18, fontWeight: FontWeight.w700)),
            const SizedBox(height: 12),
            ...m.entries
                .where((e) => e.value != null && e.value.toString().isNotEmpty)
                .map((e) => InfoRow(_label(e.key), _scalar(e.value))),
          ],
        ),
      ),
    );
  }

  static String? _display(Map<String, dynamic> m, String? field) {
    if (field == null) return null;
    final v = m[field];
    if (v == null) return null;
    final s = _scalar(v);
    return s.isEmpty ? null : s;
  }

  // first human-looking text field as a fallback title
  static String _firstText(Map<String, dynamic> m) {
    for (final k in ['name', 'title', 'full_name', 'subject']) {
      if (m[k] != null) return _scalar(m[k]);
    }
    return m['id']?.toString() ?? 'Item';
  }

  static String _scalar(dynamic v) {
    if (v is Map) {
      for (final k in ['name', 'title', 'full_name', 'objective', 'label']) {
        if (v[k] != null) return v[k].toString();
      }
      return v['id']?.toString() ?? '';
    }
    if (v is List) return v.length.toString();
    return v.toString();
  }

  static String _label(String key) => key
      .replaceAll('_id', '')
      .replaceAll('_', ' ')
      .trim()
      .replaceFirstMapped(RegExp(r'^\w'), (m) => m.group(0)!.toUpperCase());
}
