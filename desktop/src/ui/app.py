from __future__ import annotations
import base64
from datetime import date, datetime
from typing import Callable, Optional

from src.core.crypto import CryptoManager, CryptoError
from src.core.db_base import BaseDatabase
from src.core.models import Record, RecordData


def _build_default_db() -> BaseDatabase:
    from src.ui.components.settings_dialog import load_mysql_config
    from src.core.db_mysql import MySQLDatabase
    cfg = load_mysql_config()
    return MySQLDatabase(cfg)


class VaultApp:

    def __init__(self) -> None:
        self.startup_error: str = ""
        self.db: Optional[BaseDatabase] = None
        try:
            self.db = _build_default_db()
        except Exception as e:
            self.startup_error = str(e)
        self.crypto = CryptoManager()
        self._account_id: Optional[int] = None
        self._account_username: str = ""
        self._lock_callback: Optional[Callable] = None


    def switch_backend(self, mysql_cfg=None) -> None:
        from src.core.db_mysql import MySQLDatabase
        new_db = MySQLDatabase(mysql_cfg)
        if self.db is not None:
            self.db.close()
        self.db = new_db
        self.startup_error = ""
        self._account_id = None
        self._account_username = ""
        self.crypto.lock()

    @property
    def backend_name(self) -> str:
        return self.db.backend_name


    def vault_exists(self) -> bool:
        if self.db is None:
            return False
        return self.db.vault_exists()

    def list_accounts(self) -> list[dict]:
        if self.db is None:
            return []
        return self.db.list_accounts()

    def username_exists(self, username: str) -> bool:
        if self.db is None:
            return False
        return self.db.get_account(username) is not None

    def create_account(self, username: str, password: str) -> None:
        if self.db is None:
            raise RuntimeError("Нет подключения к базе данных")
        salt = CryptoManager.generate_salt()
        self.crypto.unlock(password, salt)
        canary = self.crypto.make_canary()
        self.crypto.lock()
        self.db.create_account(
            username,
            base64.b64encode(salt).decode(),
            canary,
        )

    def unlock_account(self, username: str, password: str) -> bool:
        if self.db is None:
            return False
        info = self.db.get_account(username)
        if not info:
            return False
        salt = base64.b64decode(info["salt"])
        self.crypto.unlock(password, salt)
        if not self.crypto.verify_canary(info["canary"]):
            self.crypto.lock()
            return False
        self._account_id = info["id"]
        self._account_username = username
        return True

    def lock_vault(self) -> None:
        self.crypto.lock()
        self._account_id = None
        self._account_username = ""
        if self._lock_callback:
            self._lock_callback()

    @property
    def current_username(self) -> str:
        return self._account_username

    def set_lock_callback(self, cb: Callable) -> None:
        self._lock_callback = cb


    def get_all_records(self) -> list[Record]:
        return self.db.get_all_records(self._account_id)

    def get_records_by_category(self, category: str) -> list[Record]:
        if category == "all":
            return self.db.get_all_records(self._account_id)
        if category == "favorites":
            return [r for r in self.db.get_all_records(self._account_id) if r.is_favorite]
        if category == "expiring":
            today = date.today()
            result: list[Record] = []
            for r in self.db.get_all_records(self._account_id):
                if not r.expiry_date:
                    continue
                try:
                    exp = datetime.strptime(r.expiry_date, "%Y-%m-%d").date()
                    if (exp - today).days <= 30:
                        result.append(r)
                except ValueError:
                    pass
            return result
        return self.db.get_records_by_category(category, self._account_id)

    def count_expiring(self) -> int:
        return len(self.get_records_by_category("expiring"))

    def decrypt_record(self, record: Record) -> RecordData:
        raw = self.crypto.decrypt(record.encrypted_data)
        return RecordData.from_json(raw)

    def save_record(self, record: Record, data: RecordData) -> Record:
        record.encrypted_data = self.crypto.encrypt(data.to_json())
        record.account_id = self._account_id
        if record.id is None:
            record.id = self.db.insert_record(record)
        else:
            self.db.update_record(record)
        return record

    def delete_record(self, record_id: int) -> None:
        self.db.delete_record(record_id)

    def toggle_favorite(self, record_id: int) -> None:
        self.db.toggle_favorite(record_id)

    def search_records(self, query: str) -> list[Record]:
        query_lower = query.lower()
        results: list[Record] = []
        for r in self.db.get_all_records(self._account_id):
            if query_lower in r.title.lower():
                results.append(r)
                continue
            try:
                data = self.decrypt_record(r)
                combined = " ".join(data.fields.values()) + data.notes
                if query_lower in combined.lower():
                    results.append(r)
            except CryptoError:
                pass
        return results


    def export_backup(self, dest_path: str) -> int:
        from pathlib import Path
        from src.core.backup import export_backup
        return export_backup(
            db=self.db,
            account_id=self._account_id,
            username=self._account_username,
            dest_path=Path(dest_path),
        )

    def import_backup(self, src_path: str, replace: bool = False) -> int:
        from pathlib import Path
        from src.core.backup import import_backup
        return import_backup(
            db=self.db,
            account_id=self._account_id,
            src_path=Path(src_path),
            replace=replace,
        )


    def get_attachments(self, record_id: int) -> list[dict]:
        return self.db.get_attachments(record_id)

    def upload_attachment(self, record_id: int, file_path: str) -> dict:
        import mimetypes
        from pathlib import Path

        path = Path(file_path)
        data = path.read_bytes()
        if len(data) > 20 * 1024 * 1024:
            raise ValueError("Файл слишком большой (максимум 20 МБ)")

        mimetype, _ = mimetypes.guess_type(file_path)
        mimetype = mimetype or "application/octet-stream"

        att_id = self.db.insert_attachment(
            record_id=record_id,
            account_id=self._account_id,
            filename=path.name,
            mimetype=mimetype,
            data=data,
        )
        attachments = self.db.get_attachments(record_id)
        return next(a for a in attachments if a["id"] == att_id)

    def download_attachment(self, attachment_id: int, dest_dir: str) -> str:
        from pathlib import Path

        att = self.db.get_attachment(attachment_id)
        if not att:
            raise ValueError("Вложение не найдено")

        dest = Path(dest_dir) / att["filename"]
        stem, suffix = dest.stem, dest.suffix
        counter = 1
        while dest.exists():
            dest = dest.with_name(f"{stem}_{counter}{suffix}")
            counter += 1

        dest.write_bytes(att["data"])
        return str(dest)

    def get_attachment_data(self, attachment_id: int) -> bytes:
        att = self.db.get_attachment(attachment_id)
        if not att:
            raise ValueError("Вложение не найдено")
        return att["data"]

    def delete_attachment(self, attachment_id: int) -> None:
        self.db.delete_attachment(attachment_id)

