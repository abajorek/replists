"""
Convert the repertoire workbooks to Parquet so the app starts fast.

Reading the band workbook with openpyxl takes several seconds — long enough
that the first visitor after a restart watches a spinner. Parquet loads the
same frame roughly 30x faster, so this runs at deploy time and app.py reads
the result. The .xlsx files stay the editable source of truth; app.py falls
back to them whenever a cache is missing or older than its workbook.

Usage:
    python build_cache.py
"""

import hashlib
import json
import os
import sys
import time

import pandas as pd

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(DATA_DIR, "cache")
MANIFEST = os.path.join(CACHE_DIR, "manifest.json")

SOURCES = [
    ("WindBand_Repertoire_Database.xlsx", "Band Originals", "band.parquet"),
    ("Orchestra_Repertoire_Database.xlsx", "Orchestra Repertoire", "orchestra.parquet"),
]


def digest(path: str) -> str:
    """Content hash of a workbook. Freshness cannot rely on mtimes — the caches
    are committed, and a fresh git clone stamps every file with checkout time."""
    sha = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            sha.update(chunk)
    return sha.hexdigest()


def main() -> int:
    os.makedirs(CACHE_DIR, exist_ok=True)
    manifest = {}

    for workbook, sheet, cache_name in SOURCES:
        source = os.path.join(DATA_DIR, workbook)
        target = os.path.join(CACHE_DIR, cache_name)

        if not os.path.exists(source):
            print(f"skip  {workbook} (not found)")
            continue

        start = time.time()
        frame = pd.read_excel(source, sheet_name=sheet)
        frame.to_parquet(target, index=False)
        manifest[cache_name] = {"source": workbook, "sha256": digest(source)}

        size = os.path.getsize(target) / 1024
        print(f"wrote {cache_name:16s} {len(frame):6,} rows  "
              f"{size:6.0f} KB  ({time.time() - start:.1f}s)")

    with open(MANIFEST, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)
    print(f"wrote {'manifest.json':16s} {len(manifest)} entries")

    return 0


if __name__ == "__main__":
    sys.exit(main())
