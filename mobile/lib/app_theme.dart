import 'package:flutter/material.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

const _themeStorage = FlutterSecureStorage();
const _kThemeKey = 'app_theme_mode';

final themeNotifier = ValueNotifier<ThemeMode>(ThemeMode.dark);

Future<void> loadTheme() async {
  try {
    final saved = await _themeStorage.read(key: _kThemeKey);
    if (saved == 'light') themeNotifier.value = ThemeMode.light;
  } catch (_) {}
}

Future<void> toggleTheme() async {
  final next = themeNotifier.value == ThemeMode.dark ? ThemeMode.light : ThemeMode.dark;
  themeNotifier.value = next;
  try {
    await _themeStorage.write(
        key: _kThemeKey, value: next == ThemeMode.light ? 'light' : 'dark');
  } catch (_) {}
}

extension AppTheme on BuildContext {
  bool get isDark => Theme.of(this).brightness == Brightness.dark;
  Color get bgColor => isDark ? const Color(0xFF1a1a2e) : const Color(0xFFF0F2F5);
  Color get cardColor => isDark ? const Color(0xFF16213e) : Colors.white;
  Color get appBarColor => isDark ? const Color(0xFF16213e) : Colors.white;
  Color get textPrimary => isDark ? Colors.white : const Color(0xFF1a1a2e);
  Color get textSecondary => isDark ? Colors.white54 : Colors.black45;
  Color get textHint => isDark ? Colors.white38 : Colors.black26;
  Color get inputFill => isDark ? const Color(0xFF16213e) : const Color(0xFFEEF0F5);
  Color get emptyIconBg => isDark ? const Color(0xFF16213e) : const Color(0xFFE2E4ED);
  Color get emptyIconColor => isDark ? const Color(0xFF3a3660) : const Color(0xFFBBBDD0);
}
