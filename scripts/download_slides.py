#!/usr/bin/env python3
"""
Migrate zebrafish atlas slide imagery from bio-atlas.psu.edu to DZI tile
pyramids that the bioatlas.io OpenSeadragon viewer can serve.

For every slide listed in site/assets/js/atlas-data.js this script:
  1. fetches the PSU viewer page (view.php?atlas=A&s=S) and parses the slide
     metadata (title + pyramid levels) embedded in its JavaScript;
  2. downloads all 256x256 JPEG tiles of the chosen zoom level from
     tile.jpeg.php?s=S&z=Z&i=I (tile order is auto-detected);
  3. stitches them into one full image;
  4. converts that image into a Deep Zoom (DZI) pyramid with libvips;
  5. writes the result to  site/tiles/<ageId>/<plane>/<atlas>_<s>.dzi
     (+ the matching  <atlas>_<s>_files/  tile folder), which is exactly the
     path pattern site/assets/js/viewer.js expects;
  6. records progress in a manifest so re-runs skip finished slides.

Requirements:
    pip install requests pillow pyvips
    libvips must be installed on the system:
        macOS:          brew install vips
        Debian/Ubuntu:  sudo apt install libvips

Usage:
    python3 scripts/download_slides.py                 # everything, full res
    python3 scripts/download_slides.py --age 48hpf     # one stage only
    python3 scripts/download_slides.py --age 12mpf-male --plane transverse
    python3 scripts/download_slides.py --level 1       # half resolution (~4x smaller)
    python3 scripts/download_slides.py --dry-run       # size estimate only
    python3 scripts/download_slides.py --hero          # also save a hero image

Be polite to the PSU server: the script sleeps briefly between requests.
The full-resolution dataset is LARGE (very roughly 20-60+ GB of tiles for all
630 slides). GitHub Pages caps a site at ~1 GB, so host tiles on object
storage (Cloudflare R2 / S3 / Backblaze B2) and point TILE_BASE in
site/assets/js/config.js at it. --level 1 or 2 gives a much smaller dataset
at reduced magnification if you want to test end-to-end first.
"""
import argparse, html, json, math, os, re, sys, time
from pathlib import Path

try:
    import requests
    from PIL import Image
except ImportError:
    sys.exit("pip install requests pillow pyvips  (see header of this script)")

Image.MAX_IMAGE_PIXELS = None  # slides are legitimately huge

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
TILES_OUT = SITE / "tiles"
PSU = "https://bio-atlas.psu.edu/zf/"
TILE_URL = PSU + "tile.jpeg.php?s={s}&z={z}&i={i}"
VIEW_URL = PSU + "view.php?atlas={atlas}&s={s}"
HEADERS = {"User-Agent": "bioatlas.io-migration/1.0 (contact: site admin)"}
SLEEP = 0.15  # seconds between tile requests

session = requests.Session()
session.headers.update(HEADERS)


def load_atlas_data():
    js = (SITE / "assets/js/atlas-data.js").read_text()
    return json.loads(js[js.index("{"): js.rindex("}") + 1])


def fetch_slide_meta(atlas, s):
    """Parse the `slide ={...}` object out of the PSU viewer page."""
    r = session.get(VIEW_URL.format(atlas=atlas, s=s), timeout=60)
    r.raise_for_status()
    m = re.search(r"slide\s*=\s*(\{.*?\})\s*[;,]\s*\n", r.text, re.S)
    if not m:
        m = re.search(r"slide\s*=\s*(\{.*?\"levels\":\[\[.*?\]\]\})", r.text, re.S)
    if not m:
        raise RuntimeError(f"could not parse slide metadata for atlas={atlas} s={s}")
    return json.loads(html.unescape(m.group(1)))


def grid(level):
    w, h, tw, th = level
    return math.ceil(w / tw), math.ceil(h / th)  # cols, rows


def detect_order(s, z, level):
    """Return 'row' or 'col' major tile indexing by probing an edge tile."""
    w, h, tw, th = level
    cols, rows = grid(level)
    if cols == 1 or rows == 1:
        return "row"
    edge_w = w - (cols - 1) * tw  # width of last column's tiles
    img = fetch_tile(s, z, cols - 1)  # row-major: last tile of first row
    return "row" if img.width == edge_w or edge_w == tw else "col"


