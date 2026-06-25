import 'package:flutter/material.dart';
import 'package:location/location.dart';
import 'package:image_picker/image_picker.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../core/api_client.dart';
import '../core/auth_service.dart';
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
  String? _hint;

  /// Returns {latitude, longitude} or throws with a user message.
  Future<Map<String, double>> _getLocation() async {
    final loc = Location();
    if (!await loc.serviceEnabled() && !await loc.requestService()) {
      throw 'Turn on location/GPS to clock in.';
    }
    var perm = await loc.hasPermission();
    if (perm == PermissionStatus.denied) {
      perm = await loc.requestPermission();
    }
    if (perm != PermissionStatus.granted &&
        perm != PermissionStatus.grantedLimited) {
      throw 'Location permission is required to clock in.';
    }
    final d = await loc.getLocation();
    if (d.latitude == null || d.longitude == null) {
      throw 'Could not read your location. Try again.';
    }
    return {'latitude': d.latitude!, 'longitude': d.longitude!};
  }

  /// Opens the camera for a selfie. Returns the file path, or null if cancelled.
  Future<String?> _captureFace() async {
    final x = await ImagePicker().pickImage(
      source: ImageSource.camera,
      preferredCameraDevice: CameraDevice.front,
      imageQuality: 60,
    );
    return x?.path;
  }

  Future<void> _punch(String action) async {
    final auth = context.read<AuthService>();
    setState(() {
      _busy = true;
      _hint = null;
    });
    final data = <String, dynamic>{};
    try {
      // face-detection gate (company setting) — capture a selfie first
      if (auth.faceDetection) {
        setState(() => _hint = 'Opening camera for face verification…');
        final face = await _captureFace();
        if (face == null) {
          setState(() {
            _busy = false;
            _hint = null;
          });
          return; // user cancelled
        }
      }
      // geo-fencing gate (company setting) — attach GPS coords
      if (auth.geoFencing) {
        setState(() => _hint = 'Getting your location…');
        data.addAll(await _getLocation());
      }
      setState(() => _hint = 'Submitting…');
      final r = await ApiClient.I.dio
          .post('/attendance/$action/', data: data.isEmpty ? null : data);
      final d = r.data;
      final msg = (d is Map && d['message'] != null)
          ? d['message'].toString()
          : (d is Map && d['error'] != null)
              ? d['error'].toString()
              : (r.statusCode == 200 ? 'Done' : 'Failed (${r.statusCode})');
      _toast(msg);
    } on String catch (e) {
      _toast(e); // our own validation messages
    } catch (_) {
      _toast('Could not reach server.');
    }
    if (!mounted) return;
    setState(() {
      _busy = false;
      _hint = null;
      _reloadKey++;
    });
  }

  void _toast(String m) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(m)));
  }

  String _fmtRow(Map m) =>
      (m['attendance_date'] ?? m['date'] ?? '').toString();

  String _fmtTimes(Map m) {
    final ci = m['attendance_clock_in'] ?? m['clock_in'] ?? '';
    final co = m['attendance_clock_out'] ?? m['clock_out'] ?? '';
    return 'In: ${ci.toString().isEmpty ? '—' : ci}   Out: ${co.toString().isEmpty ? '—' : co}';
  }

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthService>();
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
                if (auth.faceDetection || auth.geoFencing)
                  Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: Wrap(
                      spacing: 8,
                      children: [
                        if (auth.faceDetection)
                          const _Gate(Icons.camera_alt_outlined, 'Face'),
                        if (auth.geoFencing)
                          const _Gate(Icons.location_on_outlined, 'Location'),
                      ],
                    ),
                  ),
                const SizedBox(height: 14),
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
                  Padding(
                    padding: const EdgeInsets.only(top: 14),
                    child: Column(
                      children: [
                        const LinearProgressIndicator(),
                        if (_hint != null)
                          Padding(
                            padding: const EdgeInsets.only(top: 8),
                            child: Text(_hint!,
                                style: const TextStyle(
                                    fontSize: 12, color: Color(0xFF64748B))),
                          ),
                      ],
                    ),
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

class _Gate extends StatelessWidget {
  final IconData icon;
  final String label;
  const _Gate(this.icon, this.label);
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(
        color: AppTheme.brand.withOpacity(0.08),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 14, color: AppTheme.brand),
          const SizedBox(width: 4),
          Text(label,
              style: const TextStyle(
                  fontSize: 11,
                  color: AppTheme.brand,
                  fontWeight: FontWeight.w600)),
        ],
      ),
    );
  }
}
