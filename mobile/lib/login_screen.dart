import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:local_auth/local_auth.dart';
import 'api_service.dart';
import 'app_theme.dart';
import 'qr_scanner_screen.dart';
import 'records_screen.dart';

const _storage = FlutterSecureStorage();
const _kSavedUser = 'saved_username';
const _kSavedPass = 'saved_password';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});
  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _userCtrl = TextEditingController();
  final _passCtrl = TextEditingController();
  final _urlCtrl = TextEditingController();
  bool _obscure = true;
  bool _loading = false;
  bool _isRegister = false;
  bool _showUrl = false;
  bool _biometricAvailable = false;
  bool _hasSavedCreds = false;
  final _localAuth = LocalAuthentication();

  @override
  void initState() {
    super.initState();
    _urlCtrl.text = ApiService().baseUrl;
    _checkBiometric();
  }

  @override
  void dispose() {
    _userCtrl.dispose();
    _passCtrl.dispose();
    _urlCtrl.dispose();
    super.dispose();
  }

  Future<bool> _deviceSupportsBiometric() async {
    try {
      final canCheck = await _localAuth.canCheckBiometrics;
      if (canCheck) return true;
      return await _localAuth.isDeviceSupported();
    } catch (_) {
      return false;
    }
  }

  Future<void> _checkBiometric() async {
    try {
      final savedUser = await _storage.read(key: _kSavedUser);
      final savedPass = await _storage.read(key: _kSavedPass);
      if (savedUser == null || savedPass == null) return;

      final hasBio = await _deviceSupportsBiometric();
      if (!mounted) return;
      setState(() {
        _hasSavedCreds = true;
        _biometricAvailable = hasBio;
      });
      if (_biometricAvailable) {
        await Future.delayed(const Duration(milliseconds: 400));
        if (mounted) _tryBiometric();
      }
    } catch (_) {}
  }

  Future<void> _tryBiometric() async {
    if (_loading) return;
    setState(() => _loading = true);
    try {
      final ok = await _localAuth.authenticate(
        localizedReason: 'Разблокируйте Vault биометрией',
        options: const AuthenticationOptions(
          stickyAuth: true,
          biometricOnly: false,
        ),
      );
      if (!ok || !mounted) {
        setState(() => _loading = false);
        return;
      }
      final username = await _storage.read(key: _kSavedUser);
      final password = await _storage.read(key: _kSavedPass);
      if (username == null || password == null) {
        if (mounted) {
          setState(() => _loading = false);
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Нет сохранённых данных — войдите с паролем')),
          );
        }
        return;
      }
      await ApiService().login(username, password);
      if (!mounted) return;
      Navigator.pushReplacement(
          context, MaterialPageRoute(builder: (_) => const RecordsScreen()));
    } on PlatformException catch (e) {
      if (!mounted) return;
      setState(() => _loading = false);
      final msg = (e.message ?? '').toLowerCase();
      if (msg.contains('security credentials') || msg.contains('notavailable') || e.code == 'NotAvailable') {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Установите PIN-код в настройках телефона для биометрии'),
            duration: Duration(seconds: 5),
          ),
        );
      } else if (e.code == 'LockedOut' || e.code == 'PermanentlyLockedOut') {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Биометрия заблокирована — слишком много попыток')),
        );
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Ошибка биометрии: ${e.message}')),
        );
      }
    } on ApiException catch (e) {
      if (mounted) {
        setState(() => _loading = false);
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text('Ошибка входа: ${e.message}')));
      }
    } catch (e) {
      if (mounted) {
        setState(() => _loading = false);
      }
    }
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _loading = true);
    try {
      if (_showUrl) {
        await ApiService().saveBaseUrl(_urlCtrl.text.trim());
      }
      if (_isRegister) {
        await ApiService().register(_userCtrl.text.trim(), _passCtrl.text);
        if (!mounted) return;
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Аккаунт создан — войдите')),
        );
        setState(() => _isRegister = false);
      } else {
        await ApiService().login(_userCtrl.text.trim(), _passCtrl.text);
        await _storage.write(key: _kSavedUser, value: _userCtrl.text.trim());
        await _storage.write(key: _kSavedPass, value: _passCtrl.text);
        if (!mounted) return;

        final hasBio = await _deviceSupportsBiometric();
        if (hasBio && mounted) {
          setState(() {
            _hasSavedCreds = true;
            _biometricAvailable = true;
          });
          await Future.delayed(const Duration(milliseconds: 600));
          if (!mounted) return;
          try {
            await _localAuth.authenticate(
              localizedReason: 'Подтвердите отпечаток для быстрого входа',
              options: const AuthenticationOptions(
                stickyAuth: true,
                biometricOnly: false,
              ),
            );
          } on PlatformException catch (e) {
            final msg = (e.message ?? '').toLowerCase();
            if (msg.contains('security credentials') || e.code == 'NotAvailable') {
              if (mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('Установите PIN-код телефона: Настройки → Безопасность → Блокировка экрана'),
                    duration: Duration(seconds: 6),
                  ),
                );
              }
            }
          } catch (_) {}
        }

        if (!mounted) return;
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(builder: (_) => const RecordsScreen()),
        );
      }
    } on ApiException catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(e.message)));
    } catch (e) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Не удалось подключиться к серверу: $e')),
      );
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _scanQR() async {
    final result = await Navigator.push<String>(
      context,
      MaterialPageRoute(builder: (_) => const QRScannerScreen()),
    );
    if (result != null && mounted) {
      setState(() {
        _urlCtrl.text = result;
        _showUrl = true;
      });
      await ApiService().saveBaseUrl(result);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('URL обновлён: $result'),
          backgroundColor: const Color(0xFF6c63ff),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: context.bgColor,
      body: SafeArea(
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: Form(
              key: _formKey,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(Icons.lock_rounded, size: 72, color: const Color(0xFF6c63ff)),
                  const SizedBox(height: 16),
                  Text(
                    'Vault',
                    style: Theme.of(context)
                        .textTheme
                        .headlineMedium
                        ?.copyWith(color: context.textPrimary, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    _isRegister ? 'Создать аккаунт' : 'Войти в хранилище',
                    style: TextStyle(color: context.textSecondary),
                  ),
                  const SizedBox(height: 32),

                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      GestureDetector(
                        onTap: () => setState(() => _showUrl = !_showUrl),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(Icons.dns_rounded,
                                size: 16, color: context.textHint),
                            const SizedBox(width: 6),
                            Text(
                              _showUrl
                                  ? 'Скрыть адрес сервера'
                                  : 'Адрес сервера',
                              style: TextStyle(
                                  color: context.textHint, fontSize: 13),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(width: 12),
                      GestureDetector(
                        onTap: _scanQR,
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(Icons.qr_code_scanner_rounded,
                                size: 16, color: const Color(0xFF6c63ff)),
                            const SizedBox(width: 4),
                            Text(
                              'Скан',
                              style: TextStyle(
                                  color: const Color(0xFF6c63ff),
                                  fontSize: 13,
                                  fontWeight: FontWeight.w500),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                  if (_showUrl) ...[
                    const SizedBox(height: 12),
                    _Field(
                      controller: _urlCtrl,
                      label: 'http://192.168.x.x:8080',
                      icon: Icons.link,
                    ),
                  ],
                  const SizedBox(height: 20),

                  _Field(
                    controller: _userCtrl,
                    label: 'Имя пользователя',
                    icon: Icons.person_outline,
                    validator: (v) =>
                        v == null || v.isEmpty ? 'Введите имя' : null,
                  ),
                  const SizedBox(height: 16),
                  _Field(
                    controller: _passCtrl,
                    label: 'Пароль',
                    icon: Icons.key_outlined,
                    obscure: _obscure,
                    suffixIcon: IconButton(
                      icon: Icon(
                        _obscure ? Icons.visibility_off : Icons.visibility,
                        color: Colors.white38,
                      ),
                      onPressed: () => setState(() => _obscure = !_obscure),
                    ),
                    validator: (v) =>
                        v == null || v.isEmpty ? 'Введите пароль' : null,
                  ),
                  const SizedBox(height: 28),

                  SizedBox(
                    width: double.infinity,
                    height: 52,
                    child: ElevatedButton(
                      style: ElevatedButton.styleFrom(
                        backgroundColor: const Color(0xFF6c63ff),
                        foregroundColor: Colors.white,
                        shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(14)),
                      ),
                      onPressed: _loading ? null : _submit,
                      child: _loading
                          ? const SizedBox(
                              width: 22,
                              height: 22,
                              child: CircularProgressIndicator(
                                  strokeWidth: 2, color: Colors.white))
                          : Text(
                              _isRegister ? 'Создать аккаунт' : 'Войти',
                              style: const TextStyle(
                                  fontSize: 16, fontWeight: FontWeight.w600),
                            ),
                    ),
                  ),
                  const SizedBox(height: 16),
                  TextButton(
                    onPressed: () =>
                        setState(() => _isRegister = !_isRegister),
                    child: Text(
                      _isRegister
                          ? 'Уже есть аккаунт? Войти'
                          : 'Нет аккаунта? Создать',
                      style: const TextStyle(color: Color(0xFF6c63ff)),
                    ),
                  ),
                  if (_biometricAvailable && _hasSavedCreds && !_isRegister) ...
                    [
                      const SizedBox(height: 8),
                      OutlinedButton.icon(
                        style: OutlinedButton.styleFrom(
                          foregroundColor: const Color(0xFF6c63ff),
                          side: const BorderSide(color: Color(0xFF6c63ff), width: 1.2),
                          shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(14)),
                          minimumSize: const Size(double.infinity, 52),
                        ),
                        icon: const Icon(Icons.fingerprint_rounded, size: 26),
                        label: const Text('Войти по биометрии',
                            style: TextStyle(fontSize: 15, fontWeight: FontWeight.w500)),
                        onPressed: _loading ? null : _tryBiometric,
                      ),
                    ],
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _Field extends StatelessWidget {
  final TextEditingController controller;
  final String label;
  final IconData icon;
  final bool obscure;
  final Widget? suffixIcon;
  final String? Function(String?)? validator;

  const _Field({
    required this.controller,
    required this.label,
    required this.icon,
    this.obscure = false,
    this.suffixIcon,
    this.validator,
  });

  @override
  Widget build(BuildContext context) {
    return TextFormField(
      controller: controller,
      obscureText: obscure,
      style: TextStyle(color: context.textPrimary),
      validator: validator,
      decoration: InputDecoration(
        labelText: label,
        labelStyle: TextStyle(color: context.textSecondary),
        prefixIcon: Icon(icon, color: context.textHint),
        suffixIcon: suffixIcon,
        filled: true,
        fillColor: context.inputFill,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide.none,
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: const BorderSide(color: Color(0xFF6c63ff), width: 1.5),
        ),
      ),
    );
  }
}
