from __future__ import annotations
import customtkinter as ctk
from typing import Callable
from datetime import datetime, date

from src.core.models import Record, CATEGORIES
from src.utils.constants import *


class RecordCard(ctk.CTkFrame):
    def __init__(
        self,
        master,
        record: Record,
        on_click: Callable[[Record], None],
        on_favorite: Callable[[Record], None],
        **kw,
    ):
        super().__init__(
            master,
            fg_color=CARD,
            corner_radius=RADIUS,
            border_width=1,
            border_color=BORDER,
            **kw,
        )
        self.record = record
        self.on_click = on_click
        self.on_favorite = on_favorite
        self._build()
        self._bind_hover()


    def _build(self) -> None:
        accent_bar = ctk.CTkFrame(
            self, height=4, fg_color=self.record.color,
            corner_radius=RADIUS,
        )
        accent_bar.pack(fill="x", padx=0, pady=(0, 0))

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=PAD, pady=(10, PAD_SM))

        top = ctk.CTkFrame(body, fg_color="transparent")
        top.pack(fill="x")

        ctk.CTkLabel(
            top, text=self.record.icon,
            font=("Segoe UI Emoji", 22), width=32, anchor="w",
        ).pack(side="left")

        ctk.CTkLabel(
            top, text=self.record.title,
            font=(FONT_FAMILY, 13, "bold"),
            text_color=TEXT, anchor="w",
            wraplength=130,
        ).pack(side="left", fill="x", expand=True, padx=(8, 0))

        fav_icon = "⭐" if self.record.is_favorite else "☆"
        fav_btn = ctk.CTkButton(
            top, text=fav_icon, width=30, height=30,
            fg_color="transparent", hover_color=CARD_HOVER,
            font=("Segoe UI Emoji", 16),
            command=lambda: self.on_favorite(self.record),
        )
        fav_btn.pack(side="right")

        cat_info = self.record.category_info
        badge = ctk.CTkLabel(
            body,
            text=f" {cat_info['label']} ",
            font=FONT_SMALL,
            fg_color=self.record.color,
            text_color="#ffffff",
            corner_radius=4,
        )
        badge.pack(anchor="w", pady=(6, 0))

        if self.record.expiry_date:
            self._show_expiry(body)

        ctk.CTkLabel(
            body,
            text=self._format_date(self.record.updated_at),
            font=FONT_SMALL, text_color=TEXT_SUB,
            anchor="w",
        ).pack(anchor="w", pady=(6, 0))

    def _show_expiry(self, parent) -> None:
        try:
            exp = datetime.strptime(self.record.expiry_date, "%Y-%m-%d").date()
            today = date.today()
            delta = (exp - today).days
            if delta < 0:
                color, label = DANGER, f"Истёк {-delta} дн. назад"
            elif delta <= 30:
                color, label = WARNING, f"Истекает через {delta} дн."
            else:
                return
            ctk.CTkLabel(
                parent, text=f"⚠ {label}",
                font=FONT_SMALL, text_color=color, anchor="w",
            ).pack(anchor="w", pady=(4, 0))
        except (ValueError, TypeError):
            pass

    @staticmethod
    def _format_date(dt_str: str) -> str:
        try:
            dt = datetime.fromisoformat(dt_str)
            return f"{dt.day} {dt.strftime('%b %Y')}"
        except Exception:
            return dt_str

    def _on_enter(self, _=None) -> None:
        self.configure(fg_color=CARD_HOVER)

    def _on_leave(self, event=None) -> None:

        try:
            x, y = self.winfo_pointerxy()
            rx, ry = self.winfo_rootx(), self.winfo_rooty()
            if rx <= x < rx + self.winfo_width() and ry <= y < ry + self.winfo_height():
                return
        except Exception:
            pass
        self.configure(fg_color=CARD)

    def _on_click(self, _=None) -> None:
        self.on_click(self.record)

    def _bind_hover(self) -> None:
        self._bind_descendants(self)

    def _bind_descendants(self, widget) -> None:
        widget.bind("<Enter>", self._on_enter, add="+")
        widget.bind("<Leave>", self._on_leave, add="+")
        if isinstance(widget, ctk.CTkButton):
            return
        widget.bind("<Button-1>", self._on_click, add="+")
        for child in widget.winfo_children():
            self._bind_descendants(child)


class RecordsPanel(ctk.CTkFrame):
    COLS = 3

    def __init__(
        self,
        master,
        on_open: Callable[[Record], None],
        on_favorite: Callable[[Record], None],
        **kw,
    ):
        super().__init__(master, fg_color="transparent", **kw)
        self.on_open = on_open
        self.on_favorite = on_favorite
        self._records: list[Record] = []
        self._card_map: dict[int, RecordCard] = {}
        self._grid_frame: ctk.CTkFrame | None = None
        self._build()

    def _build(self) -> None:
        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=BORDER,
            scrollbar_button_hover_color=ACCENT_DIM,
        )
        self._scroll.pack(fill="both", expand=True)

        self._empty_label = ctk.CTkLabel(
            self._scroll, text="Нет записей\nНажмите  +  чтобы добавить",
            font=FONT_SECTION, text_color=TEXT_SUB,
        )

    @staticmethod
    def _record_sig(r: Record) -> tuple:
        return (r.id, r.title, r.category, r.is_favorite, r.expiry_date,
                r.updated_at, r.color, r.icon)

    def load(self, records: list[Record]) -> None:
        old_sigs = [self._record_sig(r) for r in self._records]
        new_sigs = [self._record_sig(r) for r in records]
        if old_sigs == new_sigs:
            return

        self._records = records

        if not records:
            if self._grid_frame is not None:
                self._grid_frame.pack_forget()
            for card in self._card_map.values():
                card.destroy()
            self._card_map.clear()
            self._empty_label.pack(expand=True, pady=80)
            return

        self._empty_label.pack_forget()

        if self._grid_frame is None:
            self._grid_frame = ctk.CTkFrame(self._scroll, fg_color="transparent")
            self._grid_frame.pack(fill="both", expand=True, padx=PAD, pady=PAD)
            for col in range(self.COLS):
                self._grid_frame.columnconfigure(col, weight=1, uniform="col")
        elif not self._grid_frame.winfo_ismapped():
            self._grid_frame.pack(fill="both", expand=True, padx=PAD, pady=PAD)

        new_ids = {r.id for r in records}
        new_sig_map = {r.id: self._record_sig(r) for r in records}

        for rid in list(self._card_map.keys()):
            if rid not in new_ids:
                self._card_map.pop(rid).destroy()

        for idx, record in enumerate(records):
            row, col = divmod(idx, self.COLS)
            existing = self._card_map.get(record.id)

            if existing is not None:
                if self._record_sig(existing.record) != new_sig_map[record.id]:
                    existing.destroy()
                    existing = None

            if existing is None:
                existing = RecordCard(
                    self._grid_frame, record=record,
                    on_click=self.on_open,
                    on_favorite=self.on_favorite,
                )
                self._card_map[record.id] = existing

            existing.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
            self._grid_frame.rowconfigure(row, weight=0)
