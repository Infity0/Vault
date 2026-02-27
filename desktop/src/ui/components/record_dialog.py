from __future__ import annotations
import customtkinter as ctk
from typing import Callable, Optional

from src.core.models import Record, RecordData, CATEGORIES, ALL_CATEGORY_KEYS
from src.utils.constants import *
from src.ui.components.date_picker import DatePickerDialog


class RecordDialog(ctk.CTkToplevel):

    def __init__(
        self,
        master,
        on_save: Callable[[Record, RecordData], None],
        record: Optional[Record] = None,
        data: Optional[RecordData] = None,
    ):
        super().__init__(master)
        self.on_save = on_save
        self._record = record
        self._data = data or RecordData()
        self._is_edit = record is not None
        self._field_vars: dict[str, ctk.StringVar] = {}
        self._custom_rows: list[tuple[ctk.StringVar, ctk.StringVar]] = []
        self._secret_entries: dict[str, ctk.CTkEntry] = {}
        self._revealed: dict[str, bool] = {}

        self.title("Редактировать запись" if self._is_edit else "Новая запись")
        self.geometry("520x680")
        self.resizable(False, True)
        self.configure(fg_color=BG)
        self.after(200, self.grab_set)
        self._build()
        self.after(100, self.lift)


    def _build(self) -> None:
        header = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=0, height=56)
        header.pack(fill="x")
        header.pack_propagate(False)
        ctk.CTkLabel(
            header,
            text="✏️  Редактировать" if self._is_edit else "➕  Новая запись",
            font=(FONT_FAMILY, 14, "bold"), text_color=TEXT,
        ).pack(side="left", padx=PAD)

        self._scroll = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=BORDER,
        )
        self._scroll.pack(fill="both", expand=True, padx=0, pady=0)

        body = self._scroll

        self._section(body, "Название")
        self._title_var = ctk.StringVar(
            value=self._record.title if self._record else ""
        )
        self._entry(body, self._title_var, placeholder="Например: Мой паспорт")

        self._section(body, "Категория")
        cat_labels = [CATEGORIES[k]["label"] for k in ALL_CATEGORY_KEYS]
        current_cat = self._record.category if self._record else "other"
        current_label = CATEGORIES[current_cat]["label"]
        self._cat_var = ctk.StringVar(value=current_label)
        cat_menu = ctk.CTkOptionMenu(
            body,
            values=cat_labels,
            variable=self._cat_var,
            font=FONT_BODY, text_color=TEXT,
            fg_color=SURFACE, button_color=ACCENT,
            button_hover_color=ACCENT_HOVER,
            dropdown_fg_color=CARD,
            dropdown_text_color=TEXT,
            command=self._on_category_change,
            height=40,
        )
        cat_menu.pack(fill="x", padx=PAD, pady=(4, 0))

        self._fields_frame = ctk.CTkFrame(body, fg_color="transparent")
        self._fields_frame.pack(fill="x")
        self._render_fields(current_cat)

        self._expiry_var = ctk.StringVar(
            value=self._record.expiry_date or "" if self._record else ""
        )
        self._expiry_container = ctk.CTkFrame(body, fg_color="transparent")
        ctk.CTkLabel(
            self._expiry_container,
            text="СРОК ДЕЙСТВИЯ (ДАТА ИСТЕЧЕНИЯ)",
            font=(FONT_FAMILY, 10, "bold"),
            text_color=TEXT_SUB, anchor="w",
        ).pack(fill="x", padx=PAD, pady=(PAD, 0))
        self._expiry_btn_frame = ctk.CTkFrame(self._expiry_container, fg_color="transparent")
        self._expiry_btn_frame.pack(fill="x", padx=PAD, pady=(4, 0))
        if CATEGORIES.get(current_cat, {}).get("has_expiry", True):
            self._expiry_container.pack(fill="x")
        self._expiry_btn = ctk.CTkButton(
            self._expiry_btn_frame,
            text=self._expiry_label(),
            height=40, font=FONT_BODY,
            fg_color=SURFACE, hover_color=CARD_HOVER,
            text_color=TEXT if self._expiry_var.get() else TEXT_SUB,
            corner_radius=RADIUS_SM,
            border_width=1, border_color=BORDER,
            anchor="w",
            command=self._open_date_picker,
        )
        self._expiry_btn.pack(side="left", fill="x", expand=True)
        self._expiry_clear_btn = ctk.CTkButton(
            self._expiry_btn_frame,
            text="✕", width=40, height=40,
            fg_color=SURFACE, hover_color=CARD_HOVER,
            text_color=TEXT_SUB, corner_radius=RADIUS_SM,
            border_width=1, border_color=BORDER,
            command=self._clear_expiry,
        )
        if self._expiry_var.get():
            self._expiry_clear_btn.pack(side="left", padx=(4, 0))

        self._notes_container = ctk.CTkFrame(body, fg_color="transparent")
        self._notes_container.pack(fill="x")
        self._section(self._notes_container, "Заметки")
        self._notes = ctk.CTkTextbox(
            self._notes_container, height=90, font=FONT_BODY,
            fg_color=SURFACE, border_color=BORDER,
            text_color=TEXT, border_width=1,
            corner_radius=RADIUS_SM,
        )
        self._notes.pack(fill="x", padx=PAD, pady=(4, 0))
        if self._data.notes:
            self._notes.insert("1.0", self._data.notes)

        ctk.CTkButton(
            body, text="+ Добавить поле",
            font=FONT_SMALL, height=32,
            fg_color="transparent", text_color=ACCENT,
            hover_color=CARD_HOVER, border_color=ACCENT,
            border_width=1, corner_radius=RADIUS_SM,
            command=self._add_custom_field,
        ).pack(anchor="w", padx=PAD, pady=(PAD, 0))

        self._custom_frame = ctk.CTkFrame(body, fg_color="transparent")
        self._custom_frame.pack(fill="x")
        for name, val in self._data.custom_fields:
            self._add_custom_field(name, val)

        footer = ctk.CTkFrame(self, fg_color=SURFACE, corner_radius=0, height=60)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)

        ctk.CTkButton(
            footer, text="Отмена", height=36,
            fg_color="transparent", text_color=TEXT_SUB,
            hover_color=CARD_HOVER, corner_radius=RADIUS_SM,
            font=FONT_BODY, command=self.destroy,
        ).pack(side="right", padx=(0, PAD), pady=12)

        ctk.CTkButton(
            footer, text="  💾  Сохранить  ", height=36,
            fg_color=ACCENT, hover_color=ACCENT_HOVER,
            corner_radius=RADIUS_SM, font=(FONT_FAMILY, 13, "bold"),
            command=self._save,
        ).pack(side="right", pady=12)

    def _expiry_label(self) -> str:
        v = self._expiry_var.get()
        return f"📅  {v}" if v else "📅  Выбрать дату  (необязательно)"

    def _open_date_picker(self) -> None:
        DatePickerDialog(
            self._expiry_btn,
            on_select=self._on_date_selected,
            initial=self._expiry_var.get() or None,
            parent_dialog=self,
        )

    def _on_date_selected(self, date_str) -> None:
        if date_str:
            self._expiry_var.set(date_str)
            self._expiry_btn.configure(
                text=self._expiry_label(), text_color=TEXT
            )
            self._expiry_clear_btn.pack(side="left", padx=(4, 0))
        else:
            self._clear_expiry()

    def _clear_expiry(self) -> None:
        self._expiry_var.set("")
        self._expiry_btn.configure(
            text=self._expiry_label(), text_color=TEXT_SUB
        )
        self._expiry_clear_btn.pack_forget()


    def _section(self, parent, text: str) -> None:
        ctk.CTkLabel(
            parent, text=text.upper(),
            font=(FONT_FAMILY, 10, "bold"),
            text_color=TEXT_SUB, anchor="w",
        ).pack(fill="x", padx=PAD, pady=(PAD, 0))

    def _entry(
        self, parent, var: ctk.StringVar,
        placeholder: str = "",
        secret: bool = False,
        key: str = "",
    ) -> ctk.CTkEntry:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=PAD, pady=(4, 0))
        entry = ctk.CTkEntry(
            row, textvariable=var, height=40,
            font=FONT_BODY, fg_color=SURFACE,
            border_color=BORDER, text_color=TEXT,
            placeholder_text=placeholder,
            show="•" if secret else "",
        )
        entry.pack(side="left", fill="x", expand=True)
        if secret and key:
            self._secret_entries[key] = entry
            self._revealed[key] = False
            toggle = ctk.CTkButton(
                row, text="👁", width=38, height=40,
                fg_color=SURFACE, hover_color=CARD_HOVER,
                text_color=TEXT_SUB, corner_radius=RADIUS_SM,
                command=lambda: self._toggle_reveal(key),
            )
            toggle.pack(side="left", padx=(4, 0))

        if secret and "password" in key.lower():
            bar_frame = ctk.CTkFrame(parent, fg_color="transparent")
            bar_frame.pack(fill="x", padx=PAD, pady=(3, 0))
            bar = ctk.CTkProgressBar(
                bar_frame, height=5, corner_radius=3,
                fg_color=CARD, progress_color=DANGER,
            )
            bar.set(0)
            bar.pack(fill="x", side="left", expand=True)
            lbl = ctk.CTkLabel(
                bar_frame, text="", font=FONT_SMALL,
                text_color=TEXT_DIM, width=60, anchor="e",
            )
            lbl.pack(side="left", padx=(6, 0))

            def _update(*_):
                score, label, color = RecordDialog._calc_strength(var.get())
                bar.set(score)
                bar.configure(progress_color=color)
                lbl.configure(text=label, text_color=color)

            var.trace_add("write", _update)
            _update()

        return entry

    @staticmethod
    def _calc_strength(pwd: str) -> tuple[float, str, str]:
        if not pwd:
            return 0.0, "", TEXT_DIM
        score = 0
        if len(pwd) >= 8:   score += 1
        if len(pwd) >= 12:  score += 1
        if any(c.isupper() for c in pwd):  score += 1
        if any(c.isdigit() for c in pwd):  score += 1
        if any(c in r"!@#$%^&*()-_=+[]{}|;:',.<>?/" for c in pwd): score += 1
        if score <= 2:
            return max(0.15, score * 0.1), "Слабый",   DANGER
        elif score == 3:
            return 0.55, "Средний",  WARNING
        elif score == 4:
            return 0.78, "Хороший",  SUCCESS
        else:
            return 1.0,  "Надёжный", SUCCESS

    def _toggle_reveal(self, key: str) -> None:
        entry = self._secret_entries[key]
        self._revealed[key] = not self._revealed[key]
        entry.configure(show="" if self._revealed[key] else "•")

    def _date_field(self, parent, key: str, var: ctk.StringVar) -> None:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=PAD, pady=(4, 0))

        def _lbl():
            v = var.get()
            return f"📅  {v}" if v else "📅  Выбрать дату"

        btn = ctk.CTkButton(
            row, text=_lbl(), height=40, font=FONT_BODY,
            fg_color=SURFACE, hover_color=CARD_HOVER,
            text_color=TEXT if var.get() else TEXT_SUB,
            corner_radius=RADIUS_SM,
            border_width=1, border_color=BORDER,
            anchor="w",
        )
        clear_btn = ctk.CTkButton(
            row, text="✕", width=40, height=40,
            fg_color=SURFACE, hover_color=CARD_HOVER,
            text_color=TEXT_SUB, corner_radius=RADIUS_SM,
            border_width=1, border_color=BORDER,
        )

        def _on_selected(date_str):
            if date_str:
                var.set(date_str)
                btn.configure(text=_lbl(), text_color=TEXT)
                clear_btn.pack(side="left", padx=(4, 0))
            else:
                _on_clear()

        def _on_clear():
            var.set("")
            btn.configure(text=_lbl(), text_color=TEXT_SUB)
            clear_btn.pack_forget()

        dlg_ref = self

        btn.configure(
            command=lambda: DatePickerDialog(
                btn, on_select=_on_selected, initial=var.get() or None,
                parent_dialog=dlg_ref,
            )
        )
        clear_btn.configure(command=_on_clear)

        btn.pack(side="left", fill="x", expand=True)
        if var.get():
            clear_btn.pack(side="left", padx=(4, 0))

    def _option_field(
        self, parent, var: ctk.StringVar, options: list[str]
    ) -> None:
        placeholder = options[0]
        if var.get() not in options:
            var.set(placeholder)

        menu = ctk.CTkOptionMenu(
            parent,
            values=options,
            variable=var,
            font=FONT_BODY, text_color=TEXT,
            fg_color=SURFACE, button_color=ACCENT,
            button_hover_color=ACCENT_HOVER,
            dropdown_fg_color=CARD,
            dropdown_text_color=TEXT,
            height=40,
        )
        menu.pack(fill="x", padx=PAD, pady=(4, 0))

    _CARD_TYPES = ["Visa", "Mastercard", "Мир", "UnionPay", "American Express", "Другая"]

    def _render_fields(self, category_key: str) -> None:
        for w in self._fields_frame.winfo_children():
            w.destroy()
        self._field_vars.clear()
        self._secret_entries.clear()

        fields = CATEGORIES.get(category_key, {}).get("fields", [])
        for label, key, is_secret in fields:
            self._section(self._fields_frame, label)
            var = ctk.StringVar(value=self._data.fields.get(key, ""))
            self._field_vars[key] = var
            if "date" in key:
                self._date_field(self._fields_frame, key, var)
            elif key == "card_type":
                self._option_field(self._fields_frame, var, self._CARD_TYPES)
            else:
                self._entry(self._fields_frame, var, secret=is_secret, key=key)

    def _on_category_change(self, label: str) -> None:
        for k, v in CATEGORIES.items():
            if v["label"] == label:
                self._render_fields(k)
                if v.get("has_expiry", True):
                    self._expiry_container.pack(fill="x", before=self._notes_container)
                else:
                    self._expiry_container.pack_forget()
                    self._clear_expiry()
                break

    def _add_custom_field(self, name: str = "", value: str = "") -> None:
        row = ctk.CTkFrame(self._custom_frame, fg_color="transparent")
        row.pack(fill="x", padx=PAD, pady=(PAD_SM, 0))
        name_var = ctk.StringVar(value=name)
        val_var = ctk.StringVar(value=value)
        ctk.CTkEntry(
            row, textvariable=name_var, placeholder_text="Название поля",
            width=140, height=36, font=FONT_BODY,
            fg_color=SURFACE, border_color=BORDER, text_color=TEXT,
        ).pack(side="left")
        ctk.CTkEntry(
            row, textvariable=val_var, placeholder_text="Значение",
            height=36, font=FONT_BODY,
            fg_color=SURFACE, border_color=BORDER, text_color=TEXT,
        ).pack(side="left", fill="x", expand=True, padx=(4, 0))
        ctk.CTkButton(
            row, text="✕", width=32, height=36,
            fg_color="transparent", text_color=DANGER,
            hover_color=CARD_HOVER,
            command=lambda r=row, p=(name_var, val_var): self._remove_custom(r, p),
        ).pack(side="left", padx=(4, 0))
        self._custom_rows.append((name_var, val_var))

    def _remove_custom(self, row, pair) -> None:
        row.destroy()
        if pair in self._custom_rows:
            self._custom_rows.remove(pair)


    def _get_category_key(self) -> str:
        label = self._cat_var.get()
        for k, v in CATEGORIES.items():
            if v["label"] == label:
                return k
        return "other"

    def _save(self) -> None:
        title = self._title_var.get().strip()
        if not title:
            from src.ui.components.message_dialog import show_error
            show_error(self, "Пустое название", "Укажите название записи.")
            return

        data = RecordData(
            fields={k: v.get() for k, v in self._field_vars.items()},
            notes=self._notes.get("1.0", "end-1c"),
            custom_fields=[
                (n.get(), v.get())
                for n, v in self._custom_rows
                if n.get()
            ],
        )

        if self._record is None:
            record = Record(
                title=title,
                category=self._get_category_key(),
                encrypted_data="",
                expiry_date=self._expiry_var.get().strip() or None,
            )
        else:
            self._record.title = title
            self._record.category = self._get_category_key()
            self._record.expiry_date = self._expiry_var.get().strip() or None
            record = self._record

        self.on_save(record, data)
        self.destroy()
