import 'package:flutter/material.dart';

/// App-wide Material 3 theme — brand blue, clean spacing, consistent cards.
class AppTheme {
  static const Color brand = Color(0xFF2563EB);
  static const Color bg = Color(0xFFF4F6FB);

  static ThemeData get light {
    final scheme = ColorScheme.fromSeed(
      seedColor: brand,
      primary: brand,
    );
    return ThemeData(
      useMaterial3: true,
      colorScheme: scheme,
      scaffoldBackgroundColor: bg,
      appBarTheme: const AppBarTheme(
        backgroundColor: Colors.white,
        foregroundColor: Color(0xFF0F172A),
        elevation: 0,
        scrolledUnderElevation: 0.5,
        centerTitle: false,
        titleTextStyle: TextStyle(
          color: Color(0xFF0F172A),
          fontSize: 18,
          fontWeight: FontWeight.w700,
        ),
      ),
      cardTheme: CardTheme(
        color: Colors.white,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(14),
          side: const BorderSide(color: Color(0xFFE2E8F0)),
        ),
        margin: EdgeInsets.zero,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: Colors.white,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: Color(0xFFE2E8F0)),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(10),
          borderSide: const BorderSide(color: Color(0xFFE2E8F0)),
        ),
        contentPadding:
            const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: brand,
          minimumSize: const Size.fromHeight(50),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(10),
          ),
          textStyle:
              const TextStyle(fontSize: 15, fontWeight: FontWeight.w600),
        ),
      ),
      chipTheme: const ChipThemeData(
        side: BorderSide(color: Color(0xFFE2E8F0)),
      ),
    );
  }

  // status colors
  static Color statusColor(String? s) {
    switch ((s ?? '').toLowerCase()) {
      case 'approved':
      case 'active':
      case 'present':
      case 'completed':
        return const Color(0xFF16A34A);
      case 'rejected':
      case 'cancelled':
      case 'absent':
        return const Color(0xFFDC2626);
      case 'requested':
      case 'pending':
      case 'review':
        return const Color(0xFFD97706);
      default:
        return const Color(0xFF64748B);
    }
  }
}
