import 'package:flutter/material.dart';
import 'api_service.dart';
import 'app_theme.dart';
import 'models.dart';
import 'login_screen.dart';
import 'record_detail_screen.dart';
import 'record_form_screen.dart';

class RecordsScreen extends StatefulWidget {
  const RecordsScreen({super.key});
  @override
  State<RecordsScreen> createState() => _RecordsScreenState();
}

class _RecordsScreenState extends State<RecordsScreen> {
  List<RecordItem> _records = [];
  List<CategoryInfo> _categories = [];
  String _selectedCategory = 'all';
  bool _loading = true;
  bool _searching = false;
  final _searchCtrl = TextEditingController();

  static const _allCategory = CategoryInfo(
    key: 'all', label: 'Все', icon: '🗂', color: '#6c63ff', fields: [],
  );
  static const _favCategory = CategoryInfo(
    key: 'favorites', label: 'Избранное', icon: '⭐', color: '#f7b731', fields: [],
  );
  static const _expiringCategory = CategoryInfo(
    key: 'expiring', label: 'Истекают', icon: '⏰', color: '#e84393', fields: [],
  );

  @override
  void initState() {
    super.initState();
    _loadAll();
  }

  Future<void> _loadAll() async {
    try {
      final cats = await ApiService().getCategories();
      if (!mounted) return;
      setState(() => _categories = [_allCategory, _favCategory, _expiringCategory, ...cats]);
      await _loadRecords();
    } catch (e) {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _loadRecords() async {
    if (!mounted) return;
    setState(() => _loading = true);
    try {
      final records = await ApiService().getRecords(
        category: _selectedCategory == 'all' ? null : _selectedCategory,
        favorites: _selectedCategory == 'favorites',
      );
      if (mounted) setState(() { _records = records; _loading = false; });
    } catch (e) {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _search(String q) async {
    if (q.isEmpty) { _loadRecords(); return; }
    if (!mounted) return;
    setState(() => _loading = true);
    try {
      final results = await ApiService().search(q);
      if (mounted) setState(() { _records = results; _loading = false; });
    } catch (e) {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _logout() async {
    await ApiService().logout();
    if (!mounted) return;
    Navigator.pushReplacement(
        context, MaterialPageRoute(builder: (_) => const LoginScreen()));
  }

  String _categoryLabel(String key) {
    try {
      return _categories.firstWhere((c) => c.key == key).label;
    } catch (_) {
      return key;
    }
  }

  Color _parseColor(String hex) {
    try { return Color(int.parse(hex.replaceFirst('#', '0xFF'))); }
    catch (_) { return const Color(0xFF6c63ff); }
  }

  List<Widget> _buildExpiryBadge(String expiryDate) {
    try {
      final exp = DateTime.parse(expiryDate);
      final today = DateTime.now();
      final delta = exp.difference(DateTime(today.year, today.month, today.day)).inDays;
      String label;
      Color color;
      if (delta < 0) {
        label = '⚠ Истёк ${-delta} дн. назад';
        color = const Color(0xFFe84393);
      } else if (delta == 0) {
        label = '⚠ Истекает сегодня';
        color = const Color(0xFFe84393);
      } else {
        label = '⏰ Через $delta дн.';
        color = const Color(0xFFf7b731);
      }
      return [
        const SizedBox(width: 8),
        Text(label, style: TextStyle(color: color, fontSize: 11, fontWeight: FontWeight.w500)),
      ];
    } catch (_) {
      return [const SizedBox(width: 8), Text('📅 $expiryDate', style: const TextStyle(color: Colors.orange, fontSize: 11))];
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: context.bgColor,
      appBar: AppBar(
        backgroundColor: context.appBarColor,
        title: _searching
            ? TextField(
                controller: _searchCtrl,
                autofocus: true,
                style: TextStyle(color: context.textPrimary),
                decoration: InputDecoration(
                  hintText: 'Поиск...',
                  hintStyle: TextStyle(color: context.textHint),
                  border: InputBorder.none,
                ),
                onChanged: _search,
              )
            : Text('Vault', style: TextStyle(color: context.textPrimary, fontWeight: FontWeight.bold)),
        iconTheme: IconThemeData(color: context.textPrimary),
        actions: [
          IconButton(
            icon: Icon(
              context.isDark ? Icons.light_mode_rounded : Icons.dark_mode_rounded,
              color: context.textPrimary,
            ),
            onPressed: toggleTheme,
          ),
          IconButton(
            icon: Icon(_searching ? Icons.close : Icons.search_rounded,
                color: context.textPrimary),
            onPressed: () {
              setState(() {
                _searching = !_searching;
                if (!_searching) { _searchCtrl.clear(); _loadRecords(); }
              });
            },
          ),
          IconButton(
            icon: Icon(Icons.logout_rounded, color: context.textPrimary),
            onPressed: _logout,
          ),
        ],
      ),
      body: Column(
        children: [
          SizedBox(
            height: 52,
            child: ListView.builder(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              itemCount: _categories.length,
              itemBuilder: (_, i) {
                final cat = _categories[i];
                final selected = cat.key == _selectedCategory;
                final color = _parseColor(cat.color);
                return GestureDetector(
                  onTap: () {
                    setState(() {
                      _selectedCategory = cat.key;
                      if (_searching) {
                        _searching = false;
                        _searchCtrl.clear();
                      }
                    });
                    _loadRecords();
                  },
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 200),
                    margin: const EdgeInsets.only(right: 8),
                    padding: const EdgeInsets.symmetric(horizontal: 14),
                    decoration: BoxDecoration(
                      color: selected ? color : context.cardColor,
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Row(
                      children: [
                        Text(cat.icon, style: const TextStyle(fontSize: 14)),
                        const SizedBox(width: 6),
                        Text(cat.label,
                            style: TextStyle(
                              color: selected
                                  ? Colors.white
                                  : context.textSecondary,
                              fontSize: 13,
                              fontWeight: selected
                                  ? FontWeight.w600
                                  : FontWeight.normal,
                            )),
                      ],
                    ),
                  ),
                );
              },
            ),
          ),

          Expanded(
            child: _loading
                ? const Center(child: CircularProgressIndicator())
                : RefreshIndicator(
                    onRefresh: _loadRecords,
                    color: const Color(0xFF6c63ff),
                    child: _records.isEmpty
                        ? ListView(
                            physics: const AlwaysScrollableScrollPhysics(),
                            children: [
                              SizedBox(
                                height: MediaQuery.of(context).size.height * 0.5,
                                child: Center(
                                  child: Column(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Container(
                                        width: 96, height: 96,
                                        decoration: BoxDecoration(
                                            color: context.emptyIconBg,
                                            shape: BoxShape.circle,
                                          ),
                                          child: Icon(Icons.lock_outline_rounded,
                                              size: 48, color: context.emptyIconColor),
                                      ),
                                      const SizedBox(height: 20),
                                      Text(
                                        _searching
                                            ? 'Ничего не найдено'
                                            : 'Здесь пусто',
                                        textAlign: TextAlign.center,
                                        style: const TextStyle(
                                          color: Colors.white38,
                                          fontSize: 16,
                                          fontWeight: FontWeight.w500,
                                        ),
                                      ),
                                      if (!_searching) ...[                                        
                                        const SizedBox(height: 8),
                                        const Text(
                                          'Нажмите + чтобы добавить запись',
                                          style: TextStyle(color: Colors.white24, fontSize: 13),
                                        ),
                                      ],
                                    ],
                                  ),
                                ),
                              ),
                            ],
                          )
                        : ListView.builder(
                            physics: const AlwaysScrollableScrollPhysics(),
                            padding: const EdgeInsets.all(12),
                            itemCount: _records.length,
                            itemBuilder: (_, i) {
                            final r = _records[i];
                            final color = _parseColor(r.color);
                            return Dismissible(
                              key: Key('record_${r.id}'),
                              direction: DismissDirection.endToStart,
                              background: Container(
                                margin: const EdgeInsets.only(bottom: 10),
                                decoration: BoxDecoration(
                                  color: Colors.red.shade700,
                                  borderRadius: BorderRadius.circular(16),
                                ),
                                alignment: Alignment.centerRight,
                                padding: const EdgeInsets.only(right: 24),
                                child: const Icon(Icons.delete_outline_rounded,
                                    color: Colors.white, size: 28),
                              ),
                              confirmDismiss: (_) async {
                                try {
                                  await ApiService().deleteRecord(r.id);
                                  return true;
                                } catch (_) {
                                  if (mounted) {
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      const SnackBar(
                                          content: Text('Ошибка удаления'),
                                          backgroundColor: Colors.red),
                                    );
                                  }
                                  return false;
                                }
                              },
                              onDismissed: (_) {
                                setState(() => _records.removeWhere((rec) => rec.id == r.id));
                                ScaffoldMessenger.of(context).showSnackBar(
                                  SnackBar(
                                    content: Text('«${r.title}» удалён'),
                                    duration: const Duration(seconds: 3),
                                  ),
                                );
                              },
                              child: Container(
                                margin: const EdgeInsets.only(bottom: 10),
                                decoration: BoxDecoration(
                                  color: context.cardColor,
                                  borderRadius: BorderRadius.circular(16),
                                ),
                                child: ClipRRect(
                                  borderRadius: BorderRadius.circular(16),
                                  child: IntrinsicHeight(
                                    child: Row(
                                      crossAxisAlignment: CrossAxisAlignment.stretch,
                                      children: [
                                        Container(width: 4, color: color),
                                        Expanded(
                                          child: ListTile(
                                            contentPadding: const EdgeInsets.symmetric(
                                                horizontal: 14, vertical: 6),
                                            leading: Hero(
                                              tag: 'record_icon_${r.id}',
                                              child: Container(
                                                width: 44,
                                                height: 44,
                                                decoration: BoxDecoration(
                                                  color: color.withValues(alpha: 0.2),
                                                  borderRadius: BorderRadius.circular(12),
                                                ),
                                                child: Center(
                                                    child: Text(r.icon,
                                                        style: const TextStyle(fontSize: 22))),
                                              ),
                                            ),
                                            title: Text(r.title,
                                                style: TextStyle(
                                                    color: context.textPrimary,
                                                    fontWeight: FontWeight.w500)),
                                            subtitle: Row(
                                              children: [
                                                Text(_categoryLabel(r.category),
                                                    style: TextStyle(
                                                        color: color, fontSize: 12)),
                                                if (r.expiryDate != null) ..._buildExpiryBadge(r.expiryDate!),
                                              ],
                                            ),
                                            trailing: r.isFavorite
                                                ? const Icon(Icons.star_rounded,
                                                    color: Colors.amber, size: 18)
                                                : null,
                                            onTap: () async {
                                              final result = await Navigator.push(
                                                context,
                                                MaterialPageRoute(
                                                  builder: (_) => RecordDetailScreen(
                                                      recordId: r.id,
                                                      categoryLabel: _categoryLabel(r.category),
                                                      categoryInfo: _categories.where((c) => c.key == r.category).isNotEmpty
                                                          ? _categories.firstWhere((c) => c.key == r.category)
                                                          : null),
                                                ),
                                              );
                                              if (result != null) _loadRecords();
                                            },
                                            onLongPress: () async {
                                              await ApiService().toggleFavorite(r.id);
                                              _loadRecords();
                                            },
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                ),
                              ),
                            );
                          },
                        ),
                    ),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        backgroundColor: const Color(0xFF6c63ff),
        foregroundColor: Colors.white,
        child: const Icon(Icons.add_rounded),
        onPressed: () async {
          final result = await Navigator.push(
            context,
            MaterialPageRoute(builder: (_) => const RecordFormScreen()),
          );
          if (result == 'saved') _loadRecords();
        },
      ),
    );
  }
}
