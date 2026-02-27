from __future__ import annotations
import customtkinter as ctk
from src.utils.constants import *


class MessageDialog(ctk.CTkToplevel):

    _ICONS = {
        "error":   ("✕", DANGER),
        "info":    ("ℹ", ACCENT),
        "warning": ("⚠", WARNING),
        "confirm": ("?", WARNING),
    }

    def __init__(
        self,
        master,
        title: str,
        message: str,
        kind: str = "error",
    ):
        super().__init__(master)
        self.result: bool = False

        self.title(title)
        self.resizable(False, False)
        self.configure(fg_color=BG)
        self.after(50, self.grab_set)
        self.after(50, self.lift)
        self.after(50, self.focus_force)

        icon_char, icon_color = self._ICONS.get(kind, self._ICONS["info"])

        header = ctk.CTkFrame(self, fg_color=SURFACE, height=52, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header, text=f"  {icon_char}  {title}",
            font=(FONT_FAMILY, 13, "bold"),
            text_color=icon_color,
        ).pack(side="left", padx=PAD)

        body = ctk.CTkFrame(self, fg_color=CARD, corner_radius=RADIUS_SM)
        body.pack(fill="x", padx=PAD, pady=PAD)

        ctk.CTkLabel(
            body,
            text=message,
            font=FONT_BODY,
            text_color=TEXT,
            wraplength=360,
            justify="left",
            anchor="w",
        ).pack(padx=PAD, pady=PAD, fill="x")

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(fill="x", padx=PAD, pady=(0, PAD))

        if kind == "confirm":
            ctk.CTkButton(
                footer, text="Отмена", height=36,
                fg_color="transparent", text_color=TEXT_SUB,
                hover_color=CARD_HOVER, corner_radius=RADIUS_SM,
                border_color=BORDER, border_width=1,
                font=FONT_BODY,
                command=self._no,
            ).pack(side="right", padx=(PAD_SM, 0))

            ctk.CTkButton(
                footer, text="  Подтвердить  ", height=36,
                fg_color=DANGER, hover_color="#c73580",
                corner_radius=RADIUS_SM,
                font=(FONT_FAMILY, 12, "bold"),
                command=self._yes,
            ).pack(side="right")
        else:
            color = ACCENT if kind == "info" else (DANGER if kind == "error" else WARNING)
            ctk.CTkButton(
                footer, text="  OK  ", height=36,
                fg_color=color, hover_color=ACCENT_HOVER if kind == "info" else color,
                corner_radius=RADIUS_SM,
                font=(FONT_FAMILY, 12, "bold"),
                command=self.destroy,
            ).pack(side="right")

        self.update_idletasks()
        w = max(420, self.winfo_reqwidth() + 20)
        h = self.winfo_reqheight() + 10
        mx = master.winfo_rootx() + master.winfo_width() // 2
        my = master.winfo_rooty() + master.winfo_height() // 2
        self.geometry(f"{w}x{h}+{mx - w // 2}+{my - h // 2}")

        self.bind("<Return>", lambda _: self._yes() if kind == "confirm" else self.destroy())
        self.bind("<Escape>", lambda _: self._no() if kind == "confirm" else self.destroy())

    def _yes(self) -> None:
        self.result = True
        self.destroy()

    def _no(self) -> None:
        self.result = False
        self.destroy()

    def wait(self) -> bool:
        self.wait_window()
        return self.result



def show_error(master, title: str, message: str) -> None:
    MessageDialog(master, title, message, kind="error").wait()


def show_info(master, title: str, message: str) -> None:
    MessageDialog(master, title, message, kind="info").wait()


def show_warning(master, title: str, message: str) -> None:
    MessageDialog(master, title, message, kind="warning").wait()


def ask_confirm(master, title: str, message: str) -> bool:
    return MessageDialog(master, title, message, kind="confirm").wait()
