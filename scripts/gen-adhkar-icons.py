"""Generate concept-driven adhkar category icons (256x256, badge style).

Style: circular badge with vertical gradient, thin lighter ring,
single cream flat glyph.

Glyph sources (reference geometry fetched into scripts/icons/):
  - Lucide Icons            (ISC)        https://lucide.dev
  - Phosphor Icons          (MIT)        https://phosphoricons.com
  - Line Awesome / Icons8   (Apache-2.0) https://icons8.com/line-awesome
  - Font Awesome 6 Solid    (CC BY 4.0)  https://fontawesome.com  [kaaba glyph]
  - Fluent Emoji High Contrast (MIT)     https://github.com/microsoft/fluentui-emoji [dua]
Custom hand-drawn glyphs: prayer, adhan, tasbih ( concept-specific).
Run: python3 scripts/gen-adhkar-icons.py  (writes backend/assets/adhkar_icons/*.png)
"""
import glob
import math
import os

from PIL import Image, ImageDraw
from PySide6.QtCore import QByteArray, QRectF
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgRenderer

SIZE = 256
CREAM = (243, 234, 216, 255)
GOLD = (212, 175, 55, 255)
OUT = os.path.join(os.path.dirname(__file__), "..", "backend", "assets", "adhkar_icons")
ICONS = os.path.join(os.path.dirname(__file__), "icons")

# role -> (svg file stem, badge top, badge bottom, glyph box px)
SVGS = {
    "morning": ("morning", (234, 179, 8), (146, 109, 3), 150),
    "evening": ("evening", (234, 88, 12), (159, 55, 8), 150),
    "sleep": ("sleep", (30, 64, 175), (18, 39, 112), 148),
    "after_prayer": ("after_prayer", (120, 33, 111), (84, 22, 76), 150),
    "mosque": ("mosque", (13, 111, 76), (8, 76, 51), 150),
    "tahara": ("tahara", (2, 132, 199), (2, 100, 150), 150),
    "eating": ("eating", (124, 60, 12), (90, 42, 9), 150),
    "home": ("home", (71, 85, 105), (50, 59, 74), 150),
    "libas": ("libas", (87, 83, 78), (62, 59, 55), 150),
    "travel": ("travel", (29, 78, 216), (20, 53, 148), 150),
    "sick": ("sick", (225, 29, 72), (170, 16, 52), 150),
    "hajj": ("hajj", (186, 141, 48), (140, 104, 30), 176),
    "distress": ("distress", (153, 27, 27), (105, 16, 16), 148),
    "ruqya": ("ruqya", (22, 101, 52), (14, 74, 36), 150),
    "protection": ("protection", (30, 58, 138), (18, 40, 95), 150),
    "manners": ("manners", (77, 124, 15), (54, 88, 10), 150),
    "nature": ("nature", (7, 89, 133), (4, 62, 96), 150),
    "dua": ("dua", (218, 152, 48), (174, 109, 24), 168),
    "tasbih": None,  # custom
    "istighfar": ("istighfar", (49, 46, 129), (32, 30, 88), 150),
    "misc": ("misc", (15, 118, 110), (10, 84, 79), 150),
}


def badge(top, bottom):
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for y in range(SIZE):
        t = y / (SIZE - 1)
        d.line([(0, y), (SIZE, y)],
               fill=tuple(int(top[i] + (bottom[i] - top[i]) * t) for i in range(3)) + (255,))
    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).ellipse([8, 8, 248, 248], fill=255)
    bg = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    bg.paste(img, (0, 0), mask)
    d = ImageDraw.Draw(bg)
    ring = tuple(min(255, int(top[i] * 0.55 + 255 * 0.45)) for i in range(3)) + (255,)
    d.ellipse([10, 10, 246, 246], outline=ring, width=5)
    return bg, ImageDraw.Draw(bg)


def save(name, img):
    img.save(os.path.join(OUT, name + ".png"))


