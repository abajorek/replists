# UIL Concert Results Scraper

## What this does
Scrapes https://www.texasmusicforms.com/csrrptuilpublic.asp — the public UIL
Concert & Sightreading Evaluation results database — and writes a structured
CSV for research use.

## Setup
```bash
pip install -r requirements.txt
```

## Usage

### Full scrape (all years, all regions, all events — ~1,836 requests, ~45 min)
```bash
python scraper.py
```

### Targeted scrape (recommended for testing or partial data)
```bash
# Just band, 2023–2025, regions 1–5
python scraper.py --years 2023 2024 2025 --regions 1 2 3 4 5 --events B

# Single region/year/event
python scraper.py --years 2025 --regions 18 --events B
```

### Resume after interruption
Just re-run — the checkpoint.txt file tracks completed combos and skips them.

## Output columns (uil_results.csv)

| Column | Description |
|---|---|
| region | UIL Region number (1–33, 76) |
| event_code | B / C / O |
| event_name | Band / Chorus / Orchestra |
| year | Performance year |
| event_date | Date of the event (MM/DD/YYYY) |
| judges_concert | Concert judge names (semicolon-separated) |
| judges_sr | Sight-reading judge names |
| school | School name |
| director | Director name |
| conference | AAAAA / 5A / CC / etc. |
| varsity | Varsity / Non-Varsity / Sub-NV |
| entry_id | CutTime entry identifier |
| concert_j1 | Concert judge 1 rating (1–5) |
| concert_j2 | Concert judge 2 rating |
| concert_j3 | Concert judge 3 rating |
| concert_final | Concert final rating |
| sr_j1 | Sightreading judge 1 rating |
| sr_j2 | Sightreading judge 2 rating |
| sr_j3 | Sightreading judge 3 rating |
| sr_final | Sightreading final rating |
| award | Award (A = Sweepstakes, numeric = rating, C = certificate, etc.) |
| piece_1 | Title of first programmed piece |
| composer_1 | Composer of first piece |
| piece_2 | Title of second piece |
| composer_2 | Composer of second piece |
| piece_3 | Title of third piece |
| composer_3 | Composer of third piece |

## Notes
- Rate limit: 1.5s between requests — do not reduce without checking ToS
- Empty result pages (no bands for that region/year/event) are skipped silently
- The `entry_id` field can be used to query individual ensembles via `cn=` param
- Scraper uses a session cookie (Classic ASP ASPSESSIONID) that auto-renews

## Known quirks
- Some older years (pre-2015) have inconsistent HTML table structure
- Region 76 appears to be a special/overflow region
- The `award` field uses multiple formats across years — normalize in post-processing
