"""
FBA Concert Program Scraper
============================
Scrapes concert program PDFs from FBA MPA Online for all years/districts.
Extracts school, director, classification, and repertoire (pieces + composers).

Outputs: fba_programs.csv

URL pattern:
  1. POST to MPAMenu.aspx to discover EventIDs per year/district
  2. GET ConcertProgram.aspx?EventID=X → redirects to generated PDF
  3. Parse PDF with pdfplumber to extract program data
"""

import requests
from bs4 import BeautifulSoup
import re
import time
import csv
import logging
import sys
import os
import tempfile
from pathlib import Path

try:
    import pdfplumber
except ImportError:
    print("Installing pdfplumber...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pdfplumber", "-q"])
    import pdfplumber

# ── Configuration ─────────────────────────────────────────────────────────────

MENU_URL = "https://flmusiced.org/MPAOnline/PublicReports/MPAMenu.aspx?ComponentID=1"
PROGRAM_URL = "https://flmusiced.org/MPAOnline/PublicReports/ConcertProgram.aspx?EventID={eid}"

ALL_YEARS = [
    "2009-2010 ", "2010-2011 ", "2011-2012 ", "2012-2013 ", "2013-2014 ",
    "2014-2015 ", "2015-2016 ", "2016-2017 ", "2017-2018 ", "2018-2019 ",
    "2019-2020 ", "2020-2021 ", "2021-2022 ", "2022-2023 ", "2023-2024 ",
    "2024-2025 ", "2025-2026 ",
]

ALL_DISTRICTS = [str(d) for d in range(1, 24)] + ["30"]  # 30 = State

REQUEST_DELAY = 0.5  # seconds between requests
PDF_DELAY = 1.0      # seconds between PDF downloads
MAX_RETRIES = 3

OUTPUT_FILE = Path("fba_programs.csv")
CHECKPOINT_FILE = Path("fba_programs_checkpoint.txt")
LOG_FILE = Path("fba_programs_scraper.log")

CSV_COLUMNS = [
    "school_year", "district", "event_id", "event_date", "event_day",
    "time", "school", "ensemble", "classification", "director", "principal",
    "piece_1", "composer_1", "grade_1",
    "piece_2", "composer_2", "grade_2",
    "piece_3", "composer_3", "grade_3",
    "piece_4", "composer_4", "grade_4",
]

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger(__name__)

# ── Checkpoint ────────────────────────────────────────────────────────────────

def load_checkpoint():
    done = set()
    if CHECKPOINT_FILE.exists():
        for line in CHECKPOINT_FILE.read_text().splitlines():
            line = line.strip()
            if line:
                done.add(line)
    return done

def save_checkpoint(key):
    with open(CHECKPOINT_FILE, "a") as f:
        f.write(key + "\n")

# ── ASP.NET form helpers ─────────────────────────────────────────────────────

def extract_asp_fields(html):
    soup = BeautifulSoup(html, "html.parser")
    fields = {}
    for name in ["__VIEWSTATE", "__VIEWSTATEGENERATOR", "__VIEWSTATEENCRYPTED", "__EVENTVALIDATION"]:
        tag = soup.find("input", {"name": name})
        fields[name] = tag["value"] if tag and tag.get("value") else ""
    return fields

# ── Step 1: Discover EventIDs ─────────────────────────────────────────────────

