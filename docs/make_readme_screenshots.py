"""Make every README screenshot exactly the same size and shape.

1. Save your raw screenshots in:   docs/screenshots/readme_raw/
2. Run from the project root:      python docs/make_readme_screenshots.py
3. Use the results in:             docs/screenshots/readme/      (all 1280 x 800 pixels)

Options:
    --mode crop   (default) fill the frame and cut off the extra part (keeps the top of the page)
    --mode fit    keep the whole picture and add dark bars where needed
    --anchor top|center   which part to keep in crop mode (default: top)
    --size 1280x800       output size
"""
import argparse
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "docs" / "screenshots" / "readme_raw"
OUT = ROOT / "docs" / "screenshots" / "readme"
BACKGROUND = (11, 18, 48)          # the dashboard's dark navy
EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


def crop_to_frame(img: Image.Image, size: tuple, anchor: str) -> Image.Image:
    """Scale to cover the frame, then cut off what sticks out."""
    w, h = size
    scale = max(w / img.width, h / img.height)
    img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    left = (img.width - w) // 2
    top = 0 if anchor == "top" else (img.height - h) // 2
    return img.crop((left, top, left + w, top + h))


def fit_in_frame(img: Image.Image, size: tuple) -> Image.Image:
    """Scale to fit inside the frame and centre it on a dark background."""
    w, h = size
    scale = min(w / img.width, h / img.height)
    img = img.resize((round(img.width * scale), round(img.height * scale)), Image.LANCZOS)
    canvas = Image.new("RGB", size, BACKGROUND)
    canvas.paste(img, ((w - img.width) // 2, (h - img.height) // 2))
    return canvas


def main() -> int:
    parser = argparse.ArgumentParser(description="Make README screenshots the same size.")
    parser.add_argument("--mode", choices=["crop", "fit"], default="crop")
    parser.add_argument("--anchor", choices=["top", "center"], default="top")
    parser.add_argument("--size", default="1280x800")
    args = parser.parse_args()
    width, height = (int(x) for x in args.size.lower().split("x"))

    files = sorted(p for p in RAW.glob("*") if p.suffix.lower() in EXTENSIONS) if RAW.exists() else []
    if not files:
        print(f"No screenshots found in {RAW}\nCreate that folder and put your raw screenshots in it, then run this again.")
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    for path in files:
        img = Image.open(path).convert("RGB")
        result = (crop_to_frame(img, (width, height), args.anchor) if args.mode == "crop"
                  else fit_in_frame(img, (width, height)))
        target = OUT / (path.stem + ".png")
        result.save(target, optimize=True)
        print(f"{path.name:35s} {img.width}x{img.height}  ->  {target.name} {width}x{height}")
    print(f"\nDone: {len(files)} screenshots written to {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
