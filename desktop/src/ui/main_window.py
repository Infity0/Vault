from __future__ import annotations
import customtkinter as ctk
from typing import Optional

from src.ui.app import VaultApp
from src.core.models import Record, CATEGORIES
from src.ui.components.sidebar import Sidebar
from src.ui.components.records_panel import RecordsPanel
from src.ui.components.record_dialog import RecordDialog
from src.ui.components.detail_panel import DetailPanel
from src.ui.components.settings_dialog import SettingsDialog
from src.ui.components.message_dialog import show_error, show_info, ask_confirm
from src.ui.components.qr_dialog import show_qr_dialog
from src.utils.constants import *
from src.ui.components.settings_dialog import load_lock_timeout

_get_lock_ms = load_lock_timeout


class MainWindow(ctk.CTkFrame):

    def __init__(self, master: ctk.CTk, app: VaultApp, on_lock: callable, **kw):
        super().__init__(master, fg_color=BG, corner_radius=0, **kw)
        self.app = app
        self.on_lock = on_lock
        self._active_category: str = "all"
        self._selected_record: Optional[Record] = None
        self._lock_timer_id: Optional[str] = None
        self._auto_refresh_id: Optional[str] = None
        self._lock_ms: int = _get_lock_ms()
        self._build()
        self._refresh()
        self._reset_lock_timer()
        self._start_auto_refresh()


    def _build(self) -> None:
        self._search_var = ctk.StringVar()
        self._title_label: ctk.CTkLabel | None = None
        self._count_label: ctk.CTkLabel | None = None
        self._backend_label: ctk.CTkLabel | None = None
        self._records_panel: RecordsPanel | None = None
        self._detail: DetailPanel | None = None

        self._sidebar = Sidebar(
            self,
            on_select=self._on_category,
            on_lock=self._lock,
            on_settings=self._open_settings,
            on_qr=self._show_qr,
            on_export=self._export_backup,
            on_import=self._import_backup,
        )
        self._sidebar.pack(side="left", fill="y")

        right = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        right.pack(side="left", fill="both", expand=True)

        topbar = ctk.CTkFrame(right, fg_color=SURFACE, height=52, corner_radius=0)
        topbar.pack(fill="x")
        topbar.pack_propagate(False)

        self._search_var.trace_add("write", self._on_search)
        search = ctk.CTkEntry(
            topbar,
            textvariable=self._search_var,
            placeholder_text="🔍  Поиск по хранилищу…",
            height=36, font=FONT_BODY,
            fg_color=CARD, border_color=BORDER,
            text_color=TEXT,
            width=320,
        )
        search.pack(side="left", padx=PAD, pady=8)

        self._title_label = ctk.CTkLabel(
            topbar, text="Все записи",
            font=(FONT_FAMILY, 14, "bold"), text_color=TEXT,
        )
        self._title_label.pack(side="left", padx=(0, PAD))

        add_btn = ctk.CTkButton(
            topbar,
            text="  +  Добавить  ",
            height=36, font=(FONT_FAMILY, 13, "bold"),
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            corner_radius=RADIUS_SM,
            command=self._add_record,
        )
        add_btn.pack(side="right", padx=PAD, pady=8)

        self._count_label = ctk.CTkLabel(
            topbar, text="", font=FONT_SMALL, text_color=TEXT_SUB,
        )
        self._count_label.pack(side="right", padx=(0, PAD_SM))

        self._backend_label = ctk.CTkLabel(
            topbar,
            text=f"🗄 {self.app.backend_name}",
            font=FONT_SMALL, text_color=TEXT_SUB,
        )
        self._backend_label.pack(side="right", padx=(0, PAD_SM))

        content = ctk.CTkFrame(right, fg_color=BG, corner_radius=0)
        content.pack(fill="both", expand=True)

        self._records_panel = RecordsPanel(
            content,
            on_open=self._on_record_click,
            on_favorite=self._on_favorite,
        )
        self._records_panel.pack(side="left", fill="both", expand=True)

        ctk.CTkFrame(content, fg_color=BORDER, width=1, corner_radius=0).pack(
            side="left", fill="y"
        )

        self._detail = DetailPanel(
            content,
            on_edit=self._edit_selected,
            on_delete=self._delete_selected,
            app=self.app,
            width=300,
        )
        self._detail.pack(side="left", fill="y")

        self.master.bind("<Control-n>", lambda _: self._add_record())
        self.master.bind("<Control-f>", lambda _: search.focus_set())
        self.master.bind("<Motion>", lambda _: self._reset_lock_timer(), add="+")
        self.master.bind("<KeyPress>", lambda _: self._reset_lock_timer(), add="+")


    def _refresh(self, search_query: str = "") -> None:
        if self._records_panel is None or self._detail is None:
            return
        if search_query:
            records = self.app.search_records(search_query)
        else:
            records = self.app.get_records_by_category(self._active_category)

        self._records_panel.load(records)
        if self._count_label:
            self._count_label.configure(text=f"{len(records)} зап.")
        self._detail.clear()
        self._selected_record = None

        try:
            expiry_count = self.app.count_expiring()
            self._sidebar.set_expiry_badge(expiry_count)
        except Exception:
            pass

    def _soft_refresh(self) -> None:
        if self._records_panel is None or self._detail is None:
            return
        q = self._search_var.get().strip()
        try:
            if q:
                records = self.app.search_records(q)
            else:
                records = self.app.get_records_by_category(self._active_category)
        except Exception:
            return

        self._records_panel.load(records)
        if self._count_label:
            self._count_label.configure(text=f"{len(records)} зап.")

        try:
            self._sidebar.set_expiry_badge(self.app.count_expiring())
        except Exception:
            pass

        if self._selected_record is not None:
            updated = next((r for r in records if r.id == self._selected_record.id), None)
            if updated is None:
                self._detail.clear()
                self._selected_record = None
            elif updated.updated_at != self._selected_record.updated_at:
                self._selected_record = updated
                try:
                    data = self.app.decrypt_record(updated)
                    self._detail.show(updated, data)
                except Exception:
                    pass


    _AUTO_REFRESH_MS = 3000

    def _start_auto_refresh(self) -> None:
        self._schedule_auto_refresh()

    def _schedule_auto_refresh(self) -> None:
        self._auto_refresh_id = self.after(self._AUTO_REFRESH_MS, self._tick_auto_refresh)

    def _tick_auto_refresh(self) -> None:
        try:
            self._soft_refresh()
        except Exception:
            pass
        try:
            self._schedule_auto_refresh()
        except Exception:
            pass

    def destroy(self) -> None:
        if self._auto_refresh_id:
            try:
                self.after_cancel(self._auto_refresh_id)
            except Exception:
                pass
        if self._lock_timer_id:
            try:
                self.after_cancel(self._lock_timer_id)
            except Exception:
                pass
        super().destroy()

    def _on_category(self, key: str) -> None:
        self._active_category = key
        self._search_var.set("")
        if key == "all":
            label = "Все записи"
        elif key == "favorites":
            label = "Избранное"
        elif key == "expiring":
            label = "Истекают скоро"
        else:
            label = CATEGORIES.get(key, {}).get("label", key)
        if self._title_label:
            self._title_label.configure(text=label)
        self._refresh()

    def _on_search(self, *_) -> None:
        q = self._search_var.get().strip()
        if self._title_label:
            if q:
                self._title_label.configure(text=f"Поиск: {q}")
            else:
                self._on_category(self._active_category)
                return
        self._refresh(search_query=q)


    def _on_record_click(self, record: Record) -> None:
        self._reset_lock_timer()
        self._selected_record = record
        data = self.app.decrypt_record(record)
        self._detail.show(record, data)

    def _on_favorite(self, record: Record) -> None:
        self.app.toggle_favorite(record.id)
        self._refresh(self._search_var.get().strip())

    def _add_record(self) -> None:
        self._reset_lock_timer()
        RecordDialog(
            self.master,
            on_save=self._save_record,
        )

    def _edit_selected(self) -> None:
        if not self._selected_record:
            return
        data = self.app.decrypt_record(self._selected_record)
        RecordDialog(
            self.master,
            on_save=self._save_record,
            record=self._selected_record,
            data=data,
        )

    def _delete_selected(self) -> None:
        if not self._selected_record:
            return
        confirmed = ask_confirm(
            self.master,
            "Удалить запись",
            f'Вы уверены, что хотите удалить запись\n"{self._selected_record.title}"?\n\nЭто действие нельзя отменить.',
        )
        if confirmed:
            self.app.delete_record(self._selected_record.id)
            self._selected_record = None
            self._refresh()

    def _save_record(self, record: Record, data) -> None:
        try:
            self.app.save_record(record, data)
            self._refresh(self._search_var.get().strip())
        except Exception as e:
            show_error(self.master, "Ошибка сохранения", str(e))

    def _show_qr(self) -> None:
        show_qr_dialog(self.master, port=8080)


    def _export_backup(self) -> None:
        import tkinter.filedialog as fd

        dest = fd.asksaveasfilename(
            title="Экспорт данных",
            defaultextension=".vaultbak",
            filetypes=[("Vault Backup", "*.vaultbak"), ("All files", "*.*")],
            initialfile=f"vault_backup_{self.app.current_username}.vaultbak",
        )
        if not dest:
            return

        try:
            count = self.app.export_backup(dest)
            show_info(
                self.master,
                "Экспорт завершён",
                f"Экспортировано {count} зап. в файл:\n{dest}",
            )
        except Exception as e:
            show_error(self.master, "Ошибка экспорта", str(e))

    def _import_backup(self) -> None:
        import tkinter.filedialog as fd

        src = fd.askopenfilename(
            title="Импорт данных",
            filetypes=[("Vault Backup", "*.vaultbak"), ("All files", "*.*")],
        )
        if not src:
            return

        replace = ask_confirm(
            self.master,
            "Режим импорта",
            "Заменить существующие записи?\n\n"
            "«Да» — удалить все текущие записи и импортировать из файла.\n"
            "«Нет» — добавить поверх существующих.",
        )

        try:
            count = self.app.import_backup(src, replace=replace)
            show_info(
                self.master,
                "Импорт завершён",
                f"Импортировано {count} зап. из файла:\n{src}",
            )
            self._refresh()
        except Exception as e:
            show_error(self.master, "Ошибка импорта", str(e))

    def _open_settings(self) -> None:
        def on_apply(backend: str, mysql_cfg) -> None:
            try:
                self.app.switch_backend(mysql_cfg)
                self.after(150, self._lock)
            except Exception as e:
                show_error(
                    self.master,
                    "Ошибка подключения",
                    f"Не удалось переключить базу данных:\n{e}\n\nОставлен текущий бэкенд.",
                )

        SettingsDialog(self.master, on_apply=on_apply)


    def _reset_lock_timer(self) -> None:
        if self._lock_timer_id:
            self.after_cancel(self._lock_timer_id)
            self._lock_timer_id = None
        if self._lock_ms > 0:
            self._lock_timer_id = self.after(self._lock_ms, self._lock)

    def _lock(self) -> None:
        if self._lock_timer_id:
            self.after_cancel(self._lock_timer_id)
        self.on_lock()
