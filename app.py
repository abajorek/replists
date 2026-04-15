"""
Moneyband
"""

import streamlit as st
import pandas as pd
import os
import re
import json

# ---------------------------------------------------------------------------
# Page config & custom CSS
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Moneyband",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700;800&display=swap');

    /* Header bar — A's green with gold accent, muted film aesthetic */
    .main-header {
        background: linear-gradient(135deg, #003831 0%, #0A4A40 60%, #1A5C50 100%);
        color: white;
        padding: 1.5rem 2rem;
        border-radius: 10px;
        margin-bottom: 1.5rem;
        border-bottom: 3px solid #C8962E;
    }
    .main-header h1 {
        color: white;
        margin: 0;
        font-family: 'Montserrat', sans-serif;
        font-weight: 800;
        font-size: 2.2rem;
        letter-spacing: 0.02em;
        text-transform: uppercase;
    }
    .main-header .tagline {
        color: #D4A843;
        margin: 0.3rem 0 0 0;
        font-family: 'Montserrat', sans-serif;
        font-weight: 600;
        font-size: 0.85rem;
        letter-spacing: 0.04em;
    }
    .main-header .quote {
        color: #8FBFB0;
        margin: 0.5rem 0 0 0;
        font-size: 0.82rem;
        font-style: italic;
    }

    /* Piece detail card — warm cream, green accent */
    .detail-card {
        background: #F7F4EE;
        border: 1px solid #D6CEBB;
        border-left: 3px solid #003831;
        border-radius: 6px;
        padding: 1.2rem 1.5rem;
        margin: 0.8rem 0;
    }
    .detail-card h4 {
        color: #003831;
        margin: 0 0 0.3rem 0;
        font-family: 'Montserrat', sans-serif;
        font-weight: 700;
    }
    .detail-card .meta { color: #6B6B6B; font-size: 0.9rem; }

    /* Pairing card */
    .pairing-card {
        background: #EFF3F0;
        border: 1px solid #C5D1C8;
        border-radius: 6px;
        padding: 0.7rem 1rem;
        margin: 0.4rem 0;
    }

    /* Program sidebar piece — gold left border */
    .program-piece {
        background: #F7F4EE;
        border-left: 3px solid #C8962E;
        padding: 0.5rem 0.8rem;
        margin-bottom: 0.4rem;
        border-radius: 0 6px 6px 0;
    }

    /* Step indicator */
    .step-indicator {
        background: #003831;
        color: #D4A843;
        display: inline-block;
        width: 28px; height: 28px;
        border-radius: 50%;
        text-align: center;
        line-height: 28px;
        font-family: 'Montserrat', sans-serif;
        font-weight: 700;
        font-size: 0.85rem;
        margin-right: 8px;
    }
    .step-inactive {
        background: #C5C5C5;
        color: white;
    }

    /* Metrics — muted cream with green text */
    [data-testid="stMetric"] {
        background: #F7F4EE;
        border: 1px solid #D6CEBB;
        padding: 0.8rem;
        border-radius: 6px;
    }
    [data-testid="stMetricValue"] {
        color: #003831;
        font-family: 'Montserrat', sans-serif;
        font-weight: 700;
    }

    [data-testid="stSidebar"] { background-color: #F5F3EE; }

    /* Tab styling */
    button[data-baseweb="tab"] {
        font-family: 'Montserrat', sans-serif;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Data paths
# ---------------------------------------------------------------------------

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
BAND_FILE = os.path.join(DATA_DIR, "WindBand_Repertoire_Database.xlsx")
ORCH_FILE = os.path.join(DATA_DIR, "Orchestra_Repertoire_Database.xlsx")
PAIRINGS_FILE = os.path.join(DATA_DIR, "pairings.json")

# ---------------------------------------------------------------------------
# Plain-language sort options
# ---------------------------------------------------------------------------

SORT_OPTIONS = {
    "Recommended overall": {
        "col": "Best Bet",
        "help": "A combined score weighing adjudication results and professional endorsement. "
                "Higher means the piece is both well-regarded by experts and performs well at festival.",
    },
    "Strongest at festival": {
        "col": "MPA Confidence",
        "help": "How consistently this piece earns top ratings at Music Performance Assessment (MPA) — "
                "adjudicated festivals where ensembles perform and receive ratings from a panel of judges. "
                "Higher means ensembles playing this piece reliably earn strong ratings.",
    },
    "Most endorsed by professionals": {
        "col": "Street Cred",
        "help": "How widely this piece has been vetted by professional sources — teaching guides, "
                "director recommendations, prescribed music lists, and composer diversity databases. "
                "Higher means more experts across the profession consider this a strong piece.",
    },
    "Most performed": {
        "col": "Total Perfs",
        "help": "How many times this piece has been programmed at festivals. "
                "A high number means many directors have chosen this piece — but popularity alone "
                "doesn't mean it's the right fit for your ensemble.",
    },
    "Alphabetical": {
        "col": "Title",
        "help": "Sort by title A–Z.",
    },
}

# Orchestra now has MPA data from UIL
ORCH_SORT_OPTIONS = {
    "Recommended overall": SORT_OPTIONS["Recommended overall"],
    "Strongest at festival": SORT_OPTIONS["Strongest at festival"],
    "Most endorsed by professionals": SORT_OPTIONS["Most endorsed by professionals"],
    "Most performed": SORT_OPTIONS["Most performed"],
    "Alphabetical": SORT_OPTIONS["Alphabetical"],
}

# Category taxonomy: main category → individual tags
CATEGORY_GROUPS = {
    "Form & Structure": [
        "Multi-Movement Works", "Suites", "Symphonies", "Concertos",
        "Overtures", "Fantasias", "Fugues", "Theme and Variations",
        "Serenades", "Tone Poems",
    ],
    "Style & Genre": [
        "Marches", "Jazz-Tinged Works", "Minimalism", "Aleatoric Works",
        "Black American Music", "Novelty/Pops Music", "Waltzes",
    ],
    "Source & Basis": [
        "Folksong-based", "Hymns", "Chorales/Preludes", "Sacred",
        "Literary", "Opera", "Broadway", "TV/Film", "Video Games",
        "Renaissance (as basis)", "Carols",
    ],
    "Type & Technique": [
        "Arrangements", "Transcriptions", "Medleys", "Narrated Works",
        "Modular Works", "Multimedia Works", "Electronics",
        "Surround-Sound", "Vocal Choir (works employing)",
    ],
    "Character & Purpose": [
        "Elegies", "Fanfares", "Holiday Music", "Patriotic",
        "Socially Relevant", "Award Winners", "Audience Participation",
    ],
}

# Display columns (plain-language headers mapped later)
BAND_DISPLAY = ["Title", "Composer", "Arranger", "Grade", "Best Bet", "MPA Confidence",
                "Street Cred", "ICD Diversity", "Trend Direction", "Categories", "On CBA PML"]
ORCH_DISPLAY = ["Title", "Composer", "Arranger", "Grade", "Best Bet", "MPA Confidence",
                "Street Cred", "% Superior", "FL MPA Perfs", "ICD Diversity",
                "Trend Direction", "Ensemble", "On TMTP"]

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner="Loading band repertoire...")
def load_band() -> pd.DataFrame:
    return pd.read_excel(BAND_FILE, sheet_name="Band Originals")

@st.cache_data(show_spinner="Loading orchestra repertoire...")
def load_orchestra() -> pd.DataFrame:
    return pd.read_excel(ORCH_FILE, sheet_name="Orchestra Repertoire")

@st.cache_data(show_spinner=False)
def load_pairings():
    if not os.path.exists(PAIRINGS_FILE):
        return None
    with open(PAIRINGS_FILE, encoding="utf-8") as f:
        return json.load(f)

def safe_load(loader, label):
    try:
        return loader(), None
    except FileNotFoundError:
        return None, f"{label} data file not found. Place the XLSX in the app directory."
    except Exception as e:
        return None, f"Error loading {label} data: {e}"

# ---------------------------------------------------------------------------
# Pairings helpers
# ---------------------------------------------------------------------------

def _norm_title(title: str) -> str:
    if not title: return ""
    t = title.strip().lower()
    t = re.sub(r"\s*\(.*?\)\s*$", "", t)
    t = re.sub(r"[^\w\s']", " ", t)
    return re.sub(r"\s+", " ", t).strip()

def _norm_composer(composer: str) -> str:
    if not composer: return ""
    c = composer.strip().lower()
    c = re.split(r"[/,]", c)[0].strip()
    c = re.sub(r"[^\w\s']", " ", c)
    return re.sub(r"\s+", " ", c).strip()

def get_pairings(title, composer, pairings_data, limit=5):
    if not pairings_data: return []
    norm_key = f"{_norm_title(title)}|{_norm_composer(composer)}"
    lookup = pairings_data.get("norm_lookup", {})
    piece_id = lookup.get(norm_key)
    if not piece_id:
        tn = _norm_title(title)
        for nk, pid in lookup.items():
            if nk.startswith(tn + "|"):
                piece_id = pid
                break
    if not piece_id: return []
    entry = pairings_data.get("pairings", {}).get(piece_id, {})
    return entry.get("suggestions", [])[:limit]


def find_piece_in_db(title, composer, source_df):
    """Find a piece in the database by matching on normalized title/composer."""
    nt = _norm_title(title)
    nc = _norm_composer(composer)
    norm_titles = source_df["Title"].fillna("").apply(_norm_title)
    norm_composers = source_df["Composer"].fillna("").apply(_norm_composer)
    # Exact match on both
    mask = (norm_titles == nt) & (norm_composers == nc)
    if mask.any():
        return source_df.loc[mask.idxmax()]
    # Title-only fallback
    mask_t = norm_titles == nt
    if mask_t.any():
        return source_df.loc[mask_t.idxmax()]
    return None

def is_march(row):
    """Check if a piece is likely a march based on style tags or categories."""
    for col in ["Style Tags", "Categories", "Style Category"]:
        val = str(row.get(col, "")).lower()
        if "march" in val:
            return True
    title = str(row.get("Title", "")).lower()
    if "march" in title:
        return True
    return False


def get_marches(source_df):
    """Extract all marches from the band database."""
    mask = (
        source_df["Categories"].fillna("").str.contains("March", case=False, regex=False)
        | source_df["Title"].fillna("").str.lower().str.contains("march", regex=False)
    )
    return source_df[mask].copy()


MARCH_SORT_OPTIONS = {
    "Recommended overall": {
        "col": "Best Bet",
        "help": "Combined score weighing adjudication results and professional endorsement.",
    },
    "Highest superior rate": {
        "col": "% Superior",
        "help": "What percentage of festival performances earned the top rating (Superior / 1). "
                "Higher means ensembles playing this march reliably earn a 1.",
    },
    "Strongest at festival": {
        "col": "MPA Confidence",
        "help": "How consistently this march earns top ratings at adjudicated festivals.",
    },
    "Most performed": {
        "col": "Total Perfs",
        "help": "How many times this march has been programmed at festivals.",
    },
    "Most endorsed by professionals": {
        "col": "Street Cred",
        "help": "How widely this march is vetted by professional sources and teaching guides.",
    },
    "Alphabetical": {
        "col": "Title",
        "help": "Sort by title A–Z.",
    },
}


def apply_march_filters(df, key_prefix="march_"):
    """Sidebar filters specific to the march selector."""
    kp = key_prefix

    grades = sorted(df["Grade"].dropna().unique())
    sel_grades = st.sidebar.multiselect("March grade level", grades, default=[], key=f"{kp}grade")
    if sel_grades:
        df = df[df["Grade"].isin(sel_grades)]

    if st.sidebar.checkbox("Prestige director picks only", key=f"{kp}prestige",
                           help="Marches favored by directors with 80%+ superior rates across 5+ years."):
        df = df[df["Dir Tier 1"].notna() | df["Dir Tier 2"].notna()]

    if st.sidebar.checkbox("On TMTP March list", key=f"{kp}tmtp",
                           help="Featured in Teaching Music Through Performance in Band: March Collection."):
        df = df[df["TMTP March"].astype(str) == "True"]

    if st.sidebar.checkbox("Underrepresented composers only (ICD)", key=f"{kp}urm"):
        df = df[df["ICD Diversity"].notna() & (df["ICD Diversity"].astype(str).str.strip() != "")]

    if "On CBA PML" in df.columns:
        if st.sidebar.checkbox("On CBA Prescribed Music List", key=f"{kp}cba"):
            df = df[df["On CBA PML"].notna() & (df["On CBA PML"].astype(str).str.strip() != "")]

    # Patriotic filter
    if st.sidebar.checkbox("Patriotic marches only", key=f"{kp}patriotic"):
        df = df[df["Categories"].fillna("").str.contains("Patriotic", case=False, regex=False)]

    # Trend filter
    trends = sorted(df["Trend Direction"].dropna().unique())
    if trends:
        sel_trend = st.sidebar.multiselect("Popularity trend", trends, default=[], key=f"{kp}trend",
                                           help="Rising = gaining popularity. Declining = fading from programs.")
        if sel_trend:
            df = df[df["Trend Direction"].isin(sel_trend)]

    search = st.sidebar.text_input("Search march title / composer", key=f"{kp}search")
    if search:
        s = search.lower()
        df = df[
            df["Title"].fillna("").str.lower().str.contains(s, regex=False)
            | df["Composer"].fillna("").str.lower().str.contains(s, regex=False)
        ]

    return df

# ---------------------------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------------------------

def apply_filters(df, is_band, key_prefix=""):
    kp = key_prefix

    grades = sorted(df["Grade"].dropna().unique())
    sel_grades = st.sidebar.multiselect("Grade level", grades, default=[], key=f"{kp}grade")
    if sel_grades:
        df = df[df["Grade"].isin(sel_grades)]

    if "ICD Diversity" in df.columns:
        if st.sidebar.checkbox("Underrepresented composers only (ICD)", key=f"{kp}urm"):
            df = df[df["ICD Diversity"].notna() & (df["ICD Diversity"].astype(str).str.strip() != "")]

    if is_band and "Categories" in df.columns:
        # Each group is its own filter. Within a group: OR. Across groups: AND.
        # e.g., (Marches OR Jazz) AND (Suites OR Symphonies) — must match
        # at least one tag from every group that has selections.
        group_selections = {}
        for group_name, group_tags in CATEGORY_GROUPS.items():
            present = [t for t in group_tags if df["Categories"].fillna("").str.contains(t, regex=False).any()]
            if present:
                sel = st.sidebar.multiselect(
                    group_name,
                    present,
                    default=[],
                    key=f"{kp}cat_{group_name}",
                )
                if sel:
                    group_selections[group_name] = sel
        # Apply: piece must match at least one tag from EACH active group
        for group_name, tags in group_selections.items():
            df = df[df["Categories"].apply(
                lambda v: any(t in str(v) for t in tags) if pd.notna(v) else False
            )]

    if not is_band and "Ensemble" in df.columns:
        ens = sorted(df["Ensemble"].dropna().unique())
        if ens:
            sel_ens = st.sidebar.multiselect("Ensemble type", ens, default=[], key=f"{kp}ens")
            if sel_ens:
                df = df[df["Ensemble"].isin(sel_ens)]

    if not is_band and "Midwest Director Pick" in df.columns:
        if st.sidebar.checkbox("Midwest Clinic director picks only", key=f"{kp}midwest",
                               help="Pieces programmed 2+ times by directors whose orchestras "
                                    "have performed at the Midwest Clinic."):
            df = df[df["Midwest Director Pick"].notna() & (df["Midwest Director Pick"].astype(str).str.strip() != "")]

    if is_band and "On CBA PML" in df.columns:
        if st.sidebar.checkbox("On CBA Prescribed Music List only", key=f"{kp}cba"):
            df = df[df["On CBA PML"].notna() & (df["On CBA PML"].astype(str).str.strip() != "")]

    search = st.sidebar.text_input("Search title / composer", key=f"{kp}search")
    if search:
        s = search.lower()
        df = df[
            df["Title"].fillna("").str.lower().str.contains(s, regex=False)
            | df["Composer"].fillna("").str.lower().str.contains(s, regex=False)
        ]

    return df

# ---------------------------------------------------------------------------
# Render a piece detail card
# ---------------------------------------------------------------------------

def render_piece_card(row, pairings_data, source_df, is_band, show_add=False, prog_titles=None):
    """Render a rich detail card for a piece. Returns True if user clicked Add."""
    added = False
    title = row.get("Title", "?")
    composer = row.get("Composer", "")
    grade = row.get("Grade", "?")

    arranger = row.get("Arranger", "")
    arr_str = ""
    if pd.notna(arranger) and str(arranger).strip():
        arr_str = f" (arr. {arranger})"

    st.markdown(
        f'<div class="detail-card">'
        f'<h4>{title}</h4>'
        f'<div class="meta">{composer}{arr_str} · Grade {grade}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    # Info columns
    c1, c2 = st.columns(2)

    with c1:
        # Performance context
        bb = row.get("Best Bet", "")
        if pd.notna(bb) and str(bb).strip():
            st.markdown(f"**Overall recommendation:** {float(bb):.2f}/100")
        mpa = row.get("MPA Confidence", "")
        if pd.notna(mpa) and str(mpa).strip():
            st.markdown(f"**Festival performance strength:** {float(mpa):.2f}/100")
        sc = row.get("Street Cred", "")
        if pd.notna(sc) and str(sc).strip():
            st.markdown(f"**Professional endorsement:** {float(sc):.2f}")
        pct_sup = row.get("% Superior", "")
        if pd.notna(pct_sup) and str(pct_sup).strip():
            st.markdown(f"**Superior rate:** {float(pct_sup):.1f}%")
        tp = row.get("Total Perfs", "")
        if pd.notna(tp) and str(tp).strip():
            st.markdown(f"**Times performed at festival:** {int(tp):,}")
        fl_perfs = row.get("FL MPA Perfs", "")
        if pd.notna(fl_perfs) and str(fl_perfs).strip():
            fl_sup = row.get("FL MPA % Superior", "")
            fl_label = f"**Florida MPA:** {int(float(fl_perfs)):,} performances"
            if pd.notna(fl_sup) and str(fl_sup).strip():
                fl_label += f", {float(fl_sup):.1f}% Superior"
            st.markdown(fl_label)
        trend = row.get("Trend Direction", "")
        if pd.notna(trend) and str(trend).strip():
            st.markdown(f"**Trend:** {trend}")

    with c2:
        # Style & identity
        cats = row.get("Categories", "")
        if pd.notna(cats) and str(cats).strip():
            st.markdown(f"**Style:** {cats}")
        tags = row.get("Style Tags", "")
        if pd.notna(tags) and str(tags).strip():
            st.markdown(f"**Character:** {tags}")
        icd = row.get("ICD Diversity", "")
        if pd.notna(icd) and str(icd).strip():
            detail = row.get("ICD Detail", "")
            label = f"{icd}"
            if pd.notna(detail) and str(detail).strip():
                label += f" — {detail}"
            st.markdown(f"**Composer identity (ICD):** {label}")
        ens = row.get("Ensemble", "")
        if pd.notna(ens) and str(ens).strip():
            st.markdown(f"**Ensemble:** {ens}")
        tmtp_march = row.get("TMTP March", "")
        if str(tmtp_march) == "True":
            st.markdown("**TMTP March Collection:** Yes")
        dir1 = row.get("Dir Tier 1", "")
        dir2 = row.get("Dir Tier 2", "")
        if pd.notna(dir1) and str(dir1).strip():
            st.markdown("**Prestige director pick:** Tier 1")
        elif pd.notna(dir2) and str(dir2).strip():
            st.markdown("**Prestige director pick:** Tier 2")
        mw = row.get("Midwest Director Pick", "")
        if pd.notna(mw) and str(mw).strip():
            st.markdown("**Midwest Clinic director pick:** Yes")
        cba = row.get("On CBA PML", "")
        if pd.notna(cba) and str(cba).strip():
            st.markdown("**On CBA Prescribed Music List:** Yes")
        sl = row.get("State List Count", "")
        if pd.notna(sl) and str(sl).strip() and str(sl).strip() != "0":
            st.markdown(f"**On state prescribed lists:** {int(sl)} states")

    # Pairings (skip for marches)
    row_dict = row if isinstance(row, dict) else row.to_dict()
    if not is_march(row_dict) and pairings_data:
        pairs = get_pairings(title, composer, pairings_data)
        if pairs:
            st.markdown("**Commonly performed alongside:**")
            st.caption("Based on 479,000+ ensemble programs from UIL Concert & Sightreading evaluations.")
            for p in pairs[:4]:
                already = False
                if prog_titles:
                    pk = (_norm_title(p["title"]), _norm_composer(p["composer"]))
                    already = pk in prog_titles
                status = " *(already in your program)*" if already else ""
                st.markdown(
                    f'<div class="pairing-card">'
                    f'<strong>{p["title"]}</strong> — {p["composer"]} '
                    f'<span style="color:#6B6B6B;">({p["count"]:,}× together)</span>'
                    f'{status}</div>',
                    unsafe_allow_html=True,
                )

    if show_add:
        if st.button(f"Add \"{title}\" to program", key=f"add_card_{hash(title+composer)}",
                     type="primary"):
            added = True

    return added


# ---------------------------------------------------------------------------
# Program state
# ---------------------------------------------------------------------------

def init_program():
    if "program" not in st.session_state:
        st.session_state["program"] = []
    if "wizard_step" not in st.session_state:
        st.session_state["wizard_step"] = 1

def add_piece(row_dict):
    prog = st.session_state["program"]
    key = (row_dict.get("Title", ""), row_dict.get("Composer", ""))
    existing = [(p.get("Title", ""), p.get("Composer", "")) for p in prog]
    if key not in existing and len(prog) < 3:
        prog.append(row_dict)
        st.session_state["wizard_step"] = len(prog) + 1

def remove_piece(idx):
    prog = st.session_state["program"]
    if 0 <= idx < len(prog):
        prog.pop(idx)
        st.session_state["wizard_step"] = len(prog) + 1

def render_program_sidebar():
    prog = st.session_state["program"]
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Your Program")

    if not prog:
        st.sidebar.info("No pieces selected yet.")
        return

    for i, p in enumerate(prog):
        st.sidebar.markdown(
            f'<div class="program-piece">'
            f'<strong>{i+1}. {p.get("Title", "?")}</strong><br>'
            f'<span style="font-size:0.85rem;color:#6B6B6B;">'
            f'{p.get("Composer", "")} · Gr {p.get("Grade", "?")}</span></div>',
            unsafe_allow_html=True,
        )
        if st.sidebar.button("Remove", key=f"rm_{i}"):
            remove_piece(i)
            st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Program Evaluation")
    st.sidebar.caption("Based on TMAA adjudication criteria and FBA mentoring guidance.")

    score = 0
    max_score = 0
    checks = []

    # --- 1. Grade spread (difficulty appropriateness) ---
    grades = [p["Grade"] for p in prog if pd.notna(p.get("Grade"))]
    max_score += 20
    if grades:
        grade_range = max(grades) - min(grades)
        st.sidebar.markdown(f"**Grade range:** {min(grades)} – {max(grades)}")
        if len(grades) > 1 and len(set(grades)) == 1:
            checks.append(("warning", "Same grade throughout — consider varying difficulty."))
            score += 10
        elif grade_range <= 2:
            checks.append(("success", f"Good grade spread ({grade_range} levels) ✓"))
            score += 20
        elif grade_range > 3:
            checks.append(("warning", f"Wide grade spread ({grade_range} levels) — may signal mismatch."))
            score += 5
        else:
            score += 15

    # --- 2. Stylistic contrast ---
    max_score += 20
    all_tags = set()
    all_cats = set()
    for p in prog:
        for col in ["Style Tags", "Categories"]:
            val = p.get(col)
            if pd.notna(val) and val:
                for t in str(val).split(";"):
                    t = t.strip()
                    if t:
                        all_tags.add(t)
                for t in str(val).split(","):
                    t = t.strip()
                    if t:
                        all_cats.add(t)
    if len(all_tags) >= 4 or len(all_cats) >= 3:
        checks.append(("success", f"Strong stylistic contrast ({len(all_cats)} categories) ✓"))
        score += 20
    elif len(all_tags) >= 2 or len(all_cats) >= 2:
        checks.append(("info", f"Some contrast ({len(all_cats)} categories) — could be stronger."))
        score += 12
    elif prog:
        checks.append(("warning", "Limited style data — ensure tempo/character variety."))
        score += 5

    # --- 3. Composer diversity (ICD) ---
    max_score += 15
    has_div = any(
        pd.notna(p.get("ICD Diversity")) and str(p.get("ICD Diversity", "")).strip()
        for p in prog
    )
    if has_div:
        checks.append(("success", "Includes underrepresented composer (ICD) ✓"))
        score += 15
    else:
        checks.append(("info", "No ICD composer — consider adding one."))
        score += 5

    # --- 4. Track record (pieces with strong MPA history) ---
    max_score += 20
    sup_rates = []
    for p in prog:
        sr = p.get("% Superior")
        if pd.notna(sr) and str(sr).strip():
            sup_rates.append(float(sr))
        else:
            fl_sr = p.get("FL MPA % Superior")
            if pd.notna(fl_sr) and str(fl_sr).strip():
                sup_rates.append(float(fl_sr))
    if sup_rates:
        avg_sup = sum(sup_rates) / len(sup_rates)
        if avg_sup >= 50:
            checks.append(("success", f"Strong MPA track record (avg {avg_sup:.0f}% superior) ✓"))
            score += 20
        elif avg_sup >= 30:
            checks.append(("info", f"Moderate MPA record (avg {avg_sup:.0f}% superior)."))
            score += 12
        else:
            checks.append(("warning", f"Low MPA record (avg {avg_sup:.0f}% superior) — challenging choices."))
            score += 5
    else:
        checks.append(("info", "No MPA history available for these pieces."))
        score += 10

    # --- 5. Edition clarity (arranger specified for transcriptions) ---
    max_score += 15
    cats_str = " ".join(str(p.get("Categories", "")) for p in prog).lower()
    is_transcription = "transcription" in cats_str or "arrangement" in cats_str
    missing_arranger = any(
        (not p.get("Arranger") or pd.isna(p.get("Arranger")) or str(p.get("Arranger", "")).strip() in ("", "nan"))
        and ("/" in str(p.get("Composer", "")) or is_transcription)
        for p in prog
    )
    if is_transcription and missing_arranger:
        checks.append(("error", "Transcription/arrangement missing arranger — verify edition! Wrong edition = DQ."))
        score += 0
    elif is_transcription:
        checks.append(("success", "Transcription with arranger specified ✓"))
        score += 15
    else:
        score += 15  # Not a transcription, not an issue

    # --- 6. Composer variety ---
    max_score += 10
    composers = set()
    for p in prog:
        c = str(p.get("Composer", "")).strip().lower().split(",")[0]
        if c and c != "nan":
            composers.add(c)
    if len(composers) >= len(prog) and len(prog) > 1:
        checks.append(("success", "All different composers ✓"))
        score += 10
    elif len(prog) > 1:
        checks.append(("warning", "Repeated composer — UIL requires different composers for orchestra."))
        score += 0

    # --- Display results ---
    if max_score > 0:
        pct = score / max_score * 100
        if pct >= 80:
            st.sidebar.success(f"**Program Score: {pct:.0f}/100**")
        elif pct >= 60:
            st.sidebar.info(f"**Program Score: {pct:.0f}/100**")
        else:
            st.sidebar.warning(f"**Program Score: {pct:.0f}/100**")

    for level, msg in checks:
        if level == "success":
            st.sidebar.success(msg)
        elif level == "warning":
            st.sidebar.warning(msg)
        elif level == "error":
            st.sidebar.error(msg)
        else:
            st.sidebar.info(msg)


def export_csv(prog):
    cols = ["Title", "Composer", "Arranger", "Grade", "Best Bet", "Street Cred",
            "MPA Confidence", "ICD Diversity", "ICD Detail", "Categories"]
    rows = [{c: p.get(c, "") for c in cols} for p in prog]
    return pd.DataFrame(rows).to_csv(index=False)


def export_text(prog):
    lines = ["ADJUDICATED CONCERT PROGRAM", "=" * 40, ""]
    for i, p in enumerate(prog, 1):
        lines.append(f"{i}. {p.get('Title', '?')}")
        composer = p.get("Composer", "")
        arranger = p.get("Arranger", "")
        credit = composer
        if arranger and pd.notna(arranger) and str(arranger).strip():
            credit += f" (arr. {arranger})"
        lines.append(f"   {credit}")
        lines.append(f"   Grade {p.get('Grade', '?')}")
        icd = p.get("ICD Diversity", "")
        if pd.notna(icd) and str(icd).strip():
            lines.append(f"   Composer identity (ICD): {icd} — {p.get('ICD Detail', '')}")
        lines.append("")

    grades = [p["Grade"] for p in prog if pd.notna(p.get("Grade"))]
    if grades:
        lines.append(f"Grade range: {min(grades)} – {max(grades)}")
    has_div = any(pd.notna(p.get("ICD Diversity")) and str(p.get("ICD Diversity", "")).strip() for p in prog)
    lines.append(f"Underrepresented composer included (ICD): {'Yes' if has_div else 'No'}")
    lines.append("")
    lines.append("Generated with Moneyband")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Concert Themer — thematic program generator
# ---------------------------------------------------------------------------

THEME_DECKS = [
    {
        "name": "Something Old, Something New, Something Borrowed, Something Blue",
        "emoji": "💍",
        "category": "classic",
        "description": "The wedding toast of concert programs.",
        "slots": [
            {
                "label": "Something Old",
                "hint": "A piece composed before 1960",
                "match": lambda df: df[df["Year"].apply(
                    lambda y: pd.notna(y) and float(y) < 1960
                )] if "Year" in df.columns else df[df["Title"].fillna("").str.contains(
                    "Suite of Old|Ancient|Antique|Renaissance|Baroque|Gregorian|Holst|Grainger|Sousa",
                    case=False, regex=True)],
            },
            {
                "label": "Something New",
                "hint": "A piece composed after 2015",
                "match": lambda df: df[df["Year"].apply(
                    lambda y: pd.notna(y) and float(y) > 2015
                )] if "Year" in df.columns else df[df["Title"].fillna("").str.contains(
                    "New|Modern|Future|Tomorrow|Dawn|Arise",
                    case=False, regex=True)],
            },
            {
                "label": "Something Borrowed",
                "hint": "A transcription or arrangement",
                "match": lambda df: df[
                    df["Categories"].fillna("").str.contains("Transcription|Arrangement", case=False, regex=True)
                ] if "Categories" in df.columns else df[df["Arranger"].notna() & (df["Arranger"].astype(str).str.strip() != "")],
            },
            {
                "label": "Something Blue",
                "hint": "A piece with 'blue' in the title",
                "match": lambda df: df[df["Title"].fillna("").str.contains("blue", case=False, regex=False)],
            },
        ],
    },
    {
        "name": "Don't Whiz on the Electric Fence",
        "emoji": "⚡",
        "category": "funny",
        "description": "A Ren & Stimpy life lesson, in three movements.",
        "slots": [
            {
                "label": "The Dare",
                "hint": "Something bold and reckless",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Bold|Brave|Dare|Fierce|Wild|Frenzy|Rush|Charge|Reckless|Rebel|Fortune Favors",
                    case=False, regex=True)],
            },
            {
                "label": "The Fence",
                "hint": "Electricity, lightning, or shock",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Electric|Lightning|Thunder|Shock|Spark|Volt|Storm|Tempest|Surge|Flash|Blitz|Jolt",
                    case=False, regex=True)],
            },
            {
                "label": "The Lesson Learned",
                "hint": "A lament, elegy, or reflection",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Elegy|Lament|Requiem|Gentle|Prayer|Solace|Solitude|Rest|Peace|Heal|Comfort|Sorrow",
                    case=False, regex=True)],
            },
        ],
    },
    {
        "name": "I Told You Not to Eat That",
        "emoji": "🤢",
        "category": "funny",
        "description": "Every potluck has consequences.",
        "slots": [
            {
                "label": "The Appetizer",
                "hint": "A bright, inviting opener — come on in",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Feast|Festival|Fiesta|Carnival|Celebration|Merry|Overture|Welcome|Invitation|Opening",
                    case=False, regex=True)],
            },
            {
                "label": "The Main Course",
                "hint": "Rich, indulgent, heavy",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Grand|Noble|Majest|Royal|Imperial|Regal|Resplendent|Magnificent|Opulent|Sumptuous|Glorious",
                    case=False, regex=True)],
            },
            {
                "label": "The Rumble",
                "hint": "Something isn't sitting right",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Rumble|Growl|Roar|Thunder|Rolling|Turmoil|Turbulence|Tremor|Shake|Quake|Churn|Tumult|Upheaval",
                    case=False, regex=True)],
            },
            {
                "label": "The Sprint",
                "hint": "A sudden urgent rush",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Rush|Dash|Race|Gallop|Flight|Escape|Presto|Prestissimo|Stampede|Frenzy|Whirlwind|Toccata",
                    case=False, regex=True)],
            },
            {
                "label": "The Aftermath",
                "hint": "Lying down, reflecting on poor decisions",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Rest|Sleep|Slumber|Dream|Lullaby|Gentle|Still|Calm|Requiem|Solace|Recovery|Peace|Adagio",
                    case=False, regex=True)],
            },
        ],
    },
    {
        "name": "Hold My Beer",
        "emoji": "🍺",
        "category": "funny",
        "description": "The last words before every great story.",
        "slots": [
            {
                "label": "The Boast",
                "hint": "Heroic, confident, full of swagger",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Fanfare|Heroic|Triumphant|Bold|Noble|Proud|Valor|Glory|Gallant|Champion|Conquer|Invincible",
                    case=False, regex=True)],
            },
            {
                "label": "Hold My Beer",
                "hint": "A moment of stillness before the chaos",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Prelude|Moment|Pause|Breath|Threshold|Precipice|Calm|Suspended|Wait|Anticipation|Stillness",
                    case=False, regex=True)],
            },
            {
                "label": "The Attempt",
                "hint": "Wild, reckless, full speed ahead",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Wild|Frenzy|Fury|Chaos|Whirlwind|Stampede|Galop|Charge|Ride|Rampage|Madness|Circus|Boom",
                    case=False, regex=True)],
            },
            {
                "label": "The Hospital",
                "hint": "Elegy, lament, or slow recovery",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Elegy|Lament|Broken|Fallen|Requiem|Heal|Comfort|Gentle|Tender|Sorrow|Wound|Mercy|Grace",
                    case=False, regex=True)],
            },
            {
                "label": "The Legend",
                "hint": "Retelling the story — it was totally worth it",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Legend|Tale|Story|Saga|Epic|Ballad|Chronicle|Myth|Fable|Folklore|Odyssey|Adventure|Memory",
                    case=False, regex=True)],
            },
        ],
    },
    {
        "name": "Famous Last Words",
        "emoji": "💀",
        "category": "funny",
        "description": "\"What's the worst that could happen?\"",
        "slots": [
            {
                "label": "\"I've Got This\"",
                "hint": "Confident march or fanfare",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "March|Fanfare|Procession|Parade|Salute|Allegiance|Resolute|Onward|Forward|Advance|Intrepid",
                    case=False, regex=True)],
            },
            {
                "label": "\"Watch This\"",
                "hint": "Flashy, virtuosic, showing off",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Toccata|Perpetual|Scherzo|Caprice|Galop|Prestissimo|Dazzle|Brilliant|Virtuos|Acrobat|Spectacle",
                    case=False, regex=True)],
            },
            {
                "label": "\"Uh Oh\"",
                "hint": "Dark turn — something went very wrong",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Dark|Sinister|Ominous|Shadow|Doom|Dread|Peril|Abyss|Descent|Plunge|Fall|Catastrophe|Havoc",
                    case=False, regex=True)],
            },
            {
                "label": "\"Tell My Story\"",
                "hint": "Memorial, elegy, or farewell",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Memorial|Elegy|Farewell|Requiem|Remember|In Memoriam|Tribute|Dirge|Last|Final|Eternal Rest",
                    case=False, regex=True)],
            },
        ],
    },
    {
        "name": "That's Not a Knife... THIS Is a Knife",
        "emoji": "🔪",
        "category": "funny",
        "description": "Crocodile Dundee's guide to dynamic contrast.",
        "slots": [
            {
                "label": "\"That's Not a Knife\"",
                "hint": "Small, delicate, miniature",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Little|Small|Miniature|Petite|Tiny|Minor|Simple|Serenade|Arietta|Berceuse|Lullaby|Bagatelle",
                    case=False, regex=True)],
            },
            {
                "label": "\"THIS Is a Knife\"",
                "hint": "Massive, colossal, overwhelming",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Grand|Great|Mighty|Colossal|Titan|Epic|Majestic|Symphonic|Monumental|Enormous|Colossus|Mammoth",
                    case=False, regex=True)],
            },
            {
                "label": "The Outback",
                "hint": "Wide open, rugged, adventurous",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Prairie|Desert|Plain|Frontier|Pioneer|Wilderness|Outpost|Canyon|Mesa|Horizon|Vast|Open|Range",
                    case=False, regex=True)],
            },
            {
                "label": "The Crocodile",
                "hint": "Danger, predator, primal",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Dragon|Serpent|Beast|Predator|Prowl|Savage|Feral|Primal|Venom|Fang|Claw|Lair|Hunter|Creature",
                    case=False, regex=True)],
            },
        ],
    },
    {
        "name": "The Floor Is Lava",
        "emoji": "🌋",
        "category": "funny",
        "description": "The childhood game that prepared you for concert programming.",
        "slots": [
            {
                "label": "Safe Ground",
                "hint": "Solid, grounded, secure",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Home|Foundation|Ground|Earth|Rock|Stone|Fortress|Stronghold|Refuge|Shelter|Abide|Stand",
                    case=False, regex=True)],
            },
            {
                "label": "THE FLOOR IS LAVA",
                "hint": "Panic — volcanic, explosive, fiery",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Volcano|Lava|Eruption|Fire|Flame|Inferno|Blaze|Molten|Scorch|Furnace|Explosion|Cataclysm",
                    case=False, regex=True)],
            },
            {
                "label": "Jump!",
                "hint": "Leaping, flying, frantic motion",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Flight|Fly|Soar|Leap|Jump|Spring|Bounce|Dance|Galop|Whirlwind|Rush|Dash|Acrobat|Airborne",
                    case=False, regex=True)],
            },
            {
                "label": "Clinging to the Couch",
                "hint": "Hanging on — suspense, tension, uncertainty",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Suspense|Tension|Edge|Cliff|Precipice|Peril|Dread|Anxious|Tremor|Balance|Tightrope|Pendulum|Fate",
                    case=False, regex=True)],
            },
            {
                "label": "Sweet Relief",
                "hint": "Made it — joy, triumph, survival",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Relief|Joy|Jubil|Triumph|Victory|Celebration|Rejoice|Exult|Hallelujah|Salvation|Deliverance|Alive",
                    case=False, regex=True)],
            },
        ],
    },
    {
        "name": "What Happens in Vegas Stays in Vegas",
        "emoji": "🎰",
        "category": "funny",
        "description": "Sin City's concert programming philosophy.",
        "slots": [
            {
                "label": "The Arrival",
                "hint": "Glitz, neon, spectacle",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Star|Sparkle|Dazzle|Brilliant|Neon|Light|Glow|Radiant|Spectacle|Shimmer|Glitter|City|Skyline",
                    case=False, regex=True)],
            },
            {
                "label": "The Roll of the Dice",
                "hint": "Chance, fate, risk",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Fortune|Fate|Chance|Gamble|Risk|Dare|Destiny|Wheel|Luck|Twist|Random|Roulette",
                    case=False, regex=True)],
            },
            {
                "label": "The Show",
                "hint": "Showtime — jazz, swing, big band energy",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Jazz|Swing|Boogie|Blues|Rag|Ragtime|Bebop|Groove|Big Band|Cabaret|Burlesque|Show|Broadway|Satin",
                    case=False, regex=True)],
            },
            {
                "label": "3 AM",
                "hint": "The quiet hours — nocturne, solitude",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Nocturne|Night|Moon|Midnight|Lonely|Solitude|Alone|Shadow|Quiet|Silence|Empty|Reflection",
                    case=False, regex=True)],
            },
            {
                "label": "The Walk of Shame",
                "hint": "A slow, weary march home",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Funeral|Dirge|March|Procession|Slow|Weary|Trudge|Lament|Farewell|Departure|Morning|Dawn|Sunrise",
                    case=False, regex=True)],
            },
        ],
    },
    {
        "name": "If It Ain't Broke, Don't Fix It",
        "emoji": "🔧",
        "category": "funny",
        "description": "But it IS broke. And you made it worse.",
        "slots": [
            {
                "label": "Working Just Fine",
                "hint": "Orderly, elegant, classic",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Suite|Overture|Sonata|Sinfonia|Concerto|Prelude|Chorale|Hymn|Aria|Serenade|Pastorale|Aubade",
                    case=False, regex=True)],
            },
            {
                "label": "\"Let Me Try Something\"",
                "hint": "Variations, experiments, tinkering",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Variation|Theme|Fantasia|Fantasy|Rhapsod|Improvisation|Invention|Experiment|Exploration|Sketch",
                    case=False, regex=True)],
            },
            {
                "label": "The Extra Screw",
                "hint": "Something's loose — scherzo, off-kilter, mischief",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Scherzo|Caprice|Capriccio|Grotesque|Bizarre|Jest|Clown|Circus|Puck|Mischief|Trick|Comic|Frolic",
                    case=False, regex=True)],
            },
            {
                "label": "It's Definitely Broke Now",
                "hint": "Total chaos — crashing, disintegrating",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Chaos|Crash|Storm|Fury|Frenzy|Havoc|Mayhem|Rage|Destruction|Shatter|Eruption|Cataclysm|Apocalypse",
                    case=False, regex=True)],
            },
            {
                "label": "Calling a Professional",
                "hint": "Order restored — hymn, chorale, resolution",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Hymn|Chorale|Heal|Restore|Redeem|Grace|Salvation|Deliverance|Resolution|Resolve|Renewal|Amen",
                    case=False, regex=True)],
            },
        ],
    },
    {
        "name": "The Good, the Bad, and the Ugly",
        "emoji": "🤠",
        "category": "funny",
        "description": "A Sergio Leone triple feature for your concert hall.",
        "slots": [
            {
                "label": "The Good",
                "hint": "Highest-rated piece — the hero rides in",
                "match": lambda df: df.nlargest(50, "Best Bet") if "Best Bet" in df.columns and df["Best Bet"].notna().any() else df.head(50),
            },
            {
                "label": "The Bad",
                "hint": "Something dark, villainous, or ominous",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Dark|Devil|Black|Evil|Sinister|Wicked|Shadow|Doom|Diabolique|Macabre|Villain|Inferno|Chaos|Venom",
                    case=False, regex=True)],
            },
            {
                "label": "The Ugly",
                "hint": "A grotesque, circus, or novelty piece",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Circus|Grotesque|Galop|Polka|Carnival|Clown|Bizarre|Freak|Goblin|Troll|Monster|Gargoyle|Ogre",
                    case=False, regex=True)],
            },
        ],
    },
    {
        "name": "What Doesn't Kill You Makes You Stronger",
        "emoji": "💪",
        "category": "classic",
        "description": "Nietzsche's pep talk, scored for wind ensemble.",
        "slots": [
            {
                "label": "The Trial",
                "hint": "Conflict, struggle, or battle",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Battle|War|Conflict|Struggle|Fight|Siege|Storm|Clash|Crisis|Peril|Dragon|Sword|Shield|Warrior",
                    case=False, regex=True)],
            },
            {
                "label": "The Reckoning",
                "hint": "Darkness, loss, or mourning",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Elegy|Fallen|Lost|Requiem|Lament|Dark|Night|Sorrow|Ruin|Ashes|Ghost|Haunted|Grave|Weep",
                    case=False, regex=True)],
            },
            {
                "label": "The Comeback",
                "hint": "Triumph, light, or redemption",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Triumph|Victory|Rise|Aurora|Dawn|Light|Glory|Resurrection|Phoenix|Awakening|Jubil|Fanfare|Rejoice|Exultation",
                    case=False, regex=True)],
            },
        ],
    },
    {
        "name": "Lions and Tigers and Bears, Oh My!",
        "emoji": "🦁",
        "category": "funny",
        "description": "Follow the yellow brick road through the animal kingdom.",
        "slots": [
            {
                "label": "Lions",
                "hint": "Big cats, pride, and majesty",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Lion|Cat|Panther|Jaguar|Tiger|Leopard|Prowl|Roar|Pride|Claw|Paw|Feline|Gato",
                    case=False, regex=True)],
            },
            {
                "label": "Tigers",
                "hint": "Birds and flight",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Bird|Eagle|Hawk|Falcon|Raven|Crow|Phoenix|Wing|Fly|Flight|Soar|Dove|Swan|Firebird|Thunderbird|Lark|Robin",
                    case=False, regex=True)],
            },
            {
                "label": "Bears",
                "hint": "Wolves, dogs, and creatures of the forest",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Wolf|Bear|Fox|Hound|Hunt|Forest|Creature|Beast|Wild|Frog|Dragon|Serpent|Spider",
                    case=False, regex=True)],
            },
        ],
    },
    {
        "name": "Red Sky at Night, Sailor's Delight",
        "emoji": "🌅",
        "category": "classic",
        "description": "The old mariner's weather forecast.",
        "slots": [
            {
                "label": "Red Sky at Night",
                "hint": "Sunset, evening, twilight",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Sunset|Twilight|Evening|Dusk|Night|Nocturne|Vesper|Red Sky|Crimson|Scarlet|Afterglow",
                    case=False, regex=True)],
            },
            {
                "label": "Sailor's Delight",
                "hint": "Sea, ships, calm waters",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Sea|Sail|Ship|Ocean|Harbor|Port|Voyage|Wave|Tide|Shore|Coast|Anchor|Shanty|Mariner|Navy|Nautical|Bay|Cove",
                    case=False, regex=True)],
            },
            {
                "label": "Red Sky at Morning",
                "hint": "Storm, danger, tempest",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Storm|Tempest|Thunder|Hurricane|Maelstrom|Fury|Rage|Turmoil|Squall|Gale|Torrent|Cyclone|Whirlwind",
                    case=False, regex=True)],
            },
        ],
    },
    {
        "name": "If You Can't Stand the Heat, Get Out of the Kitchen",
        "emoji": "🔥",
        "category": "funny",
        "description": "Harry Truman's concert program.",
        "slots": [
            {
                "label": "Turn Up the Heat",
                "hint": "Fire, flame, and heat",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Fire|Flame|Burn|Inferno|Blaze|Ember|Scorch|Forge|Volcano|Lava|Pyre|Furnace|Heat|Molten|Ignite",
                    case=False, regex=True)],
            },
            {
                "label": "Too Hot to Handle",
                "hint": "Fast, furious, and virtuosic",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Toccata|Presto|Prestissimo|Galop|Frenzy|Fury|Whirlwind|Race|Rush|Velocity|Perpetual Motion|Allegro",
                    case=False, regex=True)],
            },
            {
                "label": "Cool Down",
                "hint": "Ice, winter, and calm",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Ice|Frost|Snow|Winter|Cold|Frozen|Crystal|Cool|Chill|Arctic|Glacier|Polar|Bleak Midwinter",
                    case=False, regex=True)],
            },
        ],
    },
    {
        "name": "The Grass Is Always Greener",
        "emoji": "🌿",
        "category": "classic",
        "description": "A pastoral program about longing for what's on the other side.",
        "slots": [
            {
                "label": "Our Green Pastures",
                "hint": "Home, pastoral, and familiar",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Pastoral|Green|Meadow|Field|Garden|Valley|Home|Village|Country|Folk|Shenandoah|Kentucky|Appalachia",
                    case=False, regex=True)],
            },
            {
                "label": "Over the Fence",
                "hint": "Journey, wandering, or distant lands",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Journey|Quest|Voyage|Adventure|Wander|Pilgrimage|Odyssey|Passage|Expedition|Trail|Path|Traveler|Nomad|Roam",
                    case=False, regex=True)],
            },
            {
                "label": "Somewhere Over the Rainbow",
                "hint": "Dreams, fantasy, or utopia",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Dream|Fantasy|Fantasia|Magic|Enchant|Wonder|Fairy|Myth|Legend|Imagine|Wish|Castle|Kingdom|Emerald",
                    case=False, regex=True)],
            },
        ],
    },
    {
        "name": "A Journey of a Thousand Miles Begins with a Single Step",
        "emoji": "👣",
        "category": "classic",
        "description": "Lao Tzu's travel guide, in five movements.",
        "slots": [
            {
                "label": "The Single Step",
                "hint": "A quiet beginning — simple, tentative, small",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Simple|Gentle|Prelude|Whisper|Still|Calm|Serene|Morning|First|Begin|Tender|Lullaby",
                    case=False, regex=True)],
            },
            {
                "label": "The Open Road",
                "hint": "Walking, traveling, moving forward",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "March|Walk|Road|Path|Trail|Step|Procession|Parade|Journey|Passage|Stride",
                    case=False, regex=True)],
            },
            {
                "label": "The Mountain Pass",
                "hint": "Climbing, struggle, high places",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Mountain|Summit|Peak|Climb|Ascend|Ridge|Highland|Crest|Everest|Alp|Sierra|Height",
                    case=False, regex=True)],
            },
            {
                "label": "The Valley Below",
                "hint": "Rest, reflection, a quiet middle",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Valley|River|Stream|Meadow|Rest|Serenade|Nocturne|Reverie|Solitude|Pastoral",
                    case=False, regex=True)],
            },
            {
                "label": "The Thousand Miles",
                "hint": "Arrival, triumph, a grand destination",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Triumph|Jubil|Celebration|Fanfare|Festival|Finale|Glory|Crown|Hallelujah|Rejoice|Exalt",
                    case=False, regex=True)],
            },
        ],
    },
    {
        "name": "Every Cloud Has a Silver Lining",
        "emoji": "⛅",
        "category": "classic",
        "description": "Optimism, scored for concert band.",
        "slots": [
            {
                "label": "Gathering Clouds",
                "hint": "Approaching darkness or uncertainty",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Cloud|Shadow|Mist|Fog|Haze|Gray|Overcast|Veil|Shroud|Obscure|Gloom|Dusk",
                    case=False, regex=True)],
            },
            {
                "label": "The Downpour",
                "hint": "Storm, rain, turbulence",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Rain|Storm|Thunder|Tempest|Torrent|Flood|Deluge|Squall|Hurricane|Monsoon|Cascade",
                    case=False, regex=True)],
            },
            {
                "label": "The Silver Lining",
                "hint": "Light breaking through — hope, radiance",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Silver|Light|Shine|Radiant|Glow|Bright|Shimmer|Gleam|Luminous|Beacon|Ray|Sun|Golden|Brilliant",
                    case=False, regex=True)],
            },
            {
                "label": "Clear Skies",
                "hint": "Joy, blue sky, celebration",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Blue Sky|Joy|Jubil|Celebration|Sunburst|Morning|Clear|Bright|Hymn|Praise|Alleluia|Exult",
                    case=False, regex=True)],
            },
        ],
    },
    {
        "name": "Still Waters Run Deep",
        "emoji": "🌊",
        "category": "classic",
        "description": "Quiet intensity and hidden power.",
        "slots": [
            {
                "label": "Still Waters",
                "hint": "Calm surface — serene, sustained, lyrical",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Still|Calm|Serene|Lake|Pond|Reflection|Mirror|Glass|Silent|Quiet|Tranquil|Adagio",
                    case=False, regex=True)],
            },
            {
                "label": "The Undercurrent",
                "hint": "Hidden motion, tension beneath beauty",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Current|Tide|Deep|Beneath|Under|Hidden|Mystery|Secret|Enigma|Labyrinth|Abyss",
                    case=False, regex=True)],
            },
            {
                "label": "The Depths",
                "hint": "Full power revealed — massive, elemental",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Ocean|Sea|Flood|Maelstrom|Wave|Leviathan|Poseidon|Neptune|Titan|Colossus|Force|Power",
                    case=False, regex=True)],
            },
        ],
    },
    {
        "name": "Rome Wasn't Built in a Day",
        "emoji": "🏛️",
        "category": "classic",
        "description": "An empire in four movements.",
        "slots": [
            {
                "label": "Laying the Foundation",
                "hint": "Ancient, solemn, ceremonial origins",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Ancient|Stone|Foundation|Temple|Sacred|Hymn|Chant|Chorale|Gregorian|Rite|Ceremony|Procession",
                    case=False, regex=True)],
            },
            {
                "label": "The Builders",
                "hint": "Industry, craft, and labor",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Forge|Hammer|Iron|Steel|Machine|Engine|Build|Craft|Tower|Citadel|Fortress|Castle|Architect|Monument",
                    case=False, regex=True)],
            },
            {
                "label": "The Empire",
                "hint": "Roman grandeur — majesty and pageantry",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Roman|Empire|Caesar|Legion|Crown|King|Queen|Royal|Noble|Majest|Palace|Coronation|Imperial|Regal|Sovereign",
                    case=False, regex=True)],
            },
            {
                "label": "The Fall",
                "hint": "Crumbling, ruins, elegy for what was",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Fall|Ruin|Elegy|Requiem|Lament|Lost|Forgotten|Ashes|Dust|Decay|Farewell|Dirge|Memorial",
                    case=False, regex=True)],
            },
        ],
    },
    {
        "name": "Actions Speak Louder Than Words",
        "emoji": "📢",
        "category": "classic",
        "description": "Less talk, more band.",
        "slots": [
            {
                "label": "The Whisper",
                "hint": "Words, songs, and voices — lyrical and vocal",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Song|Sing|Voice|Word|Speak|Tell|Story|Ballad|Aria|Lied|Chanson|Hymn|Prayer|Psalm|Canticle",
                    case=False, regex=True)],
            },
            {
                "label": "The Shout",
                "hint": "Fanfare, declaration, proclamation",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Fanfare|Declaration|Proclamation|Herald|Trumpet|Call|Clarion|Salute|Announcement|Command",
                    case=False, regex=True)],
            },
            {
                "label": "The Action",
                "hint": "Dance, movement, physical energy",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Dance|Danzon|Tango|Waltz|Samba|Rhumba|Polka|Galop|Tarantella|Bolero|Mambo|Salsa|Jig|Reel|Hoedown",
                    case=False, regex=True)],
            },
            {
                "label": "The Deed",
                "hint": "March, charge, purpose in motion",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "March|Charge|Advance|Forward|Onward|Resolute|Defiant|Stand|Courage|Valor|Honor|Allegiance",
                    case=False, regex=True)],
            },
        ],
    },
    {
        "name": "All That Glitters Is Not Gold",
        "emoji": "✨",
        "category": "classic",
        "description": "Shakespeare's metallurgy lesson.",
        "slots": [
            {
                "label": "The Glitter",
                "hint": "Dazzling, bright, spectacular surface",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Star|Sparkle|Shimmer|Glitter|Dazzle|Brilliant|Diamond|Jewel|Crystal|Prism|Radiant|Celestial",
                    case=False, regex=True)],
            },
            {
                "label": "The Gold",
                "hint": "Something genuinely precious — golden, sun, treasure",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Gold|Sun|Treasure|Crown|Amber|Autumn|Harvest|Gilded|Bronze|Copper|Brass|Aureate",
                    case=False, regex=True)],
            },
            {
                "label": "The Mask",
                "hint": "Deception, illusion, hidden truth",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Mask|Phantom|Ghost|Illusion|Mirage|Shadow|Veil|Masquerade|Deception|Riddle|Enigma|Charade|Specter",
                    case=False, regex=True)],
            },
            {
                "label": "The Real Thing",
                "hint": "Heart, truth, sincerity — something genuine",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Heart|Soul|Spirit|Grace|Love|Hope|Faith|Promise|Devotion|Eternal|True|Abide|Endure",
                    case=False, regex=True)],
            },
        ],
    },
    {
        "name": "When It Rains, It Pours",
        "emoji": "🌧️",
        "category": "classic",
        "description": "Morton Salt's concert philosophy — everything at once.",
        "slots": [
            {
                "label": "The First Drop",
                "hint": "A small, quiet beginning",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Drop|Tear|Dew|Mist|Whisper|Murmur|Ripple|Trickle|Gentle|Soft|Tender|Lullaby",
                    case=False, regex=True)],
            },
            {
                "label": "The Drizzle",
                "hint": "Light percussion, patter, playfulness",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Scherzo|Caprice|Capriccio|Frolic|Play|Jest|Puck|Sprite|Imp|Pixie|Mischief|Whimsy|Comic",
                    case=False, regex=True)],
            },
            {
                "label": "The Downpour",
                "hint": "Full ensemble, relentless energy",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Toccata|Perpetual|Frenzy|Fury|Rush|Torrent|Cascade|Flood|Deluge|Unstoppable|Relentless",
                    case=False, regex=True)],
            },
            {
                "label": "The Thunder",
                "hint": "Massive, dramatic, overwhelming",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Thunder|Roar|Crash|Explosion|Eruption|Cataclysm|Apocalypse|Inferno|Chaos|Maelstrom|Fury|Rage",
                    case=False, regex=True)],
            },
            {
                "label": "After the Storm",
                "hint": "Calm returns — clearing, peace, rainbow",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Rainbow|Peace|Calm|Clear|Serene|Heaven|Paradise|Garden|Blossom|Spring|Renewal|New Day|Sunrise",
                    case=False, regex=True)],
            },
        ],
    },
    {
        "name": "Where There's Smoke, There's Fire",
        "emoji": "💨",
        "category": "classic",
        "description": "An investigation in four acts.",
        "slots": [
            {
                "label": "The Smoke",
                "hint": "Haze, mystery, something not quite right",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Smoke|Mist|Fog|Haze|Shadow|Phantom|Ghost|Vapor|Murk|Dim|Obscure|Drift",
                    case=False, regex=True)],
            },
            {
                "label": "The Spark",
                "hint": "Ignition — small but dangerous",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Spark|Flash|Flicker|Kindle|Ignite|Fuse|Match|Glint|Glimmer|Crackle|Snap",
                    case=False, regex=True)],
            },
            {
                "label": "The Fire",
                "hint": "Full blaze — fire, flame, fury",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Fire|Flame|Blaze|Inferno|Burn|Scorch|Ember|Pyre|Furnace|Volcano|Eruption|Molten",
                    case=False, regex=True)],
            },
            {
                "label": "The Ashes",
                "hint": "What remains — elegy, memory, rebirth",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Ash|Ember|Phoenix|Remain|Memory|Remember|Memorial|Legacy|Eternal|Endure|Rise|Rebirth",
                    case=False, regex=True)],
            },
        ],
    },
    {
        "name": "The Early Bird Gets the Worm",
        "emoji": "🐦",
        "category": "classic",
        "description": "A full day of music, dawn to dark.",
        "slots": [
            {
                "label": "The Early Bird",
                "hint": "Dawn, sunrise, morning",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Dawn|Sunrise|Morning|Aurora|Daybreak|First Light|Early|Waking|Aubade",
                    case=False, regex=True)],
            },
            {
                "label": "The Hunt",
                "hint": "Birds, flight, pursuit",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Bird|Eagle|Hawk|Falcon|Wing|Flight|Soar|Hunt|Chase|Prey|Swift|Swoop|Sparrow|Lark|Wren",
                    case=False, regex=True)],
            },
            {
                "label": "High Noon",
                "hint": "Bright, bold, full energy",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Sun|Bright|Blaze|Noon|Radiant|Vivid|Bold|Brilliant|Splendid|Magnificent|Resplendent",
                    case=False, regex=True)],
            },
            {
                "label": "The Worm Turns",
                "hint": "A twist — something unexpected or dark",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Turn|Twist|Strange|Weird|Bizarre|Grotesque|Macabre|Sinister|Dark|Ominous|Eerie|Haunt",
                    case=False, regex=True)],
            },
            {
                "label": "Night Owl",
                "hint": "Night, stars, moonlight",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Night|Moon|Star|Nocturne|Midnight|Evening|Twilight|Vesper|Owl|Dream|Starlight|Constellation",
                    case=False, regex=True)],
            },
        ],
    },
    {
        "name": "Blood Is Thicker Than Water",
        "emoji": "🩸",
        "category": "classic",
        "description": "Family ties and ancestral roots.",
        "slots": [
            {
                "label": "The Bloodline",
                "hint": "Heritage, ancestry, tradition",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Heritage|Ancestor|Ancient|Legacy|Tradition|Origin|Root|Lineage|Generation|Dynasty|Tribe|Clan",
                    case=False, regex=True)],
            },
            {
                "label": "The Homeland",
                "hint": "Place of origin — folk tunes, national identity",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Folk|Home|Land|Country|Nation|America|Irish|Scottish|English|African|Korean|Japanese|Chinese|Mexican|Armenian|Hebrew|Gaelic",
                    case=False, regex=True)],
            },
            {
                "label": "The Bond",
                "hint": "Love, devotion, togetherness",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Love|Heart|Together|Unite|Bond|Embrace|Wedding|Promise|Devotion|Forever|Eternal|Abide",
                    case=False, regex=True)],
            },
            {
                "label": "The Gathering",
                "hint": "Community, celebration, reunion",
                "match": lambda df: df[df["Title"].fillna("").str.contains(
                    "Festival|Celebration|Gathering|Feast|Jubil|Fiesta|Carnival|Holiday|Reunion|Communit|Assembly|Congregation",
                    case=False, regex=True)],
            },
        ],
    },
]


