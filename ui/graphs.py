# ui/graphs.py
# Streamlit graphs page using the SAME DataFrame already loaded in the app.
# Layout:
#   • Overview        ── KPIs + Completeness
#   • Job & Location  ── mini-tabs: Location (Treemap) | Job Type (Donut) | Hours/Week (Box/Bar)
#   • Enhancements    ── mini-tabs: All | Tools | Tech Skill | Contact | Period/Contract
#   • Languages       ── mini-tabs: Natural (Donut) | Programming (Donut)
#   • Time            ── mini-tab: Freshness (Line)
#
# Call render_page() (grabs st.session_state["df"]) or render(df).

from __future__ import annotations

import re
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

# App config
from .config import (
    ENHANCEMENT_COLUMNS as BASE_ENHANCEMENT_COLUMNS,
    TOPN_DEFAULT,
    FRESHNESS_CANDIDATES,
    NATURAL_LANGS,
    PROG_LANGS,
    JOB_TYPE_CANON,  # <- use canonical set to filter graph labels
)

# Names used by preprocessing; provide defaults if not imported
try:
    from .data_processing import NAT_LANG_COL, PROG_LANG_COL
except Exception:
    NAT_LANG_COL = "natural_languages"
    PROG_LANG_COL = "programming_languages"

# Columns we chart in dedicated sections (so we exclude them from generic enh.)
EXCLUDE_FROM_GENERIC = {
    "enhanced_languages",
    "enhanced_location",
    "enhanced_type",
    "enhanced_hours_per_week",
}
GENERIC_ENHANCEMENTS = [c for c in BASE_ENHANCEMENT_COLUMNS if c not in EXCLUDE_FROM_GENERIC]


# ────────────────────────────── helpers ────────────────────────────── #

