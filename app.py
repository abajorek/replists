"""
Repertoire Database Explorer
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
    page_title="Repertoire Explorer",
    page_icon="🎵",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    /* Header bar */
    .main-header {
        background: linear-gradient(135deg, #7B2D26 0%, #A13D34 100%);
        color: white;
        padding: 1.2rem 2rem;
        border-radius: 10px;
        margin-bottom: 1.5rem;
    }
    .main-header h1 { color: white; margin: 0; font-size: 1.8rem; }
    .main-header p { color: #F5E6C8; margin: 0.3rem 0 0 0; font-size: 0.95rem; }

    /* Piece detail card */
    .detail-card {
        background: #FDF8F0;
        border: 1px solid #E8D5B5;
        border-radius: 10px;
        padding: 1.2rem 1.5rem;
        margin: 0.8rem 0;
    }
    .detail-card h4 { color: #7B2D26; margin: 0 0 0.3rem 0; }
    .detail-card .meta { color: #6B6B6B; font-size: 0.9rem; }

    /* Pairing card */
    .pairing-card {
        background: #F0F4F8;
        border: 1px solid #D0D8E0;
        border-radius: 8px;
        padding: 0.7rem 1rem;
        margin: 0.4rem 0;
    }

    /* Program sidebar piece */
    .program-piece {
        background: #FDF8F0;
        border-left: 3px solid #C8962E;
        padding: 0.5rem 0.8rem;
        margin-bottom: 0.4rem;
        border-radius: 0 6px 6px 0;
    }

    /* Step indicator */
    .step-indicator {
        background: #7B2D26;
        color: white;
        display: inline-block;
        width: 28px; height: 28px;
        border-radius: 50%;
        text-align: center;
        line-height: 28px;
        font-weight: 600;
        font-size: 0.85rem;
        margin-right: 8px;
    }
    .step-inactive {
        background: #D0D0D0;
    }

    /* Metrics */
    [data-testid="stMetric"] {
        background: #FDF8F0;
        border: 1px solid #E8D5B5;
        padding: 0.8rem;
        border-radius: 8px;
    }

    [data-testid="stSidebar"] { background-color: #FAFAFA; }
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

# Orchestra has fewer columns — filter sort options
ORCH_SORT_OPTIONS = {
    "Recommended overall": SORT_OPTIONS["Recommended overall"],
    "Most endorsed by professionals": SORT_OPTIONS["Most endorsed by professionals"],
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
BAND_DISPLAY = ["Title", "Composer", "Grade", "Best Bet", "MPA Confidence",
                "Street Cred", "ICD Diversity", "Trend Direction", "Categories", "On CBA PML"]
ORCH_DISPLAY = ["Title", "Composer", "Grade", "Best Bet", "Street Cred",
                "ICD Diversity", "Ensemble", "On TMTP"]

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

    st.markdown(
        f'<div class="detail-card">'
        f'<h4>{title}</h4>'
        f'<div class="meta">{composer} · Grade {grade}</div>'
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
        tp = row.get("Total Perfs", "")
        if pd.notna(tp) and str(tp).strip():
            st.markdown(f"**Times performed at festival:** {int(tp):,}")
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
    st.sidebar.markdown("### Program Check")

    grades = [p["Grade"] for p in prog if pd.notna(p.get("Grade"))]
    if grades:
        st.sidebar.markdown(f"**Grade range:** {min(grades)} – {max(grades)}")
        if len(grades) > 1 and len(set(grades)) == 1:
            st.sidebar.warning("All pieces are the same grade — consider varying difficulty.")

    has_div = any(
        pd.notna(p.get("ICD Diversity")) and str(p.get("ICD Diversity", "")).strip()
        for p in prog
    )
    if has_div:
        st.sidebar.success("Includes underrepresented composer (ICD) ✓")
    else:
        st.sidebar.warning("No underrepresented composer — consider adding one (ICD).")

    all_tags = set()
    for p in prog:
        for col in ["Style Tags", "Categories"]:
            val = p.get(col)
            if pd.notna(val) and val:
                for t in str(val).split(";"):
                    t = t.strip()
                    if t: all_tags.add(t)
    if len(all_tags) >= 3:
        st.sidebar.success(f"Good stylistic contrast ({len(all_tags)} different styles) ✓")
    elif len(all_tags) >= 1:
        st.sidebar.info(f"Some contrast ({len(all_tags)} style{'s' if len(all_tags)!=1 else ''}) — could be stronger.")
    elif prog:
        st.sidebar.warning("No style data available for contrast check.")


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
    lines.append("Generated with Repertoire Database Explorer")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    init_program()

    st.markdown("""
    <div class="main-header">
        <h1>Repertoire Database Explorer</h1>
        <p>Browse vetted repertoire · Build adjudicated concert programs</p>
    </div>
    """, unsafe_allow_html=True)

    band_df, band_err = safe_load(load_band, "Band")
    orch_df, orch_err = safe_load(load_orchestra, "Orchestra")
    pairings_data = load_pairings()

    tab1, tab2, tab3 = st.tabs(["Browse Repertoire", "Build a Program", "About the Data"])

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

        st.dataframe(
            filtered[dcols].reset_index(drop=True),
            use_container_width=True,
            hide_index=True,
            height=500,
        )

        # Detail view
        if not filtered.empty:
            with st.expander("Select a piece to learn more"):
                options = filtered.apply(
                    lambda r: f"{r['Title']}  —  {r['Composer']}" if pd.notna(r.get("Composer")) else str(r["Title"]),
                    axis=1,
                ).tolist()
                choice = st.selectbox("Piece", options, index=None, key="detail_sel",
                                      label_visibility="collapsed")
                if choice is not None:
                    row = filtered.iloc[options.index(choice)]
                    render_piece_card(row, pairings_data, source, is_band)

    # ==================================================================
    # TAB 2: Program Builder (Wizard)
    # ==================================================================
    with tab2:
        prog = st.session_state["program"]
        n_prog = len(prog)

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
        st.sidebar.markdown("---")
        st.sidebar.markdown(f"### Narrow Your Search")
        filtered_pb = apply_filters(source_pb, is_band_pb, key_prefix="pb_")
        render_program_sidebar()

        # Step indicators
        steps_html = ""
        for i in range(1, 4):
            label = f"Piece {i}"
            if i <= n_prog:
                p = prog[i-1]
                label = p.get("Title", "Piece")[:25]
                cls = "step-indicator"
            elif i == n_prog + 1:
                cls = "step-indicator"
            else:
                cls = "step-indicator step-inactive"
            steps_html += f'<span class="{cls}">{i}</span> {label} &nbsp;&nbsp;&nbsp;'

        st.markdown(steps_html, unsafe_allow_html=True)
        st.markdown("")

        # --- Program complete ---
        if n_prog >= 3:
            st.success("Your program is complete — 3 pieces selected.")
            st.markdown("Review your selections in the sidebar, or export below.")

            st.markdown("---")
            for i, p in enumerate(prog):
                st.markdown(f"### Piece {i+1}")
                render_piece_card(p, pairings_data, source_pb, is_band_pb,
                                  prog_titles={(
                                      _norm_title(pp.get("Title", "")),
                                      _norm_composer(pp.get("Composer", ""))
                                  ) for pp in prog})

            st.markdown("---")
            st.markdown("### Export")
            ec1, ec2 = st.columns(2)
            ec1.download_button("Download as CSV", data=export_csv(prog),
                                file_name="concert_program.csv", mime="text/csv")
            ec2.download_button("Download program sheet", data=export_text(prog),
                                file_name="concert_program.txt", mime="text/plain")
            return

        # --- Selecting next piece ---
        piece_num = n_prog + 1
        if n_prog == 0:
            st.markdown("### Choose your first piece")
            st.markdown("Use the filters in the sidebar to narrow by grade level, style, "
                        "or composer identity. Then sort to find what matters most to you.")
        elif n_prog == 1:
            st.markdown("### Choose your second piece")
            st.markdown(f"Your first piece is **{prog[0].get('Title', '')}**. "
                        "Look for something that contrasts — a different tempo, style, or character.")
        else:
            st.markdown("### Choose your third piece")
            st.markdown("Complete your program. Think about what's missing — "
                        "if you have two slower pieces, consider something energetic, or vice versa.")

        # Sort
        sort_pb = st.selectbox(
            "Sort pieces by",
            list(sort_opts_pb.keys()),
            index=0,
            key="pb_sort",
            help="Choose what matters most to you for this selection.",
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

        # Piece selection
        if not filtered_pb.empty:
            options_pb = filtered_pb.apply(
                lambda r: f"{r['Title']}  —  {r['Composer']}  (Gr {r.get('Grade', '?')})"
                if pd.notna(r.get("Composer")) else str(r["Title"]),
                axis=1,
            ).tolist()

            selected = st.selectbox(
                f"Select piece {piece_num}",
                options_pb,
                index=None,
                key=f"wizard_sel_{piece_num}",
                placeholder="Type to search or scroll...",
            )

            if selected is not None:
                row = filtered_pb.iloc[options_pb.index(selected)]
                prog_titles = {(
                    _norm_title(pp.get("Title", "")),
                    _norm_composer(pp.get("Composer", ""))
                ) for pp in prog}

                did_add = render_piece_card(
                    row, pairings_data, source_pb, is_band_pb,
                    show_add=True,
                    prog_titles=prog_titles,
                )
                if did_add:
                    add_piece(row.to_dict())
                    st.rerun()

    # ==================================================================
    # TAB 3: About the Data
    # ==================================================================
    with tab3:
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
Based on Music Performance Assessment (MPA) data from Florida — adjudicated
festivals where ensembles perform prepared music and sight-reading for a panel
of judges who assign ratings from Superior (I) to Poor (V). This score
reflects how consistently ensembles performing this piece earn top ratings,
adjusted for grade level. *Only available for the band database.*

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
                pct_o = len(urm_o) / len(orch_df) * 100
                m3.metric("ICD %", f"{pct_o:.1f}%")

                st.markdown("**Pieces by grade**")
                gc_o = orch_df["Grade"].value_counts().sort_index()
                st.bar_chart(gc_o, height=200)

        st.markdown("---")
        st.caption("Data sources: Florida Bandmasters Association MPA (2009–2020), "
                   "Texas UIL Concert & Sightreading (2009–2026), "
                   "Teaching Music Through Performance in Band & Orchestra, "
                   "Kreines Concert Repertoire Guide, Band Directors Guide, "
                   "Institute for Composer Diversity, 22 state prescribed music lists, "
                   "Colorado Bandmasters Association PML, SCSBOA (CA), PMEA (PA).")


if __name__ == "__main__":
    main()
