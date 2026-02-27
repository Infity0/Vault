from __future__ import annotations
import os
import ctypes

try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
        "VaultApp.SecureStorage.1"
    )
except Exception:
    pass

import customtkinter as ctk

from src.ui.app import VaultApp
from src.ui.login_frame import LoginFrame
from src.ui.main_window import MainWindow
from src.utils.constants import BG, WIN_W, WIN_H, WIN_MIN_W, WIN_MIN_H


def _set_taskbar_icon(window, ico_path: str) -> None:
    try:
        import ctypes
        user32 = ctypes.windll.user32
        LR_LOADFROMFILE = 0x0010
        IMAGE_ICON = 1
        WM_SETICON = 0x0080
        ICON_SMALL, ICON_BIG = 0, 1

        hwnd = window.winfo_id()

        hicon_big = user32.LoadImageW(
            None, ico_path, IMAGE_ICON, 256, 256, LR_LOADFROMFILE
        )
        hicon_small = user32.LoadImageW(
            None, ico_path, IMAGE_ICON, 16, 16, LR_LOADFROMFILE
        )
        if hicon_big:
            user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, hicon_big)
        if hicon_small:
            user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, hicon_small)
    except Exception:
        pass


class Root(ctk.CTk):

    def __init__(self) -> None:
        super().__init__()
        self.title("Vault — Безопасное хранилище")
        self.configure(fg_color=BG)
        self.minsize(WIN_MIN_W, WIN_MIN_H)

        _icon = os.path.join(os.path.dirname(__file__), "assets", "icon.ico")
        if os.path.exists(_icon):
            try:
                self.iconbitmap(_icon)
            except Exception:
                pass
            self.after(200, lambda: _set_taskbar_icon(self, _icon))

        self._center(440, 560)

        self._app = VaultApp()
        self._current_frame: ctk.CTkFrame | None = None
        self._show_login()
        if self._app.startup_error:
            from src.ui.components.message_dialog import show_error
            from src.ui.components.settings_dialog import SettingsDialog
            self.after(300, lambda: show_error(
                self,
                "Невозможно подключиться к MySQL",
                f"{self._app.startup_error}\n\nОткройте Настройки и проверьте данные подключения.",
            ))

    def _center(self, w: int, h: int) -> None:
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _swap(self, frame: ctk.CTkFrame) -> None:
        if self._current_frame:
            self._current_frame.destroy()
        self._current_frame = frame
        frame.pack(fill="both", expand=True)

    def _show_login(self) -> None:
        accounts = self._app.list_accounts()
        h = min(560, 300 + max(len(accounts), 1) * 56 + 60)
        self._center(440, max(h, 460))
        self.resizable(False, False)
        frame = LoginFrame(
            self,
            accounts=accounts,
            on_unlock=self._on_unlock,
            on_create=self._on_create,
        )
        self._swap(frame)

    def _on_unlock(self, username: str, password: str) -> bool:
        if self._app.unlock_account(username, password):
            self.after(0, self._open_vault)
            return True
        return False

    def _on_create(self, username: str, password: str) -> str | None:
        if self._app.db is None:
            return f"Нет подключения к БД. {self._app.startup_error}"
        if self._app.username_exists(username):
            return "Аккаунт с таким именем уже существует."
        try:
            self._app.create_account(username, password)
        except Exception as e:
            return str(e)
        if self._app.unlock_account(username, password):
            self.after(0, self._open_vault)
        return None

    def _on_lock(self) -> None:
        self._app.lock_vault()
        self._show_login()

    def _open_vault(self) -> None:
        self._center(WIN_W, WIN_H)
        self.minsize(WIN_MIN_W, WIN_MIN_H)
        self.resizable(True, True)
        frame = MainWindow(self, self._app, on_lock=self._on_lock)
        self._swap(frame)



def main() -> None:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = Root()

    def _safe_report(exc, val, tb):
        import tkinter as _tk
        if exc is _tk.TclError and "bad window path name" in str(val):
            return
        app.tk.call("bgerror", str(val))

    app.report_callback_exception = _safe_report
    app.mainloop()


if __name__ == "__main__":
    main()
