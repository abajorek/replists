"""
UIL Concert & Sightreading Results Scraper
==========================================
Scrapes texasmusicforms.com/csrrptuilpublic.asp

Output: uil_results.csv
  - school, director, conference, varsity, year, entry_id
  - concert_j1, concert_j2, concert_j3, concert_final
  - sr_j1, sr_j2, sr_j3, sr_final
  - award
  - piece_1, composer_1, piece_2, composer_2, piece_3, composer_3
  - region, event, event_date
  - judges_concert, judges_sr
"""

import requests
from bs4 import BeautifulSoup
import csv
import time
import logging
import re
import sys
from pathlib import Path
from itertools import product

# ── Configuration ─────────────────────────────────────────────────────────────

BASE_URL = "https://www.texasmusicforms.com/csrrptuilpublic.asp"

YEARS   = list(range(2009, 2027))           # 2009–2026
REGIONS = list(range(1, 34)) + [76]         # 1–33 + 76
EVENTS  = {"B": "Band", "C": "Chorus", "O": "Orchestra"}

# Be a polite guest — 1.5s between requests, back off on errors
REQUEST_DELAY   = 1.5   # seconds between requests
BACKOFF_DELAY   = 30    # seconds to wait after a 429/503
MAX_RETRIES     = 3

OUTPUT_FILE     = Path("uil_results.csv")
LOG_FILE        = Path("scraper.log")
CHECKPOINT_FILE = Path("checkpoint.txt")  # saves progress so you can resume

HEADERS = {
    "User-Agent": "Mozilla/5.0 (research scraper; contact: your@email.com)",
    "Accept":     "text/html,application/xhtml+xml",
    "Referer":    BASE_URL,
}

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

# ── CSV columns ───────────────────────────────────────────────────────────────

FIELDNAMES = [
    "region", "event_code", "event_name", "year", "event_date",
    "judges_concert", "judges_sr",
    "school", "director",
    "conference", "varsity", "entry_id",
    "concert_j1", "concert_j2", "concert_j3", "concert_final",
    "sr_j1", "sr_j2", "sr_j3", "sr_final",
    "award",
    "piece_1", "composer_1",
    "piece_2", "composer_2",
    "piece_3", "composer_3",
]

# ── Helpers ───────────────────────────────────────────────────────────────────

def clean(text: str) -> str:
    """Strip whitespace and collapse internal spaces."""
    return re.sub(r"\s+", " ", (text or "").replace("\xa0", " ")).strip()


def parse_piece(raw: str):
    """
    Parse '  Postcard  (Ticheli)' → ('Postcard', 'Ticheli')
    Returns (title, composer) — composer may be empty.
    """
    raw = clean(raw)
    m = re.match(r"^(.*?)\s*\(([^)]+)\)\s*$", raw)
    if m:
        return clean(m.group(1)), clean(m.group(2))
    return raw, ""


def parse_conf_cell(text: str):
    """
    Parse 'AAAAA\nVarsity \n2025\n215080'
    → conference='AAAAA', varsity='Varsity', year='2025', entry_id='215080'
    """
    parts = [clean(p) for p in text.split("\n") if clean(p)]
    conf    = parts[0] if len(parts) > 0 else ""
    varsity = parts[1] if len(parts) > 1 else ""
    entry   = parts[3] if len(parts) > 3 else (parts[2] if len(parts) > 2 else "")
    return conf, varsity, entry


def fetch(session: requests.Session, region: int, year: int, event: str) -> requests.Response | None:
    """POST the form and return the response, with retries."""
    payload = {"cn": "", "ev": event, "yr": str(year), "get": "go", "reg": str(region)}
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.post(BASE_URL, data=payload, headers=HEADERS, timeout=30)
            if resp.status_code == 200:
                return resp
            elif resp.status_code in (429, 503):
                log.warning(f"Rate-limited ({resp.status_code}) — sleeping {BACKOFF_DELAY}s")
                time.sleep(BACKOFF_DELAY)
            else:
                log.warning(f"HTTP {resp.status_code} for region={region} year={year} event={event}")
                return None
        except requests.RequestException as e:
            log.error(f"Request error (attempt {attempt}/{MAX_RETRIES}): {e}")
            time.sleep(BACKOFF_DELAY)
    return None


