from PIL import Image
import os
import shutil

SOURCE = next(
    (p for p in ["assets/icon_source.png", "assets/icon_source.jpg", "assets/icon_source.jpeg"]
     if os.path.exists(p)),
    "assets/icon_source.png"
)
MOBILE_RES = r"C:\Users\Admin\Desktop\vault_mobile\android\app\src\main\res"

ANDROID_SIZES = {
    "mipmap-mdpi":    48,
    "mipmap-hdpi":    72,
    "mipmap-xhdpi":   96,
    "mipmap-xxhdpi":  144,
    "mipmap-xxxhdpi": 192,
}

ICO_SIZES = [16, 32, 48, 64, 128, 256]


def load_source() -> Image.Image:
    if not os.path.exists(SOURCE):
        raise FileNotFoundError(
            f"Не найден файл: {SOURCE}\n"
            "Сохрани картинку как assets/icon_source.png и запусти снова."
        )
    img = Image.open(SOURCE).convert("RGBA")
    print(f"Загружено: {SOURCE}  ({img.size[0]}x{img.size[1]})")
    return img


def resize_square(img: Image.Image, size: int) -> Image.Image:
    return img.resize((size, size), Image.LANCZOS)


def make_desktop_ico(img: Image.Image) -> None:
    os.makedirs("assets", exist_ok=True)
    out = "assets/icon.ico"
    src = img.convert("RGBA")
    big = resize_square(src, 256)
    big.save(out, format="ICO", sizes=[(s, s) for s in ICO_SIZES])
    size_kb = os.path.getsize(out) // 1024
    print(f"Desktop ICO  → {out}  ({size_kb} KB)")


def make_android_icons(img: Image.Image) -> None:
    for folder, size in ANDROID_SIZES.items():
        out_dir = os.path.join(MOBILE_RES, folder)
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, "ic_launcher.png")
        resized = resize_square(img, size)
        bg = Image.new("RGBA", resized.size, (0, 0, 0, 255))
        bg.paste(resized, mask=resized.split()[3])
        bg.convert("RGB").save(out_path, format="PNG")
        print(f"Android {folder:20s} {size}x{size}  → {out_path}")

    for folder, size in ANDROID_SIZES.items():
        out_dir = os.path.join(MOBILE_RES, folder)
        src = os.path.join(out_dir, "ic_launcher.png")
        dst = os.path.join(out_dir, "ic_launcher_round.png")
        shutil.copy2(src, dst)
    print("Android round icons copied.")


def make_flutter_asset(img: Image.Image) -> None:
    out_dir = r"C:\Users\Admin\Desktop\vault_mobile\assets"
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "icon.png")
    resize_square(img, 1024).save(out_path, format="PNG")
    print(f"Flutter asset → {out_path}")


if __name__ == "__main__":
    src = load_source()
    make_desktop_ico(src)
    make_android_icons(src)
    make_flutter_asset(src)
    print("\nГотово! Пересобери APK: flutter build apk --release")
