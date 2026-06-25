import 'package:cached_network_image/cached_network_image.dart';
import 'package:flutter/material.dart';

import '../config/app_config.dart';
import '../core/theme.dart';

/// Avatar from a (possibly relative) image url, with initials fallback.
class Avatar extends StatelessWidget {
  final String? url;
  final String name;
  final double size;
  const Avatar({super.key, this.url, required this.name, this.size = 44});

  @override
  Widget build(BuildContext context) {
    final full = AppConfig.mediaUrl(url);
    final initials = _initials(name);
    final fallback = CircleAvatar(
      radius: size / 2,
      backgroundColor: AppTheme.brand.withOpacity(0.12),
      child: Text(initials,
          style: TextStyle(
              color: AppTheme.brand,
              fontWeight: FontWeight.w700,
              fontSize: size * 0.34)),
    );
    if (full.isEmpty) return fallback;
    return ClipOval(
      child: CachedNetworkImage(
        imageUrl: full,
        width: size,
        height: size,
        fit: BoxFit.cover,
        placeholder: (_, __) => fallback,
        errorWidget: (_, __, ___) => fallback,
      ),
    );
  }

  static String _initials(String name) {
    final parts = name.trim().split(RegExp(r'\s+'));
    if (parts.isEmpty || parts.first.isEmpty) return '?';
    final a = parts.first[0];
    final b = parts.length > 1 ? parts.last[0] : '';
    return (a + b).toUpperCase();
  }
}

class StatusChip extends StatelessWidget {
  final String? status;
  const StatusChip(this.status, {super.key});
  @override
  Widget build(BuildContext context) {
    final c = AppTheme.statusColor(status);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
          color: c.withOpacity(0.12),
          borderRadius: BorderRadius.circular(20)),
      child: Text((status ?? '—'),
          style: TextStyle(
              color: c, fontWeight: FontWeight.w600, fontSize: 12)),
    );
  }
}

/// label/value row used in detail screens.
class InfoRow extends StatelessWidget {
  final String label;
  final String value;
  const InfoRow(this.label, this.value, {super.key});
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 7),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
              width: 130,
              child: Text(label,
                  style: const TextStyle(
                      color: Color(0xFF64748B), fontSize: 13))),
          Expanded(
              child: Text(value.isEmpty ? '—' : value,
                  style: const TextStyle(
                      fontSize: 14, fontWeight: FontWeight.w500))),
        ],
      ),
    );
  }
}

class SectionTitle extends StatelessWidget {
  final String text;
  const SectionTitle(this.text, {super.key});
  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.only(bottom: 8, top: 4),
        child: Text(text,
            style:
                const TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
      );
}

/// Reusable loading/error/empty + pull-to-refresh wrapper around a Future list.
class AsyncListView<T> extends StatefulWidget {
  final Future<List<T>> Function() loader;
  final Widget Function(BuildContext, T) itemBuilder;
  final String emptyText;
  final Widget? header;
  const AsyncListView({
    super.key,
    required this.loader,
    required this.itemBuilder,
    this.emptyText = 'Nothing here yet.',
    this.header,
  });

  @override
  State<AsyncListView<T>> createState() => _AsyncListViewState<T>();
}

class _AsyncListViewState<T> extends State<AsyncListView<T>> {
  late Future<List<T>> _future;

  @override
  void initState() {
    super.initState();
    _future = widget.loader();
  }

  Future<void> _refresh() async {
    setState(() => _future = widget.loader());
    await _future;
  }

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: _refresh,
      child: FutureBuilder<List<T>>(
        future: _future,
        builder: (context, snap) {
          if (snap.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snap.hasError) {
            return _Message(
                icon: Icons.error_outline,
                text: 'Could not load.\n${snap.error}',
                onRetry: _refresh);
          }
          final items = snap.data ?? [];
          if (items.isEmpty) {
            return _Message(
                icon: Icons.inbox_outlined,
                text: widget.emptyText,
                onRetry: _refresh);
          }
          return ListView.separated(
            padding: const EdgeInsets.all(16),
            itemCount: items.length + (widget.header != null ? 1 : 0),
            separatorBuilder: (_, __) => const SizedBox(height: 10),
            itemBuilder: (c, i) {
              if (widget.header != null && i == 0) return widget.header!;
              final idx = widget.header != null ? i - 1 : i;
              return widget.itemBuilder(c, items[idx]);
            },
          );
        },
      ),
    );
  }
}

class _Message extends StatelessWidget {
  final IconData icon;
  final String text;
  final Future<void> Function() onRetry;
  const _Message({required this.icon, required this.text, required this.onRetry});
  @override
  Widget build(BuildContext context) {
    return ListView(
      children: [
        const SizedBox(height: 120),
        Icon(icon, size: 56, color: Colors.grey),
        const SizedBox(height: 12),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 32),
          child: Text(text,
              textAlign: TextAlign.center,
              style: const TextStyle(color: Colors.grey)),
        ),
        const SizedBox(height: 16),
        Center(
          child: OutlinedButton.icon(
              onPressed: onRetry,
              icon: const Icon(Icons.refresh),
              label: const Text('Retry')),
        ),
      ],
    );
  }
}
