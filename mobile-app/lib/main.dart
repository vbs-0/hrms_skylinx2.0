import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'config/app_config.dart';
import 'core/auth_service.dart';
import 'core/theme.dart';
import 'screens/home_shell.dart';
import 'screens/login_screen.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(
    ChangeNotifierProvider(
      create: (_) => AuthService()..loadFromStorage(),
      child: const HrmsApp(),
    ),
  );
}

class HrmsApp extends StatelessWidget {
  const HrmsApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: AppConfig.appName,
      debugShowCheckedModeBanner: false,
      theme: AppTheme.light,
      home: Consumer<AuthService>(
        builder: (context, auth, _) {
          if (!auth.loaded) {
            return const Scaffold(
                body: Center(child: CircularProgressIndicator()));
          }
          return auth.isAuthenticated
              ? const HomeShell()
              : const LoginScreen();
        },
      ),
    );
  }
}
