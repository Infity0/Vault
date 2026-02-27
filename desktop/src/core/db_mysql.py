from __future__ import annotations
import json
import threading
import time
from dataclasses import dataclass, field
from typing import Optional, Any

from src.core.db_base import BaseDatabase
from src.core.models import Record


@dataclass
class MySQLConfig:
    host: str = "localhost"
    port: int = 3306
    user: str = "vault_user"
    password: str = ""
    database: str = "vault_db"
    pool_size: int = 3
    connect_timeout: int = 10
    ssl_ca: str = ""
    ssl_verify: bool = False


    def to_dict(self) -> dict:
        return {
            "host":            self.host,
            "port":            self.port,
            "user":            self.user,
            "database":        self.database,
            "pool_size":       self.pool_size,
            "connect_timeout": self.connect_timeout,
            "ssl_ca":          self.ssl_ca,
            "ssl_verify":      self.ssl_verify,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_json(cls, raw: str) -> "MySQLConfig":
        d = json.loads(raw)
        return cls(**{k: v for k, v in d.items()
                      if k in cls.__dataclass_fields__ and k != "password"})


    def safe_str(self) -> str:
        return f"{self.user}@{self.host}:{self.port}/{self.database}"


class MySQLDatabase(BaseDatabase):

    _MIGRATIONS: list[tuple[int, str]] = [
        (1, """
            CREATE TABLE IF NOT EXISTS settings (
                `key`   VARCHAR(128) NOT NULL PRIMARY KEY,
                `value` MEDIUMTEXT   NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """),
        (2, """
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
                INDEX idx_updated   (updated_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """),
        (3, """
            CREATE TABLE IF NOT EXISTS schema_version (
                version INT NOT NULL PRIMARY KEY
            ) ENGINE=InnoDB;
        """),
        (4, """
            CREATE TABLE IF NOT EXISTS accounts (
                id       BIGINT       NOT NULL AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(128) NOT NULL UNIQUE,
                salt     TEXT         NOT NULL,
                canary   TEXT         NOT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """),
        (5, """
            CREATE TABLE IF NOT EXISTS attachments (
                id         BIGINT       NOT NULL AUTO_INCREMENT PRIMARY KEY,
                record_id  BIGINT       NOT NULL,
                account_id BIGINT       NOT NULL,
                filename   VARCHAR(255) NOT NULL,
                mimetype   VARCHAR(128) NOT NULL DEFAULT 'application/octet-stream',
                size       INT          NOT NULL DEFAULT 0,
                data       LONGBLOB     NOT NULL,
                created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_att_record  (record_id),
                INDEX idx_att_account (account_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """),
    ]

    def __init__(self, config: MySQLConfig) -> None:
        self._cfg = config
        self._lock = threading.Lock()
        self._pool = None
        self._connect_pool()
        self._migrate()


    @property
    def backend_name(self) -> str:
        return f"MySQL  {self._cfg.safe_str()}"


    def _connect_pool(self) -> None:
        try:
            import mysql.connector
            from mysql.connector import pooling
        except ImportError as exc:
            raise ImportError(
                "Пакет mysql-connector-python не установлен.\n"
                "Выполните: pip install mysql-connector-python"
            ) from exc

        cfg: dict[str, Any] = dict(
            host=self._cfg.host,
            port=self._cfg.port,
            user=self._cfg.user,
            password=self._cfg.password,
            database=self._cfg.database,
            charset="utf8mb4",
            collation="utf8mb4_unicode_ci",
            autocommit=False,
            connection_timeout=self._cfg.connect_timeout,
            use_pure=True,
        )

        if self._cfg.ssl_ca:
            cfg["ssl_ca"] = self._cfg.ssl_ca
            cfg["ssl_verify_cert"] = self._cfg.ssl_verify

        pool_name = f"vault_{self._cfg.host}_{self._cfg.database}"
        self._pool = pooling.MySQLConnectionPool(
            pool_name=pool_name,
            pool_size=max(1, min(self._cfg.pool_size, 32)),
            pool_reset_session=True,
            **cfg,
        )

    def _get_conn(self):
        return self._pool.get_connection()


    @staticmethod
    def test_connection(config: MySQLConfig) -> tuple[bool, str]:
        try:
            import mysql.connector
        except ImportError:
            return False, (
                "Пакет mysql-connector-python не установлен.\n"
                "Выполните: pip install mysql-connector-python"
            )

        try:
            conn = mysql.connector.connect(
                host=config.host,
                port=config.port,
                user=config.user,
                password=config.password,
                database=config.database,
                connection_timeout=5,
                use_pure=True,
            )
            version = conn.get_server_info()
            conn.close()
            return True, f"Подключено. Версия сервера: {version}"
        except mysql.connector.Error as e:
            codes = {
                1045: "Неверный логин или пароль.",
                1049: "База данных не существует.",
                2003: "Не удалось подключиться к серверу. Проверьте хост и порт.",
                2005: "Неизвестный хост MySQL-сервера.",
            }
            msg = codes.get(e.errno, str(e))
            return False, f"Ошибка MySQL [{e.errno}]: {msg}"
        except Exception as e:
            return False, f"Неожиданная ошибка: {e}"


    def _get_schema_version(self, conn) -> int:
        try:
            cur = conn.cursor()
            cur.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
            row = cur.fetchone()
            cur.close()
            return row[0] if row else 0
        except Exception:
            return 0

    def _migrate(self) -> None:
        with self._lock:
            conn = self._get_conn()
            try:
                current = self._get_schema_version(conn)
                for version, sql in self._MIGRATIONS:
                    if version <= current:
                        continue
                    cur = conn.cursor()
                    for statement in sql.strip().split(";"):
                        s = statement.strip()
                        if s:
                            cur.execute(s)
                    if version >= 3:
                        cur.execute(
                            "INSERT INTO schema_version (version) VALUES (%s) "
                            "ON DUPLICATE KEY UPDATE version=version",
                            (version,),
                        )
                    cur.close()
                conn.commit()
            finally:
                conn.close()


    def list_accounts(self) -> list[dict]:
        with self._lock:
            conn = self._get_conn()
            try:
                cur = conn.cursor(dictionary=True)
                cur.execute("SELECT id, username FROM accounts ORDER BY id")
                rows = cur.fetchall()
                cur.close()
                return [{"id": r["id"], "username": r["username"]} for r in rows]
            finally:
                conn.close()

    def create_account(self, username: str, salt: str, canary: str) -> int:
        with self._lock:
            conn = self._get_conn()
            try:
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO accounts (username, salt, canary) VALUES (%s, %s, %s)",
                    (username, salt, canary),
                )
                conn.commit()
                rid = cur.lastrowid
                cur.close()
                return rid
            finally:
                conn.close()

    def get_account(self, username: str) -> dict | None:
        with self._lock:
            conn = self._get_conn()
            try:
                cur = conn.cursor(dictionary=True)
                cur.execute(
                    "SELECT id, username, salt, canary FROM accounts WHERE username = %s",
                    (username,),
                )
                row = cur.fetchone()
                cur.close()
                return dict(row) if row else None
            finally:
                conn.close()

    def delete_account(self, account_id: int) -> None:
        with self._lock:
            conn = self._get_conn()
            try:
                cur = conn.cursor()
                cur.execute("DELETE FROM attachments WHERE account_id = %s", (account_id,))
                cur.execute("DELETE FROM records WHERE account_id = %s", (account_id,))
                cur.execute("DELETE FROM accounts WHERE id = %s", (account_id,))
                conn.commit()
                cur.close()
            finally:
                conn.close()


    def get_setting(self, key: str, default: str = "") -> str:
        with self._lock:
            conn = self._get_conn()
            try:
                cur = conn.cursor(dictionary=True)
                cur.execute(
                    "SELECT `value` FROM settings WHERE `key` = %s", (key,)
                )
                row = cur.fetchone()
                cur.close()
                return row["value"] if row else default
            finally:
                conn.close()

    def set_setting(self, key: str, value: str) -> None:
        with self._lock:
            conn = self._get_conn()
            try:
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO settings (`key`, `value`) VALUES (%s, %s) "
                    "ON DUPLICATE KEY UPDATE `value` = VALUES(`value`)",
                    (key, value),
                )
                conn.commit()
                cur.close()
            finally:
                conn.close()


    def insert_record(self, r: Record) -> int:
        with self._lock:
            conn = self._get_conn()
            try:
                cur = conn.cursor()
                cur.execute(
                    """INSERT INTO records
                       (account_id, title, category, encrypted_data, is_favorite, expiry_date)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (r.account_id, r.title, r.category, r.encrypted_data,
                     int(r.is_favorite), r.expiry_date or None),
                )
                conn.commit()
                rid = cur.lastrowid
                cur.close()
                return rid
            finally:
                conn.close()

    def update_record(self, r: Record) -> None:
        with self._lock:
            conn = self._get_conn()
            try:
                cur = conn.cursor()
                cur.execute(
                    """UPDATE records SET
                       title=%s, category=%s, encrypted_data=%s,
                       is_favorite=%s, expiry_date=%s, updated_at=NOW()
                       WHERE id=%s AND account_id=%s""",
                    (r.title, r.category, r.encrypted_data,
                     int(r.is_favorite), r.expiry_date or None, r.id, r.account_id),
                )
                conn.commit()
                cur.close()
            finally:
                conn.close()

    def delete_record(self, record_id: int) -> None:
        with self._lock:
            conn = self._get_conn()
            try:
                cur = conn.cursor()
                cur.execute("DELETE FROM attachments WHERE record_id = %s", (record_id,))
                cur.execute("DELETE FROM records WHERE id = %s", (record_id,))
                conn.commit()
                cur.close()
            finally:
                conn.close()

    def toggle_favorite(self, record_id: int) -> None:
        with self._lock:
            conn = self._get_conn()
            try:
                cur = conn.cursor()
                cur.execute(
                    "UPDATE records SET is_favorite = 1 - is_favorite WHERE id = %s",
                    (record_id,),
                )
                conn.commit()
                cur.close()
            finally:
                conn.close()

    def get_all_records(self, account_id: int) -> list[Record]:
        with self._lock:
            conn = self._get_conn()
            try:
                cur = conn.cursor(dictionary=True)
                cur.execute(
                    "SELECT * FROM records WHERE account_id = %s "
                    "ORDER BY is_favorite DESC, updated_at DESC",
                    (account_id,),
                )
                rows = cur.fetchall()
                cur.close()
                return [Record.from_row(r) for r in rows]
            finally:
                conn.close()

    def get_records_by_category(self, category: str, account_id: int) -> list[Record]:
        with self._lock:
            conn = self._get_conn()
            try:
                cur = conn.cursor(dictionary=True)
                cur.execute(
                    "SELECT * FROM records WHERE category = %s AND account_id = %s "
                    "ORDER BY is_favorite DESC, updated_at DESC",
                    (category, account_id),
                )
                rows = cur.fetchall()
                cur.close()
                return [Record.from_row(r) for r in rows]
            finally:
                conn.close()

    def get_record_by_id(self, record_id: int) -> "Record | None":
        with self._lock:
            conn = self._get_conn()
            try:
                cur = conn.cursor(dictionary=True)
                cur.execute("SELECT * FROM records WHERE id = %s", (record_id,))
                row = cur.fetchone()
                cur.close()
                return Record.from_row(row) if row else None
            finally:
                conn.close()


    def insert_attachment(
        self, record_id: int, account_id: int,
        filename: str, mimetype: str, data: bytes,
    ) -> int:
        with self._lock:
            conn = self._get_conn()
            try:
                cur = conn.cursor()
                cur.execute(
                    """INSERT INTO attachments
                       (record_id, account_id, filename, mimetype, size, data)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (record_id, account_id, filename, mimetype, len(data), data),
                )
                rid = cur.lastrowid
                cur.execute(
                    "UPDATE records SET updated_at=NOW() WHERE id=%s",
                    (record_id,),
                )
                conn.commit()
                cur.close()
                return rid
            finally:
                conn.close()

    def get_attachments(self, record_id: int) -> list[dict]:
        with self._lock:
            conn = self._get_conn()
            try:
                cur = conn.cursor(dictionary=True)
                cur.execute(
                    "SELECT id, record_id, account_id, filename, mimetype, size, created_at "
                    "FROM attachments WHERE record_id = %s ORDER BY created_at",
                    (record_id,),
                )
                rows = cur.fetchall()
                cur.close()
                return [
                    {
                        "id":         r["id"],
                        "record_id":  r["record_id"],
                        "account_id": r["account_id"],
                        "filename":   r["filename"],
                        "mimetype":   r["mimetype"],
                        "size":       r["size"],
                        "created_at": str(r["created_at"]),
                    }
                    for r in rows
                ]
            finally:
                conn.close()

    def get_attachment(self, attachment_id: int) -> dict | None:
        with self._lock:
            conn = self._get_conn()
            try:
                cur = conn.cursor(dictionary=True)
                cur.execute(
                    "SELECT id, record_id, account_id, filename, mimetype, size, data, created_at "
                    "FROM attachments WHERE id = %s",
                    (attachment_id,),
                )
                row = cur.fetchone()
                cur.close()
                if row is None:
                    return None
                return {
                    "id":         row["id"],
                    "record_id":  row["record_id"],
                    "account_id": row["account_id"],
                    "filename":   row["filename"],
                    "mimetype":   row["mimetype"],
                    "size":       row["size"],
                    "data":       bytes(row["data"]),
                    "created_at": str(row["created_at"]),
                }
            finally:
                conn.close()

    def delete_attachment(self, attachment_id: int) -> None:
        with self._lock:
            conn = self._get_conn()
            try:
                cur = conn.cursor(dictionary=True)
                cur.execute(
                    "SELECT record_id FROM attachments WHERE id = %s", (attachment_id,)
                )
                row = cur.fetchone()
                cur.close()

                cur = conn.cursor()
                cur.execute("DELETE FROM attachments WHERE id = %s", (attachment_id,))
                if row:
                    cur.execute(
                        "UPDATE records SET updated_at=NOW() WHERE id=%s",
                        (row["record_id"],),
                    )
                conn.commit()
                cur.close()
            finally:
                conn.close()


    def close(self) -> None:
        try:
            if self._pool:
                self._pool = None
        except Exception:
            pass
