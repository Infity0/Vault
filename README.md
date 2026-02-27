# 🔐 Vault — Безопасное хранилище документов

Локальное зашифрованное хранилище личных документов с десктопным приложением и мобильным клиентом.  
Все данные шифруются **на устройстве** до записи в БД — сервер никогда не видит расшифрованного содержимого.

---

## ✨ Возможности

- 🗂 Хранение документов 12 категорий (паспорт, ИНН, СНИЛС, банковские карты, транспорт и др.)
- 🔒 Сквозное шифрование AES-256 — ключ расшифровки никогда не покидает устройство
- 👤 Мультиаккаунт — несколько пользователей на одной базе
- 📎 Вложения к записям (фото, PDF, документы) до 20 МБ
- ⭐ Избранное и фильтрация по категориям
- ⏰ Отслеживание истекающих документов (< 30 дней)
- 💾 Экспорт / импорт резервных копий
- 📱 Мобильный клиент на Flutter с QR-подключением
- 🔍 Полнотекстовый поиск по зашифрованным записям

---

## 🛠 Стек технологий

### Desktop
| Компонент | Технология |
|-----------|-----------|
| Язык | Python 3.11+ |
| UI фреймворк | CustomTkinter 5.2+ |
| Шифрование | `cryptography` — Fernet (AES-256-CBC) + PBKDF2-HMAC-SHA256 |
| База данных | MySQL 8.0+ (`mysql-connector-python`) |
| REST API сервер | FastAPI + Uvicorn |
| Аутентификация API | JWT (`python-jose`) |
| QR-коды | `qrcode[pil]` + Pillow |

### Mobile
| Компонент | Технология |
|-----------|-----------|
| Фреймворк | Flutter 3+ / Dart |
| HTTP клиент | `http` package |
| QR-сканер | `mobile_scanner` |
| Хранение токена | `flutter_secure_storage` |

---

## 📁 Структура проекта

```
vault-repo/
├── desktop/                        # Основное приложение
│   ├── main.py                     # Точка входа (CustomTkinter)
│   ├── server.py                   # FastAPI REST API для мобильного клиента
│   ├── requirements.txt
│   └── src/
│       ├── core/                   # Бизнес-логика (без UI)
│       │   ├── crypto.py           # CryptoManager — AES-256 + PBKDF2
│       │   ├── models.py           # Record, RecordData, CATEGORIES
│       │   ├── db_base.py          # Абстрактный интерфейс БД (ABC)
│       │   ├── db_mysql.py         # Реализация для MySQL + миграции
│       │   └── backup.py           # Экспорт / импорт резервных копий
│       ├── ui/
│       │   ├── app.py              # VaultApp — фасад над core
│       │   ├── login_frame.py      # Экран входа / создания аккаунта
│       │   ├── main_window.py      # Главное окно
│       │   └── components/
│       │       ├── sidebar.py      # Навигационная панель
│       │       ├── records_panel.py# Сетка карточек записей
│       │       ├── detail_panel.py # Панель детального просмотра + вложения
│       │       ├── record_dialog.py# Диалог создания / редактирования
│       │       ├── settings_dialog.py # Настройки подключения к БД
│       │       ├── date_picker.py  # Кастомный выбор даты
│       │       ├── qr_dialog.py    # QR-код для подключения телефона
│       │       └── message_dialog.py # Диалоги ошибок / подтверждений
│       └── utils/
│           └── constants.py        # Цвета, шрифты, размеры (тема)
│
└── mobile/                         # Flutter-приложение
    └── lib/
        ├── main.dart
        ├── api_service.dart        # HTTP-клиент к REST API
        ├── app_theme.dart          # Тема приложения
        ├── models.dart             # Модели данных
        ├── login_screen.dart       # Экран входа + QR-сканер
        ├── records_screen.dart     # Список записей
        ├── record_detail_screen.dart
        ├── record_form_screen.dart
        └── qr_scanner_screen.dart
```

---

## 🔐 Архитектура безопасности

```
Пользователь вводит пароль
         │
         ▼
  PBKDF2-HMAC-SHA256
  (600 000 итераций)
         │
         ▼
    AES-256 ключ  ──►  Fernet(ключ).encrypt(JSON данных)
                                │
                                ▼
                         MySQL: encrypted_data
                    (сервер видит только шифртекст)
```

- **Canary-паттерн**: при создании аккаунта шифруется строка-маркер. При входе — расшифровывается и сверяется. Хэш пароля нигде не хранится
- **Соль** (32 байта, `os.urandom`) уникальна для каждого аккаунта
- **Сессии API**: JWT-токен действует 24 часа, при выходе сессия уничтожается в памяти
- **Авто-блокировка**: настраиваемый тайм-аут бездействия (1–30 минут)

---

## 🚀 Быстрый старт

### Требования
- Python 3.11+
- MySQL 8.0+
- Flutter SDK 3.0+ (для мобильного клиента)

### 1. Настройка базы данных

```sql
-- Запустить setup_mysql.sql или выполнить вручную:
CREATE DATABASE vault_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'vault_user'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON vault_db.* TO 'vault_user'@'localhost';
```

Схема создаётся автоматически при первом запуске через встроенные миграции.

### 2. Десктопное приложение

```bash
cd desktop

# Создать виртуальное окружение
python -m venv .venv
.venv\Scripts\activate         # Windows
# source .venv/bin/activate    # Linux/macOS

# Установить зависимости
pip install -r requirements.txt

# Запустить
python main.py
```

При первом запуске откроется диалог настроек БД — введите данные подключения к MySQL.

### 3. API сервер (для мобильного клиента)

```bash
cd desktop
python server.py --host 0.0.0.0 --port 8080
```

Swagger UI: `http://localhost:8080/docs`

### 4. Мобильное приложение

```bash
cd mobile
flutter pub get
flutter run
```

На экране входа нажмите значок камеры и отсканируйте QR-код из десктопного приложения (кнопка 📱 в боковой панели).

---


## ⚙️ Конфигурация

Настройки хранятся в `~/.vault/db_config.json`:

```json
{
  "host": "localhost",
  "port": 3306,
  "user": "vault_user",
  "database": "vault_db",
  "lock_timeout": "5 минут"
}
```

Пароль БД хранится отдельно в `~/.vault/.db_pwd`.

---

## 🏗 Ключевые архитектурные решения

- **Repository pattern**: `BaseDatabase` (ABC) → `MySQLDatabase`. Легко добавить другой бэкенд
- **Façade**: `VaultApp` изолирует UI от деталей `core/`
- **Встроенные миграции**: схема БД версионируется и применяется автоматически при старте
- **Stateless API**: десктоп и мобильный клиент независимы, общаются только через REST
