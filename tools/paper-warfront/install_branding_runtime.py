"""Install the selected Paper Warfront brand assets into the Godot project.

The formal branding set lives outside the Godot checkout. This script creates
only the runtime-facing launcher icon assets, derives the opaque launcher icon
from the reviewed textless character mark, and writes a hash manifest for the export.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "assets" / "paper-warfront" / "branding" / "v2"
RUNTIME = ROOT / "game" / "assets" / "branding"
CHARACTER = SOURCE / "selected" / "logo-character-yin-marshal-woodblock-v2.png"

INK = (52, 51, 50, 255)
VERMILION = (183, 69, 50, 255)
IVORY = (243, 235, 221, 255)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def trim_alpha(image: Image.Image, threshold: int = 10, pad: int = 8) -> Image.Image:
    alpha = image.getchannel("A").point(lambda value: 255 if value > threshold else 0)
    box = alpha.getbbox()
    if box is None:
        return image
    x0, y0, x1, y1 = box
    return image.crop((max(0, x0 - pad), max(0, y0 - pad), min(image.width, x1 + pad), min(image.height, y1 + pad)))


def contained(image: Image.Image, max_size: tuple[int, int]) -> Image.Image:
    scale = min(max_size[0] / image.width, max_size[1] / image.height)
    return image.resize((round(image.width * scale), round(image.height * scale)), Image.Resampling.LANCZOS)


def make_icon(character: Image.Image) -> Image.Image:
    canvas = Image.new("RGBA", (512, 512), IVORY)
    draw = ImageDraw.Draw(canvas)
    # A quiet paper tile keeps the selected character recognizable in launcher
    # masks while retaining the project's vermilion/ink material language.
    draw.rounded_rectangle((10, 10, 501, 501), radius=58, fill=IVORY, outline=VERMILION, width=10)
    draw.rounded_rectangle((25, 25, 486, 486), radius=46, outline=INK, width=3)
    placed = contained(character, (432, 432))
    canvas.alpha_composite(placed, ((512 - placed.width) // 2, (512 - placed.height) // 2 + 6))
    return canvas.convert("RGBA")


def make_foreground(character: Image.Image) -> Image.Image:
    placed = contained(character, (364, 364))
    canvas = Image.new("RGBA", (432, 432), (0, 0, 0, 0))
    canvas.alpha_composite(placed, ((432 - placed.width) // 2, (432 - placed.height) // 2 + 4))
    return canvas


def copy_asset(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(source.read_bytes())


def metadata(path: Path, asset_id: str, role: str, source: str) -> dict:
    with Image.open(path) as image:
        return {
            "id": asset_id,
            "role": role,
            "path": path.relative_to(ROOT).as_posix(),
            "source": source,
            "version": "1.1.0-runtime",
            "width": image.width,
            "height": image.height,
            "mode": image.mode,
            "bytes": path.stat().st_size,
            "sha256": sha256(path),
        }


def main() -> None:
    RUNTIME.mkdir(parents=True, exist_ok=True)
    for name in (
        "logo-character-yin-marshal-woodblock-v2.png",
        "logo-wordmark-battle-seal-v1.png",
        "brand-lockup-primary.png",
        "keyart-main.png",
        "keyart-mobile.png",
        "keyart-chapter-map.png",
    ):
        (RUNTIME / name).unlink(missing_ok=True)

    character = trim_alpha(Image.open(CHARACTER).convert("RGBA"))
    icon = make_icon(character)
    icon.save(ROOT / "game" / "assets" / "icon.png", format="PNG", optimize=True)
    foreground = make_foreground(character)
    foreground.save(RUNTIME / "icon-foreground-432.png", format="PNG", optimize=True)

    records = [
        metadata(ROOT / "game" / "assets" / "icon.png", "brand.icon.launcher.yin_marshal.v2", "launcher-icon", "derived from assets/paper-warfront/branding/v2/selected/logo-character-yin-marshal-woodblock-v2.png"),
        metadata(RUNTIME / "icon-foreground-432.png", "brand.icon.android_foreground.yin_marshal.v2", "android-adaptive-foreground", "derived from assets/paper-warfront/branding/v2/selected/logo-character-yin-marshal-woodblock-v2.png"),
    ]
    manifest = {
        "schema": 1,
        "product_name": "纸上兵戈",
        "branding_runtime_version": "1.1.0-runtime",
        "selected": {
            "character_logo_id": "brand.logo.character.yin_marshal.woodblock_ink",
            "character_logo_label": "02 木刻墨印·印甲统帅",
            "wordmark_id": "brand.logo.wordmark.battle_seal",
            "wordmark_label": "朱印战印",
        },
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "assets": records,
        "icon_derivation": {
            "canvas": "512x512 opaque ivory paper tile",
            "foreground_canvas": "432x432 transparent adaptive foreground",
            "character_trim_threshold": 10,
            "background": "ivory #F3EBDD with vermilion #B74532 and ink #343332 border",
            "runtime_paths": ["res://assets/icon.png", "res://assets/branding/icon-foreground-432.png"],
        },
        "runtime_bindings": {
            "project_icon": "res://assets/icon.png",
            "android_launcher_main": "res://assets/icon.png",
            "android_adaptive_foreground": "res://assets/branding/icon-foreground-432.png",
        },
    }
    (ROOT / "game" / "data" / "branding-runtime.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"runtime_root": str(RUNTIME), "icon": str(ROOT / "game" / "assets" / "icon.png"), "asset_count": len(records)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
