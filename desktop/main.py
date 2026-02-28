from __future__ import annotations
import os
import sys
import subprocess
import threading
import time as _time
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


class _ServerManager:
    """
    Запускает server.py (FastAPI) как дочерний процесс и отслеживает его.
    Статусы: stopped | starting | running | error
    """

    _STATUS_LABELS = {
        "stopped":  ("⚫ Сервер выкл.",  "#778ca3"),
        "starting": ("🟡 Запуск сервера…", "#f7b731"),
        "running":  ("🟢 Сервер запущен", "#20bf6b"),
        "error":    ("🔴 Ошибка сервера", "#fc5c65"),
    }

    def __init__(self) -> None:
        self._proc: subprocess.Popen | None = None
        self._status: str = "stopped"
        self._callbacks: list = []

    def start(self) -> None:
        """Запустить сервер в фоне (безопасно вызывать повторно)."""
        if self._proc and self._proc.poll() is None:
            return
        self._set_status("starting")
        threading.Thread(target=self._launch, daemon=True,
                         name="vault-server").start()

    def stop(self) -> None:
        """Остановить сервер (вызывается при закрытии десктопного приложения)."""
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()
        self._set_status("stopped")

    def add_listener(self, cb) -> None:
        """Подписаться на смену статуса. cb(status: str) вызывается из любого потока."""
        self._callbacks.append(cb)
        cb(self._status)

    @property
    def status(self) -> str:
        return self._status

    @classmethod
    def label_for(cls, status: str) -> tuple[str, str]:
        return cls._STATUS_LABELS.get(status, ("⚫", "#778ca3"))

    def _set_status(self, s: str) -> None:
        self._status = s
        for cb in list(self._callbacks):
            try:
                cb(s)
            except Exception:
                pass

    def _launch(self) -> None:
        server_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.py")
        cwd = os.path.dirname(os.path.abspath(__file__))
        extra = {"creationflags": 0x08000000} if os.name == "nt" else {}

        env = os.environ.copy()
        try:
            from src.ui.components.settings_dialog import load_mysql_config
            cfg = load_mysql_config()
            env["MYSQL_HOST"]     = cfg.host
            env["MYSQL_PORT"]     = str(cfg.port)
            env["MYSQL_USER"]     = cfg.user
            env["MYSQL_PASSWORD"] = cfg.password
            env["MYSQL_DATABASE"] = cfg.database
        except Exception:
            pass

        try:
            self._proc = subprocess.Popen(
                [sys.executable, server_script],
                cwd=cwd,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                **extra,
            )
        except Exception:
            self._set_status("error")
            return

        _time.sleep(2)
        if self._proc.poll() is None:
            self._set_status("running")
            self._proc.wait()
            if self._status == "running":
                self._set_status("error")
        else:
            self._set_status("error")


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

        self._server_mgr = _ServerManager()

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

        self.protocol("WM_DELETE_WINDOW", self._on_close)

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

    def _on_close(self) -> None:
        """Корректное завершение: сначала останавливаем сервер, потом закрываем окно."""
        self._server_mgr.stop()
        self.destroy()

    def _on_lock(self) -> None:
        self._app.lock_vault()
        self._show_login()

    def _open_vault(self) -> None:
        self._center(WIN_W, WIN_H)
        self.minsize(WIN_MIN_W, WIN_MIN_H)
        self.resizable(True, True)
        frame = MainWindow(self, self._app, on_lock=self._on_lock,
                           server_mgr=self._server_mgr)
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
