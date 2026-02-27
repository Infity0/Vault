import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:http/http.dart' as http;
import 'models.dart';

class ApiException implements Exception {
  final String message;
  ApiException(this.message);
  @override
  String toString() => message;
}

class ApiService {
  static final ApiService _i = ApiService._();
  factory ApiService() => _i;
  ApiService._();

  static const _storage = FlutterSecureStorage();
  static const _tokenKey = 'vault_token';
  static const _baseUrlKey = 'vault_base_url';

  String _baseUrl = 'http://192.168.0.13:8001';
  String? _token;

  String get baseUrl => _baseUrl;

  Future<void> loadSettings() async {
    _token = await _storage.read(key: _tokenKey);
    final url = await _storage.read(key: _baseUrlKey);
    if (url != null && url.isNotEmpty) _baseUrl = url;
  }

  Future<void> saveBaseUrl(String url) async {
    _baseUrl = url;
    await _storage.write(key: _baseUrlKey, value: url);
  }

  bool get isLoggedIn => _token != null;

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        if (_token != null) 'Authorization': 'Bearer $_token',
      };

  Future<dynamic> _get(String path, {Map<String, String>? query}) async {
    final uri = Uri.parse('$_baseUrl$path')
        .replace(queryParameters: query);
    final res = await http.get(uri, headers: _headers)
        .timeout(const Duration(seconds: 10));
    return _handle(res);
  }

  Future<dynamic> _post(String path, Map<String, dynamic> body) async {
    final res = await http
        .post(Uri.parse('$_baseUrl$path'),
            headers: _headers, body: jsonEncode(body))
        .timeout(const Duration(seconds: 10));
    return _handle(res);
  }

  Future<dynamic> _put(String path, Map<String, dynamic> body) async {
    final res = await http
        .put(Uri.parse('$_baseUrl$path'),
            headers: _headers, body: jsonEncode(body))
        .timeout(const Duration(seconds: 10));
    return _handle(res);
  }

  Future<void> _delete(String path) async {
    final res = await http
        .delete(Uri.parse('$_baseUrl$path'), headers: _headers)
        .timeout(const Duration(seconds: 10));
    if (res.statusCode != 204 && res.statusCode >= 400) {
      _throwError(res);
    }
  }

  Future<dynamic> _patch(String path) async {
    final res = await http
        .patch(Uri.parse('$_baseUrl$path'), headers: _headers)
        .timeout(const Duration(seconds: 10));
    return _handle(res);
  }

  dynamic _handle(http.Response res) {
    if (res.statusCode >= 200 && res.statusCode < 300) {
      if (res.body.isEmpty) return null;
      return jsonDecode(utf8.decode(res.bodyBytes));
    }
    _throwError(res);
  }

  Never _throwError(http.Response res) {
    try {
      final body = jsonDecode(utf8.decode(res.bodyBytes));
      throw ApiException(body['detail'] ?? 'Ошибка ${res.statusCode}');
    } catch (e) {
      if (e is ApiException) rethrow;
      throw ApiException('Ошибка ${res.statusCode}');
    }
  }

  Future<void> register(String username, String password) async {
    await _post('/auth/register', {'username': username, 'password': password});
  }

  Future<void> login(String username, String password) async {
    final data =
        await _post('/auth/login', {'username': username, 'password': password});
    _token = data['access_token'];
    await _storage.write(key: _tokenKey, value: _token);
  }

  Future<void> logout() async {
    try {
      await _post('/auth/logout', {});
    } catch (_) {}
    _token = null;
    await _storage.delete(key: _tokenKey);
  }

  Future<List<CategoryInfo>> getCategories() async {
    final data = await _get('/categories');
    return (data as List).map((e) => CategoryInfo.fromJson(e)).toList();
  }

  Future<List<RecordItem>> getRecords(
      {String? category, bool favorites = false}) async {
    final q = <String, String>{};
    if (favorites) q['favorites'] = 'true';
    if (category != null && category != 'all') q['category'] = category;
    final data = await _get('/records', query: q);
    return (data as List).map((e) => RecordItem.fromJson(e)).toList();
  }

  Future<List<RecordItem>> search(String q) async {
    final data = await _get('/records/search', query: {'q': q});
    return (data as List).map((e) => RecordItem.fromJson(e)).toList();
  }

  Future<RecordDetail> getRecord(int id) async {
    final data = await _get('/records/$id');
    return RecordDetail.fromJson(data);
  }

  Future<RecordItem> createRecord(Map<String, dynamic> body) async {
    final data = await _post('/records', body);
    return RecordItem.fromJson(data);
  }

  Future<RecordItem> updateRecord(int id, Map<String, dynamic> body) async {
    final data = await _put('/records/$id', body);
    return RecordItem.fromJson(data);
  }

  Future<void> deleteRecord(int id) => _delete('/records/$id');

  Future<RecordItem> toggleFavorite(int id) async {
    final data = await _patch('/records/$id/favorite');
    return RecordItem.fromJson(data);
  }

  Future<List<AttachmentInfo>> getAttachments(int recordId) async {
    final data = await _get('/records/$recordId/attachments');
    return (data as List).map((e) => AttachmentInfo.fromJson(e)).toList();
  }

  Future<AttachmentInfo> uploadAttachment(
    int recordId,
    Uint8List bytes,
    String filename,
    String mimetype,
  ) async {
    final uri = Uri.parse('$_baseUrl/records/$recordId/attachments');
    final req = http.MultipartRequest('POST', uri);
    if (_token != null) {
      req.headers['Authorization'] = 'Bearer $_token';
    }
    req.files.add(http.MultipartFile.fromBytes(
      'file',
      bytes,
      filename: filename,
    ));
    final streamed = await req.send().timeout(const Duration(seconds: 30));
    final res = await http.Response.fromStream(streamed);
    if (res.statusCode >= 200 && res.statusCode < 300) {
      return AttachmentInfo.fromJson(jsonDecode(utf8.decode(res.bodyBytes)));
    }
    _throwError(res);
  }

  Future<Uint8List> downloadAttachment(int attachmentId) async {
    final uri = Uri.parse('$_baseUrl/attachments/$attachmentId/download');
    final res = await http.get(uri, headers: _headers)
        .timeout(const Duration(seconds: 30));
    if (res.statusCode >= 200 && res.statusCode < 300) {
      return res.bodyBytes;
    }
    _throwError(res);
  }

  Future<void> deleteAttachment(int attachmentId) =>
      _delete('/attachments/$attachmentId');
}