def discover_event_ids(session):
    """Iterate all year/district combos, return list of (year, district, event_id, label)."""
    log.info("Fetching menu page for initial ViewState...")
    resp = session.get(MENU_URL)
    resp.raise_for_status()
    asp = extract_asp_fields(resp.text)

    events = []
    done = load_checkpoint()

    for year in ALL_YEARS:
        year_clean = year.strip()
        for district in ALL_DISTRICTS:
            combo_key = f"discover|{year_clean}|{district}"
            if combo_key in done:
                continue

            data = {
                **asp,
                "__EVENTTARGET": "ctl00$Content$ddlDistrict",
                "__EVENTARGUMENT": "",
                "ctl00$Content$ddlYear": year,
                "ctl00$Content$ddlDistrict": district,
            }

            for attempt in range(MAX_RETRIES):
                try:
                    resp = session.post(MENU_URL, data=data)
                    resp.raise_for_status()
                    break
                except Exception as e:
                    log.warning(f"  Retry {attempt+1} for {year_clean} D{district}: {e}")
                    time.sleep(5)
            else:
                log.error(f"  Failed {year_clean} D{district} after {MAX_RETRIES} retries")
                continue

            # Update ASP fields for next request
            asp = extract_asp_fields(resp.text)

            # Extract EventIDs from the grid
            soup = BeautifulSoup(resp.text, "html.parser")
            grid = soup.find("table", id="ctl00_Content_GridView1")
            if not grid:
                save_checkpoint(combo_key)
                time.sleep(REQUEST_DELAY)
                continue

            for row in grid.find_all("tr"):
                cells = row.find_all("td")
                if len(cells) < 2:
                    continue
                label = cells[0].get_text(strip=True).lower()
                # Match Concert MPA events, exclude Solo & Ensemble
                if "concert" in label and "solo" not in label:
                    for link in row.find_all("a", href=True):
                        href = link["href"]
                        m = re.search(r"EventID=(\d+)", href)
                        if m and "ConcertProgram" in href:
                            eid = m.group(1)
                            events.append((year_clean, district, eid, cells[0].get_text(strip=True)))
                            log.info(f"  Found EventID={eid} — {year_clean} D{district} {cells[0].get_text(strip=True)}")

            save_checkpoint(combo_key)
            time.sleep(REQUEST_DELAY)

    return events

# ── Step 2: Parse a Concert Program PDF ───────────────────────────────────────

def parse_program_pdf(pdf_path, school_year, district, event_id):
    """Parse a concert program PDF into a list of record dicts."""
    records = []

    with pdfplumber.open(pdf_path) as pdf:
        full_text = ""
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                full_text += text + "\n"

    if not full_text.strip():
        return records

    # Split into day sections
    lines = full_text.split("\n")

    current_date = ""
    current_day = ""
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # Detect date headers like "Thursday, March 2, 2017"
        date_match = re.match(
            r"^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),?\s+(.+\d{4})$",
            line, re.IGNORECASE
        )
        if date_match:
            current_day = date_match.group(1)
            current_date = date_match.group(2).strip()
            i += 1
            continue

        # Detect ensemble entry: starts with time like "3:45 pm" or "10:00 am"
        time_match = re.match(r"^(\d{1,2}:\d{2}\s*[ap]m)\s+(.+)", line, re.IGNORECASE)
        if time_match:
            perf_time = time_match.group(1).strip()
            rest = time_match.group(2).strip()

            # rest = "School Name Ensemble Name Classification"
            # Classification is usually at the end: A, AA, B, BB, C, CC, J/S-C, J/S-CC, etc.
            class_match = re.search(
                r"\s+((?:J/S-)?(?:AA|A|BB|B|CC|C|D|Open))\s*$",
                rest, re.IGNORECASE
            )
            if class_match:
                classification = class_match.group(1).strip()
                school_ensemble = rest[:class_match.start()].strip()
            else:
                classification = ""
                school_ensemble = rest

            # Next line(s): Director and Principal
            director = ""
            principal = ""
            i += 1
            if i < len(lines):
                dir_line = lines[i].strip()
                dir_match = re.match(r"Director\(s\):\s*(.+?)(?:\s+Principal:\s*(.+))?$", dir_line)
                if dir_match:
                    director = dir_match.group(1).strip()
                    principal = dir_match.group(2).strip() if dir_match.group(2) else ""
                    i += 1

            # Following lines are pieces until next time entry, date, or blank section
            pieces = []
            while i < len(lines):
                pline = lines[i].strip()
                if not pline:
                    i += 1
                    continue
                # Stop if we hit a new time entry, date, or page header
                if re.match(r"^\d{1,2}:\d{2}\s*[ap]m\s+", pline, re.IGNORECASE):
                    break
                if re.match(r"^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),", pline, re.IGNORECASE):
                    break
                if "Florida Bandmasters Association" in pline:
                    i += 1
                    continue
                if re.match(r"^District \d", pline):
                    i += 1
                    continue
                if re.match(r"^(March|April|May|February|January)\s+\d", pline):
                    i += 1
                    continue

                # Parse piece line: "Title Composer Grade" or "Title Composer"
                # Grade is typically a single digit at the end
                grade_match = re.search(r"\s+(\d(?:\.\d)?)\s*$", pline)
                if grade_match:
                    grade = grade_match.group(1)
                    title_composer = pline[:grade_match.start()].strip()
                else:
                    grade = ""
                    title_composer = pline

                # Split title from composer — composer is usually the last word(s)
                # This is tricky; composers often have / for arrangers
                # Common pattern: "Title Name Composer" or "Title Composer/Arranger"
                # We'll store the whole line and let post-processing split it
                pieces.append({
                    "title_composer": title_composer,
                    "grade": grade,
                })
                i += 1

            # Build record
            record = {
                "school_year": school_year,
                "district": district,
                "event_id": event_id,
                "event_date": current_date,
                "event_day": current_day,
                "time": perf_time,
                "school": school_ensemble,
                "ensemble": "",  # embedded in school field for now
                "classification": classification,
                "director": director,
                "principal": principal,
            }

            for j, piece in enumerate(pieces[:4], 1):
                record[f"piece_{j}"] = piece["title_composer"]
                record[f"composer_{j}"] = ""  # parsed in post-processing
                record[f"grade_{j}"] = piece["grade"]

            records.append(record)
            continue

        i += 1

    return records