def svg_glyph(stem, glyph):
    """Render reference SVG (tinted cream) onto a transparent canvas."""
    svg = open(os.path.join(ICONS, stem + ".svg"), encoding="utf-8").read()
    svg = svg.replace("currentColor", "#f3ead8")
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    img = QImage(SIZE, SIZE, QImage.Format_ARGB32)
    img.fill(0)
    painter = QPainter(img)
    painter.setRenderHint(QPainter.Antialiasing)
    m = (SIZE - glyph) / 2
    renderer.render(painter, QRectF(m, m, glyph, glyph))
    painter.end()
    data = Image.frombytes("RGBA", (img.width(), img.height()),
                           bytes(img.constBits()))
    alpha = data.split()[3]
    out = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    solid = Image.new("RGBA", (SIZE, SIZE), CREAM)
    out.paste(solid, (0, 0), alpha)
    return out


def svg_icon(role):
    stem, top, bottom, glyph = SVGS[role]
    img, _ = badge(top, bottom)
    img.alpha_composite(svg_glyph(stem, glyph))
    save(role, img)


# ---------- custom hand-drawn glyphs (concept-specific) ----------

def prayer():  # prayer rug with mihrab arch — Salah
    img, d = badge((13, 115, 119), (8, 80, 84))
    d.polygon([(76, 182), (180, 182), (160, 88), (96, 88)], fill=CREAM)
    d.arc([100, 104, 156, 160], start=180, end=360, fill=(13, 115, 119, 255), width=6)
    d.line([(100, 132), (100, 172)], fill=(13, 115, 119, 255), width=6)
    d.line([(156, 132), (156, 172)], fill=(13, 115, 119, 255), width=6)
    d.ellipse([122, 74, 134, 86], fill=CREAM)
    save("prayer", img)


def adhan():  # traditional Islamic minaret with balconies, dome, and sound arcs
    img, d = badge((180, 83, 9), (130, 60, 6))
    # Base shaft (tapered Islamic minaret)
    d.polygon([(112, 190), (144, 190), (140, 96), (116, 96)], fill=CREAM)
    # Lower balcony
    d.rectangle([106, 126, 150, 136], fill=CREAM)
    # Upper balcony
    d.rectangle([110, 96, 146, 104], fill=CREAM)
    # Islamic onion/pointed dome cap
    d.pieslice([112, 60, 144, 98], start=180, end=360, fill=CREAM)
    d.polygon([(128, 44), (132, 54), (124, 54)], fill=CREAM)  # Crescent finial top
    # Doorway arch
    d.pieslice([120, 164, 136, 190], start=180, end=360, fill=(130, 60, 6, 255))
    d.rectangle([120, 176, 136, 190], fill=(130, 60, 6, 255))
    # Sound waves (adhan call)
    for r in (30, 48, 66):
        d.arc([154 - r, 124 - r, 154 + r, 124 + r], start=-55, end=55, fill=CREAM, width=5)
        d.arc([102 - r, 124 - r, 102 + r, 124 + r], start=125, end=235, fill=CREAM, width=5)
    save("adhan", img)


def tasbih():
    img, d = badge((120, 53, 15), (84, 36, 10))
    cx, cy, rx, ry = 128, 118, 46, 38
    for i in range(12):
        a = 2 * math.pi * i / 12
        x, y = cx + rx * math.cos(a), cy + ry * math.sin(a)
        d.ellipse([x - 7, y - 7, x + 7, y + 7], fill=CREAM)
    d.ellipse([cx - 10, cy + ry - 4, cx + 10, cy + ry + 16], fill=CREAM)
    d.line([(cx, cy + ry + 14), (cx, 200)], fill=GOLD, width=5)
    d.rectangle([cx - 8, 200, cx + 8, 212], fill=GOLD)
    save("tasbih", img)


def contact_sheet(names, out_path, cell=96, cols=6):
    rows = (len(names) + cols - 1) // cols
    sheet = Image.new("RGBA", (cols * cell, rows * cell), (250, 247, 242, 255))
    for i, n in enumerate(names):
        im = Image.open(os.path.join(OUT, n + ".png")).convert("RGBA")
        im.thumbnail((cell - 8, cell - 8))
        u = i % cols
        v = i // cols
        sheet.alpha_composite(im, (u * cell + (cell - im.width) // 2,
                                   v * cell + (cell - im.height) // 2))
    sheet.save(out_path)
    print("sheet ->", out_path)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for role in SVGS:
        if SVGS[role] is None:  # custom glyph
            continue
        svg_icon(role)
    prayer()
    adhan()
    tasbih()
    print("wrote", len(SVGS) + 2, "icons to", OUT)
