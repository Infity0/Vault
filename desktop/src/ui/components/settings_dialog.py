from __future__ import annotations
import json
import threading
import customtkinter as ctk
from pathlib import Path
from typing import Callable

from src.core.db_mysql import MySQLConfig, MySQLDatabase
from src.utils.constants import *

CONFIG_PATH = Path.home() / ".vault" / "db_config.json"
_PWD_PATH = Path.home() / ".vault" / ".db_pwd"

LOCK_TIMEOUT_OPTIONS: dict[str, int] = {
    "1 минута":   60_000,
    "5 минут":   300_000,
    "15 минут":  900_000,
    "30 минут": 1_800_000,
    "Отключить":        0,
}
_DEFAULT_LOCK_LABEL = "5 минут"


def load_mysql_config() -> MySQLConfig:
    cfg = MySQLConfig()
    if CONFIG_PATH.exists():
        try:
            cfg = MySQLConfig.from_json(CONFIG_PATH.read_text("utf-8"))
        except Exception:
            pass
    if not cfg.password:
        cfg.password = load_mysql_password()
    return cfg


def save_mysql_config(cfg: MySQLConfig) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    data: dict = {}
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text("utf-8"))
        except Exception:
            pass
    data.update(cfg.to_dict())
    CONFIG_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    if cfg.password:
        _PWD_PATH.write_text(cfg.password, encoding="utf-8")


def load_mysql_password() -> str:
    if _PWD_PATH.exists():
        try:
            return _PWD_PATH.read_text("utf-8").strip()
        except Exception:
            pass
    return ""


def load_lock_timeout() -> int:
    if CONFIG_PATH.exists():
        try:
            d = json.loads(CONFIG_PATH.read_text("utf-8"))
            label = d.get("lock_timeout", _DEFAULT_LOCK_LABEL)
            return LOCK_TIMEOUT_OPTIONS.get(label, LOCK_TIMEOUT_OPTIONS[_DEFAULT_LOCK_LABEL])
        except Exception:
            pass
    return LOCK_TIMEOUT_OPTIONS[_DEFAULT_LOCK_LABEL]


def save_lock_timeout(label: str) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    data: dict = {}
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text("utf-8"))
        except Exception:
            pass
    data["lock_timeout"] = label
    CONFIG_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


