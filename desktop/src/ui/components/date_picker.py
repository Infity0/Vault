from __future__ import annotations
import calendar
from datetime import date
from typing import Callable, Optional

import customtkinter as ctk
from src.utils.constants import *


class DatePickerDialog(ctk.CTkToplevel):

    _ДНИ = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    _МЕСЯЦЫ = [
        "", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
        "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь",
    ]

    _DAY_NAMES   = _ДНИ
    _MONTH_NAMES = _МЕСЯЦЫ

    def __init__(
        self,
        master,
        on_select: Callable[[Optional[str]], None],
        initial: Optional[str] = None,
        parent_dialog=None,
        **kw,
    ):
        super().__init__(master, **kw)
        self.on_select = on_select
        self._parent_dialog = parent_dialog
        self._poll_id: Optional[str] = None
        self._click_bind_dlg: Optional[str] = None
        self._click_bind_root: Optional[str] = None

        self.overrideredirect(True)
        self.configure(fg_color=SURFACE)
        self.resizable(False, False)
        self.wm_attributes("-topmost", True)

        today = date.today()
        if initial:
            try:
                parts = initial.split("-")
                today = date(int(parts[0]), int(parts[1]), int(parts[2]))
            except Exception:
                pass
        self._selected: Optional[date] = None if not initial else today
        self._year = today.year
        self._month = today.month
        self._day_btns: list[ctk.CTkButton] = []

        self._build()
        self._render_days()
        self.update_idletasks()

        cal_w = self.winfo_reqwidth()
        cal_h = self.winfo_reqheight()
        sw    = self.winfo_screenwidth()
        sh    = self.winfo_screenheight()

        btn_x = master.winfo_rootx()
        btn_y = master.winfo_rooty()
        btn_h = master.winfo_height()

        self._geometry(btn_x, btn_y, btn_h, cal_w, cal_h, sw, sh)
        self.lift()
        self.focus_force()

        self._master_ref = master
        self._cal_w = cal_w
        self._cal_h = cal_h
        self._last_btn_x: int = btn_x
        self._last_btn_y: int = btn_y
        self._btn_h: int = btn_h
        self._poll_id = self.after(50, self._опрос_позиции)

        if parent_dialog is not None:
            self._click_bind_dlg = parent_dialog.bind(
                "<ButtonPress-1>", self._при_клике_снаружи, add="+"
            )
        root_win = self.winfo_toplevel()
        self._click_bind_root = root_win.bind(
            "<ButtonPress-1>", self._при_клике_снаружи, add="+"
        )
        self._root_ref = root_win

        self.bind("<Escape>", lambda _: self._закрыть())




    def _build(self) -> None:
        outer = ctk.CTkFrame(
            self, fg_color=SURFACE, corner_radius=RADIUS,
            border_width=1, border_color=BORDER,
        )
        outer.pack(padx=2, pady=2)

        nav = ctk.CTkFrame(outer, fg_color="transparent")
        nav.pack(fill="x", padx=PAD_SM, pady=(PAD_SM, 0))

        btn_kw = dict(
            width=32, height=32, fg_color="transparent",
            hover_color=CARD_HOVER, text_color=TEXT,
            corner_radius=RADIUS_SM, font=FONT_BODY,
        )
        ctk.CTkButton(nav, text="‹‹", command=self._пред_год,   **btn_kw).pack(side="left")
        ctk.CTkButton(nav, text="‹",  command=self._пред_месяц, **btn_kw).pack(side="left")
        ctk.CTkButton(nav, text="›",  command=self._след_месяц, **btn_kw).pack(side="right")
        ctk.CTkButton(nav, text="››", command=self._след_год,   **btn_kw).pack(side="right")

        self._header_var = ctk.StringVar()
        ctk.CTkLabel(
            nav, textvariable=self._header_var,
            font=(FONT_FAMILY, 13, "bold"), text_color=TEXT,
        ).pack(expand=True)

        days_row = ctk.CTkFrame(outer, fg_color="transparent")
        days_row.pack(padx=PAD_SM, pady=(PAD_SM // 2, 0))
        for i, d in enumerate(self._ДНИ):
            color = DANGER if i >= 5 else TEXT_SUB
            ctk.CTkLabel(
                days_row, text=d, width=36, height=24,
                font=(FONT_FAMILY, 10, "bold"), text_color=color,
            ).grid(row=0, column=i)

        self._grid_frame = ctk.CTkFrame(outer, fg_color="transparent")
        self._grid_frame.pack(padx=PAD_SM, pady=(2, PAD_SM // 2))

        for i in range(42):
            btn = ctk.CTkButton(
                self._grid_frame, text="", width=36, height=32,
                fg_color="transparent", hover_color=CARD_HOVER,
                text_color=TEXT, corner_radius=RADIUS_SM,
                font=FONT_BODY, command=lambda idx=i: self._выбор_дня(idx),
            )
            btn.grid(row=i // 7, column=i % 7, padx=1, pady=1)
            self._day_btns.append(btn)

        footer = ctk.CTkFrame(outer, fg_color="transparent")
        footer.pack(fill="x", padx=PAD_SM, pady=(0, PAD_SM))
        ctk.CTkButton(
            footer, text="✕  Очистить дату", height=30,
            fg_color="transparent", text_color=TEXT_SUB,
            hover_color=CARD_HOVER, corner_radius=RADIUS_SM,
            font=FONT_SMALL, command=self._очистить,
        ).pack(side="left")
        ctk.CTkButton(
            footer, text="Сегодня", height=30,
            fg_color="transparent", text_color=ACCENT,
            hover_color=CARD_HOVER, corner_radius=RADIUS_SM,
            font=FONT_SMALL, command=self._сегодня,
        ).pack(side="right")

    def _render_days(self) -> None:
        self._header_var.set(f"{self._МЕСЯЦЫ[self._month]}  {self._year}")
        cal   = calendar.monthcalendar(self._year, self._month)
        today = date.today()

        flat: list[int] = [d for week in cal for d in week]

        for i, btn in enumerate(self._day_btns):
            day_num = flat[i] if i < len(flat) else 0
            if day_num == 0:
                btn.configure(text="", state="disabled",
                              fg_color="transparent", text_color=TEXT_SUB)
                continue

            d          = date(self._year, self._month, day_num)
            is_sel     = (self._selected == d)
            is_today   = (d == today)
            is_weekend = (i % 7 >= 5)

            if is_sel:
                fg, tc = ACCENT, "#ffffff"
            elif is_today:
                fg, tc = CARD, ACCENT
            else:
                fg = "transparent"
                tc = DANGER if is_weekend else TEXT

            btn.configure(
                text=str(day_num), state="normal",
                fg_color=fg, text_color=tc, hover_color=CARD_HOVER,
            )




    def _выбор_дня(self, idx: int) -> None:
        flat = [d for week in calendar.monthcalendar(self._year, self._month) for d in week]
        if idx >= len(flat) or flat[idx] == 0:
            return
        d = date(self._year, self._month, flat[idx])
        self._selected = d
        self.on_select(f"{d.year}-{d.month:02d}-{d.day:02d}")
        self._закрыть()

    def _очистить(self) -> None:
        self.on_select(None)
        self._закрыть()

    def _сегодня(self) -> None:
        today = date.today()
        self._year, self._month, self._selected = today.year, today.month, today
        self._render_days()
        self.on_select(f"{today.year}-{today.month:02d}-{today.day:02d}")
        self._закрыть()

    def _пред_месяц(self) -> None:
        self._month -= 1
        if self._month < 1:
            self._month, self._year = 12, self._year - 1
        self._render_days()

    def _след_месяц(self) -> None:
        self._month += 1
        if self._month > 12:
            self._month, self._year = 1, self._year + 1
        self._render_days()

    def _пред_год(self) -> None:
        self._year -= 1
        self._render_days()

    def _след_год(self) -> None:
        self._year += 1
        self._render_days()




    def _geometry(self, bx: int, by: int, bh: int, cw: int, ch: int, sw: int, sh: int) -> None:
        cx = bx
        cy = by + bh + 4
        if cx + cw > sw:
            cx = sw - cw - 4
        if cy + ch > sh:
            cy = by - ch - 4
        self.geometry(f"+{cx}+{cy}")

    def _опрос_позиции(self) -> None:
        try:
            if not self.winfo_exists():
                return
            new_x = self._master_ref.winfo_rootx()
            new_y = self._master_ref.winfo_rooty()
            if new_x != self._last_btn_x or new_y != self._last_btn_y:
                sw = self.winfo_screenwidth()
                sh = self.winfo_screenheight()
                self._geometry(new_x, new_y, self._btn_h,
                               self._cal_w, self._cal_h, sw, sh)
                self._last_btn_x = new_x
                self._last_btn_y = new_y
            self._poll_id = self.after(50, self._опрос_позиции)
        except Exception:
            pass

    def _при_клике_снаружи(self, event) -> None:
        try:
            cx, cy = self.winfo_rootx(), self.winfo_rooty()
            cw, ch = self.winfo_width(), self.winfo_height()
            if cx <= event.x_root <= cx + cw and cy <= event.y_root <= cy + ch:
                return
            self._закрыть()
        except Exception:
            pass

    def _закрыть(self) -> None:
        try:
            if self._poll_id:
                self.after_cancel(self._poll_id)
                self._poll_id = None
        except Exception:
            pass
        try:
            if self._parent_dialog and self._click_bind_dlg:
                self._parent_dialog.unbind("<ButtonPress-1>", self._click_bind_dlg)
        except Exception:
            pass
        try:
            if self._click_bind_root:
                self._root_ref.unbind("<ButtonPress-1>", self._click_bind_root)
        except Exception:
            pass
        try:
            self.destroy()
        except Exception:
            pass

    def _cancel(self) -> None:
        self._закрыть()

    def _close(self) -> None:
        self._закрыть()
