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

import os
import sys
import time

import pandas as pd

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
CACHE_DIR = os.path.join(DATA_DIR, "cache")

SOURCES = [
    ("WindBand_Repertoire_Database.xlsx", "Band Originals", "band.parquet"),
    ("Orchestra_Repertoire_Database.xlsx", "Orchestra Repertoire", "orchestra.parquet"),
]


def main() -> int:
    os.makedirs(CACHE_DIR, exist_ok=True)

    for workbook, sheet, cache_name in SOURCES:
        source = os.path.join(DATA_DIR, workbook)
        target = os.path.join(CACHE_DIR, cache_name)

        if not os.path.exists(source):
            print(f"skip  {workbook} (not found)")
            continue

        start = time.time()
        frame = pd.read_excel(source, sheet_name=sheet)
        frame.to_parquet(target, index=False)
        # Keep mtime ordering unambiguous for app.py's freshness check.
        os.utime(target, None)

        size = os.path.getsize(target) / 1024
        print(f"wrote {cache_name:16s} {len(frame):6,} rows  "
              f"{size:6.0f} KB  ({time.time() - start:.1f}s)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
