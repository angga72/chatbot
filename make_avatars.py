#!/usr/bin/env python3
"""Generate avatar PNG untuk chatbot (tanpa emoji — murni grafis)."""
import os
from PIL import Image, ImageDraw, ImageFont

OUT = os.path.join(os.path.dirname(__file__), "assets")
os.makedirs(OUT, exist_ok=True)

SIZE = 160
FONT_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
]
font = None
for fp in FONT_PATHS:
    if os.path.exists(fp):
        font = ImageFont.truetype(fp, 96)
        break
if font is None:
    font = ImageFont.load_default()


def circle_avatar(path: str, bg: str, letter: str, fg: str):
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((4, 4, SIZE - 4, SIZE - 4), fill=bg)
    # teks tengah
    bbox = d.textbbox((0, 0), letter, font=font)
    w = bbox[2] - bbox[0]
    h = bbox[3] - bbox[1]
    x = (SIZE - w) / 2 - bbox[0]
    y = (SIZE - h) / 2 - bbox[1] - 6
    d.text((x, y), letter, font=font, fill=fg)
    img.save(path)
    print("saved", path)


# Avatar bot: lingkaran hijau industrial #14532D, huruf B putih
circle_avatar(os.path.join(OUT, "avatar-bot.png"), "#14532D", "B", "#FFFFFF")

# Avatar user: lingkaran abu muda, huruf U netral
circle_avatar(os.path.join(OUT, "avatar-user.png"), "#E2E8F0", "U", "#334155")
