"""
Build Pairings Index
====================
Analyzes UIL results to find which pieces are commonly programmed together.
Outputs pairings.json — a lookup of piece → co-programmed pieces with counts.

Also attempts to fuzzy-match UIL piece titles to the repertoire database
so suggestions link back to database entries.
"""

import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

UIL_FILE = Path("uil_results.csv")
OUTPUT_FILE = Path("pairings.json")

# ---------------------------------------------------------------------------
# Normalization
# ---------------------------------------------------------------------------

def normalize_title(title: str) -> str:
    """Normalize a piece title for matching."""
    if not title:
        return ""
    t = title.strip()
    # Lowercase
    t = t.lower()
    # Remove common suffixes/parentheticals
    t = re.sub(r"\s*\(.*?\)\s*$", "", t)
    # Remove punctuation except apostrophes
    t = re.sub(r"[^\w\s']", " ", t)
    # Collapse whitespace
    t = re.sub(r"\s+", " ", t).strip()
    return t


def normalize_composer(composer: str) -> str:
    if not composer:
        return ""
    c = composer.strip().lower()
    # Take last name if "Last/Arranger" or "Last, First"
    c = re.split(r"[/,]", c)[0].strip()
    c = re.sub(r"[^\w\s']", " ", c)
    c = re.sub(r"\s+", " ", c).strip()
    return c


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build_pairings():
    if not UIL_FILE.exists():
        print(f"Error: {UIL_FILE} not found. Run the UIL scraper first.")
        return

    # Read all programs (sets of pieces per ensemble performance)
    programs = []
    with open(UIL_FILE, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pieces = []
            for i in range(1, 4):
                title = row.get(f"piece_{i}", "").strip()
                composer = row.get(f"composer_{i}", "").strip()
                if title:
                    pieces.append({
                        "title": title,
                        "composer": composer,
                        "norm_title": normalize_title(title),
                        "norm_composer": normalize_composer(composer),
                    })
            if len(pieces) >= 2:
                programs.append(pieces)

    print(f"Loaded {len(programs)} programs with 2+ pieces")

    # Build co-occurrence: for each piece, count what other pieces appear with it
    # Key: (norm_title, norm_composer) → Counter of (norm_title, norm_composer)
    cooccurrence = defaultdict(Counter)
    # Also track display names (most common raw title/composer for each normalized key)
    display_names = defaultdict(Counter)

    for prog in programs:
        keys = []
        for p in prog:
            k = (p["norm_title"], p["norm_composer"])
            keys.append(k)
            display_names[k][(p["title"], p["composer"])] += 1

        # Count pairings
        for i, k1 in enumerate(keys):
            for j, k2 in enumerate(keys):
                if i != j:
                    cooccurrence[k1][k2] += 1

    print(f"Found {len(cooccurrence)} unique pieces with pairing data")

    # Build output: for each piece, top 10 pairings
    pairings = {}
    for piece_key, partners in cooccurrence.items():
        # Get best display name for this piece
        best_display = display_names[piece_key].most_common(1)[0][0]
        piece_id = f"{best_display[0]}|{best_display[1]}"

        top_partners = []
        for partner_key, count in partners.most_common(5):
            if count < 3:  # Only include pairings seen 3+ times
                continue
            partner_display = display_names[partner_key].most_common(1)[0][0]
            top_partners.append({
                "title": partner_display[0],
                "composer": partner_display[1],
                "count": count,
                "norm_title": partner_key[0],
                "norm_composer": partner_key[1],
            })

        if top_partners:
            pairings[piece_id] = {
                "title": best_display[0],
                "composer": best_display[1],
                "norm_title": piece_key[0],
                "norm_composer": piece_key[1],
                "suggestions": top_partners,
            }

    # Also build a normalized lookup for the app to find pairings by title
    norm_lookup = {}
    for piece_id, data in pairings.items():
        norm_key = f"{data['norm_title']}|{data['norm_composer']}"
        norm_lookup[norm_key] = piece_id

    output = {
        "pairings": pairings,
        "norm_lookup": norm_lookup,
        "stats": {
            "total_programs": len(programs),
            "unique_pieces": len(cooccurrence),
            "pieces_with_suggestions": len(pairings),
        },
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(pairings)} pieces with suggestions to {OUTPUT_FILE}")
    print(f"Stats: {output['stats']}")

    # Show a few examples
    print("\n--- Example pairings ---")
    shown = 0
    for pid, data in sorted(pairings.items(), key=lambda x: -max(s["count"] for s in x[1]["suggestions"])):
        if shown >= 5:
            break
        print(f"\n{data['title']} ({data['composer']})")
        for s in data["suggestions"][:3]:
            print(f"  + {s['title']} ({s['composer']}) — {s['count']} times")
        shown += 1


if __name__ == "__main__":
    build_pairings()
