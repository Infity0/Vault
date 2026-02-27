from __future__ import annotations
import customtkinter as ctk
from typing import Callable, Optional

from src.utils.constants import *


class LoginFrame(ctk.CTkFrame):

    def __init__(
        self,
        master,
        accounts: list[dict],
        on_unlock: Callable[[str, str], bool],
        on_create: Callable[[str, str], Optional[str]],
    ):
        super().__init__(master, fg_color=BG, corner_radius=0)
        self._accounts = accounts
        self._on_unlock = on_unlock
        self._on_create = on_create
        self._panel: ctk.CTkFrame | None = None
        self._focus_after_id = None   # ID pending after() для фокуса

        if accounts:
            self._show_picker()
        else:
            self._show_create()

    # ==================================================================
    # Утилиты
    # ==================================================================

    def _replace(self, new_panel: ctk.CTkFrame) -> None:
        # Отменяем pending focus-after чтобы не стрелять по уничтоженным виджетам
        if self._panel and self._panel.winfo_exists():
            self._panel.destroy()
        self._panel = new_panel
        new_panel.pack(expand=True)

    def _schedule_focus(self, widget) -> None:
        pass  # temporarily disabled

    def _make_panel(self, width: int = 360) -> ctk.CTkFrame:
        p = ctk.CTkFrame(self, fg_color="transparent", width=width)
        return p

    # ==================================================================
    # Панель 1 — выбор аккаунта
    # ==================================================================

    def _show_picker(self) -> None:
        p = self._make_panel(360)

        ctk.CTkLabel(p, text="🔐", font=("Segoe UI Emoji", 52)).pack(pady=(0, 6))
        ctk.CTkLabel(
            p, text="Vault",
            font=(FONT_FAMILY, 24, "bold"), text_color=TEXT,
        ).pack()
        ctk.CTkLabel(
            p, text="Выберите аккаунт для входа",
            font=FONT_SMALL, text_color=TEXT_SUB,
        ).pack(pady=(4, 16))

        # Список аккаунтов — обычный Frame, без CTkScrollableFrame
        list_box = ctk.CTkFrame(p, fg_color=SURFACE, corner_radius=RADIUS, width=340)
        list_box.pack(fill="x", pady=(0, 4))
        list_box.pack_propagate(False)
        list_h = min(len(self._accounts), 5) * 56 + 8
        list_box.configure(height=list_h)

        for acc in self._accounts:
            username = acc["username"]
            ctk.CTkButton(
                list_box,
                text=f"👤  {username}",
                anchor="w",
                font=FONT_BODY,
                height=48,
                fg_color="transparent",
                hover_color=CARD_HOVER,
                text_color=TEXT,
                corner_radius=RADIUS_SM,
                command=lambda u=username: self._show_unlock(u),
            ).pack(fill="x", padx=4, pady=2)

        ctk.CTkFrame(p, height=1, fg_color=BORDER).pack(fill="x", pady=14)

        # Кнопка нового аккаунта
        ctk.CTkButton(
            p,
            text="＋  Создать новый аккаунт",
            height=44,
            font=FONT_BODY,
            fg_color=ACCENT_DIM,
            hover_color=ACCENT,
            text_color=TEXT,
            corner_radius=RADIUS_SM,
            command=self._show_create,
        ).pack(fill="x")

        self._replace(p)

    # ==================================================================
    # Панель 2 — ввод пароля
    # ==================================================================

    def _show_unlock(self, username: str) -> None:
        p = self._make_panel(360)
        err_var = ctk.StringVar(value="")

        ctk.CTkLabel(p, text="🔐", font=("Segoe UI Emoji", 52)).pack(pady=(0, 6))
        ctk.CTkLabel(
            p, text=username,
            font=(FONT_FAMILY, 20, "bold"), text_color=TEXT,
        ).pack()
        ctk.CTkLabel(
            p, text="Введите мастер-пароль",
            font=FONT_SMALL, text_color=TEXT_SUB,
        ).pack(pady=(4, 20))

        form = ctk.CTkFrame(p, fg_color="transparent", width=340)
        form.pack(fill="x")

        ctk.CTkLabel(
            form, text="Мастер-пароль",
            font=FONT_BODY, text_color=TEXT_SUB, anchor="w",
        ).pack(fill="x")

        pw_row = ctk.CTkFrame(form, fg_color="transparent")
        pw_row.pack(fill="x", pady=(4, 8))

        pw_var = ctk.StringVar()
        show_pw = {"v": False}
        pw_entry = ctk.CTkEntry(
            pw_row, textvariable=pw_var,
            show="•", height=44, font=FONT_BODY,
            fg_color=SURFACE, border_color=BORDER,
            text_color=TEXT, placeholder_text="••••••••",
        )
        pw_entry.pack(side="left", fill="x", expand=True)

        def toggle():
            show_pw["v"] = not show_pw["v"]
            pw_entry.configure(show="" if show_pw["v"] else "•")

        ctk.CTkButton(
            pw_row, text="👁", width=44, height=44,
            fg_color=SURFACE, hover_color=CARD_HOVER,
            text_color=TEXT_SUB, corner_radius=RADIUS_SM,
            command=toggle,
        ).pack(side="left", padx=(4, 0))

        ctk.CTkLabel(
            form, textvariable=err_var,
            font=FONT_SMALL, text_color=DANGER,
            wraplength=320, anchor="w",
        ).pack(fill="x", pady=(0, 6))

        btn = ctk.CTkButton(
            form, text="Войти", height=46,
            font=(FONT_FAMILY, 13, "bold"),
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            corner_radius=RADIUS_SM,
        )
        btn.pack(fill="x")

        def submit():
            pw = pw_var.get()
            if not pw:
                err_var.set("Введите пароль.")
                return
            err_var.set("")
            btn.configure(state="disabled", text="Загрузка…")

            def do():
                ok = self._on_unlock(username, pw)
                if not ok:
                    err_var.set("Неверный пароль. Попробуйте снова.")
                    btn.configure(state="normal", text="Войти")

            self.after(80, do)

        btn.configure(command=submit)
        pw_entry.bind("<Return>", lambda _: submit())

        # Кнопка назад
        ctk.CTkButton(
            p, text="← Назад",
            height=36, font=FONT_SMALL,
            fg_color="transparent", hover_color=CARD_HOVER,
            text_color=TEXT_SUB, corner_radius=RADIUS_SM,
            command=self._show_picker,
        ).pack(pady=(12, 0))

        self._replace(p)
        self._schedule_focus(pw_entry)

    # ==================================================================
    # Панель 3 — создание аккаунта
    # ==================================================================

    def _show_create(self) -> None:
        p = self._make_panel(360)
        err_var = ctk.StringVar(value="")

        ctk.CTkLabel(p, text="🔐", font=("Segoe UI Emoji", 52)).pack(pady=(0, 6))
        ctk.CTkLabel(
            p, text="Новый аккаунт",
            font=(FONT_FAMILY, 22, "bold"), text_color=TEXT,
        ).pack()
        ctk.CTkLabel(
            p, text="Придумайте имя и надёжный пароль",
            font=FONT_SMALL, text_color=TEXT_SUB,
        ).pack(pady=(4, 20))

        form = ctk.CTkFrame(p, fg_color="transparent", width=340)
        form.pack(fill="x")

        # Имя пользователя
        ctk.CTkLabel(
            form, text="Имя аккаунта",
            font=FONT_BODY, text_color=TEXT_SUB, anchor="w",
        ).pack(fill="x")
        name_var = ctk.StringVar()
        name_entry = ctk.CTkEntry(
            form, textvariable=name_var,
            height=44, font=FONT_BODY,
            fg_color=SURFACE, border_color=BORDER,
            text_color=TEXT, placeholder_text="Например: Иван",
        )
        name_entry.pack(fill="x", pady=(4, 12))

        # Пароль
        ctk.CTkLabel(
            form, text="Мастер-пароль",
            font=FONT_BODY, text_color=TEXT_SUB, anchor="w",
        ).pack(fill="x")
        pw_row = ctk.CTkFrame(form, fg_color="transparent")
        pw_row.pack(fill="x", pady=(4, 12))
        pw_var = ctk.StringVar()
        show_pw = {"v": False}
        pw_entry = ctk.CTkEntry(
            pw_row, textvariable=pw_var,
            show="•", height=44, font=FONT_BODY,
            fg_color=SURFACE, border_color=BORDER,
            text_color=TEXT, placeholder_text="••••••••",
        )
        pw_entry.pack(side="left", fill="x", expand=True)

        def toggle():
            show_pw["v"] = not show_pw["v"]
            pw_entry.configure(show="" if show_pw["v"] else "•")
            confirm_entry.configure(show="" if show_pw["v"] else "•")

        ctk.CTkButton(
            pw_row, text="👁", width=44, height=44,
            fg_color=SURFACE, hover_color=CARD_HOVER,
            text_color=TEXT_SUB, corner_radius=RADIUS_SM,
            command=toggle,
        ).pack(side="left", padx=(4, 0))

        # Подтверждение пароля
        ctk.CTkLabel(
            form, text="Подтвердите пароль",
            font=FONT_BODY, text_color=TEXT_SUB, anchor="w",
        ).pack(fill="x")
        confirm_var = ctk.StringVar()
        confirm_entry = ctk.CTkEntry(
            form, textvariable=confirm_var,
            show="•", height=44, font=FONT_BODY,
            fg_color=SURFACE, border_color=BORDER,
            text_color=TEXT, placeholder_text="••••••••",
        )
        confirm_entry.pack(fill="x", pady=(4, 8))

        ctk.CTkLabel(
            form, textvariable=err_var,
            font=FONT_SMALL, text_color=DANGER,
            wraplength=320, anchor="w",
        ).pack(fill="x", pady=(0, 6))

        btn = ctk.CTkButton(
            form, text="Создать аккаунт", height=46,
            font=(FONT_FAMILY, 13, "bold"),
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            corner_radius=RADIUS_SM,
        )
        btn.pack(fill="x")

        ctk.CTkLabel(
            p, text="⚠  Пароль нельзя восстановить. Запомните его.",
            font=FONT_SMALL, text_color=WARNING, wraplength=320,
        ).pack(pady=(12, 0))

        def submit():
            name = name_var.get().strip()
            pw = pw_var.get()
            confirm = confirm_var.get()
            if not name:
                err_var.set("Введите имя аккаунта.")
                return
            if len(name) > 64:
                err_var.set("Имя не должно превышать 64 символа.")
                return
            if not pw:
                err_var.set("Введите пароль.")
                return
            if len(pw) < 6:
                err_var.set("Минимум 6 символов.")
                return
            if pw != confirm:
                err_var.set("Пароли не совпадают.")
                return
            err_var.set("")
            btn.configure(state="disabled", text="Создание…")

            def do():
                result = self._on_create(name, pw)
                if result:  # строка = ошибка
                    err_var.set(result)
                    btn.configure(state="normal", text="Создать аккаунт")

            self.after(80, do)

        btn.configure(command=submit)
        confirm_entry.bind("<Return>", lambda _: submit())
        name_entry.bind("<Return>", lambda _: pw_entry.focus())
        pw_entry.bind("<Return>", lambda _: confirm_entry.focus())

        # Кнопка назад (если аккаунты уже есть)
        if self._accounts:
            ctk.CTkButton(
                p, text="← Назад",
                height=36, font=FONT_SMALL,
                fg_color="transparent", hover_color=CARD_HOVER,
                text_color=TEXT_SUB, corner_radius=RADIUS_SM,
                command=self._show_picker,
            ).pack(pady=(10, 0))

        self._replace(p)
        self._schedule_focus(name_entry)


