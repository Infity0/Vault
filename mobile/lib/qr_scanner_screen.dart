import 'package:flutter/material.dart';
import 'package:mobile_scanner/mobile_scanner.dart';
import 'app_theme.dart';

class QRScannerScreen extends StatefulWidget {
  const QRScannerScreen({super.key});

  @override
  State<QRScannerScreen> createState() => _QRScannerScreenState();
}

class _QRScannerScreenState extends State<QRScannerScreen> {
  bool _scanned = false;
  final _controller = MobileScannerController();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _onDetect(BarcodeCapture capture) {
    if (_scanned) return;
    for (final barcode in capture.barcodes) {
      final value = barcode.rawValue;
      if (value != null && value.startsWith('http')) {
        _scanned = true;
        Navigator.pop(context, value);
        return;
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.black,
      appBar: AppBar(
        backgroundColor: context.appBarColor,
        foregroundColor: context.textPrimary,
        title: Text('Сканировать QR-код',
            style: TextStyle(color: context.textPrimary)),
        iconTheme: IconThemeData(color: context.textPrimary),
      ),
      body: Stack(
        children: [
          MobileScanner(
            controller: _controller,
            onDetect: _onDetect,
          ),
          CustomPaint(
            size: MediaQuery.of(context).size,
            painter: _ScanOverlayPainter(),
          ),
          Positioned(
            bottom: 48,
            left: 0,
            right: 0,
            child: Text(
              'Наведи камеру на QR-код\nв десктопном приложении',
              textAlign: TextAlign.center,
              style: TextStyle(
                  color: Colors.white.withValues(alpha: 0.85), fontSize: 15),
            ),
          ),
        ],
      ),
    );
  }
}

class _ScanOverlayPainter extends CustomPainter {
  @override
  void paint(Canvas canvas, Size size) {
    const side = 220.0;
    final cx = size.width / 2;
    final cy = size.height / 2 - 40;
    final rect = Rect.fromCenter(
        center: Offset(cx, cy), width: side, height: side);

    final paint = Paint()..color = Colors.black.withValues(alpha: 0.55);
    final path = Path()
      ..addRect(Rect.fromLTWH(0, 0, size.width, size.height))
      ..addRRect(RRect.fromRectAndRadius(rect, const Radius.circular(16)))
      ..fillType = PathFillType.evenOdd;
    canvas.drawPath(path, paint);

    canvas.drawRRect(
      RRect.fromRectAndRadius(rect, const Radius.circular(16)),
      Paint()
        ..color = const Color(0xFF6c63ff)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2.5,
    );

    const corner = 24.0;
    const thick = 4.0;
    final cp = Paint()
      ..color = const Color(0xFF6c63ff)
      ..strokeWidth = thick
      ..strokeCap = StrokeCap.round
      ..style = PaintingStyle.stroke;
    final l = rect.left, r = rect.right, t = rect.top, b = rect.bottom;
    canvas.drawLine(Offset(l, t + corner), Offset(l, t), cp);
    canvas.drawLine(Offset(l, t), Offset(l + corner, t), cp);
    canvas.drawLine(Offset(r - corner, t), Offset(r, t), cp);
    canvas.drawLine(Offset(r, t), Offset(r, t + corner), cp);
    canvas.drawLine(Offset(l, b - corner), Offset(l, b), cp);
    canvas.drawLine(Offset(l, b), Offset(l + corner, b), cp);
    canvas.drawLine(Offset(r - corner, b), Offset(r, b), cp);
    canvas.drawLine(Offset(r, b), Offset(r, b - corner), cp);
  }

  @override
  bool shouldRepaint(covariant CustomPainter oldDelegate) => false;
}