# ── Step 3: Download and parse all programs ───────────────────────────────────

def scrape_programs(session, events):
    """Download concert program PDFs and parse them."""
    done = load_checkpoint()
    all_records = []

    # Initialize CSV if needed
    write_header = not OUTPUT_FILE.exists() or OUTPUT_FILE.stat().st_size == 0
    outfile = open(OUTPUT_FILE, "a", newline="", encoding="utf-8")
    writer = csv.DictWriter(outfile, fieldnames=CSV_COLUMNS, extrasaction="ignore")
    if write_header:
        writer.writeheader()

    for idx, (year, district, eid, label) in enumerate(events):
        eid_key = f"program|{eid}"
        if eid_key in done:
            continue

        log.info(f"[{idx+1}/{len(events)}] EventID={eid} — {year} D{district} {label}")

        pdf_url = PROGRAM_URL.format(eid=eid)

        for attempt in range(MAX_RETRIES):
            try:
                resp = session.get(pdf_url, allow_redirects=True, timeout=30)
                resp.raise_for_status()

                if resp.headers.get("Content-Type", "").startswith("application/pdf") or \
                   resp.content[:5] == b"%PDF-":
                    break
                else:
                    # May have redirected to a PDF URL
                    log.warning(f"  Non-PDF response, content-type: {resp.headers.get('Content-Type')}")
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(5)
            except Exception as e:
                log.warning(f"  Retry {attempt+1}: {e}")
                time.sleep(5)
        else:
            log.error(f"  Failed to download EventID={eid}")
            save_checkpoint(eid_key)
            continue

        # Save PDF to temp file and parse
        try:
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(resp.content)
                tmp_path = tmp.name

            records = parse_program_pdf(tmp_path, year, district, eid)
            log.info(f"  → {len(records)} ensembles parsed")

            for rec in records:
                writer.writerow(rec)
            outfile.flush()

            all_records.extend(records)
        except Exception as e:
            log.error(f"  Parse error for EventID={eid}: {e}")
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

        save_checkpoint(eid_key)
        time.sleep(PDF_DELAY)

    outfile.close()
    return all_records

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    log.info("=" * 60)
    log.info("FBA Concert Program Scraper")
    log.info("=" * 60)

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (research-scraper; repertoire-database)",
    })

    # Step 1: Discover EventIDs
    log.info("Step 1: Discovering EventIDs...")
    events = discover_event_ids(session)
    log.info(f"Found {len(events)} concert MPA events")

    if not events:
        log.info("No new events to scrape.")
        return

    # Step 2: Download and parse programs
    log.info("Step 2: Downloading and parsing concert programs...")
    records = scrape_programs(session, events)

    log.info(f"\nDone. {len(records)} total ensemble records written to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
