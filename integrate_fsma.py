"""
FSMA MPA Results Integrator
============================
Reads the long-format FSMA export (one row per judge per ensemble)
and pivots it into one row per ensemble per level, matching the
structure used in the UIL results CSV.

Input:  FSMA_MPA_Concert_Results_20242025__*.xlsx
Output: fsma_results.csv
"""

import openpyxl
import csv
from collections import defaultdict
from pathlib import Path

INPUT_FILE = Path.home() / "Downloads" / "FSMA_MPA_Concert_Results_20242025__20260406041525725.xlsx"
OUTPUT_FILE = Path("fsma_results.csv")

# Rating text → numeric (mirrors UIL 1-5 scale)
RATING_MAP = {
    "Superior": 1,
    "Excellent": 2,
    "Good": 3,
    "Fair": 4,
    "Poor": 5,
}

FIELDNAMES = [
    "school_year",
    "component",          # FBA / FOA / FVA
    "school",
    "fsma_school_id",
    "ensemble",
    "directors",
    "level",              # DISTRICT / STATE
    "mpa_type",           # Concert MPA / Marching Band MPA / Jazz Band MPA
    "grade_level",        # High School / Middle School
    "classification",
    "student_count",
    "final_rating",
    "final_rating_num",
    # Concert judges (up to 3)
    "concert_j1",
    "concert_j1_rating",
    "concert_j1_num",
    "concert_j2",
    "concert_j2_rating",
    "concert_j2_num",
    "concert_j3",
    "concert_j3_rating",
    "concert_j3_num",
    # Sight-reading judge
    "sr_j1",
    "sr_j1_rating",
    "sr_j1_num",
    # Music judges (marching/jazz)
    "music_j1",
    "music_j1_rating",
    "music_j1_num",
    "music_j2",
    "music_j2_rating",
    "music_j2_num",
    # Visual/Auxiliary/Percussion/GE/Jazz (catch-all for other categories)
    "other_judges",       # semicolon-separated "Name:Category:Rating"
]


def pivot_fsma(input_path, output_path):
    wb = openpyxl.load_workbook(input_path, read_only=True)
    ws = wb["sheet1"]

    # Group rows by (school, ensemble, level, mpa_type)
    groups = defaultdict(lambda: {"meta": None, "judges": []})

    for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True)):
        vals = [str(c).strip() if c else "" for c in row]
        # cols: 0=SchoolYear, 1=Component, 2=SchoolName, 3=FSMASchoolID,
        #        4=EnsembleName, 5=Directors, 6=Level, 7=MPAType,
        #        8=GradeLevel, 9=Classification, 10=StudentCount,
        #        11=JudgeName, 12=JudgeCategory, 13=JudgeRating, 14=FinalRating

        key = (vals[2], vals[4], vals[6], vals[7])
        if groups[key]["meta"] is None:
            groups[key]["meta"] = {
                "school_year": vals[0],
                "component": vals[1],
                "school": vals[2],
                "fsma_school_id": vals[3],
                "ensemble": vals[4],
                "directors": vals[5],
                "level": vals[6],
                "mpa_type": vals[7],
                "grade_level": vals[8],
                "classification": vals[9],
                "student_count": vals[10],
                "final_rating": vals[14],
                "final_rating_num": RATING_MAP.get(vals[14], ""),
            }
        groups[key]["judges"].append({
            "name": vals[11],
            "category": vals[12],
            "rating": vals[13],
            "rating_num": RATING_MAP.get(vals[13], ""),
        })

    wb.close()

    # Write pivoted CSV
    with open(output_path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDNAMES)
        writer.writeheader()

        for key, group in sorted(groups.items()):
            row = dict(group["meta"])
            judges = group["judges"]

            # Separate by category
            concert = [j for j in judges if j["category"] == "Concert"]
            sr = [j for j in judges if j["category"] == "Sight-Reading"]
            music = [j for j in judges if j["category"] == "Music"]
            other = [j for j in judges if j["category"] not in ("Concert", "Sight-Reading", "Music")]

            # Concert judges (up to 3)
            for idx, j in enumerate(concert[:3], start=1):
                row[f"concert_j{idx}"] = j["name"]
                row[f"concert_j{idx}_rating"] = j["rating"]
                row[f"concert_j{idx}_num"] = j["rating_num"]

            # Sight-reading (typically 1)
            if sr:
                row["sr_j1"] = sr[0]["name"]
                row["sr_j1_rating"] = sr[0]["rating"]
                row["sr_j1_num"] = sr[0]["rating_num"]

            # Music judges (up to 2)
            for idx, j in enumerate(music[:2], start=1):
                row[f"music_j{idx}"] = j["name"]
                row[f"music_j{idx}_rating"] = j["rating"]
                row[f"music_j{idx}_num"] = j["rating_num"]

            # Everything else → semicolon list
            if other:
                row["other_judges"] = "; ".join(
                    f"{j['name']}:{j['category']}:{j['rating']}" for j in other
                )

            # Fill missing keys with empty string
            for f in FIELDNAMES:
                row.setdefault(f, "")

            writer.writerow(row)

    print(f"Wrote {len(groups)} ensemble records to {output_path}")


if __name__ == "__main__":
    pivot_fsma(INPUT_FILE, OUTPUT_FILE)