# ── Parser ────────────────────────────────────────────────────────────────────

def parse_page(html: str, region: int, year: int, event: str) -> list[dict]:
    """Extract all ensemble rows from one result page."""
    soup = BeautifulSoup(html, "html.parser")
    rows_out = []

    # ── Header info (date, judges) ────────────────────────────────────────────
    # The first table has metadata rows before the data table
    event_date    = ""
    judges_concert = []
    judges_sr      = []

    header_tds = soup.find_all("td", class_="text")
    for td in header_tds:
        t = clean(td.get_text())
        if t.startswith("DATE of EVENT"):
            m = re.search(r"(\d{2}/\d{2}/\d{4})", t)
            if m:
                event_date = m.group(1)

    # Judge names are in plain <td> cells adjacent to "Concert Judges" / "Sightreading"
    all_rows = soup.find_all("tr")
    for row in all_rows:
        tds = row.find_all("td")
        for i, td in enumerate(tds):
            t = clean(td.get_text())
            if re.match(r"^\d+\.\s+\w", t):
                # Looks like "1. Jerry Gowler" — figure out concert vs SR by position
                if i <= 1:
                    judges_concert.append(re.sub(r"^\d+\.\s*", "", t))
                else:
                    judges_sr.append(re.sub(r"^\d+\.\s*", "", t))

    judges_concert_str = "; ".join(judges_concert)
    judges_sr_str      = "; ".join(judges_sr)

    # ── Data table ────────────────────────────────────────────────────────────
    # The data table has class "default_table dynamicTable_two"
    data_table = soup.find("table", class_="dynamicTable_two")
    if not data_table:
        return []  # No results for this region/year/event combo

    data_rows = data_table.find_all("tr")

    # Skip the header row (th elements)
    for row in data_rows:
        cells = row.find_all("td")
        if len(cells) < 11:
            continue

        # Cell 0: School & Director
        # Structure (pipe-separated via <br> tags):
        #   "100-Concert Band | School Name | TEA: XXXXXX | City | Director(s)"
        parts = [p.replace("\xa0", "").strip()
                 for p in cells[0].get_text("|").split("|")
                 if p.replace("\xa0", "").strip()]

        # Drop "100-Concert Band" header token
        parts = [p for p in parts if not re.match(r"^\d{3}-", p)]

        school   = parts[0] if parts else ""
        director = parts[-1] if len(parts) > 1 else ""

        # Cell 1: Conf, Varsity, Year, Entry ID
        conf_text = cells[1].get_text("\n")
        conference, varsity, entry_id = parse_conf_cell(conf_text)

        # Cells 2-5: Concert scores (j1, j2, j3, final)
        concert_j1    = clean(cells[2].get_text())
        concert_j2    = clean(cells[3].get_text())
        concert_j3    = clean(cells[4].get_text())
        concert_final = clean(cells[5].get_text())

        # Cells 6-9: SR scores (j1, j2, j3, final)
        sr_j1    = clean(cells[6].get_text())
        sr_j2    = clean(cells[7].get_text())
        sr_j3    = clean(cells[8].get_text())
        sr_final = clean(cells[9].get_text())

        # Cell 10: Award
        award = clean(cells[10].get_text())

        # Cell 11: Selections (newline-separated "Title (Composer)")
        pieces = []
        if len(cells) > 11:
            raw_pieces = cells[11].get_text("\n")
            for line in raw_pieces.split("\n"):
                line = clean(line)
                if line:
                    pieces.append(parse_piece(line))

        # Pad to 3 pieces
        while len(pieces) < 3:
            pieces.append(("", ""))

        rows_out.append({
            "region":          region,
            "event_code":      event,
            "event_name":      EVENTS[event],
            "year":            year,
            "event_date":      event_date,
            "judges_concert":  judges_concert_str,
            "judges_sr":       judges_sr_str,
            "school":          school,
            "director":        director,
            "conference":      conference,
            "varsity":         varsity,
            "entry_id":        entry_id,
            "concert_j1":      concert_j1,
            "concert_j2":      concert_j2,
            "concert_j3":      concert_j3,
            "concert_final":   concert_final,
            "sr_j1":           sr_j1,
            "sr_j2":           sr_j2,
            "sr_j3":           sr_j3,
            "sr_final":        sr_final,
            "award":           award,
            "piece_1":         pieces[0][0],
            "composer_1":      pieces[0][1],
            "piece_2":         pieces[1][0],
            "composer_2":      pieces[1][1],
            "piece_3":         pieces[2][0],
            "composer_3":      pieces[2][1],
        })

    return rows_out


