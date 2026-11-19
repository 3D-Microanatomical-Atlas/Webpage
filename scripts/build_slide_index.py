#!/usr/bin/env python3
"""
Build the index of original Bio-Atlas tile pyramids for the bioatlas.io viewer.

bioatlas_extract.py wrote every slide of the legacy Bio-Atlas database as its
original JPEG tiles:

    <extract>/tiles/<10-digit slide number>/<level>/<tile id>.jpg

Level 0 is full resolution and each further level is half the size. Tiles are
numbered row by row, and the last one or two levels of a slide are stored as a
single image. The viewer can show these tiles as they are (no conversion), but
it needs each slide's size, tile size and number of levels. This script reads
them from <extract>/manifest.csv, checks every level against the files on
disk, and writes

    site/assets/js/slides-index.js

for the slides listed in site/assets/js/atlas-data.js. Each entry is
[width, height, tile width, tile height, levels, first single-image level].

Usage (from the repository root):
    python scripts/build_slide_index.py E:\\LegacyBioAtlas_Histology\\bioatlas_fullres

Requires Python 3.8+ only. Runs on Windows, macOS and Linux.
"""
import argparse
import csv
import json
import os
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"


def load_atlas_index():
    """slide number -> (stage id, plane, position in series)"""
    js = (SITE / "assets/js/atlas-data.js").read_text(encoding="utf-8")
    data = json.loads(js[js.index("{"):js.rindex("}") + 1])
    index = {}
    for age in data["ages"]:
        for plane, series in age["planes"].items():
            for slide in series["slides"]:
                index[slide["s"]] = (age["id"], plane, slide["n"])
    return index


def jpeg_size(path):
    """(width, height) of a JPEG file, or None."""
    with open(path, "rb") as fh:
        d = fh.read(65536)
    i = 2
    while i + 9 < len(d):
        if d[i] != 0xFF:
            return None
        mk = d[i + 1]
        if mk == 0xFF:
            i += 1
            continue
        if mk in (0xC0, 0xC1, 0xC2):
            h, w = struct.unpack(">HH", d[i + 5:i + 9])
            return w, h
        i += 2 + struct.unpack(">H", d[i + 2:i + 4])[0]
    return None


def ceil_div(a, b):
    return -(-a // b)


def check_slide(tiles_dir, w, h, tw, th):
    """Return (levels, first single-image level, problems) for one slide."""
    problems = []
    try:
        names = sorted(int(n) for n in os.listdir(tiles_dir) if n.isdigit())
    except FileNotFoundError:
        return 0, 0, ["no tile folder"]
    if not names or names != list(range(len(names))):
        return 0, 0, ["level folders are not 0..n-1: %s" % names]
    levels = len(names)
    counts, grids = [], []
    for lev in names:
        files = [f for f in os.listdir(os.path.join(tiles_dir, str(lev))) if f.endswith(".jpg")]
        lw, lh = ceil_div(w, 2 ** lev), ceil_div(h, 2 ** lev)
        counts.append((len(files), max((int(f[:-4]) for f in files), default=-1)))
        grids.append((lw, lh, ceil_div(lw, tw) * ceil_div(lh, th)))
    # Single-image levels: from the top down, one tile where a grid would need several.
    single = levels
    for lev in range(levels - 1, -1, -1):
        (n, _), (lw, lh, grid) = counts[lev], grids[lev]
        if n != 1:
            break
        if grid > 1:
            size = jpeg_size(os.path.join(tiles_dir, str(lev), "0.jpg"))
            # The legacy pyramid rounded these images down in places; the viewer
            # stretches a single image over the whole level, so 1-2 px is immaterial.
            if size is None or abs(size[0] - lw) > 2 or abs(size[1] - lh) > 2:
                problems.append("level %d: single tile is %s, level is %dx%d" % (lev, size, lw, lh))
                break
        single = lev
    for lev in range(min(single, levels)):
        (n, top), (lw, lh, grid) = counts[lev], grids[lev]
        if top >= grid:
            problems.append("level %d: tile id %d beyond the %d-tile grid" % (lev, top, grid))
        elif n != grid:
            problems.append("level %d: %d of %d tiles present" % (lev, n, grid))
    return levels, single, problems


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("extract", help="output folder of bioatlas_extract.py (contains manifest.csv and tiles/)")
    args = ap.parse_args()
    extract = Path(args.extract)
    manifest = extract / "manifest.csv"
    if not manifest.is_file():
        sys.exit("Not found: %s" % manifest)

    atlas = load_atlas_index()
    rows = {}
    with open(manifest, newline="", encoding="utf-8", errors="replace") as fh:
        for r in csv.DictReader(fh):
            rows[int(r["slide_id"])] = r

    index, report, absent = {}, [], []
    for s in sorted(atlas):
        stage, plane, n = atlas[s]
        name = "%s %s #%02d (slide %d)" % (stage, plane, n, s)
        r = rows.get(s)
        if r is None:
            absent.append(name)
            continue
        w, h = int(r["width"]), int(r["height"])
        tw, th = (int(v) for v in r["tile_size"].split("x"))
        levels, single, problems = check_slide(str(extract / "tiles" / ("%010d" % s)), w, h, tw, th)
        if levels == 0:
            absent.append(name + ": " + "; ".join(problems))
            continue
        if levels != int(r["levels"]):
            problems.append("manifest lists %s levels, %d on disk" % (r["levels"], levels))
        index[s] = [w, h, tw, th, levels, single]
        if problems:
            report.append(name + ": " + "; ".join(problems))

    out = SITE / "assets/js/slides-index.js"
    body = ",\n".join(' "%d": %s' % (s, json.dumps(v, separators=(",", ":"))) for s, v in sorted(index.items()))
    out.write_text(
        "// Generated by scripts/build_slide_index.py. Do not edit by hand.\n"
        "// Original Bio-Atlas tile pyramids, keyed by Bio-Atlas slide number:\n"
        "// [width, height, tile width, tile height, levels, first single-image level].\n"
        "// The viewer loads <ORIGINAL_TILE_BASE>/<10-digit slide number>/<level>/<tile>.jpg.\n"
        "const BIOATLAS_SLIDES = {\n" + body + "\n};\n", encoding="utf-8")

    print("%d of %d atlas slides indexed -> %s" % (len(index), len(atlas), out.relative_to(ROOT).as_posix()))
    if absent:
        print("\nNot in the extraction (%d); these keep the Penn State link:" % len(absent))
        for line in absent:
            print("  " + line)
    if report:
        print("\nIndexed with notes (%d):" % len(report))
        for line in report:
            print("  " + line)


if __name__ == "__main__":
    main()
