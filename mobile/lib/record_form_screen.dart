import 'package:flutter/material.dart';
import 'package:file_picker/file_picker.dart';
import 'api_service.dart';
import 'app_theme.dart';
import 'models.dart';

class RecordFormScreen extends StatefulWidget {
  final RecordDetail? record;
  const RecordFormScreen({super.key, this.record});

  @override
  State<RecordFormScreen> createState() => _RecordFormScreenState();
}

class _RecordFormScreenState extends State<RecordFormScreen> {
  final _titleCtrl = TextEditingController();
  final _notesCtrl = TextEditingController();
  List<CategoryInfo> _categories = [];
  String _selectedCategory = 'other';
  bool _isFavorite = false;
  String? _expiryDate;
  bool _loading = false;
  bool _saving = false;

  final Map<String, TextEditingController> _fieldControllers = {};
  final List<Map<String, TextEditingController>> _customFields = [];

  final List<PlatformFile> _pendingAttachments = [];

  @override
  void initState() {
    super.initState();
    _loadCategories();
  }

  Future<void> _loadCategories() async {
    setState(() => _loading = true);
    try {
      final cats = await ApiService().getCategories();
      if (!mounted) return;
      setState(() {
        _categories = cats;
        if (widget.record != null) {
          final r = widget.record!;
          _titleCtrl.text = r.title;
          _notesCtrl.text = r.notes;
          _selectedCategory = r.category;
          _isFavorite = r.isFavorite;
          _expiryDate = r.expiryDate;
          _buildFieldControllers(r.category, existing: r.fields);
          for (final cf in r.customFields) {
            _customFields.add({
              'name': TextEditingController(text: cf.isNotEmpty ? cf[0] : ''),
              'value': TextEditingController(text: cf.length > 1 ? cf[1] : ''),
            });
          }
        } else {
          _buildFieldControllers(_selectedCategory);
        }
        _loading = false;
      });
    } catch (e) {
      if (mounted) {
        setState(() => _loading = false);
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text('$e')));
      }
    }
  }

  void _buildFieldControllers(String category,
      {Map<String, String> existing = const {}}) {

    final oldControllers = Map<String, TextEditingController>.from(_fieldControllers);
    if (mounted) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        for (final c in oldControllers.values) {
          c.dispose();
        }
      });
    }
    _fieldControllers.clear();
    final cat = _categories.firstWhere((c) => c.key == category,
        orElse: () => CategoryInfo(
            key: 'other',
            label: 'Прочее',
            icon: '📋',
            color: '#8d99ae',
            fields: []));
    for (final f in cat.fields) {
      _fieldControllers[f.key] =
          TextEditingController(text: existing[f.key] ?? '');
    }
  }

  CategoryInfo? get _currentCategory {
    try {
      return _categories.firstWhere((c) => c.key == _selectedCategory);
    } catch (_) {
      return null;
    }
  }

  static String _mimeFromExtension(String? ext) {
    const map = {
      'jpg': 'image/jpeg', 'jpeg': 'image/jpeg', 'png': 'image/png',
      'gif': 'image/gif', 'webp': 'image/webp', 'bmp': 'image/bmp',
      'heic': 'image/heic', 'heif': 'image/heif',
      'pdf': 'application/pdf',
      'doc': 'application/msword',
      'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'xls': 'application/vnd.ms-excel',
      'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'txt': 'text/plain',
      'mp3': 'audio/mpeg', 'mp4': 'video/mp4',
      'zip': 'application/zip',
    };
    return map[ext?.toLowerCase()] ?? 'application/octet-stream';
  }

  Future<void> _pickFiles() async {
    final result = await FilePicker.platform.pickFiles(
      withData: true,
      allowMultiple: true,
      type: FileType.any,
    );
    if (result == null || result.files.isEmpty) return;
    setState(() {
      for (final f in result.files) {
        if (f.bytes != null) _pendingAttachments.add(f);
      }
    });
  }

  Future<void> _save() async {
    if (_titleCtrl.text.trim().isEmpty) {
      ScaffoldMessenger.of(context)
          .showSnackBar(const SnackBar(content: Text('Введите название')));
      return;
    }
    setState(() => _saving = true);
    try {
      final fields = <String, String>{};
      _fieldControllers.forEach((k, v) => fields[k] = v.text);

      final custom = _customFields
          .map((cf) => [cf['name']!.text, cf['value']!.text])
          .where((cf) => cf[0].isNotEmpty)
          .toList();

      final body = {
        'title': _titleCtrl.text.trim(),
        'category': _selectedCategory,
        'is_favorite': _isFavorite,
        'expiry_date': _expiryDate,
        'fields': fields,
        'notes': _notesCtrl.text,
        'custom_fields': custom,
      };

      int recordId;
      if (widget.record == null) {
        final created = await ApiService().createRecord(body);
        recordId = created.id;
      } else {
        await ApiService().updateRecord(widget.record!.id, body);
        recordId = widget.record!.id;
      }

      for (final f in _pendingAttachments) {
        if (f.bytes == null) continue;
        try {
          await ApiService().uploadAttachment(
            recordId,
            f.bytes!,
            f.name,
            _mimeFromExtension(f.extension),
          );
        } catch (e) {
          if (mounted) {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(content: Text('Не удалось загрузить «${f.name}»: $e')),
            );
          }
        }
      }

      if (mounted) Navigator.pop(context, 'saved');
    } catch (e) {
      if (mounted) {
        setState(() => _saving = false);
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text('$e')));
      }
    }
  }

  @override
  void dispose() {
    _titleCtrl.dispose();
    _notesCtrl.dispose();
    for (final c in _fieldControllers.values) {
      c.dispose();
    }
    for (final m in _customFields) {
      m['name']?.dispose();
      m['value']?.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: context.bgColor,
      appBar: AppBar(
        backgroundColor: context.appBarColor,
        title: Text(
          widget.record == null ? 'Новая запись' : 'Редактировать',
          style: TextStyle(color: context.textPrimary),
        ),
        iconTheme: IconThemeData(color: context.textPrimary),
        actions: [
          if (!_saving)
            TextButton(
              onPressed: _save,
              child: const Text('Сохранить',
                  style: TextStyle(
                      color: Color(0xFF6c63ff), fontWeight: FontWeight.w600)),
            )
          else
            const Padding(
              padding: EdgeInsets.all(16),
              child: SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(
                      strokeWidth: 2, color: Color(0xFF6c63ff))),
            ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                _buildInput(
                    controller: _titleCtrl, label: 'Название', icon: Icons.label_outline),
                const SizedBox(height: 16),

                Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
                  decoration: BoxDecoration(
                    color: context.cardColor,
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: DropdownButtonHideUnderline(
                    child: DropdownButton<String>(
                      value: _selectedCategory,
                      dropdownColor: context.cardColor,
                      style: TextStyle(color: context.textPrimary),
                      isExpanded: true,
                      items: _categories
                          .map((c) => DropdownMenuItem(
                                value: c.key,
                                child: Row(
                                  children: [
                                    Text(c.icon),
                                    const SizedBox(width: 8),
                                    Text(c.label,
                                        style: TextStyle(
                                            color: context.textPrimary)),
                                  ],
                                ),
                              ))
                          .toList(),
                      onChanged: (v) {
                        if (v == null) return;
                        setState(() {
                          _selectedCategory = v;
                          _buildFieldControllers(v);
                        });
                      },
                    ),
                  ),
                ),
                const SizedBox(height: 16),

                if (_currentCategory != null)
                  ..._currentCategory!.fields.map((f) => Padding(
                        padding: const EdgeInsets.only(bottom: 12),
                        child: f.key.contains('date')
                            ? _buildDatePicker(
                                controller: _fieldControllers[f.key]!,
                                label: f.label,
                              )
                            : f.key == 'card_type'
                                ? _buildCardTypeDropdown(
                                    controller: _fieldControllers[f.key]!,
                                  )
                                : _buildInput(
                                    controller: _fieldControllers[f.key]!,
                                    label: f.label,
                                    icon: f.secret
                                        ? Icons.key_outlined
                                        : Icons.edit_outlined,
                                    obscure: f.secret,
                                  ),
                      )),

                if (_currentCategory?.hasExpiry == true)
                GestureDetector(
                  onTap: () async {
                    final d = await showDatePicker(
                      context: context,
                      initialDate: DateTime.now(),
                      firstDate: DateTime(2000),
                      lastDate: DateTime(2050),
                      builder: (ctx, child) => Theme(
                        data: context.isDark ? ThemeData.dark() : ThemeData.light(),
                        child: child!,
                      ),
                    );
                    if (d != null) {
                      setState(() =>
                          _expiryDate = '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}');
                    }
                  },
                  child: Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: context.cardColor,
                      borderRadius: BorderRadius.circular(14),
                    ),
                    child: Row(
                      children: [
                        Icon(Icons.calendar_today_outlined,
                            color: context.textHint, size: 20),
                        const SizedBox(width: 12),
                        Text(
                          _expiryDate ?? 'Срок действия (необязательно)',
                          style: TextStyle(
                              color: _expiryDate != null
                                  ? context.textPrimary
                                  : context.textHint),
                        ),
                        if (_expiryDate != null) ...[
                          const Spacer(),
                          GestureDetector(
                            onTap: () =>
                                setState(() => _expiryDate = null),
                            child: Icon(Icons.close,
                                color: context.textHint, size: 18),
                          )
                        ]
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 16),

                Container(
                  decoration: BoxDecoration(
                    color: context.cardColor,
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: SwitchListTile(
                    title: Text('Избранное',
                        style: TextStyle(color: context.textPrimary)),
                    secondary: const Icon(Icons.star_rounded, color: Colors.amber),
                    value: _isFavorite,
                    activeThumbColor: const Color(0xFF6c63ff),
                    onChanged: (v) => setState(() => _isFavorite = v),
                  ),
                ),
                const SizedBox(height: 16),

                _buildInput(
                  controller: _notesCtrl,
                  label: 'Заметки',
                  icon: Icons.notes_rounded,
                  maxLines: 4,
                ),
                const SizedBox(height: 20),

                _buildAttachmentsSection(),
                const SizedBox(height: 20),

                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text('Дополнительные поля',
                        style: TextStyle(color: context.textSecondary, fontSize: 13)),
                    TextButton.icon(
                      onPressed: () => setState(() => _customFields.add({
                            'name': TextEditingController(),
                            'value': TextEditingController(),
                          })),
                      icon: const Icon(Icons.add, size: 16),
                      label: const Text('Добавить'),
                      style: TextButton.styleFrom(
                          foregroundColor: const Color(0xFF6c63ff)),
                    ),
                  ],
                ),
                ..._customFields.asMap().entries.map((e) => Padding(
                      padding: const EdgeInsets.only(bottom: 10),
                      child: Row(
                        children: [
                          Expanded(
                            child: _buildInput(
                                controller: e.value['name']!,
                                label: 'Название поля'),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: _buildInput(
                                controller: e.value['value']!,
                                label: 'Значение'),
                          ),
                          IconButton(
                            icon: const Icon(Icons.remove_circle_outline,
                                color: Colors.red),
                            onPressed: () => setState(
                                () => _customFields.removeAt(e.key)),
                          ),
                        ],
                      ),
                    )),
              ],
            ),
    );
  }

  Widget _buildAttachmentsSection() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              _pendingAttachments.isEmpty
                  ? 'Вложения'
                  : 'Вложения (${_pendingAttachments.length})',
              style: TextStyle(color: context.textSecondary, fontSize: 13),
            ),
            TextButton.icon(
              onPressed: _pickFiles,
              icon: const Icon(Icons.add_photo_alternate_outlined, size: 18),
              label: const Text('Добавить файл'),
              style: TextButton.styleFrom(
                  foregroundColor: const Color(0xFF6c63ff)),
            ),
          ],
        ),
        if (_pendingAttachments.isNotEmpty) ...
          _pendingAttachments.asMap().entries.map((e) {
            final f = e.value;
            final isImage = f.name.toLowerCase().endsWith('.jpg') ||
                f.name.toLowerCase().endsWith('.jpeg') ||
                f.name.toLowerCase().endsWith('.png') ||
                f.name.toLowerCase().endsWith('.gif') ||
                f.name.toLowerCase().endsWith('.webp');
            return Container(
              margin: const EdgeInsets.only(bottom: 8),
              decoration: BoxDecoration(
                color: context.cardColor,
                borderRadius: BorderRadius.circular(12),
              ),
              child: ListTile(
                contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                leading: isImage && f.bytes != null
                    ? ClipRRect(
                        borderRadius: BorderRadius.circular(6),
                        child: Image.memory(
                          f.bytes!,
                          width: 44,
                          height: 44,
                          fit: BoxFit.cover,
                        ),
                      )
                    : Container(
                        width: 44,
                        height: 44,
                        decoration: BoxDecoration(
                          color: const Color(0xFF6c63ff).withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: const Icon(Icons.attach_file_rounded,
                            color: Color(0xFF6c63ff), size: 22),
                      ),
                title: Text(
                  f.name,
                  style: TextStyle(color: context.textPrimary, fontSize: 13),
                  overflow: TextOverflow.ellipsis,
                ),
                subtitle: Text(
                  () {
                    final kb = f.size / 1024;
                    return kb < 1024
                        ? '${kb.toStringAsFixed(1)} КБ'
                        : '${(kb / 1024).toStringAsFixed(1)} МБ';
                  }(),
                  style: TextStyle(color: context.textHint, fontSize: 12),
                ),
                trailing: IconButton(
                  icon: const Icon(Icons.close_rounded, color: Colors.red, size: 20),
                  onPressed: () => setState(
                      () => _pendingAttachments.removeAt(e.key)),
                ),
              ),
            );
          }).toList(),
        if (_pendingAttachments.isEmpty)
          GestureDetector(
            onTap: _pickFiles,
            child: Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(vertical: 20),
              decoration: BoxDecoration(
                color: context.cardColor,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: const Color(0xFF6c63ff).withValues(alpha: 0.3),
                  width: 1.5,
                  strokeAlign: BorderSide.strokeAlignOutside,
                ),
              ),
              child: Column(
                children: [
                  Icon(Icons.add_photo_alternate_outlined,
                      size: 32, color: const Color(0xFF6c63ff).withValues(alpha: 0.6)),
                  const SizedBox(height: 8),
                  Text('Нажмите, чтобы прикрепить',
                      style: TextStyle(color: context.textHint, fontSize: 13)),
                  Text('фото, документы, файлы',
                      style: TextStyle(
                          color: context.textHint.withValues(alpha: 0.6), fontSize: 11)),
                ],
              ),
            ),
          ),
      ],
    );
  }

  Widget _buildCardTypeDropdown({
    required TextEditingController controller,
  }) {
    const options = ['Visa', 'Mastercard', 'Мир', 'UnionPay', 'American Express', 'Другая'];
    return StatefulBuilder(
      builder: (ctx, setLocal) {
        final currentValue =
            options.contains(controller.text) ? controller.text : options[0];
        return Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
          decoration: BoxDecoration(
            color: context.cardColor,
            borderRadius: BorderRadius.circular(14),
          ),
          child: DropdownButtonHideUnderline(
            child: DropdownButton<String>(
              value: currentValue,
              dropdownColor: context.cardColor,
              style: TextStyle(color: context.textPrimary, fontSize: 16),
              isExpanded: true,
              icon: const Icon(Icons.keyboard_arrow_down_rounded,
                  color: Color(0xFF6c63ff)),
              items: options
                  .map((t) => DropdownMenuItem(
                        value: t,
                        child: Row(
                          children: [
                            Icon(Icons.credit_card_outlined,
                                color: context.textHint, size: 20),
                            const SizedBox(width: 12),
                            Text(t),
                          ],
                        ),
                      ))
                  .toList(),
              onChanged: (v) {
                if (v == null) return;
                setState(() => controller.text = v);
                setLocal(() {});
              },
            ),
          ),
        );
      },
    );
  }

  Widget _buildDatePicker({
    required TextEditingController controller,
    required String label,
  }) {
    return StatefulBuilder(
      builder: (ctx, setLocal) {
        final hasValue = controller.text.isNotEmpty;
        return GestureDetector(
          onTap: () async {
            DateTime initial = DateTime.now();
            if (controller.text.isNotEmpty) {
              try {
                initial = DateTime.parse(controller.text);
              } catch (_) {}
            }
            final d = await showDatePicker(
              context: context,
              initialDate: initial,
              firstDate: DateTime(1900),
              lastDate: DateTime(2100),
              builder: (ctx, child) =>
                  Theme(data: context.isDark ? ThemeData.dark() : ThemeData.light(), child: child!),
            );
            if (d != null) {
              final str =
                  '${d.year}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';
              setLocal(() => controller.text = str);
            }
          },
          child: Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: context.cardColor,
              borderRadius: BorderRadius.circular(14),
            ),
            child: Row(
              children: [
                Icon(Icons.calendar_today_outlined,
                    color: context.textHint, size: 20),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    hasValue ? controller.text : label,
                    style: TextStyle(
                        color: hasValue ? context.textPrimary : context.textHint),
                  ),
                ),
                if (hasValue)
                  GestureDetector(
                    onTap: () => setLocal(() => controller.text = ''),
                    child: Icon(Icons.close,
                        color: context.textHint, size: 18),
                  ),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildInput({
    required TextEditingController controller,
    required String label,
    IconData? icon,
    bool obscure = false,
    int maxLines = 1,
  }) {
    return TextFormField(
      controller: controller,
      obscureText: obscure,
      maxLines: maxLines,
      style: TextStyle(color: context.textPrimary),
      decoration: InputDecoration(
        labelText: label,
        labelStyle: TextStyle(color: context.textSecondary),
        prefixIcon:
            icon != null ? Icon(icon, color: context.textHint) : null,
        filled: true,
        fillColor: context.inputFill,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide.none,
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide:
              const BorderSide(color: Color(0xFF6c63ff), width: 1.5),
        ),
      ),
    );
  }
}