# ── Checkpoint ────────────────────────────────────────────────────────────────

def load_checkpoint() -> set[str]:
    """Return set of already-completed 'region|year|event' combos."""
    done = set()
    if CHECKPOINT_FILE.exists():
        for line in CHECKPOINT_FILE.read_text().splitlines():
            done.add(line.strip())
    return done


def save_checkpoint(region: int, year: int, event: str):
    with open(CHECKPOINT_FILE, "a") as f:
        f.write(f"{region}|{year}|{event}\n")


# ── Main ──────────────────────────────────────────────────────────────────────

def main(
    years=YEARS,
    regions=REGIONS,
    events=list(EVENTS.keys()),
    output=OUTPUT_FILE,
):
    done     = load_checkpoint()
    is_new   = not output.exists()
    total    = len(years) * len(regions) * len(events)
    count    = 0
    written  = 0

    log.info(f"Starting scrape: {len(years)} years × {len(regions)} regions × {len(events)} events = {total} requests")
    log.info(f"Already completed: {len(done)} combos")

    session = requests.Session()

    with open(output, "a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDNAMES)
        if is_new:
            writer.writeheader()

        # Iterate years outer so CSV stays grouped chronologically
        for year, region, event in product(years, regions, events):
            key = f"{region}|{year}|{event}"
            count += 1

            if key in done:
                continue

            log.info(f"[{count}/{total}] Region {region:>2}  {year}  {EVENTS[event]}")

            resp = fetch(session, region, year, event)
            if resp is None:
                log.warning(f"  → Skipped (no response)")
                time.sleep(REQUEST_DELAY)
                continue

            rows = parse_page(resp.text, region, year, event)

            if rows:
                writer.writerows(rows)
                fh.flush()
                written += len(rows)
                log.info(f"  → {len(rows)} ensembles written (total: {written})")
            else:
                log.info(f"  → No results")

            save_checkpoint(region, year, event)
            time.sleep(REQUEST_DELAY)

    log.info(f"\nDone. {written} rows written to {output}")


# ── CLI entry points ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Scrape UIL Concert & Sightreading results")
    parser.add_argument("--years",   nargs="+", type=int, default=YEARS,
                        help="Years to scrape (e.g. --years 2023 2024 2025)")
    parser.add_argument("--regions", nargs="+", type=int, default=REGIONS,
                        help="Regions to scrape (e.g. --regions 1 2 3)")
    parser.add_argument("--events",  nargs="+", default=list(EVENTS.keys()),
                        choices=list(EVENTS.keys()),
                        help="Event types: B C O")
    parser.add_argument("--output",  type=Path, default=OUTPUT_FILE,
                        help="Output CSV path")
    args = parser.parse_args()

    main(
        years=args.years,
        regions=args.regions,
        events=args.events,
        output=args.output,
    )
