from __future__ import annotations
import socket
import customtkinter as ctk
from PIL import Image
try:
    import qrcode
    _HAS_QR = True
except ImportError:
    _HAS_QR = False

from src.utils.constants import *


def _get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def show_qr_dialog(parent: ctk.CTk, port: int = 8080) -> None:
    ip = _get_local_ip()
    url = f"http://{ip}:{port}"

    win = ctk.CTkToplevel(parent)
    win.title("Подключить телефон")
    win.resizable(False, False)
    win.configure(fg_color=BG)
    win.grab_set()
    win.focus_set()

    ctk.CTkLabel(
        win, text="📱 Подключить телефон",
        font=(FONT_FAMILY, 15, "bold"), text_color=TEXT,
    ).pack(pady=(20, 2))
    ctk.CTkLabel(
        win, text="Отсканируй QR в мобильном приложении\nна экране входа → значок камеры",
        font=FONT_SMALL, text_color=TEXT_SUB, justify="center",
    ).pack(pady=(0, 12))

    if _HAS_QR:
        qr = qrcode.QRCode(
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=7,
            border=3,
        )
        qr.add_data(url)
        qr.make(fit=True)
        pil_img = qr.make_image(fill_color="#6c63ff", back_color="#1a1a2e")
        pil_img = pil_img.resize((260, 260), Image.LANCZOS)
        ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(260, 260))
        ctk.CTkLabel(win, image=ctk_img, text="").pack()
    else:
        ctk.CTkLabel(
            win, text="⚠ Установи пакет qrcode:\npip install qrcode[pil]",
            text_color=WARNING, font=FONT_BODY,
        ).pack(pady=20)

    ctk.CTkLabel(
        win, text=url,
        font=(FONT_FAMILY, 11), text_color=ACCENT,
    ).pack(pady=(10, 4))

    ctk.CTkLabel(
        win, text="Убедись, что телефон и ПК\nв одной Wi-Fi сети",
        font=FONT_SMALL, text_color=TEXT_SUB, justify="center",
    ).pack(pady=(0, 8))

    ctk.CTkButton(
        win, text="Закрыть", command=win.destroy,
        fg_color=SURFACE, hover_color=CARD_HOVER, text_color=TEXT,
        width=120, height=36,
    ).pack(pady=(0, 20))

    win.update_idletasks()
    w, h = win.winfo_reqwidth() + 40, win.winfo_reqheight() + 20
    px = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
    py = parent.winfo_rooty() + (parent.winfo_height() - h) // 2
    win.geometry(f"{w}x{h}+{px}+{py}")
