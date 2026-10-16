"""Generate concept-driven adhkar category icons (256x256, badge style).

Style matches the shipped set: circular badge with vertical gradient,
thin lighter ring, single cream flat glyph.
Run: python3 scripts/gen-adhkar-icons.py  (writes backend/assets/adhkar_icons/*.png)
"""
import math
import os

from PIL import Image, ImageDraw

SIZE = 256
CREAM = (243, 234, 216, 255)
GOLD = (212, 175, 55, 255)
OUT = os.path.join(os.path.dirname(__file__), "..", "backend", "assets", "adhkar_icons")


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


def prayer():  # prayer rug with mihrab arch — Salah
    img, d = badge((13, 115, 119), (8, 80, 84))
    d.polygon([(76, 182), (180, 182), (160, 88), (96, 88)], fill=CREAM)
    d.arc([100, 104, 156, 160], start=180, end=360, fill=(13, 115, 119, 255), width=6)
    d.line([(100, 132), (100, 172)], fill=(13, 115, 119, 255), width=6)
    d.line([(156, 132), (156, 172)], fill=(13, 115, 119, 255), width=6)
    d.ellipse([122, 74, 134, 86], fill=CREAM)
    save("prayer", img)


def adhan():  # tapered minaret with dome cap, doorway + sound arcs
    img, d = badge((180, 83, 9), (130, 60, 6))
    d.polygon([(110, 182), (146, 182), (139, 84), (117, 84)], fill=CREAM)
    d.pieslice([112, 58, 144, 90], start=180, end=360, fill=CREAM)
    d.line([(128, 44), (128, 60)], fill=CREAM, width=5)
    d.ellipse([124, 38, 132, 46], fill=CREAM)
    d.pieslice([118, 148, 138, 184], start=180, end=360, fill=(130, 60, 6, 255))
    d.rectangle([118, 166, 138, 184], fill=(130, 60, 6, 255))
    for r in (28, 46, 64):
        d.arc([152 - r, 118 - r, 152 + r, 118 + r], start=-55, end=55, fill=CREAM, width=6)
        d.arc([104 - r, 118 - r, 104 + r, 118 + r], start=125, end=235, fill=CREAM, width=6)
    save("adhan", img)


def tahara():  # water drop — purification / wudu
    img, d = badge((2, 132, 199), (2, 100, 150))
    d.polygon([(128, 56), (93, 130), (163, 130)], fill=CREAM)
    d.ellipse([93, 95, 163, 165], fill=CREAM)
    d.ellipse([(112, 118), (127, 138)], fill=(255, 255, 255, 255))
    save("tahara", img)


def libas():  # thobe robe with long sleeves — clothing
    img, d = badge((87, 83, 78), (60, 57, 53))
    d.polygon([(116, 80), (96, 88), (88, 142), (104, 138), (100, 192),
               (156, 192), (152, 138), (168, 142), (160, 88), (140, 80),
               (140, 94), (116, 94)], fill=CREAM)
    save("libas", img)


def sick():  # heart with pulse — illness (matches Heart convention)
    img, d = badge((225, 29, 72), (170, 16, 52))
    d.ellipse([88, 96, 128, 136], fill=CREAM)
    d.ellipse([128, 96, 168, 136], fill=CREAM)
    d.polygon([(90, 122), (128, 172), (166, 122)], fill=CREAM)
    d.line([(84, 134), (108, 134), (118, 118), (130, 150), (140, 126), (172, 126)],
           fill=(159, 18, 57, 255), width=6, joint="curve")
    save("sick", img)


def hajj():  # Kaaba front square with gold band — Hajj & Umrah
    img, d = badge((28, 25, 23), (10, 8, 7))
    d.rectangle([92, 108, 164, 192], fill=(8, 8, 8, 255), outline=CREAM, width=5)
    d.rectangle([92, 128, 164, 146], fill=GOLD)
    d.rectangle([148, 152, 158, 182], fill=(168, 132, 44, 255))
    save("hajj", img)