def _tok(s: str) -> str:
    s = s.strip().lower()
    s = re.sub(r"[^\w+.\-#/ ,]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s

def _to_list(cell) -> List[str]:
    if isinstance(cell, list):
        return [str(v) for v in cell if f"{v}".strip()]
    if isinstance(cell, dict):
        return [f"{k}: {v}" for k, v in cell.items()]
    if isinstance(cell, str):
        return [p.strip() for p in re.split(r"[;,/|]", cell) if p.strip()]
    return []

def _explode_enhancements(df: pd.DataFrame, cols: List[str]) -> pd.DataFrame:
    rows = []
    for col in cols:
        if col not in df.columns:
            continue
        for idx, val in df[col].items():
            for token in _to_list(val):
                tok = _tok(token)
                if tok:
                    rows.append({"row_id": idx, "enhancement_type": col, "value": tok})
    return pd.DataFrame(rows)

# --- MODIFIED: This function no longer creates an "other" bucket ---
def _get_top_n(vc: pd.Series, n: int) -> pd.DataFrame:
    """Return Top-N items as a DataFrame, without an 'other' category."""
    vc = vc.dropna()
    top_n_items = vc.head(n)
    return top_n_items.rename_axis("value").reset_index(name="Count")

def _bar_counts(df_counts: pd.DataFrame, title: str, height: int = 520):
    if df_counts.empty:
        st.info("No data to display.")
        return
    fig = px.bar(
        df_counts,
        x="Count",
        y="value",
        orientation="h",
        text="Count",
        title=title,
    )
    fig.update_layout(template="plotly_dark", height=height, margin=dict(t=40, l=10, r=10, b=20))
    fig.update_yaxes(categoryorder="total ascending", title=None)
    fig.update_xaxes(title="Count", rangemode="tozero")
    st.plotly_chart(fig, use_container_width=True)

def _donut(df_counts: pd.DataFrame, title: str, height: int = 360):
    if df_counts.empty:
        st.info("No data to display.")
        return
    fig = px.pie(df_counts, values="Count", names="value", hole=0.55, title=title)
    fig.update_layout(template="plotly_dark", height=height, margin=dict(t=40, l=10, r=10, b=20))
    st.plotly_chart(fig, use_container_width=True)

def _treemap(df_counts: pd.DataFrame, title: str, height: int = 520):
    if df_counts.empty:
        st.info("No data to display.")
        return
    df_counts = df_counts.rename(columns={"value": "label"})
    fig = px.treemap(df_counts, path=["label"], values="Count", title=title)
    fig.update_layout(template="plotly_dark", height=height, margin=dict(t=40, l=10, r=10, b=20))
    st.plotly_chart(fig, use_container_width=True)

def _freshness_series(df: pd.DataFrame) -> Tuple[Optional[str], pd.DataFrame]:
    for c in FRESHNESS_CANDIDATES:
        if c in df.columns:
            s = pd.to_datetime(df[c], errors="coerce").dropna()
            if not s.empty:
                daily = s.dt.date.value_counts().sort_index()
                return c, daily.rename_axis("Date").reset_index(name="Count")
    return None, pd.DataFrame(columns=["Date", "Count"])

def _completeness_table(df: pd.DataFrame) -> pd.DataFrame:
    comp = df.notna().mean().mul(100).round(1)
    return comp.rename("Completeness %").reset_index().rename(columns={"index": "Column"})

def _dup_pct(df: pd.DataFrame) -> float:
    if "job_link" in df.columns:
        uniq = df["job_link"].dropna().nunique()
    else:
        cols = [c for c in ["job_position", "company_name"] if c in df.columns]
        if not cols:
            return 0.0
        uniq = df[cols].dropna(how="all").drop_duplicates().shape[0]
    return round(100 * (1 - uniq / max(1, len(df))), 2)

def _ensure_language_split(df: pd.DataFrame) -> pd.DataFrame:
    """
    Ensure we have NAT_LANG_COL and PROG_LANG_COL.
    If missing, derive them from enhanced_languages using vocab.
    """
    if NAT_LANG_COL in df.columns and PROG_LANG_COL in df.columns:
        return df

    new = df.copy()
    if "enhanced_languages" not in new.columns:
        new[NAT_LANG_COL] = [[] for _ in range(len(new))]
        new[PROG_LANG_COL] = [[] for _ in range(len(new))]
        return new

    def split_cell(cell) -> Tuple[List[str], List[str]]:
        naturals, progs = [], []
        for raw in _to_list(cell):
            tok = _tok(raw)
            if tok in NATURAL_LANGS:
                naturals.append(tok)
            elif tok in PROG_LANGS:
                progs.append(tok)
        # dedupe keep order
        def dedupe(seq):
            seen, out = set(), []
            for x in seq:
                if x not in seen:
                    seen.add(x); out.append(x)
            return out
        return dedupe(naturals), dedupe(progs)

    nat, prog = zip(*[split_cell(x) for x in new["enhanced_languages"]])
    new[NAT_LANG_COL] = list(nat)
    new[PROG_LANG_COL] = list(prog)
    return new

def _hours_to_numeric(cell) -> Optional[float]:
    """
    Convert 'enhanced_hours_per_week' cell to a single numeric when possible.
    Examples: '40', '32-40', '38 hours', 'full-time' (≈40), 'part-time' (≈20)
    """
    if isinstance(cell, (int, float)):
        return float(cell)
    if not isinstance(cell, str):
        return None
    s = _tok(cell)
    # range like 32-40
    m = re.search(r"(\d+)\s*[-–]\s*(\d+)", s)
    if m:
        a, b = float(m.group(1)), float(m.group(2))
        return (a + b) / 2.0
    # single number
    m = re.search(r"(\d+(\.\d+)?)", s)
    if m:
        return float(m.group(1))
    # semantic fallbacks
    if "full" in s:
        return 40.0
    if "part" in s:
        return 20.0
    return None


# ──────────────────────────── top-level tabs ──────────────────────────── #

def _section_overview(df: pd.DataFrame):
    st.markdown("#### Overview")
    dup_pct = _dup_pct(df)
    fresh_col, fresh_df = _freshness_series(df)
    median_days = None
    if not fresh_df.empty:
        ages = (pd.Timestamp.now().normalize() - pd.to_datetime(fresh_df["Date"])).dt.days
        median_days = int(np.median(ages)) if len(ages) else None

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rows", len(df))
    c2.metric("Duplicates (%)", dup_pct)
    c3.metric("Freshness column", fresh_col or "—")
    c4.metric("Median days since", "—" if median_days is None else median_days)

    with st.expander("Data completeness (%)", expanded=False):
        st.dataframe(_completeness_table(df), hide_index=True, use_container_width=True)

    return fresh_df  # to reuse on Time tab

def _section_job_location(df: pd.DataFrame, top_n: int):
    st.markdown("#### Job & Location")
    tabs = st.tabs(["Location", "Job Type", "Hours/Week"])

    # Location (Treemap)
    with tabs[0]:
        col = "enhanced_location" if "enhanced_location" in df.columns else "job_location"
        if col not in df.columns:
            st.info("No location column found.")
        else:
            series = df[col].fillna("").astype(str).apply(_tok)
            series = series[series.str.len() > 0]
            if series.empty:
                st.info("No location data to display.")
            else:
                vc = _get_top_n(series.value_counts(), top_n) # <-- MODIFIED
                _treemap(vc, "Top locations (treemap)")


    # Job Type (Donut) — filter to canonical labels only
    with tabs[1]:
        col = "enhanced_type" if "enhanced_type" in df.columns else None
        if not col or col not in df.columns:
            st.info("No job type column found.")
        else:
            s = df[col].apply(lambda v: _tok(v) if isinstance(v, str) else "")
            s = s[s.isin(JOB_TYPE_CANON)]  # <- drop anything not in {remote,on-site,hybrid}
            if s.empty:
                st.info("No valid job type values after normalization.")
            else:
                dfc = s.value_counts().rename_axis("value").reset_index(name="Count")
                _donut(dfc, "Job type distribution")

    # Hours/Week (Box or Bar)
    with tabs[2]:
        col = "enhanced_hours_per_week"
        if col not in df.columns:
            st.info("No hours-per-week column found.")
        else:
            nums = df[col].apply(_hours_to_numeric).dropna().astype(float)
            if len(nums) >= 3:
                fig = px.box(nums, x=nums, points="all", title="Hours per week (boxplot)")
                fig.update_layout(template="plotly_dark", height=320, margin=dict(t=40, l=10, r=10, b=20))
                fig.update_xaxes(title="Hours/week")
                fig.update_yaxes(title=None, showticklabels=False)
                st.plotly_chart(fig, use_container_width=True)
            else:
                s = df[col].fillna("").astype(str).apply(_tok)
                if s.str.len().sum() == 0:
                    st.info("No hours-per-week data to display.")
                else:
                    dfc = s.value_counts().rename_axis("value").reset_index(name="Count")
                    _bar_counts(dfc, "Hours per week (categorical)", height=420)

def _section_enhancements(df: pd.DataFrame, top_n: int):
    st.markdown("#### Enhancements")
    cols = [c for c in GENERIC_ENHANCEMENTS if c in df.columns]
    if not cols:
        st.info("No enhancement columns available.")
        return

    df_long = _explode_enhancements(df, cols)

    if df_long.empty:
        st.info("No enhancement data to display.")
        return

    tabs = st.tabs(["All"] + cols)

    with tabs[0]:
        vc = df_long["value"].value_counts()
        _bar_counts(_get_top_n(vc, top_n), "Top items across enhancement columns") # <-- MODIFIED

    for i, col in enumerate(cols, start=1):
        with tabs[i]:
            sub = df_long[df_long["enhancement_type"] == col]
            if sub.empty:
                st.info(f"No data for '{col}'.")
            else:
                vc = sub["value"].value_counts()
                pretty = col.replace("enhanced_", "").replace("_", " ").title()
                _bar_counts(_get_top_n(vc, top_n), f"Top items — {pretty}") # <-- MODIFIED


def _section_languages(df: pd.DataFrame, top_n: int):
    st.markdown("#### Languages")
    df_lang = _ensure_language_split(df)
    tabs = st.tabs(["Natural", "Programming"])

    with tabs[0]:
        nat_series = pd.Series([v for lst in df_lang.get(NAT_LANG_COL, []) for v in (lst or [])])
        if nat_series.empty:
            st.info("No natural language data to display.")
        else:
            vc_nat = _get_top_n(nat_series.value_counts(), top_n) # <-- MODIFIED
            _donut(vc_nat, "Top natural languages")


    with tabs[1]:
        prog_series = pd.Series([v for lst in df_lang.get(PROG_LANG_COL, []) for v in (lst or [])])
        if prog_series.empty:
            st.info("No programming language data to display.")
        else:
            vc_prog = _get_top_n(prog_series.value_counts(), top_n) # <-- MODIFIED
            _donut(vc_prog, "Top programming languages")

def _section_time(df_fresh: pd.DataFrame):
    st.markdown("#### Time")
    tabs = st.tabs(["Freshness"])
    with tabs[0]:
        if df_fresh.empty:
            st.info("No date column found (job_posting_date / date_collected / scrape_date).")
        else:
            fig = px.line(df_fresh, x="Date", y="Count", markers=True, title="Records by date")
            fig.update_layout(template="plotly_dark", height=320, margin=dict(t=40, l=10, r=10, b=20))
            st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────── page ─────────────────────────────── #

def render(df_raw: Optional[pd.DataFrame]):
    """Render the Graphs page using the SAME df the app already loaded."""
    st.subheader("📊 Graphs & Data Quality")
    if df_raw is None or df_raw.empty:
        st.warning("Load data first (Run scrape or Demo), then open this tab.")
        return

    # global control for Top-N
    top_n = st.slider("Top-N items", 5, 50, TOPN_DEFAULT, 5)

    # Top-level tabs → each uses mini-tabs internally
    t_overview, t_jobloc, t_enh, t_lang, t_time = st.tabs(
        ["Overview", "Job & Location", "Enhancements", "Languages", "Time"]
    )

    with t_overview:
        fresh_df = _section_overview(df_raw)

    with t_jobloc:
        _section_job_location(df_raw, top_n)

    with t_enh:
        _section_enhancements(df_raw, top_n)

    with t_lang:
        _section_languages(df_raw, top_n)

    with t_time:
        _section_time(fresh_df)

def render_page():
    """Back-compat shim: read df from session and render."""
    df = st.session_state.get("df")  # same df used in Explore/Insights
    render(df)