def fetch_tile(s, z, i, retries=4):
    for attempt in range(retries):
        try:
            r = session.get(TILE_URL.format(s=s, z=z, i=i), timeout=60)
            r.raise_for_status()
            from io import BytesIO
            return Image.open(BytesIO(r.content)).convert("RGB")
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)
        finally:
            time.sleep(SLEEP)


def download_slide(s_id, level_idx, meta, out_png):
    levels = meta["levels"]
    level_idx = min(level_idx, len(levels) - 1)
    level = levels[level_idx]
    w, h, tw, th = level
    cols, rows = grid(level)
    order = detect_order(s_id, level_idx, level)
    canvas = Image.new("RGB", (w, h), meta.get("bgColor", "#FFFFFF"))
    n = cols * rows
    for i in range(n):
        if order == "row":
            x, y = (i % cols) * tw, (i // cols) * th
        else:
            x, y = (i // rows) * tw, (i % rows) * th
        canvas.paste(fetch_tile(s_id, level_idx, i), (x, y))
        if (i + 1) % 25 == 0 or i + 1 == n:
            print(f"      tiles {i + 1}/{n}", end="\r", flush=True)
    print()
    canvas.save(out_png, quality=95)
    return w, h


def to_dzi(png_path, dzi_base):
    import pyvips
    img = pyvips.Image.new_from_file(str(png_path))
    img.dzsave(str(dzi_base), suffix=".jpeg[Q=88]", tile_size=254, overlap=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--age", help="only this age id, e.g. 48hpf or 12mpf-male")
    ap.add_argument("--plane", choices=["coronal", "sagittal", "transverse"])
    ap.add_argument("--level", type=int, default=0,
                    help="0=full res (default), 1=half, 2=quarter …")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--hero", action="store_true",
                    help="also save a low-res sagittal preview as the site hero image")
    args = ap.parse_args()

    data = load_atlas_data()
    manifest_path = TILES_OUT / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}

    jobs = []
    for age in data["ages"]:
        if args.age and age["id"] != args.age:
            continue
        for plane, series in age["planes"].items():
            if args.plane and plane != args.plane:
                continue
            for slide in series["slides"]:
                jobs.append((age, plane, slide))

    print(f"{len(jobs)} slides queued (zoom level {args.level})")
    total_px = 0
    for k, (age, plane, slide) in enumerate(jobs, 1):
        key = f'{age["id"]}/{plane}/{slide["atlas"]}_{slide["s"]}'
        out_dir = TILES_OUT / age["id"] / plane
        dzi = out_dir / f'{slide["atlas"]}_{slide["s"]}'
        if manifest.get(key) == "done" and (dzi.with_suffix(".dzi")).exists():
            continue
        print(f'[{k}/{len(jobs)}] {age["label"]} {plane} slide {slide["n"]} '
              f'(atlas={slide["atlas"]} s={slide["s"]})')
        meta = fetch_slide_meta(slide["atlas"], slide["s"])
        lv = meta["levels"][min(args.level, len(meta["levels"]) - 1)]
        total_px += lv[0] * lv[1]
        if args.dry_run:
            print(f'      {lv[0]}x{lv[1]} px')
            continue
        out_dir.mkdir(parents=True, exist_ok=True)
        tmp_png = out_dir / f'{slide["atlas"]}_{slide["s"]}.tmp.png'
        w, h = download_slide(slide["s"], args.level, meta, tmp_png)
        to_dzi(tmp_png, dzi)
        tmp_png.unlink()
        manifest[key] = "done"
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(manifest, indent=1))
        print(f'      -> {dzi}.dzi  ({w}x{h})')

    if args.dry_run:
        gb = total_px * 0.35 / 1e9  # ~0.35 bytes/px as JPEG Q88 with pyramid overhead
        print(f"\nEstimated output: ~{gb:.1f} GB for this selection.")

    if args.hero and not args.dry_run:
        # small sagittal overview of a 12mpf male makes a nice hero background
        meta = fetch_slide_meta(17, 271)
        z = len(meta["levels"]) - 2 if len(meta["levels"]) > 1 else 0
        hero = SITE / "assets/images/hero.jpg"
        tmp = SITE / "assets/images/hero.tmp.png"
        download_slide(271, z, meta, tmp)
        Image.open(tmp).convert("RGB").save(hero, quality=85)
        tmp.unlink()
        print(f"hero image saved to {hero}")

    print("\nDone. When your tiles are uploaded wherever TILE_BASE points,\n"
          "set USE_PSU_FALLBACK: false in site/assets/js/config.js.")


if __name__ == "__main__":
    main()