def distress():  # fanous lantern — hardship seeking light
    img, d = badge((153, 27, 27), (105, 16, 16))
    d.ellipse([120, 48, 136, 64], outline=CREAM, width=4)
    d.polygon([(106, 64), (150, 64), (142, 82), (114, 82)], fill=CREAM)
    d.polygon([(114, 82), (142, 82), (152, 154), (104, 154)], fill=CREAM)
    d.polygon([(128, 98), (116, 136), (140, 136)], fill=(251, 191, 36, 255))
    d.ellipse([121, 130, 135, 148], fill=(153, 27, 27, 255))
    d.polygon([(104, 154), (152, 154), (142, 168), (114, 168)], fill=CREAM)
    for x in (78, 178):
        d.line([(x, 98), (x - 14 if x < 128 else x + 14, 84)], fill=CREAM, width=5)
    save("distress", img)


def ruqya():  # open Quran — Ruqyah
    img, d = badge((21, 128, 61), (13, 88, 42))
    d.polygon([(128, 96), (62, 110), (62, 178), (128, 164)], fill=CREAM)
    d.polygon([(128, 96), (194, 110), (194, 178), (128, 164)], fill=CREAM)
    d.line([(128, 96), (128, 164)], fill=(21, 128, 61, 255), width=4)
    for y in (120, 134, 148):
        d.line([(74, y), (114, y + 4)], fill=(21, 128, 61, 255), width=4)
        d.line([(142, y + 4), (182, y)], fill=(21, 128, 61, 255), width=4)
    save("ruqya", img)


def protection():  # shield with crescent — protection
    img, d = badge((30, 58, 138), (18, 40, 95))
    d.polygon([(128, 62), (178, 84), (178, 130), (128, 188), (78, 130), (78, 84)],
              fill=(43, 74, 158, 255), outline=CREAM, width=6)
    d.ellipse([106, 100, 150, 144], fill=CREAM)
    d.ellipse([116, 94, 156, 134], fill=(43, 74, 158, 255))
    d.polygon([(152, 148), (156, 158), (166, 162), (156, 166), (152, 176),
               (148, 166), (138, 162), (148, 158)], fill=CREAM)
    save("protection", img)


def manners():  # two people — social etiquette
    img, d = badge((77, 124, 15), (52, 88, 10))
    dark = (217, 207, 174, 255)
    d.ellipse([72, 128, 128, 184], fill=dark)
    d.ellipse([84, 92, 116, 124], fill=dark)
    d.chord([120, 138, 184, 202], start=180, end=360, fill=CREAM)
    d.ellipse([134, 98, 168, 132], fill=CREAM)
    save("manners", img)


def nature():  # cloud with rain — rain & nature
    img, d = badge((7, 89, 133), (4, 62, 96))
    d.ellipse([84, 108, 140, 150], fill=CREAM)
    d.ellipse([110, 94, 168, 136], fill=CREAM)
    d.ellipse([140, 108, 190, 148], fill=CREAM)
    d.rectangle([92, 128, 184, 150], fill=CREAM)
    for x in (108, 134, 160):
        d.line([(x, 160), (x - 8, 186)], fill=(125, 211, 252, 255), width=6)
    save("nature", img)


def tasbih():  # prayer beads loop — tasbih
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


def istighfar():  # two raised cupped hands — supplication
    img, d = badge((49, 46, 129), (32, 30, 88))
    d.arc([40, 96, 118, 186], start=15, end=165, fill=CREAM, width=13)
    d.arc([138, 96, 216, 186], start=15, end=165, fill=CREAM, width=13)
    d.rectangle([52, 184, 96, 200], fill=CREAM)
    d.rectangle([160, 184, 204, 200], fill=CREAM)
    save("istighfar", img)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    prayer()
    adhan()
    tahara()
    libas()
    sick()
    hajj()
    distress()
    ruqya()
    protection()
    manners()
    nature()
    tasbih()
    istighfar()
    print("wrote 13 icons to", OUT)
