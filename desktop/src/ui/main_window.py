from __future__ import annotations
import customtkinter as ctk
import threading
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

    def __init__(self, master: ctk.CTk, app: VaultApp, on_lock: callable,
                 server_mgr=None, **kw):
        super().__init__(master, fg_color=BG, corner_radius=0, **kw)
        self.app = app
        self.on_lock = on_lock
        self._server_mgr = server_mgr
        self._active_category: str = "all"
        self._selected_record: Optional[Record] = None
        self._lock_timer_id: Optional[str] = None
        self._auto_refresh_id: Optional[str] = None
        self._lock_ms: int = _get_lock_ms()
        self._refresh_seq: int = 0
        self._suppress_search: bool = False
        self._records_cache: list = []
        self._build()
        self._fetch_all_records_bg()
        self._reset_lock_timer()
        self._start_auto_refresh()


    def _build(self) -> None:
        self._search_var = ctk.StringVar()
        self._title_label: ctk.CTkLabel | None = None
        self._count_label: ctk.CTkLabel | None = None
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

        self._server_label = ctk.CTkLabel(
            topbar, text="⚫ Сервер выкл.",
            font=FONT_SMALL, text_color=TEXT_SUB,
        )
        self._server_label.pack(side="right", padx=(0, PAD_SM))
        if self._server_mgr is not None:
            self._server_mgr.add_listener(self._on_server_status)

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

    def _on_server_status(self, status: str) -> None:
        """Вызывается из фонового потока при смене статуса сервера."""
        if self._server_mgr is None:
            return
        text, color = self._server_mgr.label_for(status)
        try:
            self.after(0, lambda t=text, c=color: self._server_label.configure(
                text=t, text_color=c
            ))
        except Exception:
            pass

    def _show_filtered(self) -> None:
        """Мгновенно отображает записи из кэша с учётом текущего фильтра — без обращения к БД."""
        if self._records_panel is None:
            return
        q = self._search_var.get().strip()
        if q:
            records = self.app.filter_search(q, self._records_cache)
        else:
            records = self.app.filter_by_category(self._active_category, self._records_cache)
        self._records_panel.load(records)
        if self._count_label:
            self._count_label.configure(text=f"{len(records)} зап." if records else "")
        try:
            expiry = len(self.app.filter_by_category("expiring", self._records_cache))
            self._sidebar.set_expiry_badge(expiry)
        except Exception:
            pass

    def _fetch_all_records_bg(self, after_done=None) -> None:
        """Загружает все записи из БД в кэш в фоновом потоке, затем обновляет UI."""
        if self._records_panel is None:
            return
        self._refresh_seq += 1
        seq = self._refresh_seq

        selected_id = self._selected_record.id if self._selected_record else None
        selected_updated = self._selected_record.updated_at if self._selected_record else None

        def _fetch():
            if seq != self._refresh_seq:
                return
            try:
                all_records = self.app.get_all_records()
            except Exception:
                return

            def _apply():
                if seq != self._refresh_seq:
                    return
                self._records_cache = all_records
                self._show_filtered()
                if selected_id is not None:
                    updated = next((r for r in all_records if r.id == selected_id), None)
                    if updated is None:
                        self._detail.clear()
                        self._selected_record = None
                    elif updated.updated_at != selected_updated:
                        self._selected_record = updated
                        try:
                            data = self.app.decrypt_record(updated)
                            self._detail.show(updated, data)
                        except Exception:
                            pass
                if after_done:
                    after_done()
            self.after(0, _apply)

        threading.Thread(target=_fetch, daemon=True).start()

    def _refresh(self) -> None:
        """Обновить кэш из БД и перерисовать список."""
        self._fetch_all_records_bg()

    def _soft_refresh(self) -> None:
        """Автообновление (таймер) — то же что _refresh, но не сбрасывает деталь."""
        self._fetch_all_records_bg()

    _AUTO_REFRESH_MS = 15000

    def _start_auto_refresh(self) -> None:
        self._schedule_auto_refresh()

    def _schedule_auto_refresh(self) -> None:
        self._auto_refresh_id = self.after(self._AUTO_REFRESH_MS, self._tick_auto_refresh)

    def _tick_auto_refresh(self) -> None:
        self._soft_refresh()
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
        self._suppress_search = True
        self._search_var.set("")
        self._suppress_search = False
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
        self._detail.clear()
        self._selected_record = None
        self._show_filtered()
        self._fetch_all_records_bg()

    def _on_search(self, *_) -> None:
        if self._suppress_search:
            return
        q = self._search_var.get().strip()
        if self._title_label:
            if q:
                self._title_label.configure(text=f"Поиск: {q}")
            else:
                self._on_category(self._active_category)
                return
        self._show_filtered()


    def _on_record_click(self, record: Record) -> None:
        self._reset_lock_timer()
        self._selected_record = record
        self._detail.show_loading()

        def _fetch():
            try:
                data = self.app.decrypt_record(record)
                self.after(0, lambda: self._detail.show(record, data))
            except Exception as e:
                self.after(0, self._detail.clear)
        threading.Thread(target=_fetch, daemon=True).start()

    def _on_favorite(self, record: Record) -> None:
        for r in self._records_cache:
            if r.id == record.id:
                r.is_favorite = not r.is_favorite
                break
        self._show_filtered()

        def _do():
            try:
                self.app.toggle_favorite(record.id)
            except Exception:
                pass
        threading.Thread(target=_do, daemon=True).start()

    def _add_record(self) -> None:
        self._reset_lock_timer()
        RecordDialog(
            self.master,
            on_save=self._save_record,
        )

    def _edit_selected(self) -> None:
        if not self._selected_record:
            return
        record = self._selected_record

        def _fetch():
            try:
                data = self.app.decrypt_record(record)
                attachments = self.app.get_attachments(record.id)
                self.after(0, lambda: RecordDialog(
                    self.master,
                    on_save=self._save_record,
                    record=record,
                    data=data,
                    attachments=attachments,
                ))
            except Exception:
                pass
        threading.Thread(target=_fetch, daemon=True).start()

    def _delete_selected(self) -> None:
        if not self._selected_record:
            return
        confirmed = ask_confirm(
            self.master,
            "Удалить запись",
            f'Вы уверены, что хотите удалить запись\n"{self._selected_record.title}"?\n\nЭто действие нельзя отменить.',
        )
        if confirmed:
            record_to_del = self._selected_record
            self._records_cache = [r for r in self._records_cache if r.id != record_to_del.id]
            self._selected_record = None
            self._detail.clear()
            self._show_filtered()
            def _do():
                try:
                    self.app.delete_record(record_to_del.id)
                    self.after(0, self._fetch_all_records_bg)
                except Exception:
                    pass
            threading.Thread(target=_do, daemon=True).start()

    def _save_record(self, record: Record, data,
                     pending_files: list = None, removed_ids: list = None) -> None:
        def _do():
            try:
                saved = self.app.save_record(record, data)
                for aid in (removed_ids or []):
                    try:
                        self.app.delete_attachment(aid)
                    except Exception:
                        pass
                for pf in (pending_files or []):
                    try:
                        self.app.upload_attachment_bytes(
                            saved.id, pf["name"], pf["data"], pf["mimetype"]
                        )
                    except Exception:
                        pass
                all_records = self.app.get_all_records()
                def _apply():
                    self._records_cache = all_records
                    self._show_filtered()
                    if self._selected_record and self._selected_record.id == saved.id:
                        updated = next((r for r in all_records if r.id == saved.id), None)
                        if updated:
                            self._selected_record = updated
                            try:
                                d = self.app.decrypt_record(updated)
                                self._detail.show(updated, d)
                            except Exception:
                                pass
                self.after(0, _apply)
            except Exception as e:
                self.after(0, lambda: show_error(self.master, "Ошибка сохранения", str(e)))
        threading.Thread(target=_do, daemon=True).start()

    def _show_qr(self) -> None:
        try:
            host = self.app.db._cfg.host
        except Exception:
            host = "localhost"
        _local_hosts = ("localhost", "127.0.0.1", "")
        if host not in _local_hosts:
            qr_url = f"http://{host}:8080"
        else:
            if self._server_mgr is not None and self._server_mgr.status not in ("running", "starting"):
                self._server_mgr.start()
            qr_url = ""
        show_qr_dialog(self.master, port=8080, url=qr_url)


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

        def _do():
            try:
                count = self.app.export_backup(dest)
                self.after(0, lambda: show_info(
                    self.master, "Экспорт завершён",
                    f"Экспортировано {count} зап. в файл:\n{dest}",
                ))
            except Exception as e:
                self.after(0, lambda: show_error(self.master, "Ошибка экспорта", str(e)))
        threading.Thread(target=_do, daemon=True).start()

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

        def _do():
            try:
                count = self.app.import_backup(src, replace=replace)
                self.after(0, lambda: show_info(
                    self.master, "Импорт завершён",
                    f"Импортировано {count} зап. из файла:\n{src}",
                ))
                self.after(0, self._refresh)
            except Exception as e:
                self.after(0, lambda: show_error(self.master, "Ошибка импорта", str(e)))
        threading.Thread(target=_do, daemon=True).start()

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
