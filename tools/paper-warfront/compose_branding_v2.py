"""Compose the selected Paper Warfront brand into a coherent banner family.

Generated key art is intentionally text-free. This script places the frozen
wordmark and renders copy with the game's local fonts so the final banner text
is exact and remains readable at every export size.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "output" / "imagegen" / "paper-warfront" / "branding-v2"
BG = OUT / "backgrounds"
FINAL = OUT / "final"
PROMPTS = OUT / "prompts"
WORDMARK = OUT.parent / "logo-directions-v1" / "01-battle-seal.png"
CHARACTER = OUT.parent / "logo-character-v2" / "02-woodblock-ink-warrior.png"
SERIF = ROOT / "game" / "assets" / "fonts" / "NotoSerifSC.ttf"
SANS = ROOT / "game" / "assets" / "fonts" / "NotoSansSC.ttf"

INK = (52, 51, 50, 255)
VERMILION = (183, 69, 50, 255)
IVORY = (243, 235, 221, 255)
PAPER = (232, 222, 202, 255)
JADE = (55, 123, 120, 255)
GOLD = (185, 150, 79, 255)


def rgba(path: Path) -> Image.Image:
    return Image.open(path).convert("RGBA")


def trim_alpha(im: Image.Image, threshold: int = 10, pad: int = 8) -> Image.Image:
    alpha = im.getchannel("A").point(lambda v: 255 if v > threshold else 0)
    box = alpha.getbbox()
    if box is None:
        return im
    x0, y0, x1, y1 = box
    x0 = max(0, x0 - pad)
    y0 = max(0, y0 - pad)
    x1 = min(im.width, x1 + pad)
    y1 = min(im.height, y1 + pad)
    return im.crop((x0, y0, x1, y1))


def cover(im: Image.Image, size: tuple[int, int], bias_y: float = 0.5) -> Image.Image:
    tw, th = size
    scale = max(tw / im.width, th / im.height)
    resized = im.resize((round(im.width * scale), round(im.height * scale)), Image.Resampling.LANCZOS)
    left = max(0, (resized.width - tw) // 2)
    extra_y = max(0, resized.height - th)
    top = round(extra_y * max(0.0, min(1.0, bias_y)))
    return resized.crop((left, top, left + tw, top + th))


def paste_fit(base: Image.Image, im: Image.Image, box: tuple[int, int, int, int]) -> None:
    x, y, w, h = box
    scale = min(w / im.width, h / im.height)
    placed = im.resize((max(1, round(im.width * scale)), max(1, round(im.height * scale))), Image.Resampling.LANCZOS)
    px = x + (w - placed.width) // 2
    py = y + (h - placed.height) // 2
    base.alpha_composite(placed, (px, py))


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size)


def text_size(draw: ImageDraw.ImageDraw, text: str, fnt: ImageFont.FreeTypeFont) -> tuple[int, int]:
    box = draw.textbbox((0, 0), text, font=fnt)
    return box[2] - box[0], box[3] - box[1]


def draw_left(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, fnt: ImageFont.FreeTypeFont, fill=INK) -> None:
    draw.text(xy, text, font=fnt, fill=fill)


def draw_center(draw: ImageDraw.ImageDraw, center_x: int, y: int, text: str, fnt: ImageFont.FreeTypeFont, fill=INK) -> None:
    width, _ = text_size(draw, text, fnt)
    draw.text((center_x - width // 2, y), text, font=fnt, fill=fill)


def rough_panel(canvas: Image.Image, polygon: Iterable[tuple[int, int]], fill=(243, 235, 221, 213), outline=None, width=2) -> None:
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    pts = list(polygon)
    d.polygon(pts, fill=fill)
    if outline:
        d.line(pts + [pts[0]], fill=outline, width=width, joint="curve")
    canvas.alpha_composite(layer)


def add_rule(draw: ImageDraw.ImageDraw, x: int, y: int, length: int, color=VERMILION, width: int = 4) -> None:
    draw.line((x, y, x + length, y), fill=color, width=width)
    draw.ellipse((x + length + 8, y - width // 2 - 2, x + length + width + 8, y + width // 2 + 2), fill=color)


def compose_main(word: Image.Image) -> Image.Image:
    canvas = cover(Image.open(BG / "main-key-art.png").convert("RGBA"), (1920, 800), 0.38)
    rough_panel(canvas, [(58, 32), (686, 32), (700, 740), (55, 768)], fill=(243, 235, 221, 214), outline=(183, 69, 50, 95), width=2)
    draw = ImageDraw.Draw(canvas)
    paste_fit(canvas, word, (112, 66, 330, 330))
    add_rule(draw, 124, 412, 118)
    draw_left(draw, (124, 438), "一纸成阵，横行破局", font(SERIF, 48), INK)
    draw_left(draw, (126, 510), "自动行军 · 金币与法力 · 雾中决策", font(SANS, 22), INK)
    draw_left(draw, (126, 560), "把每一次推进，都变成可读的战局。", font(SANS, 20), INK)
    # A small stamped action label keeps the panel visually grounded without becoming UI.
    draw.rounded_rectangle((124, 632, 300, 696), radius=10, fill=VERMILION, outline=INK, width=2)
    draw_center(draw, 212, 646, "展开战局", font(SERIF, 28), IVORY)
    draw_left(draw, (730, 738), "PAPER WARFRONT  ·  纸上兵戈", font(SANS, 16), IVORY)
    return canvas.convert("RGB")


def compose_mobile(word: Image.Image) -> Image.Image:
    canvas = cover(Image.open(BG / "mobile-key-art.png").convert("RGBA"), (1080, 1440), 0.06)
    # The generated top field is deliberately quiet; a very light paper plate makes copy readable on device screens.
    rough_panel(canvas, [(88, 46), (992, 42), (1002, 720), (78, 715)], fill=(243, 235, 221, 184), outline=(183, 69, 50, 82), width=2)
    draw = ImageDraw.Draw(canvas)
    paste_fit(canvas, word, (366, 82, 348, 348))
    add_rule(draw, 350, 458, 120)
    draw_center(draw, 540, 494, "纸上起兵，所见即战局", font(SERIF, 42), INK)
    draw_center(draw, 540, 570, "自动行军 · 金币与法力 · 雾中决策", font(SANS, 21), INK)
    draw.rounded_rectangle((399, 642, 681, 712), radius=12, fill=VERMILION, outline=INK, width=2)
    draw_center(draw, 540, 655, "展开战局", font(SERIF, 31), IVORY)
    return canvas.convert("RGB")


def compose_chapter(word: Image.Image) -> Image.Image:
    canvas = cover(Image.open(BG / "chapter-key-art.png").convert("RGBA"), (1600, 900), 0.32)
    draw = ImageDraw.Draw(canvas)
    # The source art reserves the scroll for copy. Keep the seal inside that boundary.
    paste_fit(canvas, word, (154, 110, 330, 330))
    add_rule(draw, 180, 492, 106)
    draw_left(draw, (180, 520), "每一次分岔，都是一场战役", font(SERIF, 36), INK)
    draw_left(draw, (182, 584), "路线未定，战局先行。", font(SANS, 22), INK)
    draw.rounded_rectangle((180, 650, 396, 710), radius=10, fill=JADE, outline=INK, width=2)
    draw_center(draw, 288, 661, "进入章节", font(SERIF, 26), IVORY)
    return canvas.convert("RGB")


def compose_social(main: Image.Image, word: Image.Image) -> Image.Image:
    # Use the same key art and typography, only changing the crop and copy for social cards.
    canvas = cover(Image.open(BG / "main-key-art.png").convert("RGBA"), (1200, 630), 0.35)
    rough_panel(canvas, [(34, 25), (440, 24), (450, 586), (32, 598)], fill=(243, 235, 221, 218), outline=(183, 69, 50, 92), width=2)
    draw = ImageDraw.Draw(canvas)
    paste_fit(canvas, word, (66, 54, 196, 196))
    add_rule(draw, 75, 292, 78, width=3)
    draw_left(draw, (75, 320), "布阵 · 推进 · 破城", font(SERIF, 31), INK)
    draw_left(draw, (77, 376), "一纸成阵，横行破局", font(SANS, 21), INK)
    draw_left(draw, (77, 424), "自动行军 · 雾中决策", font(SANS, 18), INK)
    draw.rounded_rectangle((77, 500, 222, 552), radius=9, fill=VERMILION, outline=INK, width=2)
    draw_center(draw, 149, 509, "纸上兵戈", font(SERIF, 23), IVORY)
    return canvas.convert("RGB")


def compose_lockup(word: Image.Image, character: Image.Image) -> Image.Image:
    canvas = Image.new("RGBA", (1440, 520), (0, 0, 0, 0))
    # One continuous paper plate keeps the two selected marks in the same material system.
    rough_panel(canvas, [(48, 52), (1382, 44), (1395, 454), (62, 472)], fill=(243, 235, 221, 244), outline=VERMILION, width=3)
    draw = ImageDraw.Draw(canvas)
    paste_fit(canvas, word, (120, 80, 360, 350))
    draw.line((600, 112, 600, 400), fill=VERMILION, width=4)
    draw.ellipse((590, 98, 610, 118), fill=GOLD)
    paste_fit(canvas, character, (760, 76, 420, 370))
    return canvas


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def file_entry(path: Path, role: str, usage: str | None = None) -> dict:
    with Image.open(path) as im:
        item = {"path": path.relative_to(ROOT).as_posix(), "role": role, "width": im.width, "height": im.height, "mode": im.mode, "sha256": sha256(path)}
    if usage:
        item["usage"] = usage
    return item


def main() -> None:
    FINAL.mkdir(parents=True, exist_ok=True)
    word = trim_alpha(rgba(WORDMARK))
    character = trim_alpha(rgba(CHARACTER))
    outputs = {
        "brand-lockup-primary.png": compose_lockup(word, character),
        "banner-main-1920x800.png": compose_main(word),
        "banner-mobile-1080x1440.png": compose_mobile(word),
        "banner-chapter-map-1600x900.png": compose_chapter(word),
        "banner-social-1200x630.png": compose_social(Image.open(BG / "main-key-art.png"), word),
    }
    for name, im in outputs.items():
        im.save(FINAL / name, format="PNG", optimize=True)

    copy = {
        "main": {
            "headline": "一纸成阵，横行破局",
            "feature_line": "自动行军 · 金币与法力 · 雾中决策",
            "support_line": "把每一次推进，都变成可读的战局。",
            "cta": "展开战局",
            "signature_line": "PAPER WARFRONT  ·  纸上兵戈",
        },
        "mobile": {
            "headline": "纸上起兵，所见即战局",
            "feature_line": "自动行军 · 金币与法力 · 雾中决策",
            "cta": "展开战局",
        },
        "chapter": {
            "headline": "每一次分岔，都是一场战役",
            "support_line": "路线未定，战局先行。",
            "cta": "进入章节",
        },
        "social": {
            "headline": "布阵 · 推进 · 破城",
            "support_line": "一纸成阵，横行破局",
            "feature_line": "自动行军 · 雾中决策",
            "cta": "纸上兵戈",
        },
    }
    manifest = {
        "schema": 1,
        "product_name": "纸上兵戈",
        "branding_version": "1.1.0-candidate",
        "status": "candidate-cohesive-banner-set",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "selected": {
            "character_logo_id": "brand.logo.character.yin_marshal.woodblock_ink",
            "character_logo_label": "02 木刻墨印·印甲统帅",
            "character_source": CHARACTER.relative_to(ROOT).as_posix(),
            "wordmark_id": "brand.logo.wordmark.battle_seal",
            "wordmark_label": "朱印战印",
            "wordmark_source": WORDMARK.relative_to(ROOT).as_posix(),
        },
        "art_direction": {
            "style": "two-color woodblock / risograph paper theatre",
            "palette": {"ink": "#343332", "vermilion": "#B74532", "ivory": "#F3EBDD", "paper": "#E8DECA", "jade": "#377B78", "gold": "#B9964F"},
            "generated_art_has_text": False,
            "copy_rendered_with": {"display": SERIF.relative_to(ROOT).as_posix(), "body": SANS.relative_to(ROOT).as_posix()},
            "composition_rule": "Generate one shared paper theatre key art per surface; render exact selected wordmark and copy locally.",
        },
        "copy": copy,
        "sources": [
            {"path": p.relative_to(ROOT).as_posix(), "sha256": sha256(p)}
            for p in sorted(PROMPTS.glob("*.txt"))
        ],
        "assets": [
            file_entry(FINAL / "brand-lockup-primary.png", "brand-lockup", "selected character logo + selected wordmark on one paper plate"),
            file_entry(FINAL / "banner-main-1920x800.png", "banner", "desktop / landing hero"),
            file_entry(FINAL / "banner-mobile-1080x1440.png", "banner", "portrait mobile launch / store feature"),
            file_entry(FINAL / "banner-chapter-map-1600x900.png", "banner", "chapter map / campaign selection"),
            file_entry(FINAL / "banner-social-1200x630.png", "banner", "social / release card"),
        ],
        "processing": {
            "script": "tools/paper-warfront/compose_branding_v2.py",
            "source_backgrounds": [
                p.relative_to(ROOT).as_posix() for p in sorted(BG.glob("*.png"))
            ],
            "notes": [
                "Sub2API gpt-image-2.5 generated text-free key art backgrounds.",
                "Selected logos are composited from frozen source files; copy is rendered with local Noto fonts for exact spelling.",
                "Candidate banners are not wired into the Godot runtime until visual approval.",
            ],
        },
    }
    (OUT / "branding-v2-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
