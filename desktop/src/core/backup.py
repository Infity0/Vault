from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.core.db_base import BaseDatabase
    from src.core.models import Record

BACKUP_VERSION = 1



def export_backup(
    db: "BaseDatabase",
    account_id: int,
    username: str,
    dest_path: Path,
) -> int:
    records = db.get_all_records(account_id)

    records_data = [
        {
            "title":          r.title,
            "category":       r.category,
            "encrypted_data": r.encrypted_data,
            "is_favorite":    r.is_favorite,
            "expiry_date":    r.expiry_date,
        }
        for r in records
    ]

    records_json = json.dumps(records_data, ensure_ascii=False)
    checksum = hashlib.sha256(records_json.encode()).hexdigest()

    payload = {
        "version":     BACKUP_VERSION,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "username":    username,
        "records":     records_data,
        "checksum":    checksum,
    }

    dest_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return len(records)



class BackupError(Exception):
    pass


def import_backup(
    db: "BaseDatabase",
    account_id: int,
    src_path: Path,
    replace: bool = False,
) -> int:
    raw = src_path.read_text(encoding="utf-8")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as e:
        raise BackupError(f"Файл повреждён или не является резервной копией: {e}")

    if payload.get("version") != BACKUP_VERSION:
        raise BackupError(
            f"Неподдерживаемая версия резервной копии: {payload.get('version')}"
        )

    records_data = payload.get("records", [])
    if not isinstance(records_data, list):
        raise BackupError("Неверный формат файла: поле 'records' отсутствует.")

    expected = payload.get("checksum", "")
    actual = hashlib.sha256(
        json.dumps(records_data, ensure_ascii=False).encode()
    ).hexdigest()
    if expected and expected != actual:
        raise BackupError(
            "Контрольная сумма не совпадает. Файл мог быть изменён или повреждён."
        )

    from src.core.models import Record

    if replace:
        for existing in db.get_all_records(account_id):
            db.delete_record(existing.id)

    count = 0
    for item in records_data:
        r = Record(
            title=item.get("title", ""),
            category=item.get("category", "other"),
            encrypted_data=item.get("encrypted_data", ""),
            is_favorite=bool(item.get("is_favorite", False)),
            expiry_date=item.get("expiry_date"),
            account_id=account_id,
        )
        db.insert_record(r)
        count += 1

    return count
