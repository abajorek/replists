"""
FBA Concert Program Post-Processor
====================================
Splits combined title+composer fields from FBA program PDFs,
matches against the WindBand Repertoire Database, and flags confidence.

Input:  fba_programs.csv (raw scraped data)
Output: fba_programs_matched.csv (with split title/composer/arranger + confidence)
        fba_programs_review.csv (low-confidence matches for human review)
"""

import pandas as pd
import re
import os
from collections import Counter

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
FBA_FILE = os.path.join(DATA_DIR, "fba_programs.csv")
DB_FILE = os.path.join(DATA_DIR, "WindBand_Repertoire_Database.xlsx")
OUTPUT_FILE = os.path.join(DATA_DIR, "fba_programs_matched.csv")
REVIEW_FILE = os.path.join(DATA_DIR, "fba_programs_review.csv")


def normalize(s):
    """Normalize a string for fuzzy matching."""
    if not s or not isinstance(s, str):
        return ""
    s = s.strip().lower()
    s = re.sub(r"[^\w\s']", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def normalize_title(title):
    """Normalize title, stripping parenthetical suffixes."""
    t = normalize(title)
    t = re.sub(r"\s*\(.*?\)\s*$", "", t)
    return t


def build_db_lookup(db):
    """Build lookup structures from the band database."""
    lookup = {}  # norm_title -> list of (row_dict)
    for _, row in db.iterrows():
        title = str(row.get("Title", "")).strip()
        if not title:
            continue
        nt = normalize_title(title)
        if nt not in lookup:
            lookup[nt] = []
        lookup[nt].append({
            "title": title,
            "composer": str(row.get("Composer", "")).strip(),
            "arranger": str(row.get("Arranger", "")).strip() if pd.notna(row.get("Arranger")) else "",
            "grade": row.get("Grade"),
        })
    return lookup


def split_title_composer(raw_string, db_lookup):
    """
    Split a combined "Title Composer" string using the DB as reference.
    Returns (title, composer, arranger, confidence, db_match).

    Confidence levels:
      HIGH   - exact title match in DB, composer confirmed
      MEDIUM - title match but composer/arranger differs or partial
      LOW    - fuzzy match or couldn't split cleanly
      NONE   - no match found
    """
    if not raw_string or not isinstance(raw_string, str) or raw_string.strip().lower() in ("tbd", ""):
        return "", "", "", "NONE", None

    raw = raw_string.strip()

    # Skip garbage (lone digits, etc.)
    if re.match(r"^\d+$", raw):
        return "", "", "", "NONE", None

    norm_raw = normalize(raw)

    # Pre-process: handle trailing article pattern
    # "Silent Hills of My Childhood, The Farmer" → "The Silent Hills of My Childhood Farmer"
    # "Quiet Rain, A Cummings" → "A Quiet Rain Cummings"
    article_match = re.match(r"^(.+?),\s+(The|A|An)\s+(.*)$", raw, re.IGNORECASE)
    if article_match:
        title_part = article_match.group(1).strip()
        article = article_match.group(2).strip()
        rest = article_match.group(3).strip()
        raw = f"{article} {title_part} {rest}".strip()
        norm_raw = normalize(raw)

    # Strategy 1: Try matching longest DB title prefix
    best_match = None
    best_title_len = 0

    for norm_title, entries in db_lookup.items():
        if not norm_title:
            continue
        # Check if raw string starts with this title
        if norm_raw.startswith(norm_title) and len(norm_title) > best_title_len:
            # What's left after the title?
            remainder = norm_raw[len(norm_title):].strip()
            # Make sure we're not splitting mid-word
            if remainder == "" or remainder[0] == " " or norm_raw[len(norm_title):][0:1] in (" ", ""):
                best_match = (norm_title, entries, remainder.strip())
                best_title_len = len(norm_title)

    if best_match:
        norm_title, entries, remainder_norm = best_match
        # remainder_norm is the composer portion
        entry = entries[0]  # Take first DB match

        # Extract the actual composer text from the raw string
        raw_title_end = len(raw) - len(remainder_norm) if remainder_norm else len(raw)
        # Find where title ends in original string
        for i in range(len(raw), 0, -1):
            if normalize(raw[:i]) == norm_title:
                raw_title_end = i
                break

        matched_title = raw[:raw_title_end].strip()
        raw_composer = raw[raw_title_end:].strip()

        # Check if the raw composer matches DB composer
        db_composer_norm = normalize(entry["composer"])
        raw_composer_norm = normalize(raw_composer)

        # Handle "Composer/Arranger" or "Composer arr. Arranger" patterns in raw
        arranger = ""
        composer_part = raw_composer
        arr_match = re.search(r"[/,]\s*(arr\.?\s+|ed\.?\s+)?(.+)$", raw_composer, re.IGNORECASE)
        if arr_match:
            composer_part = raw_composer[:arr_match.start()].strip()
            arranger = arr_match.group(2).strip() if arr_match.group(2) else ""
        elif re.search(r"\barr\.?\s+", raw_composer, re.IGNORECASE):
            parts = re.split(r"\barr\.?\s+", raw_composer, flags=re.IGNORECASE)
            composer_part = parts[0].strip().rstrip(",").rstrip("/").strip()
            arranger = parts[1].strip() if len(parts) > 1 else ""

        # Determine confidence
        if db_composer_norm and raw_composer_norm:
            # Check if DB composer appears in raw composer
            if db_composer_norm in raw_composer_norm or raw_composer_norm in db_composer_norm:
                confidence = "HIGH"
            elif normalize(composer_part) in db_composer_norm or db_composer_norm in normalize(composer_part):
                confidence = "HIGH"
            else:
                # Composer doesn't match — could be different edition
                confidence = "MEDIUM"
        elif not raw_composer_norm:
            # No composer in raw string but we matched title
            confidence = "MEDIUM"
        else:
            confidence = "MEDIUM"

        return entry["title"], composer_part if composer_part else entry["composer"], \
               arranger if arranger else entry["arranger"], confidence, entry

    # Strategy 1b: Try with article prepended ("Childhood Hymn" → "A Childhood Hymn")
    if not best_match:
        for article in ["a ", "an ", "the "]:
            test = article + norm_raw
            for norm_title, entries in db_lookup.items():
                if test.startswith(norm_title) and len(norm_title) > best_title_len:
                    remainder = test[len(norm_title):].strip()
                    best_match = (norm_title, entries, remainder)
                    best_title_len = len(norm_title)

    # Strategy 2: Try matching with words removed from the end (composer words)
    words = norm_raw.split()
    for n_composer_words in range(1, min(5, len(words))):
        candidate_title = " ".join(words[:-n_composer_words])
        if candidate_title in db_lookup:
            entries = db_lookup[candidate_title]
            entry = entries[0]
            composer_words = " ".join(words[-n_composer_words:])
            raw_composer = raw.split()[-n_composer_words:]
            raw_composer_str = " ".join(raw_composer)

            # Parse arranger from composer portion
            arranger = ""
            composer_part = raw_composer_str
            if "/" in raw_composer_str or "arr" in raw_composer_str.lower():
                arr_match = re.search(r"[/,]\s*(arr\.?\s+|ed\.?\s+)?(.+)$", raw_composer_str, re.IGNORECASE)
                if arr_match:
                    composer_part = raw_composer_str[:arr_match.start()].strip()
                    arranger = arr_match.group(2).strip()

            return entry["title"], composer_part if composer_part else entry["composer"], \
                   arranger if arranger else entry["arranger"], "MEDIUM", entry

    # Strategy 3: No DB match — try to split heuristically
    # Common pattern: last 1-2 words are composer (possibly with arr.)
    arranger = ""
    composer = ""
    title = raw

    # Look for "arr." or "/" separator
    arr_idx = re.search(r"\b(arr\.?\s+|ed\.?\s+|trans\.?\s+)", raw, re.IGNORECASE)
    slash_idx = raw.rfind("/")

    if arr_idx:
        before_arr = raw[:arr_idx.start()].strip().rstrip(",").rstrip("/").strip()
        arranger = raw[arr_idx.end():].strip()
        # Before arr, last word(s) might be composer
        # Try to find title/composer split
        title = before_arr
        composer = ""
    elif slash_idx > 0:
        # "Title Composer/Arranger"
        before_slash = raw[:slash_idx].strip()
        arranger = raw[slash_idx+1:].strip()
        title = before_slash
        composer = ""
    else:
        title = raw
        composer = ""

    return title, composer, arranger, "LOW", None


def process():
    print("Loading band database...")
    db1 = pd.read_excel(DB_FILE, sheet_name="Band Originals")
    try:
        db2 = pd.read_excel(DB_FILE, sheet_name="Transcriptions & Arrangements")
        db = pd.concat([db1, db2], ignore_index=True)
    except Exception:
        db = db1
    print(f"  {len(db)} DB entries")

    db_lookup = build_db_lookup(db)
    print(f"  {len(db_lookup)} unique normalized titles")

    print("Loading FBA programs...")
    fba = pd.read_csv(FBA_FILE, dtype=str)
    print(f"  {len(fba)} ensembles")

    # Process each piece column
    results = []
    review_rows = []
    confidence_counts = Counter()

    for row_idx, row in fba.iterrows():
        result = dict(row)

        for i in [1, 2, 3, 4]:
            raw = row.get(f"piece_{i}", "")
            if pd.isna(raw) or not str(raw).strip():
                result[f"title_{i}"] = ""
                result[f"match_composer_{i}"] = ""
                result[f"match_arranger_{i}"] = ""
                result[f"confidence_{i}"] = ""
                result[f"db_grade_{i}"] = ""
                continue

            title, composer, arranger, confidence, db_entry = split_title_composer(
                str(raw), db_lookup
            )

            result[f"title_{i}"] = title
            result[f"match_composer_{i}"] = composer
            result[f"match_arranger_{i}"] = arranger
            result[f"confidence_{i}"] = confidence
            result[f"db_grade_{i}"] = str(db_entry["grade"]) if db_entry and db_entry.get("grade") else ""

            confidence_counts[confidence] += 1

            if confidence in ("LOW", "NONE") and str(raw).strip().lower() not in ("tbd", ""):
                review_rows.append({
                    "school_year": row.get("school_year", ""),
                    "district": row.get("district", ""),
                    "school": row.get("school", ""),
                    "director": row.get("director", ""),
                    "piece_slot": i,
                    "raw_string": raw,
                    "parsed_title": title,
                    "parsed_composer": composer,
                    "parsed_arranger": arranger,
                    "pdf_grade": row.get(f"grade_{i}", ""),
                    "confidence": confidence,
                })

        results.append(result)

        if (row_idx + 1) % 5000 == 0:
            print(f"  Processed {row_idx + 1}/{len(fba)}...")

    # Write outputs
    out_df = pd.DataFrame(results)
    out_df.to_csv(OUTPUT_FILE, index=False)
    print(f"\nWrote {len(out_df)} rows to {OUTPUT_FILE}")

    if review_rows:
        review_df = pd.DataFrame(review_rows)
        review_df.to_csv(REVIEW_FILE, index=False)
        print(f"Wrote {len(review_df)} rows to {REVIEW_FILE}")

    print(f"\nConfidence distribution:")
    for conf, count in sorted(confidence_counts.items()):
        pct = count / sum(confidence_counts.values()) * 100
        print(f"  {conf}: {count} ({pct:.1f}%)")


if __name__ == "__main__":
    process()
