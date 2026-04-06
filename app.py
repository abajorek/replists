"""
Repertoire Database Explorer
Colorado Mesa University — Instrumental Methods
"""

import streamlit as st
import pandas as pd
import os
import io
import textwrap

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

    /* Piece cards in program builder */
    .piece-card {
        background: #FDF8F0;
        border: 1px solid #E8D5B5;
        border-radius: 8px;
        padding: 0.8rem 1rem;
        margin-bottom: 0.5rem;
    }
    .piece-card .title { font-weight: 600; color: #7B2D26; }
    .piece-card .meta { font-size: 0.85rem; color: #6B6B6B; }

    /* Program sidebar */
    .program-piece {
        background: #FDF8F0;
        border-left: 3px solid #C8962E;
        padding: 0.5rem 0.8rem;
        margin-bottom: 0.4rem;
        border-radius: 0 6px 6px 0;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        padding: 8px 20px;
        border-radius: 6px 6px 0 0;
    }

    /* Metrics */
    [data-testid="stMetric"] {
        background: #FDF8F0;
        border: 1px solid #E8D5B5;
        padding: 0.8rem;
        border-radius: 8px;
    }

    /* Sidebar header */
    [data-testid="stSidebar"] { background-color: #FAFAFA; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Data paths & column config
# ---------------------------------------------------------------------------

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
BAND_FILE = os.path.join(DATA_DIR, "WindBand_Repertoire_Database.xlsx")
ORCH_FILE = os.path.join(DATA_DIR, "Orchestra_Repertoire_Database.xlsx")

BAND_DISPLAY = [
    "Title", "Composer", "Grade", "Best Bet", "MPA Confidence",
    "Street Cred", "ICD Diversity", "Trend Direction", "Categories",
    "On CBA PML",
]
ORCH_DISPLAY = [
    "Title", "Composer", "Grade", "Best Bet", "Street Cred",
    "ICD Diversity", "Ensemble", "On TMTP",
]

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner="Loading band repertoire...")
def load_band() -> pd.DataFrame:
    return pd.read_excel(BAND_FILE, sheet_name="Band Originals")


@st.cache_data(show_spinner="Loading orchestra repertoire...")
def load_orchestra() -> pd.DataFrame:
    return pd.read_excel(ORCH_FILE, sheet_name="Orchestra Repertoire")


def safe_load(loader, label):
    try:
        return loader(), None
    except FileNotFoundError:
        return None, f"{label} data file not found. Place the XLSX in the app directory."
    except Exception as e:
        return None, f"Error loading {label} data: {e}"


# ---------------------------------------------------------------------------
# Sidebar filters
# ---------------------------------------------------------------------------

def apply_filters(df, is_band: bool, key_prefix: str = ""):
    """Render sidebar filters and return filtered dataframe."""
    kp = key_prefix

    # Grade
    grades = sorted(df["Grade"].dropna().unique())
    sel_grades = st.sidebar.multiselect("Grade level", grades, default=[], key=f"{kp}grade")
    if sel_grades:
        df = df[df["Grade"].isin(sel_grades)]

    # Best Bet
    if "Best Bet" in df.columns and df["Best Bet"].notna().any():
        bb_min, bb_max = float(df["Best Bet"].min()), float(df["Best Bet"].max())
        if bb_min < bb_max:
            min_bb = st.sidebar.slider("Minimum Best Bet", bb_min, bb_max, bb_min,
                                       step=1.0, key=f"{kp}bb")
            df = df[df["Best Bet"] >= min_bb]

    # URM only
    if "ICD Diversity" in df.columns:
        if st.sidebar.checkbox("URM composers only", key=f"{kp}urm"):
            df = df[df["ICD Diversity"].notna() & (df["ICD Diversity"].astype(str).str.strip() != "")]

    # Band: Style Tags / Categories
    if is_band:
        for col in ["Categories", "Style Tags"]:
            if col in df.columns:
                tags = set()
                for val in df[col].dropna():
                    for t in str(val).split(";"):
                        t = t.strip()
                        if t:
                            tags.add(t)
                if tags:
                    sel = st.sidebar.multiselect(col, sorted(tags), default=[], key=f"{kp}{col}")
                    if sel:
                        df = df[df[col].apply(
                            lambda v: any(t in str(v) for t in sel) if pd.notna(v) else False
                        )]

    # Orchestra: Ensemble
    if not is_band and "Ensemble" in df.columns:
        ens = sorted(df["Ensemble"].dropna().unique())
        if ens:
            sel_ens = st.sidebar.multiselect("Ensemble type", ens, default=[], key=f"{kp}ens")
            if sel_ens:
                df = df[df["Ensemble"].isin(sel_ens)]

    # CBA PML filter (band only)
    if is_band and "On CBA PML" in df.columns:
        if st.sidebar.checkbox("On CBA PML only", key=f"{kp}cba"):
            df = df[df["On CBA PML"].notna() & (df["On CBA PML"].astype(str).str.strip() != "")]

    # Text search
    search = st.sidebar.text_input("Search title / composer", key=f"{kp}search")
    if search:
        s = search.lower()
        df = df[
            df["Title"].fillna("").str.lower().str.contains(s, regex=False)
            | df["Composer"].fillna("").str.lower().str.contains(s, regex=False)
        ]

    return df


# ---------------------------------------------------------------------------
# Program builder state
# ---------------------------------------------------------------------------

def init_program():
    if "program" not in st.session_state:
        st.session_state["program"] = []


def add_piece(row_dict):
    prog = st.session_state["program"]
    key = (row_dict.get("Title", ""), row_dict.get("Composer", ""))
    existing = [(p.get("Title", ""), p.get("Composer", "")) for p in prog]
    if key not in existing and len(prog) < 3:
        prog.append(row_dict)


def remove_piece(idx):
    prog = st.session_state["program"]
    if 0 <= idx < len(prog):
        prog.pop(idx)


def render_program_sidebar():
    prog = st.session_state["program"]
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🎼 Your Program")

    if not prog:
        st.sidebar.info("No pieces yet. Add up to 3 from the list.")
        return

    for i, p in enumerate(prog):
        st.sidebar.markdown(
            f'<div class="program-piece">'
            f'<strong>{i+1}. {p.get("Title", "?")}</strong><br>'
            f'<span style="font-size:0.85rem;color:#6B6B6B;">'
            f'{p.get("Composer", "")} &middot; Gr {p.get("Grade", "?")} '
            f'&middot; BB {p.get("Best Bet", "N/A")}</span></div>',
            unsafe_allow_html=True,
        )
        if st.sidebar.button("Remove", key=f"rm_{i}"):
            remove_piece(i)
            st.rerun()

    # --- Feedback ---
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Feedback")

    # Grade range
    grades = [p["Grade"] for p in prog if pd.notna(p.get("Grade"))]
    if grades:
        st.sidebar.markdown(f"**Grade range:** {min(grades)} – {max(grades)}")
        if len(grades) > 1 and len(set(grades)) == 1:
            st.sidebar.warning("All pieces are the same grade — consider varying difficulty.")

    # Diversity
    has_urm = any(
        pd.notna(p.get("ICD Diversity")) and str(p.get("ICD Diversity", "")).strip()
        for p in prog
    )
    if has_urm:
        st.sidebar.success("Includes URM composer ✓")
    else:
        st.sidebar.warning("No URM composer — consider adding one.")

    # Contrast
    all_tags = set()
    for p in prog:
        for col in ["Style Tags", "Categories"]:
            val = p.get(col)
            if pd.notna(val) and val:
                for t in str(val).split(";"):
                    t = t.strip()
                    if t:
                        all_tags.add(t)
    if len(all_tags) >= 3:
        st.sidebar.success(f"Good contrast ({len(all_tags)} style tags) ✓")
    elif len(all_tags) >= 1:
        st.sidebar.info(f"Some contrast ({len(all_tags)} tag{'s' if len(all_tags)!=1 else ''}) — could be stronger.")
    elif prog:
        st.sidebar.warning("No style data available for contrast check.")


def export_csv(prog):
    cols = ["Title", "Composer", "Arranger", "Grade", "Best Bet", "Street Cred",
            "MPA Confidence", "ICD Diversity", "ICD Detail", "Categories"]
    rows = [{c: p.get(c, "") for c in cols} for p in prog]
    return pd.DataFrame(rows).to_csv(index=False)


def export_text(prog):
    lines = [
        "ADJUDICATED CONCERT PROGRAM",
        "=" * 40, "",
    ]
    for i, p in enumerate(prog, 1):
        lines.append(f"{i}. {p.get('Title', '?')}")
        composer = p.get("Composer", "")
        arranger = p.get("Arranger", "")
        credit = composer
        if arranger and pd.notna(arranger) and str(arranger).strip():
            credit += f" (arr. {arranger})"
        lines.append(f"   {credit}")
        lines.append(f"   Grade {p.get('Grade', '?')}  |  Best Bet {p.get('Best Bet', 'N/A')}  |  Street Cred {p.get('Street Cred', 'N/A')}")
        icd = p.get("ICD Diversity", "")
        if pd.notna(icd) and str(icd).strip():
            lines.append(f"   ICD: {icd} — {p.get('ICD Detail', '')}")
        lines.append("")

    # Summary
    grades = [p["Grade"] for p in prog if pd.notna(p.get("Grade"))]
    if grades:
        lines.append(f"Grade range: {min(grades)} – {max(grades)}")
    has_urm = any(pd.notna(p.get("ICD Diversity")) and str(p.get("ICD Diversity", "")).strip() for p in prog)
    lines.append(f"URM composer included: {'Yes' if has_urm else 'No'}")
    lines.append("")
    lines.append("Generated with Repertoire Database Explorer")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    init_program()

    # Header
    st.markdown("""
    <div class="main-header">
        <h1>Repertoire Database Explorer</h1>
        <p>Colorado Mesa University &middot; Instrumental Methods</p>
    </div>
    """, unsafe_allow_html=True)

    # Load data
    band_df, band_err = safe_load(load_band, "Band")
    orch_df, orch_err = safe_load(load_orchestra, "Orchestra")

    tab1, tab2, tab3 = st.tabs(["🔍 Explore Repertoire", "📋 Program Builder", "📊 Data Insights"])

    # ==================================================================
    # TAB 1: Explore
    # ==================================================================
    with tab1:
        db_choice = st.radio("Database", ["Band", "Orchestra"], horizontal=True, key="explore_db")
        is_band = db_choice == "Band"

        if is_band:
            if band_err:
                st.error(band_err); return
            source = band_df.copy()
            dcols = [c for c in BAND_DISPLAY if c in source.columns]
        else:
            if orch_err:
                st.error(orch_err); return
            source = orch_df.copy()
            dcols = [c for c in ORCH_DISPLAY if c in source.columns]

        st.sidebar.markdown(f"### Filters — {db_choice}")
        filtered = apply_filters(source, is_band, key_prefix="ex_")

        st.markdown(f"**{len(filtered):,}** pieces match your filters")

        # Sortable dataframe
        st.dataframe(
            filtered[dcols].reset_index(drop=True),
            use_container_width=True,
            hide_index=True,
            height=500,
        )

        # Detail view
        if not filtered.empty:
            with st.expander("View piece details"):
                options = filtered.apply(
                    lambda r: f"{r['Title']}  —  {r['Composer']}" if pd.notna(r.get("Composer")) else str(r["Title"]),
                    axis=1,
                ).tolist()
                choice = st.selectbox("Select a piece", options, index=None, key="detail_sel")
                if choice is not None:
                    row = filtered.iloc[options.index(choice)]
                    col1, col2 = st.columns(2)
                    left_cols = ["Title", "Composer", "Arranger", "Grade", "Best Bet",
                                 "MPA Confidence", "Street Cred", "Raw MPA Score"]
                    right_cols = ["ICD Diversity", "ICD Detail", "Categories", "Style Tags",
                                  "On CBA PML", "State List Count", "Trend Direction",
                                  "Total Perfs", "Unique Schools", "Ensemble", "On TMTP"]
                    with col1:
                        for c in left_cols:
                            if c in row.index and pd.notna(row[c]) and str(row[c]).strip():
                                st.markdown(f"**{c}:** {row[c]}")
                    with col2:
                        for c in right_cols:
                            if c in row.index and pd.notna(row[c]) and str(row[c]).strip():
                                st.markdown(f"**{c}:** {row[c]}")

    # ==================================================================
    # TAB 2: Program Builder
    # ==================================================================
    with tab2:
        db_choice_pb = st.radio("Database", ["Band", "Orchestra"], horizontal=True, key="pb_db")
        is_band_pb = db_choice_pb == "Band"

        if is_band_pb:
            if band_err:
                st.error(band_err); return
            source_pb = band_df.copy()
            dcols_pb = [c for c in BAND_DISPLAY if c in source_pb.columns]
        else:
            if orch_err:
                st.error(orch_err); return
            source_pb = orch_df.copy()
            dcols_pb = [c for c in ORCH_DISPLAY if c in source_pb.columns]

        st.sidebar.markdown("---")
        st.sidebar.markdown(f"### Builder Filters — {db_choice_pb}")
        filtered_pb = apply_filters(source_pb, is_band_pb, key_prefix="pb_")

        # Program sidebar
        render_program_sidebar()

        # Status bar
        n_prog = len(st.session_state["program"])
        status_col1, status_col2 = st.columns([3, 1])
        status_col1.markdown(f"**{len(filtered_pb):,}** pieces match  |  **{n_prog}/3** in program")
        if n_prog >= 3:
            status_col2.success("Program full!")

        # Piece list with add buttons
        display_limit = 80
        for i, (_, row) in enumerate(filtered_pb.head(display_limit).iterrows()):
            c1, c2, c3 = st.columns([4, 2, 1])
            c1.markdown(f"**{row.get('Title', '')}** — {row.get('Composer', '')}")
            meta_parts = [f"Gr {row.get('Grade', '?')}", f"BB {row.get('Best Bet', '—')}"]
            icd = row.get("ICD Diversity", "")
            if pd.notna(icd) and str(icd).strip():
                meta_parts.append(f"ICD: {icd}")
            c2.caption(" · ".join(meta_parts))
            if c3.button("Add ＋", key=f"add_{i}_{hash(str(row.get('Title','')))}",
                         disabled=n_prog >= 3):
                add_piece(row.to_dict())
                st.rerun()

        if len(filtered_pb) > display_limit:
            st.caption(f"Showing {display_limit} of {len(filtered_pb):,}. Use filters to narrow down.")

        # Export
        if st.session_state["program"]:
            st.markdown("---")
            st.markdown("### Export Program")
            ec1, ec2 = st.columns(2)
            ec1.download_button(
                "⬇ Download CSV",
                data=export_csv(st.session_state["program"]),
                file_name="concert_program.csv",
                mime="text/csv",
            )
            ec2.download_button(
                "⬇ Download Program Sheet",
                data=export_text(st.session_state["program"]),
                file_name="concert_program.txt",
                mime="text/plain",
            )

    # ==================================================================
    # TAB 3: Data Insights
    # ==================================================================
    with tab3:
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("### Band Database")
            if band_err:
                st.warning(band_err)
            else:
                m1, m2, m3 = st.columns(3)
                m1.metric("Total pieces", f"{len(band_df):,}")
                urm_b = band_df[band_df["ICD Diversity"].notna() & (band_df["ICD Diversity"].astype(str).str.strip() != "")]
                m2.metric("URM composers", f"{len(urm_b):,}")
                pct_b = len(urm_b) / len(band_df) * 100
                m3.metric("URM %", f"{pct_b:.1f}%")

                st.markdown("**Pieces by grade**")
                gc = band_df["Grade"].value_counts().sort_index()
                st.bar_chart(gc, height=200)

                st.markdown("**Top 20 by Best Bet**")
                top20b = band_df.dropna(subset=["Best Bet"]).nlargest(20, "Best Bet")[
                    ["Title", "Composer", "Grade", "Best Bet", "Street Cred"]
                ]
                st.dataframe(top20b, hide_index=True, use_container_width=True)

        with col2:
            st.markdown("### Orchestra Database")
            if orch_err:
                st.warning(orch_err)
            else:
                m1, m2, m3 = st.columns(3)
                m1.metric("Total pieces", f"{len(orch_df):,}")
                urm_o = orch_df[orch_df["ICD Diversity"].notna() & (orch_df["ICD Diversity"].astype(str).str.strip() != "")]
                m2.metric("URM composers", f"{len(urm_o):,}")
                pct_o = len(urm_o) / len(orch_df) * 100
                m3.metric("URM %", f"{pct_o:.1f}%")

                st.markdown("**Pieces by grade**")
                gc_o = orch_df["Grade"].value_counts().sort_index()
                st.bar_chart(gc_o, height=200)

                st.markdown("**Top 20 by Best Bet**")
                top20o = orch_df.dropna(subset=["Best Bet"]).nlargest(20, "Best Bet")[
                    ["Title", "Composer", "Grade", "Best Bet", "Street Cred"]
                ]
                st.dataframe(top20o, hide_index=True, use_container_width=True)


if __name__ == "__main__":
    main()
