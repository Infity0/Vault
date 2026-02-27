from __future__ import annotations
from abc import ABC, abstractmethod
from src.core.models import Record


class BaseDatabase(ABC):


    @abstractmethod
    def list_accounts(self) -> list[dict]: ...

    @abstractmethod
    def create_account(self, username: str, salt: str, canary: str) -> int: ...

    @abstractmethod
    def get_account(self, username: str) -> dict | None: ...

    @abstractmethod
    def delete_account(self, account_id: int) -> None: ...

    def vault_exists(self) -> bool:
        return len(self.list_accounts()) > 0


    @abstractmethod
    def get_setting(self, key: str, default: str = "") -> str: ...

    @abstractmethod
    def set_setting(self, key: str, value: str) -> None: ...


    @abstractmethod
    def insert_record(self, r: Record) -> int: ...

    @abstractmethod
    def update_record(self, r: Record) -> None: ...

    @abstractmethod
    def delete_record(self, record_id: int) -> None: ...

    @abstractmethod
    def toggle_favorite(self, record_id: int) -> None: ...

    @abstractmethod
    def get_all_records(self, account_id: int) -> list[Record]: ...

    @abstractmethod
    def get_records_by_category(self, category: str, account_id: int) -> list[Record]: ...

    @abstractmethod
    def get_record_by_id(self, record_id: int) -> "Record | None": ...

    @abstractmethod
    def close(self) -> None: ...


    @abstractmethod
    def insert_attachment(
        self, record_id: int, account_id: int,
        filename: str, mimetype: str, data: bytes,
    ) -> int: ...

    @abstractmethod
    def get_attachments(self, record_id: int) -> list[dict]: ...

    @abstractmethod
    def get_attachment(self, attachment_id: int) -> dict | None: ...

    @abstractmethod
    def delete_attachment(self, attachment_id: int) -> None: ...


    @property
    @abstractmethod
    def backend_name(self) -> str:
        ...
