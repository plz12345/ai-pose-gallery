#!/usr/bin/env python3
"""Regenerate thumbs/ from the full-size PNGs in img/.

The source site ships white-background JPEG thumbnails that do not match the
dark full-size PNGs in img/. This resizes each full PNG to 300x400 and writes
it as a JPEG to thumbs/, so the gallery grid matches the full images.

Reads data/pose-en.json for the (full, thumb) path pairs. Idempotent: always
overwrites the thumb from the current full.

Usage:
    python3 scripts/make_thumbs.py [--workers N]
"""
import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SIZE = (300, 400)      # matches the existing thumb spec (3:4)
QUALITY = 88           # JPEG quality
TARGET_ASPECT = SIZE[0] / SIZE[1]  # 0.75


def make_one(pair):
    full, thumb = pair
    with Image.open(full) as im:
        im = im.convert("RGB")
        w, h = im.size
        aspect = w / h
        if abs(aspect - TARGET_ASPECT) > 0.02:
            # Non-standard aspect: fit within the box, preserve ratio.
            im.thumbnail(SIZE, Image.LANCZOS)
        else:
            im = im.resize(SIZE, Image.LANCZOS)
        thumb.parent.mkdir(parents=True, exist_ok=True)
        im.save(thumb, "JPEG", quality=QUALITY, optimize=True)
    return thumb


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--workers", type=int, default=8)
    args = ap.parse_args()

    data = json.loads((ROOT / "data" / "pose-en.json").read_text(encoding="utf-8"))
    tasks, missing = [], 0
    for r in data:
        full = ROOT / r["full"]
        thumb = ROOT / r["thumb"]
        if not full.exists():
            missing += 1
            print(f"MISSING full: {r['full']}", file=sys.stderr)
            continue
        tasks.append((full, thumb))

    print(f"regenerating {len(tasks)} thumbs from img/ with {args.workers} workers...")
    done = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(make_one, p) for p in tasks]
        for f in as_completed(futs):
            f.result()  # re-raise any worker exception
            done += 1
            if done % 200 == 0:
                print(f"  {done}/{len(tasks)}")
    print(f"done: {done} thumbs written" + (f" ({missing} fulls missing)" if missing else ""))


if __name__ == "__main__":
    main()
