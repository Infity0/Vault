import 'dart:io';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:file_picker/file_picker.dart';
import 'package:path_provider/path_provider.dart';
import 'api_service.dart';
import 'app_theme.dart';
import 'models.dart';
import 'record_form_screen.dart';

class RecordDetailScreen extends StatefulWidget {
  final int recordId;
  final String? categoryLabel;
  final CategoryInfo? categoryInfo;
  const RecordDetailScreen({
    super.key,
    required this.recordId,
    this.categoryLabel,
    this.categoryInfo,
  });

  @override
  State<RecordDetailScreen> createState() => _RecordDetailScreenState();
}

class _RecordDetailScreenState extends State<RecordDetailScreen> {
  RecordDetail? _record;
  bool _loading = true;
  List<AttachmentInfo> _attachments = [];
  bool _attachmentsLoading = false;

  @override
  void initState() {
    super.initState();
    _load();
    _loadAttachments();
  }

  Future<void> _load() async {
    try {
      final r = await ApiService().getRecord(widget.recordId);
      if (mounted) setState(() { _record = r; _loading = false; });
    } catch (e) {
      if (mounted) {
        setState(() => _loading = false);
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text('$e')));
      }
    }
  }

  Future<void> _loadAttachments() async {
    if (!mounted) return;
    setState(() => _attachmentsLoading = true);
    try {
      final list = await ApiService().getAttachments(widget.recordId);
      if (mounted) setState(() { _attachments = list; _attachmentsLoading = false; });
    } catch (_) {
      if (mounted) setState(() => _attachmentsLoading = false);
    }
  }

  Future<void> _delete() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        backgroundColor: context.cardColor,
        title: Text('Удалить запись?', style: TextStyle(color: context.textPrimary)),
        content: Text('Это действие нельзя отменить.',
            style: TextStyle(color: context.textSecondary)),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Отмена')),
          TextButton(
              onPressed: () => Navigator.pop(context, true),
              child: const Text('Удалить', style: TextStyle(color: Colors.red))),
        ],
      ),
    );
    if (ok != true) return;
    try {
      await ApiService().deleteRecord(widget.recordId);
      if (mounted) Navigator.pop(context, 'deleted');
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text('$e')));
      }
    }
  }

  Future<void> _toggleFavorite() async {
    try {
      await ApiService().toggleFavorite(widget.recordId);
      _load();
    } catch (_) {}
  }

  static String _mimeFromName(String name) {
    final ext = name.split('.').last.toLowerCase();
    const map = {
      'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png',
      'gif': 'image/gif', 'webp': 'image/webp', 'bmp': 'image/bmp',
      'heic': 'image/heic', 'heif': 'image/heif',
      'pdf': 'application/pdf',
      'mp4': 'video/mp4', 'mov': 'video/quicktime', 'avi': 'video/x-msvideo',
      'mp3': 'audio/mpeg', 'aac': 'audio/aac', 'm4a': 'audio/mp4',
      'doc': 'application/msword',
      'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'xls': 'application/vnd.ms-excel',
      'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'txt': 'text/plain',
      'zip': 'application/zip',
    };
    return map[ext] ?? 'application/octet-stream';
  }

  static bool _isImageMime(String mime, String filename) {
    if (mime.startsWith('image/')) return true;
    final ext = filename.split('.').last.toLowerCase();
    return {'jpg','jpeg','png','gif','webp','bmp','heic','heif'}.contains(ext);
  }

  Future<void> _uploadAttachment() async {
    final result = await FilePicker.platform.pickFiles(
      withData: true,
      allowMultiple: false,
    );
    if (result == null || result.files.isEmpty) return;
    final file = result.files.first;
    if (file.bytes == null) return;

    try {
      await ApiService().uploadAttachment(
        widget.recordId,
        file.bytes!,
        file.name,
        _mimeFromName(file.name),
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Файл прикреплён')),
        );
      }
      _loadAttachments();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text('Ошибка: $e')));
      }
    }
  }

  Future<void> _downloadAttachment(AttachmentInfo att) async {
    try {
      final bytes = await ApiService().downloadAttachment(att.id);

      if (!mounted) return;

      if (_isImageMime(att.mimetype, att.filename)) {
        _showImageViewer(bytes, att.filename);
        return;
      }

      final dir = await getTemporaryDirectory();
      final path = '${dir.path}/${att.filename}';
      final file = File(path);
      await file.writeAsBytes(bytes);

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Сохранено: $path'), duration: const Duration(seconds: 3)),
      );
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text('Ошибка: $e')));
      }
    }
  }

  void _showImageViewer(Uint8List bytes, String filename) {
    Navigator.push(
      context,
      MaterialPageRoute(
        fullscreenDialog: true,
        builder: (_) => Scaffold(
          backgroundColor: Colors.black,
          appBar: AppBar(
            backgroundColor: Colors.black,
            iconTheme: const IconThemeData(color: Colors.white),
            title: Text(
              filename,
              style: const TextStyle(color: Colors.white, fontSize: 14),
              overflow: TextOverflow.ellipsis,
            ),
          ),
          body: Center(
            child: InteractiveViewer(
              panEnabled: true,
              minScale: 0.5,
              maxScale: 5.0,
              child: Image.memory(bytes, fit: BoxFit.contain),
            ),
          ),
        ),
      ),
    );
  }

  Future<void> _deleteAttachment(AttachmentInfo att) async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        backgroundColor: context.cardColor,
        title: Text('Удалить файл?', style: TextStyle(color: context.textPrimary)),
        content: Text('«${att.filename}» будет удалён.',
            style: TextStyle(color: context.textSecondary)),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(context, false),
              child: const Text('Отмена')),
          TextButton(
              onPressed: () => Navigator.pop(context, true),
              child: const Text('Удалить', style: TextStyle(color: Colors.red))),
        ],
      ),
    );
    if (ok != true) return;
    try {
      await ApiService().deleteAttachment(att.id);
      _loadAttachments();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text('Ошибка: $e')));
      }
    }
  }

  void _showAttachmentsSheet(BuildContext context) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => StatefulBuilder(
        builder: (ctx, setSheet) {
          void reload() async {
            try {
              final list = await ApiService().getAttachments(widget.recordId);
              if (mounted) {
                setState(() => _attachments = list);
                try { setSheet(() {}); } catch (_) {}
              }
            } catch (_) {}
          }

          return DraggableScrollableSheet(
            initialChildSize: 0.55,
            minChildSize: 0.35,
            maxChildSize: 0.92,
            expand: false,
            builder: (_, scrollCtrl) => Container(
              decoration: BoxDecoration(
                color: context.cardColor,
                borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
              ),
              child: Column(
                children: [
                  Container(
                    margin: const EdgeInsets.only(top: 12, bottom: 4),
                    width: 40, height: 4,
                    decoration: BoxDecoration(
                      color: Colors.white24,
                      borderRadius: BorderRadius.circular(2),
                    ),
                  ),
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(
                          'ВЛОЖЕНИЯ',
                          style: TextStyle(
                            color: context.textSecondary,
                            fontSize: 13,
                            fontWeight: FontWeight.w700,
                            letterSpacing: 1.2,
                          ),
                        ),
                        ElevatedButton.icon(
                          onPressed: () async {
                            Navigator.pop(context);
                            await _uploadAttachment();
                            if (mounted) _showAttachmentsSheet(context);
                          },
                          icon: const Icon(Icons.add_rounded, size: 16),
                          label: const Text('Прикрепить файл'),
                          style: ElevatedButton.styleFrom(
                            backgroundColor: const Color(0xFF6c63ff),
                            foregroundColor: Colors.white,
                            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                            textStyle: const TextStyle(fontSize: 13),
                          ),
                        ),
                      ],
                    ),
                  ),
                  const Divider(height: 1, color: Colors.white10),
                  Expanded(
                    child: _attachmentsLoading
                        ? const Center(child: CircularProgressIndicator())
                        : _attachments.isEmpty
                            ? Center(
                                child: Column(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    const Icon(Icons.attach_file_rounded,
                                        size: 48, color: Colors.white24),
                                    const SizedBox(height: 12),
                                    Text('Нет вложений',
                                        style: TextStyle(
                                            color: context.textHint, fontSize: 14)),
                                    const SizedBox(height: 4),
                                    Text('Нажмите «Прикрепить файл»',
                                        style: TextStyle(
                                            color: context.textHint, fontSize: 12)),
                                  ],
                                ),
                              )
                            : ListView.builder(
                                controller: scrollCtrl,
                                padding: const EdgeInsets.all(12),
                                itemCount: _attachments.length,
                                itemBuilder: (_, i) {
                                  final att = _attachments[i];
                                  final sizeKb = att.size / 1024;
                                  final sizeStr = sizeKb < 1024
                                      ? '${sizeKb.toStringAsFixed(1)} КБ'
                                      : '${(sizeKb / 1024).toStringAsFixed(1)} МБ';
                                  final icon = _isImageMime(att.mimetype, att.filename)
                                      ? Icons.image_rounded
                                      : att.mimetype.contains('pdf')
                                          ? Icons.picture_as_pdf_rounded
                                          : att.mimetype.startsWith('audio/')
                                              ? Icons.audio_file_rounded
                                              : att.mimetype.startsWith('video/')
                                                  ? Icons.video_file_rounded
                                                  : Icons.attach_file_rounded;
                                  return Container(
                                    margin: const EdgeInsets.only(bottom: 8),
                                    decoration: BoxDecoration(
                                      color: context.bgColor,
                                      borderRadius: BorderRadius.circular(12),
                                    ),
                                    child: ListTile(
                                      onTap: () => _downloadAttachment(att),
                                      leading: Icon(icon, color: const Color(0xFF6c63ff)),
                                      title: Text(att.filename,
                                          style: TextStyle(
                                              color: context.textPrimary,
                                              fontSize: 14,
                                              fontWeight: FontWeight.w500),
                                          overflow: TextOverflow.ellipsis),
                                      subtitle: Text(sizeStr,
                                          style: TextStyle(
                                              color: context.textHint, fontSize: 12)),
                                      trailing: Row(
                                        mainAxisSize: MainAxisSize.min,
                                        children: [
                                          if (!_isImageMime(att.mimetype, att.filename))
                                          IconButton(
                                            icon: Icon(Icons.download_rounded,
                                                color: context.textSecondary, size: 20),
                                            onPressed: () => _downloadAttachment(att),
                                            tooltip: 'Скачать',
                                          ),
                                          if (_isImageMime(att.mimetype, att.filename))
                                          IconButton(
                                            icon: Icon(Icons.open_in_full_rounded,
                                                color: context.textSecondary, size: 20),
                                            onPressed: () => _downloadAttachment(att),
                                            tooltip: 'Открыть',
                                          ),
                                          IconButton(
                                            icon: const Icon(Icons.delete_outline_rounded,
                                                color: Colors.red, size: 20),
                                            onPressed: () async {
                                              await _deleteAttachment(att);
                                              reload();
                                            },
                                            tooltip: 'Удалить',
                                          ),
                                        ],
                                      ),
                                    ),
                                  );
                                },
                              ),
                  ),
                ],
              ),
            ),
          );
        },
      ),
    );
  }

  Color _parseColor(String hex) {
    try {
      return Color(int.parse(hex.replaceFirst('#', '0xFF')));
    } catch (_) {
      return const Color(0xFF6c63ff);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return Scaffold(
        backgroundColor: context.bgColor,
        body: const Center(child: CircularProgressIndicator()),
      );
    }
    if (_record == null) {
      return Scaffold(
        backgroundColor: context.bgColor,
        appBar: AppBar(backgroundColor: context.appBarColor),
        body: Center(
            child: Text('Запись не найдена', style: TextStyle(color: context.textPrimary))),
      );
    }

    final r = _record!;
    final color = _parseColor(r.color);

    return Scaffold(
      backgroundColor: context.bgColor,
      appBar: AppBar(
        backgroundColor: context.appBarColor,
        title: Text(r.title, style: TextStyle(color: context.textPrimary)),
        iconTheme: IconThemeData(color: context.textPrimary),
        actions: [
          IconButton(
            icon: Icon(
              r.isFavorite ? Icons.star_rounded : Icons.star_border_rounded,
              color: r.isFavorite ? Colors.amber : context.textSecondary,
            ),
            onPressed: _toggleFavorite,
          ),
          IconButton(
            icon: const Icon(Icons.attach_file_rounded, color: Colors.white),
            tooltip: 'Вложения',
            onPressed: () => _showAttachmentsSheet(context),
          ),
          IconButton(
            icon: const Icon(Icons.edit_rounded, color: Colors.white),
            onPressed: () async {
              final result = await Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (_) => RecordFormScreen(record: r),
                ),
              );
              if (result == 'saved') _load();
            },
          ),
          IconButton(
            icon: const Icon(Icons.delete_outline_rounded, color: Colors.red),
            onPressed: _delete,
          ),
        ],
      ),
      body: ListView(
        padding: EdgeInsets.fromLTRB(16, 16, 16, 16 + MediaQuery.of(context).padding.bottom),
        children: [
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: color.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: color.withValues(alpha: 0.3)),
            ),
            child: Row(
              children: [
                Hero(
                  tag: 'record_icon_${widget.recordId}',
                  child: Container(
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: color.withValues(alpha: 0.2),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text(r.icon, style: const TextStyle(fontSize: 28)),
                  ),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(r.title,
                          style: TextStyle(
                              color: context.textPrimary,
                              fontSize: 18,
                              fontWeight: FontWeight.bold)),
                      const SizedBox(height: 4),
                      Text(widget.categoryLabel ?? r.category,
                          style: TextStyle(color: color, fontSize: 13)),
                      if (r.expiryDate != null)
                        Padding(
                          padding: const EdgeInsets.only(top: 4),
                          child: Builder(builder: (_) {
                            try {
                              final exp = DateTime.parse(r.expiryDate!);
                              final today = DateTime.now();
                              final delta = exp.difference(DateTime(today.year, today.month, today.day)).inDays;
                              String label;
                              Color col;
                              if (delta < 0) {
                                label = '⚠ Истёк ${-delta} дн. назад';
                                col = const Color(0xFFe84393);
                              } else if (delta == 0) {
                                label = '⚠ Истекает сегодня';
                                col = const Color(0xFFe84393);
                              } else if (delta <= 30) {
                                label = '⏰ Истекает через $delta дн.';
                                col = const Color(0xFFf7b731);
                              } else {
                                label = '📅 Срок: ${r.expiryDate}';
                                col = Colors.white54;
                              }
                              return Text(label, style: TextStyle(color: col, fontSize: 12, fontWeight: FontWeight.w500));
                            } catch (_) {
                              return Text('📅 ${r.expiryDate}', style: const TextStyle(color: Colors.orange, fontSize: 12));
                            }
                          }),
                        ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),

          if (r.fields.isNotEmpty) ...[
            _sectionTitle('Поля'),
            ...r.fields.entries.map((e) {
              final fieldDef = widget.categoryInfo?.fields
                  .where((f) => f.key == e.key)
                  .isNotEmpty == true
                  ? widget.categoryInfo!.fields.firstWhere((f) => f.key == e.key)
                  : null;
              return _FieldTile(
                label: fieldDef?.label ?? e.key,
                value: e.value,
                isSecret: fieldDef?.secret ?? false,
              );
            }),
            const SizedBox(height: 16),
          ],

          if (r.customFields.isNotEmpty) ...[
            _sectionTitle('Дополнительные поля'),
            ...r.customFields.map((cf) => _FieldTile(
                  label: cf.isNotEmpty ? cf[0] : '',
                  value: cf.length > 1 ? cf[1] : '',
                )),
            const SizedBox(height: 16),
          ],

          if (r.notes.isNotEmpty) ...[
            _sectionTitle('Заметки'),
            Container(
              width: double.infinity,
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: context.cardColor,
                borderRadius: BorderRadius.circular(12),
              ),
              child: Text(r.notes,
                  style: TextStyle(color: context.textSecondary, height: 1.5)),
            ),
          ],
          const SizedBox(height: 16),
        ],
      ),
    );
  }

  Widget _sectionTitle(String title) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Text(title,
            style: TextStyle(
                color: context.textSecondary,
                fontSize: 12,
                fontWeight: FontWeight.w600,
                letterSpacing: 1)),
      );
}

