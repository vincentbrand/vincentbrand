#!/usr/bin/env python3
"""
Turns a picture or logo into ascii.txt for the profile card.

    pip install pillow
    python img2ascii.py photo.jpg             # photo: bright areas become dense characters
    python img2ascii.py photo.jpg --invert    # dark areas become dense characters instead
    python img2ascii.py logo.png              # transparent PNG: the logo shape becomes the characters
    python build.py --offline                 # then rebuild to see the result

Runs locally, the image is not sent anywhere.
"""
import argparse

from PIL import Image, ImageOps

COLS, ROWS = 38, 25          # space available left of the text
CELL_W, CELL_H = 9.6, 20     # one character cell in the SVG, in pixels
RAMP = " .:-=+*#%@"          # light to dense


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--invert", action="store_true")
    ap.add_argument("--out", default="ascii.txt")
    ap.add_argument("--ramp", default=RAMP, help="characters from empty to dense")
    args = ap.parse_args()

    img = ImageOps.exif_transpose(Image.open(args.image)).convert("RGBA")
    alpha = img.getchannel("A")
    if alpha.getextrema()[0] < 255:
        # Transparent background: draw the opaque shape, trimmed to its bounds.
        box = alpha.getbbox()
        ink = alpha.crop(box)
    else:
        ink = ImageOps.autocontrast(img.convert("L"), cutoff=1)
    if args.invert:
        ink = ImageOps.invert(ink)

    # Fit inside COLS x ROWS while keeping the picture's proportions.
    aspect = ink.height / ink.width * (CELL_W / CELL_H)
    cols = COLS
    rows = round(cols * aspect)
    if rows > ROWS:
        rows, cols = ROWS, round(ROWS / aspect)
    small = ink.resize((cols, rows), Image.LANCZOS)

    pad_left = " " * ((COLS - cols) // 2)
    pad_top = (ROWS - rows) // 2
    px = small.load()
    last = len(args.ramp) - 1
    lines = [""] * pad_top
    for y in range(rows):
        row = "".join(args.ramp[px[x, y] * last // 255] for x in range(cols))
        lines.append((pad_left + row).rstrip())
    lines += [""] * (ROWS - rows - pad_top)

    with open(args.out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
