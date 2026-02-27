from __future__ import annotations
import json
from dataclasses import dataclass, field
from typing import Any, Optional



CATEGORIES: dict[str, dict] = {
    "passport": {
        "label": "Паспорт",
        "icon": "🪪",
        "color": "#6c63ff",
        "has_expiry": False,
        "fields": [
            ("Серия и номер",       "series_number",  False),
            ("Дата выдачи",        "issue_date",     False),
            ("Кем выдан",          "issued_by",      False),
            ("Код подразделения",  "dept_code",      False),
            ("Дата рождения",      "birth_date",     False),
            ("Место рождения",     "birth_place",    False),
            ("Адрес регистрации",  "reg_address",    False),
        ],
    },
    "foreign_passport": {
        "label": "Загранпаспорт",
        "icon": "✈️",
        "color": "#48cfad",
        "has_expiry": True,
        "fields": [
            ("Серия и номер",      "series_number",  False),
            ("Дата рождения",      "birth_date",     False),
            ("Место рождения",     "birth_place",    False),
            ("Дата выдачи",        "issue_date",     False),
            ("Кем выдан",          "issued_by",      False),
        ],
    },
    "driver_license": {
        "label": "Водительское уд.",
        "icon": "🚗",
        "color": "#f7b731",
        "has_expiry": True,
        "fields": [
            ("Серия и номер",      "series_number",  False),
            ("Дата рождения",      "birth_date",     False),
            ("Место рождения",     "birth_place",    False),
            ("Категории",          "categories",     False),
            ("Дата выдачи",        "issue_date",     False),
            ("Кем выдан",          "issued_by",      False),
        ],
    },
    "snils": {
        "label": "СНИЛС",
        "icon": "🟢",
        "color": "#20bf6b",
        "has_expiry": False,
        "fields": [
            ("Номер СНИЛС",        "number",         False),
            ("Дата регистрации",   "reg_date",       False),
        ],
    },
    "inn": {
        "label": "ИНН",
        "icon": "🔢",
        "color": "#45aaf2",
        "has_expiry": False,
        "fields": [
            ("Номер ИНН",          "number",         False),
            ("ИФНС",               "ifns",           False),
            ("Дата присвоения",    "issue_date",     False),
        ],
    },
    "oms": {
        "label": "Полис ОМС",
        "icon": "🏥",
        "color": "#fc5c65",
        "has_expiry": False,
        "fields": [
            ("Номер полиса",       "number",         False),
            ("Страховая компания", "insurer",        False),
            ("Дата выдачи",        "issue_date",     False),
        ],
    },
    "insurance": {
        "label": "Страховка",
        "icon": "🛡️",
        "color": "#fd9644",
        "has_expiry": True,
        "fields": [
            ("Номер полиса",       "number",         False),
            ("Вид страхования",    "type",           False),
            ("Страховая компания", "insurer",        False),
            ("Страхователь",       "insured",        False),
            ("Страховая сумма",    "sum",            False),
        ],
    },
    "bank_card": {
        "label": "Банковская карта",
        "icon": "💳",
        "color": "#a55eea",
        "has_expiry": True,
        "fields": [
            ("Последние 4 цифры",  "last4",          False),
            ("Банк",               "bank",           False),
            ("Имя на карте",       "holder",         False),
            ("Тип карты",          "card_type",      False),
            ("ПИН-код",            "pin",            True),
        ],
    },
    "vehicle": {
        "label": "Транспорт (ПТС/СТС)",
        "icon": "🚙",
        "color": "#eb3b5a",
        "has_expiry": False,
        "fields": [
            ("Гос. номер",         "reg_number",     False),
            ("VIN",                "vin",            False),
            ("Марка / Модель",     "model",          False),
            ("Год выпуска",        "year",           False),
            ("Цвет",               "color",          False),
            ("Мощность (л.с.)",    "power",          False),
            ("СТС номер",          "sts",            False),
            ("ПТС номер",          "pts",            False),
        ],
    },
    "real_estate": {
        "label": "Недвижимость",
        "icon": "🏠",
        "color": "#26de81",
        "has_expiry": False,
        "fields": [
            ("Вид",                "estate_type",    False),
            ("Адрес",              "address",        False),
            ("Площадь (м²)",       "area",           False),
            ("Кадастровый номер",  "cadastral",      False),
            ("Дата регистрации права", "reg_date",   False),
            ("Номер договора",     "contract",       False),
        ],
    },
    "password": {
        "label": "Логин / Пароль",
        "icon": "🔑",
        "color": "#778ca3",
        "has_expiry": False,
        "fields": [
            ("Сайт / Сервис",      "service",        False),
            ("Эл. почта",          "email",          False),
            ("Логин",              "login",          False),
            ("Пароль",             "password",       True),
        ],
    },
    "other": {
        "label": "Прочее",
        "icon": "📋",
        "color": "#8d99ae",
        "has_expiry": True,
        "fields": [
            ("Тип документа",      "doc_type",       False),
            ("Номер",              "number",         False),
            ("Кем выдан",          "issued_by",      False),
            ("Дата выдачи",        "issue_date",     False),
        ],
    },
}

ALL_CATEGORY_KEYS = list(CATEGORIES.keys())



@dataclass
class RecordData:
    fields: dict[str, str] = field(default_factory=dict)
    notes: str = ""
    custom_fields: list[tuple[str, str]] = field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps({
            "fields": self.fields,
            "notes": self.notes,
            "custom_fields": self.custom_fields,
        }, ensure_ascii=False)

    @classmethod
    def from_json(cls, raw: str) -> "RecordData":
        d = json.loads(raw)
        return cls(
            fields=d.get("fields", {}),
            notes=d.get("notes", ""),
            custom_fields=d.get("custom_fields", []),
        )


@dataclass
class Record:
    title: str
    category: str
    encrypted_data: str
    is_favorite: bool = False
    expiry_date: Optional[str] = None
    id: Optional[int] = None
    account_id: int = 0
    created_at: str = ""
    updated_at: str = ""

    @classmethod
    def from_row(cls, row) -> "Record":
        if not isinstance(row, dict):
            row = dict(row)
        return cls(
            id=row["id"],
            title=row["title"],
            category=row["category"],
            encrypted_data=row["encrypted_data"],
            is_favorite=bool(row["is_favorite"]),
            expiry_date=str(row["expiry_date"]) if row.get("expiry_date") else None,
            account_id=int(row.get("account_id", 0) or 0),
            created_at=str(row.get("created_at", "")),
            updated_at=str(row.get("updated_at", "")),
        )

    @property
    def category_info(self) -> dict:
        return CATEGORIES.get(self.category, CATEGORIES["other"])

    @property
    def icon(self) -> str:
        return self.category_info["icon"]

    @property
    def color(self) -> str:
        return self.category_info["color"]
