from __future__ import annotations
import tkinter as tk
import customtkinter as ctk
from typing import TYPE_CHECKING, Callable, Optional

from src.core.models import Record, RecordData, CATEGORIES
from src.utils.constants import *

if TYPE_CHECKING:
    from src.ui.app import VaultApp


def _show_image_preview(parent, title: str, data_bytes: bytes) -> None:
    try:
        from PIL import Image, ImageTk
        import io
        img = Image.open(io.BytesIO(data_bytes))

        max_w, max_h = 900, 700
        img.thumbnail((max_w, max_h), Image.LANCZOS)

        win = ctk.CTkToplevel(parent)
        win.title(title)
        win.resizable(True, True)
        win.grab_set()

        photo = ImageTk.PhotoImage(img)
        lbl = tk.Label(win, image=photo, bg="#1a1a2e")
        lbl.image = photo
        lbl.pack(padx=8, pady=8)

        ctk.CTkButton(
            win, text="Закрыть", width=100,
            command=win.destroy,
        ).pack(pady=(0, 8))

        win.update_idletasks()
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        ww = win.winfo_width()
        wh = win.winfo_height()
        win.geometry(f"+{(sw - ww) // 2}+{(sh - wh) // 2}")
    except Exception as e:
        import tkinter.messagebox as mb
        mb.showerror("Ошибка просмотра", str(e))


class _ToolTip:
    def __init__(self, widget, text: str):
        self._widget = widget
        self._text = text
        self._win: tk.Toplevel | None = None
        widget.bind("<Enter>", self._show, add="+")
        widget.bind("<Leave>", self._hide, add="+")

    def _show(self, _=None) -> None:
        try:
            x = self._widget.winfo_rootx() + self._widget.winfo_width() // 2 - 30
            y = self._widget.winfo_rooty() - 28
            self._win = tk.Toplevel(self._widget)
            self._win.wm_overrideredirect(True)
            self._win.wm_geometry(f"+{x}+{y}")
            tk.Label(
                self._win, text=self._text,
                background="#2a2a40", foreground="#f0f0f8",
                relief="flat", padx=6, pady=3,
                font=("Segoe UI", 9),
            ).pack()
        except Exception:
            pass

    def _hide(self, _=None) -> None:
        if self._win:
            try:
                self._win.destroy()
            except Exception:
                pass
            self._win = None