class SettingsDialog(ctk.CTkToplevel):

    def __init__(self, master, on_apply: Callable, **kw):
        super().__init__(master, **kw)
        self.on_apply = on_apply
        self.title("Настройки — База данных")
        self.geometry("500x600")
        self.resizable(False, True)
        self.configure(fg_color=BG)
        self.after(200, self.grab_set)
        self._cfg = load_mysql_config()
        self._status_var = ctk.StringVar(value="")
        _stored_ms = load_lock_timeout()
        _stored_label = next(
            (lbl for lbl, ms in LOCK_TIMEOUT_OPTIONS.items() if ms == _stored_ms),
            _DEFAULT_LOCK_LABEL,
        )
        self._lock_timeout_var = ctk.StringVar(value=_stored_label)
        self._build()
        self.after(100, self.lift)

    def _build(self) -> None:
        hdr = ctk.CTkFrame(self, fg_color=SURFACE, height=52, corner_radius=0)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        ctk.CTkLabel(
            hdr, text="⚙️  База данных",
            font=(FONT_FAMILY, 14, "bold"), text_color=TEXT,
        ).pack(side="left", padx=PAD)

        body = ctk.CTkScrollableFrame(self, fg_color="transparent",
                                       scrollbar_button_color=BORDER)
        body.pack(fill="both", expand=True, padx=0, pady=0)

        self._section(body, "MySQL сервер")
        self._build_mysql_form(body)

        self._section(body, "Безопасность")
        ctk.CTkLabel(
            body,
            text=(
                "Данные хранятся в зашифрованном виде (AES-256).\n"
                "Сервер MySQL видит только зашифрованный текст — "
                "ключ расшифровки никогда не покидает ваше устройство."
            ),
            font=FONT_SMALL, text_color=TEXT_SUB,
            anchor="w", wraplength=440, justify="left",
        ).pack(fill="x", padx=PAD, pady=(4, 0))

        self._section(body, "Авто-блокировка")
        ctk.CTkLabel(
            body,
            text="Блокировать хранилище после периода бездействия:",
            font=FONT_SMALL, text_color=TEXT_SUB, anchor="w",
        ).pack(fill="x", padx=PAD, pady=(4, 0))
        ctk.CTkOptionMenu(
            body,
            values=list(LOCK_TIMEOUT_OPTIONS.keys()),
            variable=self._lock_timeout_var,
            font=FONT_BODY,
            fg_color=CARD,
            button_color=ACCENT_DIM,
            button_hover_color=ACCENT,
            text_color=TEXT,
            dropdown_fg_color=CARD,
            dropdown_hover_color=CARD_HOVER,
            dropdown_text_color=TEXT,
        ).pack(fill="x", padx=PAD, pady=(4, 0))

        self._status_label = ctk.CTkLabel(
            body, textvariable=self._status_var,
            font=FONT_SMALL, text_color=SUCCESS,
            anchor="w", wraplength=440,
        )
        self._status_label.pack(fill="x", padx=PAD, pady=(PAD, 0))

        footer = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=0, height=56)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)

        ctk.CTkButton(
            footer, text="Отмена", height=36,
            fg_color="transparent", text_color=TEXT_SUB,
            hover_color=CARD_HOVER, corner_radius=RADIUS_SM,
            font=FONT_BODY, command=self.destroy,
        ).pack(side="right", padx=(0, PAD), pady=10)

        self._apply_btn = ctk.CTkButton(
            footer, text="  ✓  Применить  ", height=36,
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            corner_radius=RADIUS_SM, font=(FONT_FAMILY, 13, "bold"),
            command=self._apply,
        )
        self._apply_btn.pack(side="right", pady=10)

        self._test_btn = ctk.CTkButton(
            footer, text="Проверить соединение", height=36,
            fg_color="transparent", text_color=ACCENT,
            hover_color=CARD_HOVER, border_color=ACCENT,
            border_width=1, corner_radius=RADIUS_SM, font=FONT_BODY,
            command=self._test_connection,
        )
        self._test_btn.pack(side="right", padx=(0, PAD_SM), pady=10)

    def _build_mysql_form(self, parent) -> None:
        def field(lbl, attr, placeholder="", secret=False):
            self._section(parent, lbl)
            var = ctk.StringVar(value=getattr(self._cfg, attr))
            setattr(self, f"_mysql_{attr}", var)
            ctk.CTkEntry(
                parent,
                textvariable=var,
                placeholder_text=placeholder,
                height=40, font=FONT_BODY,
                fg_color=SURFACE, border_color=BORDER,
                text_color=TEXT,
                show="•" if secret else "",
            ).pack(fill="x", padx=PAD, pady=(4, 0))

        field("Хост", "host", "localhost")
        field("Порт", "port", "3306")
        field("Пользователь", "user", "vault_user")
        field("Пароль", "password", "••••••••", secret=True)
        field("База данных", "database", "vault_db")

    def _section(self, parent, text: str) -> None:
        ctk.CTkLabel(
            parent, text=text.upper(),
            font=(FONT_FAMILY, 10, "bold"),
            text_color=TEXT_SUB, anchor="w",
        ).pack(fill="x", padx=PAD, pady=(PAD, 0))

    def _collect_mysql_config(self) -> MySQLConfig:
        try:
            port = int(self._mysql_port.get().strip() or "3306")
        except ValueError:
            port = 3306
        return MySQLConfig(
            host=self._mysql_host.get().strip(),
            port=port,
            user=self._mysql_user.get().strip(),
            password=self._mysql_password.get(),
            database=self._mysql_database.get().strip(),
        )

    def _test_connection(self) -> None:
        cfg = self._collect_mysql_config()
        self._set_status("Проверка соединения…", TEXT_SUB)
        self._test_btn.configure(state="disabled")

        def run():
            ok, err = MySQLDatabase.test_connection(cfg)
            self.after(0, lambda: self._on_test_done(ok, err))

        threading.Thread(target=run, daemon=True).start()

    def _on_test_done(self, ok: bool, err: str) -> None:
        self._test_btn.configure(state="normal")
        if ok:
            self._set_status("Соединение успешно!", SUCCESS)
        else:
            self._set_status(f"Ошибка: {err}", DANGER)

    def _set_status(self, msg: str, color: str) -> None:
        self._status_var.set(msg)
        self._status_label.configure(text_color=color)

    def _apply(self) -> None:
        save_lock_timeout(self._lock_timeout_var.get())
        mysql_cfg = self._collect_mysql_config()
        save_mysql_config(mysql_cfg)
        self.on_apply("mysql", mysql_cfg)
        self.destroy()
