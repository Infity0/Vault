from __future__ import annotations
import customtkinter as ctk
from typing import Callable

from src.core.models import CATEGORIES
from src.utils.constants import *


NAV_ITEMS = [
    ("all",       "📦", "Все записи"),
    ("favorites", "⭐", "Избранное"),
    ("expiring",  "⏰", "Истекают скоро"),
    None,
] + [
    (key, info["icon"], info["label"])
    for key, info in CATEGORIES.items()
]


class _NavItem(ctk.CTkFrame):

    def __init__(self, master, key: str, icon: str, label: str,
                 on_click: Callable[[str], None],
                 text_color: str = None, **kw):
        super().__init__(master, fg_color="transparent",
                         corner_radius=RADIUS_SM, cursor="hand2", **kw)
        self._key = key
        self._on_click = on_click
        self._normal_color = text_color or TEXT_SUB
        self._active = False
        self._base_label = label

        self._icon_lbl = ctk.CTkLabel(
            self, text=icon,
            font=(FONT_FAMILY, 14),
            text_color=self._normal_color,
            width=28, height=36,
            anchor="center",
        )
        self._icon_lbl.pack(side="left", padx=(8, 0))

        self._text_lbl = ctk.CTkLabel(
            self, text=label,
            font=FONT_BODY,
            text_color=self._normal_color,
            anchor="w",
            height=36,
        )
        self._text_lbl.pack(side="left", padx=(4, 8), fill="x", expand=True)

        for w in (self, self._icon_lbl, self._text_lbl):
            w.bind("<Button-1>", self._on_press)
            w.bind("<Enter>",    self._on_enter)
            w.bind("<Leave>",    self._on_leave)

    def _on_press(self, _=None) -> None:
        self._on_click(self._key)

    def _on_enter(self, _=None) -> None:
        if not self._active:
            self.configure(fg_color=CARD_HOVER)

    def _on_leave(self, _=None) -> None:
        if not self._active:
            self.configure(fg_color="transparent")

    def set_active(self, active: bool) -> None:
        self._active = active
        if active:
            self.configure(fg_color=ACCENT_DIM)
            self._icon_lbl.configure(
                text_color=TEXT, font=(FONT_FAMILY, 14, "bold"))
            self._text_lbl.configure(
                text_color=TEXT, font=(FONT_FAMILY, 12, "bold"))
        else:
            self.configure(fg_color="transparent")
            self._icon_lbl.configure(
                text_color=self._normal_color, font=(FONT_FAMILY, 14))
            self._text_lbl.configure(
                text_color=self._normal_color, font=FONT_BODY)

    def set_badge(self, count: int) -> None:
        lbl = self._base_label
        if count > 0:
            self._text_lbl.configure(text=f"{lbl}  ● {count}")
        else:
            self._text_lbl.configure(text=lbl)


class Sidebar(ctk.CTkFrame):
    def __init__(self, master, on_select: Callable[[str], None],
                 on_lock: Callable, on_settings: Callable,
                 on_qr: Callable = None,
                 on_export: Callable = None,
                 on_import: Callable = None,
                 **kw):
        super().__init__(
            master,
            width=SIDEBAR_W,
            fg_color=SURFACE,
            corner_radius=0,
            **kw,
        )
        self.on_select = on_select
        self.on_lock = on_lock
        self.on_settings = on_settings
        self.on_qr = on_qr
        self.on_export = on_export
        self.on_import = on_import
        self._active: str = "all"
        self._items: dict[str, _NavItem] = {}
        self._build()


    def _build(self) -> None:
        header = ctk.CTkFrame(self, fg_color="transparent", height=64)
        header.pack(fill="x", padx=PAD, pady=(PAD, 0))
        header.pack_propagate(False)
        ctk.CTkLabel(
            header, text="🔐 Vault",
            font=(FONT_FAMILY, 16, "bold"), text_color=TEXT,
            anchor="w",
        ).place(relx=0, rely=0.5, anchor="w")

        ctk.CTkFrame(self, fg_color=BORDER, height=1).pack(
            fill="x", padx=PAD, pady=(4, 8))

        scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=BORDER,
            scrollbar_button_hover_color=ACCENT_DIM,
        )
        scroll.pack(fill="both", expand=True, padx=4)

        for item in NAV_ITEMS:
            if item is None:
                ctk.CTkFrame(scroll, fg_color=BORDER, height=1).pack(
                    fill="x", padx=PAD_SM, pady=6)
                continue
            key, icon, label = item
            nav = _NavItem(scroll, key, icon, label, on_click=self._select)
            nav.pack(fill="x", padx=PAD_SM, pady=2)
            self._items[key] = nav

        ctk.CTkFrame(self, fg_color=BORDER, height=1).pack(
            fill="x", padx=PAD, pady=(4, 0))

        if self.on_qr:
            _NavItem(self, "qr", "📱", "Подключить телефон",
                     on_click=lambda _: self.on_qr(),
                     text_color=ACCENT,
                     ).pack(fill="x", padx=4)

        if self.on_export:
            _NavItem(self, "export", "📤", "Экспорт данных",
                     on_click=lambda _: self.on_export(),
                     ).pack(fill="x", padx=4)

        if self.on_import:
            _NavItem(self, "import", "📥", "Импорт данных",
                     on_click=lambda _: self.on_import(),
                     ).pack(fill="x", padx=4)

        _NavItem(self, "settings", "⚙", "Настройки",
                 on_click=lambda _: self.on_settings(),
                 ).pack(fill="x", padx=4)

        _NavItem(self, "lock", "🔒", "Заблокировать",
                 on_click=lambda _: self.on_lock(),
                 text_color=DANGER,
                 ).pack(fill="x", padx=4, pady=(0, PAD_SM))

        self._highlight("all")


    def _highlight(self, key: str) -> None:
        if self._active in self._items:
            self._items[self._active].set_active(False)
        self._active = key
        if key in self._items:
            self._items[key].set_active(True)

    def _select(self, key: str) -> None:
        self._highlight(key)
        self.on_select(key)

    def refresh(self) -> None:
        self._highlight(self._active)

    def set_expiry_badge(self, count: int) -> None:
        if "expiring" in self._items:
            item = self._items["expiring"]
            item.set_badge(count)
            color = WARNING if count > 0 else TEXT_SUB
            item._icon_lbl.configure(text_color=color)
            item._text_lbl.configure(
                text_color=color if not item._active else TEXT
            )