class _FieldTile extends StatefulWidget {
  final String label;
  final String value;
  final bool isSecret;
  const _FieldTile({
    required this.label,
    required this.value,
    this.isSecret = false,
  });

  @override
  State<_FieldTile> createState() => _FieldTileState();
}

class _FieldTileState extends State<_FieldTile> {
  bool _copied = false;
  bool _revealed = false;

  @override
  Widget build(BuildContext context) {
    final displayValue =
        widget.isSecret && !_revealed ? '•' * 8 : widget.value;
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(
        color: context.cardColor,
        borderRadius: BorderRadius.circular(12),
      ),
      child: ListTile(
        title: Text(widget.label,
            style: TextStyle(color: context.textSecondary, fontSize: 12)),
        subtitle: Text(displayValue,
            style: TextStyle(
                color: context.textPrimary,
                fontSize: 15,
                fontWeight: FontWeight.w500,
                letterSpacing: widget.isSecret && !_revealed ? 2 : 0)),
        trailing: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (widget.isSecret)
              IconButton(
                icon: Icon(
                  _revealed ? Icons.visibility_off : Icons.visibility,
                  color: context.textHint,
                  size: 20,
                ),
                onPressed: () => setState(() => _revealed = !_revealed),
                tooltip: _revealed ? 'Скрыть' : 'Показать',
              ),
            IconButton(
              icon: Icon(
                _copied ? Icons.check_rounded : Icons.copy_rounded,
                color: _copied ? Colors.green : context.textHint,
                size: 20,
              ),
              onPressed: () async {
                await Clipboard.setData(ClipboardData(text: widget.value));
                setState(() => _copied = true);
                await Future.delayed(const Duration(seconds: 2));
                if (mounted) setState(() => _copied = false);
              },
              tooltip: 'Копировать',
            ),
          ],
        ),
      ),
    );
  }
}