class DetailPanel(ctk.CTkFrame):
    def __init__(
        self, master,
        on_edit: Callable,
        on_delete: Callable,
        app: "Optional[VaultApp]" = None,
        **kw,
    ):
        super().__init__(master, fg_color=SURFACE, corner_radius=0, **kw)
        self.on_edit = on_edit
        self.on_delete = on_delete
        self._app = app
        self._record: Optional[Record] = None
        self._data: Optional[RecordData] = None
        self._hidden: dict[str, bool] = {}
        self._value_labels: dict[str, ctk.CTkLabel] = {}
        self._scroll: Optional[ctk.CTkScrollableFrame] = None
        self._build_empty()


    def _build_empty(self) -> None:
        self._empty = ctk.CTkLabel(
            self,
            text="Выберите запись\nдля просмотра",
            font=FONT_SECTION, text_color=TEXT_SUB,
        )
        self._empty.pack(expand=True)

    def show(self, record: Record, data: RecordData) -> None:
        self._record = record
        self._data = data
        self._hidden = {}
        self._value_labels = {}
        for w in self.winfo_children():
            w.destroy()
        self._render()

    def clear(self) -> None:
        for w in self.winfo_children():
            w.destroy()
        self._build_empty()


    def _render(self) -> None:
        r = self._record
        d = self._data

        hdr = ctk.CTkFrame(self, fg_color=r.color, height=6, corner_radius=0)
        hdr.pack(fill="x")

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=PAD, pady=(PAD, 0))

        ctk.CTkLabel(
            top, text=r.icon, font=("Segoe UI Emoji", 30),
        ).pack(side="left")
        ctk.CTkLabel(
            top, text=r.title,
            font=(FONT_FAMILY, 16, "bold"),
            text_color=TEXT, anchor="w", wraplength=200,
        ).pack(side="left", padx=(PAD_SM, 0), fill="x", expand=True)

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.pack(fill="x", padx=PAD, pady=(PAD_SM, 0))

        ctk.CTkButton(
            btn_row, text="✏️  Изменить", height=34,
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            corner_radius=RADIUS_SM, font=FONT_BODY,
            command=self.on_edit,
        ).pack(side="left")
        ctk.CTkButton(
            btn_row, text="🗑  Удалить", height=34,
            fg_color="transparent", text_color=DANGER,
            hover_color=CARD_HOVER, border_color=DANGER,
            border_width=1, corner_radius=RADIUS_SM, font=FONT_BODY,
            command=self.on_delete,
        ).pack(side="left", padx=(PAD_SM, 0))

        divider = ctk.CTkFrame(self, fg_color=BORDER, height=1)
        divider.pack(fill="x", padx=PAD, pady=PAD_SM)

        scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=BORDER,
        )
        scroll.pack(fill="both", expand=True, padx=0, pady=0)
        self._scroll = scroll

        fields_def = CATEGORIES.get(r.category, {}).get("fields", [])
        for label, key, is_secret in fields_def:
            val = d.fields.get(key, "")
            if not val:
                continue
            self._field_row(scroll, label, val, is_secret, key)

        if d.custom_fields:
            ctk.CTkLabel(
                scroll, text="ДОПОЛНИТЕЛЬНО",
                font=(FONT_FAMILY, 10, "bold"),
                text_color=TEXT_SUB, anchor="w",
            ).pack(fill="x", padx=PAD, pady=(PAD, 0))
            for name, val in d.custom_fields:
                self._field_row(scroll, name, val, False, f"custom_{name}")

        if d.notes.strip():
            ctk.CTkLabel(
                scroll, text="ЗАМЕТКИ",
                font=(FONT_FAMILY, 10, "bold"),
                text_color=TEXT_SUB, anchor="w",
            ).pack(fill="x", padx=PAD, pady=(PAD, 0))
            notes_box = ctk.CTkTextbox(
                scroll, height=80, font=FONT_BODY,
                fg_color=CARD, text_color=TEXT,
                state="normal", border_width=0,
            )
            notes_box.pack(fill="x", padx=PAD, pady=(4, 0))
            notes_box.insert("1.0", d.notes)
            notes_box.configure(state="disabled")

        if r.expiry_date:
            ctk.CTkLabel(
                scroll, text="СРОК ДЕЙСТВИЯ",
                font=(FONT_FAMILY, 10, "bold"),
                text_color=TEXT_SUB, anchor="w",
            ).pack(fill="x", padx=PAD, pady=(PAD, 0))
            ctk.CTkLabel(
                scroll, text=r.expiry_date,
                font=FONT_MONO, text_color=TEXT, anchor="w",
            ).pack(fill="x", padx=PAD, pady=(4, 0))

        if self._app is not None:
            self._render_attachments(scroll)


    def _render_attachments(self, parent) -> None:
        import threading
        import tkinter.filedialog as fd
        import tkinter.messagebox as mb
        import os

        ctk.CTkFrame(parent, fg_color=BORDER, height=1).pack(
            fill="x", padx=PAD, pady=(PAD, 0)
        )

        hdr = ctk.CTkFrame(parent, fg_color="transparent")
        hdr.pack(fill="x", padx=PAD, pady=(PAD_SM, 0))

        ctk.CTkLabel(
            hdr, text="ВЛОЖЕНИЯ",
            font=(FONT_FAMILY, 10, "bold"),
            text_color=TEXT_SUB, anchor="w",
        ).pack(side="left")

        attach_btn = ctk.CTkButton(
            hdr, text="📎 Прикрепить", height=26, width=110,
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            corner_radius=RADIUS_SM, font=(FONT_FAMILY, 11),
        )
        attach_btn.pack(side="right")

        att_container = ctk.CTkFrame(parent, fg_color="transparent")
        att_container.pack(fill="x", padx=PAD, pady=(4, PAD))

        def _refresh():
            for w in att_container.winfo_children():
                w.destroy()
            try:
                attachments = self._app.get_attachments(self._record.id)
            except Exception:
                attachments = []

            if not attachments:
                ctk.CTkLabel(
                    att_container,
                    text="Нет вложений",
                    font=FONT_BODY, text_color=TEXT_SUB, anchor="w",
                ).pack(fill="x")
                return

            _IMAGE_EXTS = {
                ".jpg", ".jpeg", ".png", ".gif",
                ".bmp", ".webp", ".heic", ".heif",
            }

            for att in attachments:
                row = ctk.CTkFrame(att_container, fg_color=CARD, corner_radius=RADIUS_SM)
                row.pack(fill="x", pady=(0, 4))

                mime = att.get("mimetype", "")
                fname = att["filename"]
                fext = os.path.splitext(fname)[1].lower()
                is_image = mime.startswith("image") or fext in _IMAGE_EXTS
                icon = "🖼" if is_image else \
                       "📄" if "pdf" in mime else \
                       "🎵" if mime.startswith("audio") else \
                       "🎬" if mime.startswith("video") else "📎"

                size_kb = att.get("size", 0) / 1024
                size_str = f"{size_kb:.1f} КБ" if size_kb < 1024 else f"{size_kb/1024:.1f} МБ"

                att_id = att["id"]
                att_name = fname
                att_mime = mime
                att_is_image = is_image

                def _open(aid=att_id, aname=att_name, amime=att_mime, aimg=att_is_image, aext=fext):
                    try:
                        data_bytes = self._app.get_attachment_data(aid)
                    except Exception as e:
                        mb.showerror("Ошибка", str(e))
                        return

                    if aimg:
                        _show_image_preview(self, aname, data_bytes)
                    else:
                        import tempfile, subprocess, threading
                        ext = os.path.splitext(aname)[1] or aext
                        with tempfile.NamedTemporaryFile(
                            delete=False, suffix=ext
                        ) as tmp:
                            tmp.write(data_bytes)
                            tmp_path = tmp.name
                        try:
                            os.startfile(tmp_path)
                        except Exception:
                            subprocess.Popen(["explorer", tmp_path])
                        # Удаляем временный файл через 60 сек (после того как ОС успеет открыть)
                        def _cleanup(p=tmp_path):
                            try:
                                os.remove(p)
                            except Exception:
                                pass
                        threading.Timer(60.0, _cleanup).start()

                def _download(aid=att_id, aname=att_name):
                    dest_dir = fd.askdirectory(title="Выберите папку для сохранения")
                    if not dest_dir:
                        return
                    try:
                        saved = self._app.download_attachment(aid, dest_dir)
                        mb.showinfo("Сохранено", f"Файл сохранён:\n{saved}")
                    except Exception as e:
                        mb.showerror("Ошибка", str(e))

                def _del(aid=att_id, aname=att_name):
                    if not mb.askyesno(
                        "Удалить", f"Удалить вложение «{aname}»?",
                        icon="warning",
                    ):
                        return
                    try:
                        self._app.delete_attachment(aid)
                        _refresh()
                    except Exception as e:
                        mb.showerror("Ошибка", str(e))


                del_btn = ctk.CTkButton(
                    row, text="🗑", width=30, height=28,
                    fg_color="transparent", hover_color=CARD_HOVER,
                    text_color=DANGER, font=("Segoe UI Emoji", 13),
                    command=_del,
                )
                _ToolTip(del_btn, "Удалить вложение")
                del_btn.pack(side="right", padx=(0, 4))

                dl_btn = ctk.CTkButton(
                    row, text="⬇", width=30, height=28,
                    fg_color="transparent", hover_color=CARD_HOVER,
                    font=("Segoe UI Emoji", 13),
                    command=_download,
                )
                _ToolTip(dl_btn, "Скачать")
                dl_btn.pack(side="right", padx=(0, 2))

                open_btn = ctk.CTkButton(
                    row, text="👁", width=30, height=28,
                    fg_color="transparent", hover_color=CARD_HOVER,
                    font=("Segoe UI Emoji", 13),
                    command=_open,
                )
                _ToolTip(open_btn, "Открыть")
                open_btn.pack(side="right", padx=(0, 2))

                ctk.CTkLabel(
                    row, text=size_str,
                    font=(FONT_FAMILY, 10), text_color=TEXT_SUB,
                ).pack(side="left", padx=(0, 4))

                name_lbl = ctk.CTkLabel(
                    row,
                    text=f"{icon}  {att_name}",
                    font=FONT_BODY, text_color=TEXT, anchor="w",
                )
                name_lbl.pack(
                    side="left", padx=(PAD_SM, 0),
                    pady=PAD_SM, fill="x", expand=True,
                )
                for w in (row, name_lbl):
                    w.bind("<Double-Button-1>", lambda _, f=_open: f())

        _refresh()

        def _upload():
            path = fd.askopenfilename(
                title="Выберите файл",
                filetypes=[
                    ("Все файлы", "*.*"),
                    ("Изображения", "*.png *.jpg *.jpeg *.gif *.bmp *.webp"),
                    ("PDF", "*.pdf"),
                    ("Документы", "*.doc *.docx *.xlsx *.txt"),
                ],
            )
            if not path:
                return
            try:
                self._app.upload_attachment(self._record.id, path)
                _refresh()
            except Exception as e:
                mb.showerror("Ошибка загрузки", str(e))

        attach_btn.configure(command=_upload)


    def _field_row(
        self, parent, label: str, value: str,
        is_secret: bool, key: str,
    ) -> None:
        ctk.CTkLabel(
            parent, text=label.upper(),
            font=(FONT_FAMILY, 10, "bold"),
            text_color=TEXT_SUB, anchor="w",
        ).pack(fill="x", padx=PAD, pady=(PAD, 0))

        row = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=RADIUS_SM)
        row.pack(fill="x", padx=PAD, pady=(4, 0))

        display = "••••••••" if is_secret else value
        self._hidden[key] = is_secret
        lbl = ctk.CTkLabel(
            row, text=display,
            font=FONT_MONO, text_color=TEXT,
            anchor="w", wraplength=240,
        )
        lbl.pack(side="left", padx=PAD_SM, pady=PAD_SM, fill="x", expand=True)
        self._value_labels[key] = lbl

        copy_btn = ctk.CTkButton(
            row, text="📋", width=34, height=30,
            fg_color="transparent", hover_color=CARD_HOVER,
            font=("Segoe UI Emoji", 14),
        )
        copy_btn.configure(command=lambda v=value, b=copy_btn: self._copy(v, b))
        copy_btn.pack(side="right", padx=(0, 4))
        _ToolTip(copy_btn, "Скопировать")

        if is_secret:
            tog = ctk.CTkButton(
                row, text="👁", width=34, height=30,
                fg_color="transparent", hover_color=CARD_HOVER,
                font=("Segoe UI Emoji", 14),
                command=lambda k=key, v=value: self._toggle(k, v),
            )
            tog.pack(side="right")
            _ToolTip(tog, "Показать / скрыть")

    def _toggle(self, key: str, value: str) -> None:
        lbl = self._value_labels.get(key)
        if not lbl:
            return
        self._hidden[key] = not self._hidden[key]
        lbl.configure(text="••••••••" if self._hidden[key] else value)

    def _copy(self, value: str, btn: ctk.CTkButton | None = None) -> None:
        self.clipboard_clear()
        self.clipboard_append(value)
        if btn:
            btn.configure(text="✓", text_color=SUCCESS)
            self.after(1500, lambda: btn.configure(text="📋", text_color=TEXT))
