-- =============================================================================
-- Vault — Первоначальная настройка MySQL / MariaDB
-- =============================================================================
-- Запустите от имени суперпользователя:
--   mysql -u root -p < setup_mysql.sql
--
-- После запуска обязательно смените пароль 'CHANGE_ME':
--   ALTER USER 'vault_user'@'%' IDENTIFIED BY 'ваш_сильный_пароль';
-- =============================================================================

-- Создаём базу данных с полной поддержкой Unicode
CREATE DATABASE IF NOT EXISTS vault_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

-- Создаём пользователя (доступ с любого хоста; для продакшена замените % на IP)
CREATE USER IF NOT EXISTS 'vault_user'@'%'
    IDENTIFIED BY 'CHANGE_ME';

-- Минимально необходимые права (без SUPER, FILE, REPLICATION…)
GRANT SELECT, INSERT, UPDATE, DELETE, CREATE, INDEX, ALTER
    ON vault_db.*
    TO 'vault_user'@'%';

FLUSH PRIVILEGES;

-- =============================================================================
-- Структура таблиц (приложение создаёт их само через миграции,
-- но на случай ручной установки — дублируем здесь)
-- =============================================================================

USE vault_db;

CREATE TABLE IF NOT EXISTS schema_version (
    version INT NOT NULL PRIMARY KEY
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS settings (
    `key`   VARCHAR(128) NOT NULL PRIMARY KEY,
    `value` MEDIUMTEXT   NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Аккаунты пользователей (каждый со своим солёным ключом)
CREATE TABLE IF NOT EXISTS accounts (
    id       BIGINT       NOT NULL AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(128) NOT NULL UNIQUE,
    salt     TEXT         NOT NULL,   -- base64-encoded 16 bytes
    canary   TEXT         NOT NULL    -- AES-зашифрованная строка для проверки пароля
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS records (
    id             BIGINT       NOT NULL AUTO_INCREMENT PRIMARY KEY,
    account_id     BIGINT       NOT NULL DEFAULT 1,
    title          VARCHAR(512) NOT NULL,
    category       VARCHAR(64)  NOT NULL DEFAULT 'other',
    encrypted_data LONGTEXT     NOT NULL,
    is_favorite    TINYINT(1)   NOT NULL DEFAULT 0,
    expiry_date    DATE         NULL,
    created_at     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
                                ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_account   (account_id),
    INDEX idx_category  (category),
    INDEX idx_favorite  (is_favorite),
    INDEX idx_updated   (updated_at),
    CONSTRAINT fk_records_account FOREIGN KEY (account_id)
        REFERENCES accounts (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- Проверка
-- =============================================================================

SELECT 'Setup complete. Tables:' AS status;
SHOW TABLES;
