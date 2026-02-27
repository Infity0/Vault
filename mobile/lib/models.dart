class RecordItem {
  final int id;
  final String title;
  final String category;
  final String icon;
  final String color;
  final bool isFavorite;
  final String? expiryDate;
  final String createdAt;
  final String updatedAt;

  RecordItem({
    required this.id,
    required this.title,
    required this.category,
    required this.icon,
    required this.color,
    required this.isFavorite,
    this.expiryDate,
    required this.createdAt,
    required this.updatedAt,
  });

  factory RecordItem.fromJson(Map<String, dynamic> j) => RecordItem(
        id: j['id'],
        title: j['title'],
        category: j['category'],
        icon: j['icon'],
        color: j['color'],
        isFavorite: j['is_favorite'] ?? false,
        expiryDate: j['expiry_date'],
        createdAt: j['created_at'] ?? '',
        updatedAt: j['updated_at'] ?? '',
      );
}

class RecordDetail extends RecordItem {
  final Map<String, String> fields;
  final String notes;
  final List<List<String>> customFields;

  RecordDetail({
    required super.id,
    required super.title,
    required super.category,
    required super.icon,
    required super.color,
    required super.isFavorite,
    super.expiryDate,
    required super.createdAt,
    required super.updatedAt,
    required this.fields,
    required this.notes,
    required this.customFields,
  });

  factory RecordDetail.fromJson(Map<String, dynamic> j) => RecordDetail(
        id: j['id'],
        title: j['title'],
        category: j['category'],
        icon: j['icon'],
        color: j['color'],
        isFavorite: j['is_favorite'] ?? false,
        expiryDate: j['expiry_date'],
        createdAt: j['created_at'] ?? '',
        updatedAt: j['updated_at'] ?? '',
        fields: Map<String, String>.from(j['fields'] ?? {}),
        notes: j['notes'] ?? '',
        customFields: (j['custom_fields'] as List? ?? [])
            .map((e) => List<String>.from(e))
            .toList(),
      );
}

class CategoryField {
  final String label;
  final String key;
  final bool secret;
  CategoryField({required this.label, required this.key, required this.secret});
  factory CategoryField.fromJson(Map<String, dynamic> j) => CategoryField(
        label: j['label'],
        key: j['key'],
        secret: j['secret'] ?? false,
      );
}

class CategoryInfo {
  final String key;
  final String label;
  final String icon;
  final String color;
  final bool hasExpiry;
  final List<CategoryField> fields;
  const CategoryInfo({
    required this.key,
    required this.label,
    required this.icon,
    required this.color,
    this.hasExpiry = true,
    required this.fields,
  });
  factory CategoryInfo.fromJson(Map<String, dynamic> j) => CategoryInfo(
        key: j['key'],
        label: j['label'],
        icon: j['icon'],
        color: j['color'],
        hasExpiry: j['has_expiry'] ?? true,
        fields: (j['fields'] as List)
            .map((f) => CategoryField.fromJson(f))
            .toList(),
      );
}

class AttachmentInfo {
  final int id;
  final int recordId;
  final String filename;
  final String mimetype;
  final int size;
  final String createdAt;

  AttachmentInfo({
    required this.id,
    required this.recordId,
    required this.filename,
    required this.mimetype,
    required this.size,
    required this.createdAt,
  });

  factory AttachmentInfo.fromJson(Map<String, dynamic> j) => AttachmentInfo(
        id: j['id'],
        recordId: j['record_id'],
        filename: j['filename'],
        mimetype: j['mimetype'],
        size: j['size'],
        createdAt: j['created_at'] ?? '',
      );
}