def deal_theme_program(theme, source_df, grade_range=None):
    """Pick one random piece per slot from matching pieces."""
    import random
    program = []
    used_titles = set()

    pool = source_df.copy()
    if grade_range and "Grade" in pool.columns:
        pool = pool[(pool["Grade"] >= grade_range[0]) & (pool["Grade"] <= grade_range[1])]

    # Require meaningful professional endorsement for themed programs
    if "Street Cred" in pool.columns:
        pool = pool[pool["Street Cred"].fillna(0) >= 3]

    for slot in theme["slots"]:
        try:
            matches = slot["match"](pool)
        except Exception:
            matches = pd.DataFrame()

        # Exclude already-used titles
        if not matches.empty:
            matches = matches[~matches["Title"].isin(used_titles)]

        if matches.empty:
            program.append(None)
        else:
            # Weighted random: prefer higher Best Bet
            if "Best Bet" in matches.columns and matches["Best Bet"].notna().any():
                weights = matches["Best Bet"].fillna(0).clip(lower=1)
                pick = matches.sample(1, weights=weights).iloc[0]
            else:
                pick = matches.sample(1).iloc[0]
            program.append(pick.to_dict())
            used_titles.add(pick["Title"])

    return program


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

MONEYBALL_QUOTES = [
    '"It\'s about getting things down to one number." — Peter Brand',
    '"People are overlooked for biased reasons." — Peter Brand',
    '"The first guy through the wall always gets bloody." — John Henry',
    '"There are rich teams and poor teams. Then there\'s fifty feet of crap, and then there\'s us."',
    '"You don\'t put a team together with a computer." "No. What you don\'t do is think about it."',
    '"We\'re going to find value where nobody else can find it."',
]


def main():
    init_program()

    import hashlib, datetime
    quote_idx = int(hashlib.md5(str(datetime.date.today()).encode()).hexdigest(), 16) % len(MONEYBALL_QUOTES)

    st.markdown(f"""
    <div class="main-header">
        <h1>Moneyband</h1>
        <div class="tagline">DATA-DRIVEN REPERTOIRE DECISIONS</div>
        <div class="quote">{MONEYBALL_QUOTES[quote_idx]}</div>
    </div>
    """, unsafe_allow_html=True)

    band_df, band_err = safe_load(load_band, "Band")
    orch_df, orch_err = safe_load(load_orchestra, "Orchestra")
    pairings_data = load_pairings()

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Browse Repertoire", "Build a Program",
                                            "Concert Themer", "About the Data",
                                            "The Tuba of Fate"])

    # ==================================================================
    # TAB 1: Browse
    # ==================================================================
    with tab1:
        db_choice = st.radio("Database", ["Band", "Orchestra"], horizontal=True, key="explore_db")
        is_band = db_choice == "Band"

        if is_band:
            if band_err: st.error(band_err); return
            source = band_df.copy()
            dcols = [c for c in BAND_DISPLAY if c in source.columns]
            sort_opts = SORT_OPTIONS
        else:
            if orch_err: st.error(orch_err); return
            source = orch_df.copy()
            dcols = [c for c in ORCH_DISPLAY if c in source.columns]
            sort_opts = ORCH_SORT_OPTIONS

        st.sidebar.markdown(f"### Filters — {db_choice}")
        filtered = apply_filters(source, is_band, key_prefix="ex_")

        # Sort selector with explanations
        sort_choice = st.selectbox(
            "Show pieces sorted by",
            list(sort_opts.keys()),
            index=0,
            key="explore_sort",
            help="Choose what matters most to you for this search.",
        )
        sort_info = sort_opts[sort_choice]
        st.caption(sort_info["help"])

        # Apply sort
        sort_col = sort_info["col"]
        if sort_col in filtered.columns:
            if sort_col == "Title":
                filtered = filtered.sort_values(sort_col, ascending=True, na_position="last")
            else:
                filtered = filtered.sort_values(sort_col, ascending=False, na_position="last")

        st.markdown(f"**{len(filtered):,}** pieces match your filters")
        st.caption("Click a row to see details and add it to your program.")

        event = st.dataframe(
            filtered[dcols].reset_index(drop=True),
            use_container_width=True,
            hide_index=True,
            height=500,
            on_select="rerun",
            selection_mode="single-row",
            key="browse_df",
        )

        # Detail view when a row is selected
        selected_rows = event.selection.rows if event.selection else []
        if selected_rows and not filtered.empty:
            sel_idx = selected_rows[0]
            if sel_idx < len(filtered):
                row = filtered.iloc[sel_idx]
                prog = st.session_state.get("program", [])
                prog_titles = {
                    (_norm_title(p.get("Title", "")), _norm_composer(p.get("Composer", "")))
                    for p in prog
                }
                added = render_piece_card(row, pairings_data, source, is_band,
                                          show_add=True, prog_titles=prog_titles)
                if added:
                    add_piece(row.to_dict())
                    st.rerun()

    # ==================================================================
    # TAB 2: Program Builder (Wizard)
    # ==================================================================
    with tab2:
        prog = st.session_state["program"]

        # Ensemble selection
        db_pb = st.radio("What ensemble are you programming for?",
                         ["Band", "Orchestra"], horizontal=True, key="pb_db")
        is_band_pb = db_pb == "Band"

        if is_band_pb:
            if band_err: st.error(band_err); return
            source_pb = band_df.copy()
            sort_opts_pb = SORT_OPTIONS
        else:
            if orch_err: st.error(orch_err); return
            source_pb = orch_df.copy()
            sort_opts_pb = ORCH_SORT_OPTIONS

        # Sidebar: filters + program
        render_program_sidebar()

        if is_band_pb:
            # ==========================================================
            # BAND: March + Anchor Piece + Auto-Paired Companion
            # ==========================================================

            # --- March selection ---
            st.markdown("### 1. Choose your march")
            st.markdown("A band concert program starts with a march. "
                        "Use the sidebar filters to narrow by grade, style, or preference.")

            st.sidebar.markdown("---")
            st.sidebar.markdown("### March Filters")
            all_marches = get_marches(source_pb)
            filtered_marches = apply_march_filters(all_marches, key_prefix="march_")

            march_sort = st.selectbox(
                "Sort marches by",
                list(MARCH_SORT_OPTIONS.keys()),
                index=0,
                key="pb_march_sort",
            )
            march_sort_info = MARCH_SORT_OPTIONS[march_sort]
            st.caption(march_sort_info["help"])

            march_sort_col = march_sort_info["col"]
            if march_sort_col in filtered_marches.columns:
                if march_sort_col == "Title":
                    filtered_marches = filtered_marches.sort_values(march_sort_col, ascending=True, na_position="last")
                else:
                    filtered_marches = filtered_marches.sort_values(march_sort_col, ascending=False, na_position="last")

            st.markdown(f"**{len(filtered_marches):,}** marches available")

            march_selected = None
            if not filtered_marches.empty:
                march_options = filtered_marches.apply(
                    lambda r: f"{r['Title']}  —  {r['Composer']}  (Gr {r.get('Grade', '?')})"
                    if pd.notna(r.get("Composer")) else str(r["Title"]),
                    axis=1,
                ).tolist()

                march_choice = st.selectbox(
                    "Select your march",
                    march_options,
                    index=None,
                    key="pb_march_sel",
                    placeholder="Type to search or scroll...",
                )

                if march_choice is not None:
                    march_row = filtered_marches.iloc[march_options.index(march_choice)]
                    march_selected = march_row.to_dict()

                    # Show march detail card
                    render_piece_card(march_row, None, source_pb, is_band_pb)
            else:
                st.info("No marches match your filters. Adjust the sidebar filters.")

            st.markdown("---")

            # --- Anchor piece selection (non-march) ---
            st.markdown("### 2. Choose your anchor piece")
            st.markdown("Pick the concert piece you want to build around. "
                        "A common companion will be suggested automatically.")

            st.sidebar.markdown("---")
            st.sidebar.markdown("### Concert Piece Filters")
            # Filter marches OUT of the concert piece pool
            non_march_pb = source_pb[~source_pb.index.isin(all_marches.index)]
            filtered_pb = apply_filters(non_march_pb, is_band_pb, key_prefix="pb_")

            sort_pb = st.selectbox(
                "Sort pieces by",
                list(sort_opts_pb.keys()),
                index=0,
                key="pb_sort",
            )
            sort_info_pb = sort_opts_pb[sort_pb]
            st.caption(sort_info_pb["help"])

            sort_col_pb = sort_info_pb["col"]
            if sort_col_pb in filtered_pb.columns:
                if sort_col_pb == "Title":
                    filtered_pb = filtered_pb.sort_values(sort_col_pb, ascending=True, na_position="last")
                else:
                    filtered_pb = filtered_pb.sort_values(sort_col_pb, ascending=False, na_position="last")

            st.markdown(f"**{len(filtered_pb):,}** pieces available")

            if filtered_pb.empty:
                st.info("No pieces match your filters. Adjust the sidebar filters.")
            else:
                options_pb = filtered_pb.apply(
                    lambda r: f"{r['Title']}  —  {r['Composer']}  (Gr {r.get('Grade', '?')})"
                    if pd.notna(r.get("Composer")) else str(r["Title"]),
                    axis=1,
                ).tolist()

                selected = st.selectbox(
                    "Select your anchor piece",
                    options_pb,
                    index=None,
                    key="pb_anchor_sel",
                    placeholder="Type to search or scroll...",
                )

                if selected is not None:
                    anchor_row = filtered_pb.iloc[options_pb.index(selected)]
                    anchor_dict = anchor_row.to_dict()

                    render_piece_card(anchor_row, None, source_pb, is_band_pb)

                    # Build suggested companion from pairings
                    pairs = get_pairings(
                        anchor_dict.get("Title", ""),
                        anchor_dict.get("Composer", ""),
                        pairings_data,
                        limit=10,
                    )
                    pairs = [p for p in pairs if not is_march(p)]

                    st.markdown("---")
                    st.markdown("### 3. Suggested companion piece")

                    if not pairs:
                        st.info("No pairing data available for this piece. "
                                "You can still browse for a companion in the Browse tab.")
                    else:
                        st.markdown("Based on **479,000+ ensemble programs** from UIL evaluations, "
                                    "here is the most common companion. Swap if you'd like.")

                        pair_options_2 = [
                            f"{p['title']}  —  {p['composer']}  ({p['count']:,}× together)"
                            for p in pairs
                        ]
                        swap_2 = st.selectbox(
                            "Companion piece",
                            pair_options_2,
                            index=0,
                            key="pb_pair2",
                            label_visibility="collapsed",
                        )
                        sel_pair_2 = pairs[pair_options_2.index(swap_2)]
                        db_row_2 = find_piece_in_db(sel_pair_2["title"], sel_pair_2["composer"], source_pb)
                        if db_row_2 is not None:
                            render_piece_card(db_row_2, None, source_pb, is_band_pb)
                        else:
                            st.markdown(f"**{sel_pair_2['title']}** — {sel_pair_2['composer']}")
                            st.caption("Not in the current database — no additional details available.")

                    # --- Confirm & Export ---
                    st.markdown("---")

                    final_prog = []
                    if march_selected:
                        final_prog.append(march_selected)
                    final_prog.append(anchor_dict)
                    if pairs:
                        if db_row_2 is not None:
                            final_prog.append(db_row_2.to_dict() if hasattr(db_row_2, 'to_dict') else db_row_2)
                        else:
                            final_prog.append({"Title": sel_pair_2["title"], "Composer": sel_pair_2["composer"]})

                    if march_selected and pairs:
                        if st.button("Confirm this program", type="primary", key="pb_confirm"):
                            st.session_state["program"] = final_prog
                            st.rerun()
                    elif not march_selected:
                        st.warning("Select a march above to complete your program.")

                    if len(prog) >= 2:
                        st.success("Program confirmed! Export below.")
                        st.markdown("### Export")
                        ec1, ec2 = st.columns(2)
                        ec1.download_button("Download as CSV", data=export_csv(prog),
                                            file_name="concert_program.csv", mime="text/csv")
                        ec2.download_button("Download program sheet", data=export_text(prog),
                                            file_name="concert_program.txt", mime="text/plain")

        else:
            # ==========================================================
            # ORCHESTRA: Anchor Piece + 2 Auto-Paired Companions
            # ==========================================================
            st.sidebar.markdown("---")
            st.sidebar.markdown("### Filters")
            filtered_pb = apply_filters(source_pb, is_band_pb, key_prefix="pb_")

            st.markdown("### Pick your anchor piece")
            st.markdown("Choose the piece you want to build your program around. "
                        "Common pairings will fill in automatically.")

            sort_pb = st.selectbox(
                "Sort pieces by",
                list(sort_opts_pb.keys()),
                index=0,
                key="pb_sort",
            )
            sort_info_pb = sort_opts_pb[sort_pb]
            st.caption(sort_info_pb["help"])

            sort_col_pb = sort_info_pb["col"]
            if sort_col_pb in filtered_pb.columns:
                if sort_col_pb == "Title":
                    filtered_pb = filtered_pb.sort_values(sort_col_pb, ascending=True, na_position="last")
                else:
                    filtered_pb = filtered_pb.sort_values(sort_col_pb, ascending=False, na_position="last")

            st.markdown(f"**{len(filtered_pb):,}** pieces available")

            if filtered_pb.empty:
                st.info("No pieces match your filters. Adjust the sidebar filters.")
            else:
                options_pb = filtered_pb.apply(
                    lambda r: f"{r['Title']}  —  {r['Composer']}  (Gr {r.get('Grade', '?')})"
                    if pd.notna(r.get("Composer")) else str(r["Title"]),
                    axis=1,
                ).tolist()

                selected = st.selectbox(
                    "Select your anchor piece",
                    options_pb,
                    index=None,
                    key="pb_anchor_sel",
                    placeholder="Type to search or scroll...",
                )

                if selected is not None:
                    anchor_row = filtered_pb.iloc[options_pb.index(selected)]
                    anchor_dict = anchor_row.to_dict()

                    render_piece_card(anchor_row, None, source_pb, is_band_pb)

                    pairs = get_pairings(
                        anchor_dict.get("Title", ""),
                        anchor_dict.get("Composer", ""),
                        pairings_data,
                        limit=10,
                    )
                    pairs = [p for p in pairs if not is_march(p)]

                    st.markdown("---")

                    if not pairs:
                        st.info("No pairing data available for this piece.")
                    else:
                        st.markdown("### Suggested companion pieces")
                        st.markdown("Based on **479,000+ ensemble programs** from UIL evaluations. "
                                    "Swap any piece if you'd like.")

                        # --- Piece 2 ---
                        st.markdown("#### Piece 2")
                        pair_options_2 = [
                            f"{p['title']}  —  {p['composer']}  ({p['count']:,}× together)"
                            for p in pairs
                        ]
                        swap_2 = st.selectbox(
                            "Piece 2",
                            pair_options_2,
                            index=0,
                            key="pb_pair2",
                            label_visibility="collapsed",
                        )
                        sel_pair_2 = pairs[pair_options_2.index(swap_2)]
                        db_row_2 = find_piece_in_db(sel_pair_2["title"], sel_pair_2["composer"], source_pb)
                        if db_row_2 is not None:
                            render_piece_card(db_row_2, None, source_pb, is_band_pb)
                        else:
                            st.markdown(f"**{sel_pair_2['title']}** — {sel_pair_2['composer']}")
                            st.caption("Not in the current database — no additional details available.")

                        # --- Piece 3 ---
                        remaining = [p for p in pairs if p is not sel_pair_2]
                        st.markdown("#### Piece 3")
                        sel_pair_3 = None
                        db_row_3 = None
                        if remaining:
                            pair_options_3 = [
                                f"{p['title']}  —  {p['composer']}  ({p['count']:,}× together)"
                                for p in remaining
                            ]
                            swap_3 = st.selectbox(
                                "Piece 3",
                                pair_options_3,
                                index=0,
                                key="pb_pair3",
                                label_visibility="collapsed",
                            )
                            sel_pair_3 = remaining[pair_options_3.index(swap_3)]
                            db_row_3 = find_piece_in_db(sel_pair_3["title"], sel_pair_3["composer"], source_pb)
                            if db_row_3 is not None:
                                render_piece_card(db_row_3, None, source_pb, is_band_pb)
                            else:
                                st.markdown(f"**{sel_pair_3['title']}** — {sel_pair_3['composer']}")
                                st.caption("Not in the current database — no additional details available.")
                        else:
                            st.info("Only one pairing suggestion available.")

                        # --- Confirm & Export ---
                        st.markdown("---")
                        final_prog = [anchor_dict]
                        if db_row_2 is not None:
                            final_prog.append(db_row_2.to_dict() if hasattr(db_row_2, 'to_dict') else db_row_2)
                        else:
                            final_prog.append({"Title": sel_pair_2["title"], "Composer": sel_pair_2["composer"]})
                        if sel_pair_3:
                            if db_row_3 is not None:
                                final_prog.append(db_row_3.to_dict() if hasattr(db_row_3, 'to_dict') else db_row_3)
                            else:
                                final_prog.append({"Title": sel_pair_3["title"], "Composer": sel_pair_3["composer"]})

                        if st.button("Confirm this program", type="primary", key="pb_confirm"):
                            st.session_state["program"] = final_prog
                            st.rerun()

                        if len(prog) >= 2:
                            st.success("Program confirmed! Export below.")
                            st.markdown("### Export")
                            ec1, ec2 = st.columns(2)
                            ec1.download_button("Download as CSV", data=export_csv(prog),
                                                file_name="concert_program.csv", mime="text/csv")
                            ec2.download_button("Download program sheet", data=export_text(prog),
                                                file_name="concert_program.txt", mime="text/plain")

    # ==================================================================
    # TAB 3: Concert Themer
    # ==================================================================
    with tab3:
        st.markdown("### Concert Themer")
        st.markdown("Pick an aphorism. We'll deal you a thematic concert program from the database. "
                    "Hit **Deal again** to reshuffle.")

        db_deck = st.radio("Database", ["Band", "Orchestra"], horizontal=True, key="deck_db")
        is_band_deck = db_deck == "Band"

        if is_band_deck:
            if band_err:
                st.error(band_err)
            else:
                deck_source = band_df.copy()
        else:
            if orch_err:
                st.error(orch_err)
            else:
                deck_source = orch_df.copy()

        if (is_band_deck and not band_err) or (not is_band_deck and not orch_err):
            # Grade range filter
            grades_avail = sorted(deck_source["Grade"].dropna().unique())
            if grades_avail:
                g_min, g_max = st.select_slider(
                    "Grade range",
                    options=grades_avail,
                    value=(min(grades_avail), max(grades_avail)),
                    key="deck_grade",
                )
                grade_filter = (g_min, g_max)
            else:
                grade_filter = None

            # Pick a theme — split into classic and funny
            classic_themes = [t for t in THEME_DECKS if t.get("category") == "classic"]
            funny_themes = [t for t in THEME_DECKS if t.get("category") == "funny"]

            vibe = st.radio("Vibe", ["Timeless Wisdom", "Unhinged"], horizontal=True, key="deck_vibe")
            deck_pool = classic_themes if vibe == "Timeless Wisdom" else funny_themes
            theme_names = [f"{t['emoji']}  {t['name']}" for t in deck_pool]
            chosen = st.selectbox("Pick your poison", theme_names, index=None,
                                  key="deck_theme", placeholder="Choose an aphorism...")

            if chosen is not None:
                theme_idx = theme_names.index(chosen)
                theme = deck_pool[theme_idx]

                st.markdown(f"### {theme['emoji']} {theme['name']}")
                st.caption(theme["description"])

                # Deal button / initial deal
                if "deck_seed" not in st.session_state:
                    st.session_state["deck_seed"] = 0

                if st.button("Deal again", key="deck_reshuffle", type="secondary"):
                    st.session_state["deck_seed"] += 1

                import random
                random.seed(st.session_state["deck_seed"] + theme_idx)

                program = deal_theme_program(theme, deck_source, grade_filter)

                st.markdown("---")
                all_found = True
                prog_dicts = []
                for i, slot in enumerate(theme["slots"]):
                    piece = program[i]
                    st.markdown(f'**{slot["label"]}** — *{slot["hint"]}*')
                    if piece is None:
                        st.warning("No match found for this slot. Try a wider grade range or a different database.")
                        all_found = False
                    else:
                        prog_dicts.append(piece)
                        row_series = pd.Series(piece)
                        render_piece_card(row_series, None, deck_source, is_band_deck)
                    st.markdown("")

                if all_found and prog_dicts:
                    st.markdown("---")
                    st.markdown("### Export this ridiculous program")
                    ec1, ec2 = st.columns(2)
                    ec1.download_button("Download as CSV", data=export_csv(prog_dicts),
                                        file_name="themed_program.csv", mime="text/csv")
                    ec2.download_button("Download program sheet", data=export_text(prog_dicts),
                                        file_name="themed_program.txt", mime="text/plain")

    # ==================================================================
    # TAB 4: About the Data
    # ==================================================================
    with tab4:
        st.markdown("### How this tool works")
        st.markdown("""
This tool brings together several sources of information to help you make
informed repertoire decisions. It is **not** a ranking system — no score can
tell you what's right for your ensemble. Think of it as a research assistant
that shows you what the profession has learned about these pieces.
        """)

        st.markdown("---")
        st.markdown("### What the numbers mean")

        st.markdown("""
**Overall recommendation** (Best Bet, 0–100)
A combined score weighing festival performance results and professional
endorsement. A piece scoring 90+ has both strong adjudication results *and*
broad recognition from teaching guides, prescribed lists, and expert directors.

**Festival performance strength** (MPA Confidence, 0–100)
Based on adjudicated festival data — for band, from Florida MPA results (2009–2026)
and Texas UIL Concert & Sightreading evaluations; for orchestra, from UIL data.
Ensembles perform a complete concert program (typically 3 pieces) and sight-reading
for a panel of judges who assign ratings from Superior (I) to Poor (V).

**Important:** Ratings are given to the *ensemble's full program*, not to individual
pieces. This score reflects how consistently ensembles *whose programs include this
piece* earn top ratings, adjusted for grade level. It's an associative signal — strong
directors tend to choose certain pieces, and programs containing those pieces tend to
score well — but it does not mean the piece itself caused the rating.

**Professional endorsement** (Street Cred, 0–15.5)
An additive score from professional sources: Teaching Music Through Performance
series (+3), Kreines Concert Repertoire Guide (+3), director teaching history (+3),
Band Directors Guide (+2), Institute for Composer Diversity (+2), state prescribed
music lists (+0.01 per state), and CBA Prescribed Music List (+1).

**Composer identity** (ICD Diversity)
From the Institute for Composer Diversity — flags composers from underrepresented
groups. This helps you build programs that reflect the breadth of the profession.
        """)

        st.markdown("---")
        st.markdown("### Pairing suggestions")
        st.markdown("""
When you select a piece in the Program Builder, the tool shows you what other
pieces have historically been programmed alongside it. This is based on
**479,000+ ensemble programs** from Texas UIL Concert & Sightreading evaluations
(2009–2026).

These pairings reflect what directors have actually done — not what they
*should* do. Common pairings may indicate complementary difficulty or style,
but they can also reflect habits and trends. Use them as a starting point, not
a prescription.

Pairing suggestions are not shown for marches, since marches are typically
selected independently of the other concert pieces.
        """)

        st.markdown("---")
        st.markdown("### Programming guide")
        st.markdown("""
**Building a strong adjudicated concert program** requires balancing musical
merit, ensemble capability, and strategic awareness. These principles are
synthesized from FBA mentoring resources, OrchestraTeacher.net, UIL performance
requirements, and experienced adjudicators.

**1. Play to your strengths, not your ego.**
Choose music that showcases your ensemble's strongest sections. Avoid pieces
that feature prominent solos for struggling players or expose weak sections.
"It is not difficult to play difficult music poorly." — James Sammons

**2. Right difficulty, right time.**
Program one grade above your ensemble's comfortable reading level at most.
If students are spending rehearsals learning notes instead of making music,
the piece is too hard. MPA preparation is for refinement, not remediation.

**3. Contrast is everything.**
A strong program has variety in tempo, style, key, and character. If your
first piece is fast and loud, your second should breathe. Judges notice —
and reward — thoughtful programming.

**4. Know the requirements.**
- **Band (UIL/FBA):** Typically march + two concert pieces from the prescribed list.
- **Orchestra (UIL):** Three pieces; first from prescribed list, second from grade-appropriate list, third from any source. No two pieces by the same composer.
- **Orchestra (FOA):** Two from the FOA music list, third from any source. Classification is determined by the *director* based on the level of music chosen, not school size.

**5. The first and last two minutes matter most.**
Open strong, close strong. Judges are human — first impressions and final
impressions carry disproportionate weight.

**6. Transcriptions demand extra work.**
Orchestral transcriptions require studying the original score. Edit doublings,
match the orchestral style and texture. Only program transcriptions if your
ensemble can perform them with the refinement they demand.

**7. Plan for real rehearsal time.**
Assume 70–80% of your scheduled time is effective rehearsal. A typical
program should include pieces totaling 10–15 minutes. Don't overschedule.

**8. Include underrepresented voices.**
Programs that include diverse composers demonstrate musical breadth and
reflect the full landscape of the profession. Use the ICD filter to explore.
        """)

        st.markdown("---")
        st.markdown("### What judges evaluate")
        st.markdown("""
Per the **Texas Music Adjudicators Association** (TMAA) orchestra workshop
and UIL concert adjudication rubric, judges score three areas:

**Tone** — Mature, characteristic sound. Balance and blend across sections.
Intonation. Dynamic contrast without distortion.

**Technique** — Accuracy of notes and rhythms. Appropriate tempo for the
literature. Clean articulation. Observance of ties, slurs, and markings.

**Musicianship** — Appropriate style. Sensitivity to phrasing. Nuance and
contrast. Correct tempo. Conveying musical understanding and emotion.

*Ratings:*
- **I (Superior)** — Worthy of the highest recognition. "Should be fun to hear."
- **II (Excellent)** — Distinctive quality, but minor defects or ineffective interpretation.
- **III (Average)** — Accomplishment and promise, lacking in one or more essentials.
- **IV (Below Average)** — Basic weakness in a fundamental factor.
- **V (Poor)** — Much room for improvement.

Key principle: **Judges evaluate the performance as heard, not the reputation
of the program.** They consider both frequency of errors and recovery from
errors. No performance is expected to be perfect.

*Source: TMAA Orchestra Workshop (Jeff Turner, TMAA Orchestra VP), UIL C&SR rubric.*
        """)

        st.markdown("---")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### Band Database")
            if band_err:
                st.warning(band_err)
            else:
                m1, m2, m3 = st.columns(3)
                m1.metric("Total pieces", f"{len(band_df):,}")
                urm_b = band_df[band_df["ICD Diversity"].notna() & (band_df["ICD Diversity"].astype(str).str.strip() != "")]
                m2.metric("Underrepresented", f"{len(urm_b):,}")
                pct_b = len(urm_b) / len(band_df) * 100
                m3.metric("ICD %", f"{pct_b:.1f}%")

                st.markdown("**Pieces by grade**")
                gc = band_df["Grade"].value_counts().sort_index()
                st.bar_chart(gc, height=200)

        with col2:
            st.markdown("### Orchestra Database")
            if orch_err:
                st.warning(orch_err)
            else:
                m1, m2, m3 = st.columns(3)
                m1.metric("Total pieces", f"{len(orch_df):,}")
                urm_o = orch_df[orch_df["ICD Diversity"].notna() & (orch_df["ICD Diversity"].astype(str).str.strip() != "")]
                m2.metric("Underrepresented", f"{len(urm_o):,}")
                with_perf = orch_df["Total Perfs"].notna().sum() if "Total Perfs" in orch_df.columns else 0
                m3.metric("With UIL data", f"{with_perf:,}")

                st.markdown("**Pieces by grade**")
                gc_o = orch_df["Grade"].value_counts().sort_index()
                st.bar_chart(gc_o, height=200)

        st.markdown("---")
        st.caption("Data sources: Florida Bandmasters Association Concert MPA (2009–2026), "
                   "Texas UIL Concert & Sightreading (2009–2026), "
                   "Wind Repertory Project (windrep.org), "
                   "Teaching Music Through Performance in Band & Orchestra, "
                   "Kreines Concert Repertoire Guide, Band Directors Guide, "
                   "Institute for Composer Diversity, 22 state prescribed music lists, "
                   "Colorado Bandmasters Association PML, SCSBOA (CA), PMEA (PA).")

    # ==================================================================
    # TAB 5: The Tuba of Fate
    # ==================================================================
    with tab5:
        st.markdown("### The Tuba of Fate")
        st.markdown("An interactive choose-your-own-adventure for selecting concert repertoire.")
        st.link_button(
            "Play The Tuba of Fate",
            "https://claude.ai/public/artifacts/e87fc043-7693-4fb9-ab85-c9a357381543",
            type="primary",
        )


if __name__ == "__main__":
    main()
