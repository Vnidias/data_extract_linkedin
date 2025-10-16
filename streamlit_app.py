# streamlit_app.py

import json
from datetime import date
import streamlit as st
import pandas as pd
import os
from pathlib import Path

# ---- Import your modularized utilities ----
from ui import components
from ui import config
from ui import data_processing
from ui import extraction
from ui import visualization
from ui import graphs as graphs_page
from ui import workflow as workflow_page

# ---- App Setup ----
st.set_page_config(page_title=config.APP_TITLE, page_icon="🔎", layout="wide")
st.markdown(components.load_css(config.CSS_PATH), unsafe_allow_html=True)
card_tpl = components.load_card_template(config.CARD_TEMPLATE_PATH)

# ---- Session flags and state initialization ----
if "cancel_scrape" not in st.session_state:
    st.session_state["cancel_scrape"] = False
if "keywords" not in st.session_state:
    st.session_state["keywords"] = [config.DEFAULT_FIELD]


def find_latest_run_file():
    """Finds the most recent .json file in the exports directory."""
    export_dir = config.EXPORTS_DIR
    json_files = [f for f in export_dir.glob("*.json")]
    if not json_files:
        return None
    latest_file = max(json_files, key=lambda f: f.stat().st_mtime)
    return latest_file

# ---- Sidebar: Parameters and Demo Loader ----
left, right = st.columns([1, 3], gap="large")
with left:
    st.header("🔧 Parameters")
    st.caption("Map directly to the scraper function inputs.")
    
    api_key = st.text_input("SCRAPINGDOG_API_KEY", type="password")
    openai_key = st.text_input("OPENAI_API_KEY", type="password", help="Paste your OpenAI API key for extraction")

    st.subheader("Search")
    
    # --- UI for adding and removing keywords ---
    def add_keyword():
        new_kw = st.session_state.new_keyword_input
        if new_kw and new_kw not in st.session_state.keywords:
            st.session_state.keywords.append(new_kw)
        st.session_state.new_keyword_input = "" 

    def remove_keyword(kw):
        st.session_state.keywords.remove(kw)

    st.text_input(
        "Add a keyword", 
        key="new_keyword_input", 
        on_change=add_keyword,
        placeholder="e.g., data analyst"
    )

    st.write("Current keywords:")
    for kw in st.session_state.keywords:
        col1, col2 = st.columns([4, 1])
        with col1:
            st.info(kw)
        with col2:
            st.button("🗑️", key=f"del_{kw}", on_click=remove_keyword, args=(kw,))

    with st.form("params", clear_on_submit=False):
        country = st.selectbox("Country", list(config.GEOIDS.keys()), index=0)
        geoid_default = config.GEOIDS[country]
        geoid = st.text_input("GEOID", value=geoid_default, help="LinkedIn geoId. Prefilled from country.")
        location = st.text_input("LOCATION (optional)", value="")
        sort_by = st.selectbox("SORT_BY", ["", "day", "week", "month"], index=0)

        st.subheader("Date window")
        d_start = st.date_input("From", value=date(2025, 7, 1))
        d_end = st.date_input("To", value=date(2025, 7, 31))

        with st.expander("Advanced filters", expanded=False):
            job_type = st.selectbox("JOB_TYPE", ["", "temporary", "contract", "volunteer", "full_time", "part_time"])
            exp_level = st.selectbox("EXP_LEVEL", ["", "internship", "entry_level", "associate", "mid_senior_level", "director"])
            work_type = st.selectbox("WORK_TYPE", ["", "at_work", "remote", "hybrid"])
            filter_company = st.text_input("FILTER_BY_COMPANY (LinkedIn ID)", value="")

        st.subheader("Credits & timing")
        base_delay = st.number_input("BASE_DELAY (s)", min_value=0.1, max_value=10.0, value=config.DEFAULT_BASE_DELAY, step=0.1)
        ov_delay = st.number_input("OV_DELAY (s)", min_value=0.1, max_value=10.0, value=config.DEFAULT_OV_DELAY, step=0.1)
        max_overviews = st.number_input("MAX_OVERVIEWS (0 = no cap)", min_value=0, value=config.DEFAULT_MAX_OVERVIEWS, step=1)
        max_listings = st.number_input("MAX_LISTINGS (0 = no cap)", min_value=0, value=config.DEFAULT_MAX_LISTINGS, step=10)
        
        st.subheader("File Output")
        save_files = st.checkbox("Also write JSON/CSV to disk", value=True)
        output_filename_base = st.text_input("Output Filename (no extension)", value="linkedin_jobs_export")
        
        submitted = st.form_submit_button("Run scrape 🚀")

    st.button("Cancel scrape", on_click=lambda: st.session_state.update(cancel_scrape=True))

    st.divider()
    st.caption("Load a previous run.")
    demo_upload = st.file_uploader("Upload a JSON export", type=["json"])
    
# ---- Data Scrape/Load Functionality ----
def run_and_load():
    """
    Calls the scraper, handles cancellation gracefully, enriches the data,
    and stores it in the session state.
    """
    import li_july_2025_with_desc as li  # Lazy import for scraping

    field = ", ".join(st.session_state.get("keywords", []))
    if not field:
        st.warning("Please add at least one keyword to search for.")
        return

    if not api_key or len(api_key) < 10:
        st.toast("A valid ScrapingDog API key is required.", icon="⚠️")
        return

    st.session_state["cancel_scrape"] = False
    
    rows = []
    meta = {}

    with st.status("Fetching jobs...", expanded=True) as status:
        try:
            progress = st.empty()
            def _cb(stats: dict):
                progress.write(
                    f"Page {stats.get('page', '?')} • Seen {stats.get('seen', 0)} • "
                    f"In window {stats.get('in_window', 0)} • Overviews {stats.get('overviews', 0)}"
                )

            rows, meta = li.run_scrape(
                api_key=api_key.strip(), field=field.strip(), geoid=geoid.strip(),
                location=location.strip(), sort_by=sort_by, job_type=job_type,
                exp_level=exp_level, work_type=work_type, filter_by_company=filter_company.strip(),
                base_delay=float(base_delay), ov_delay=float(ov_delay),
                max_overviews=int(max_overviews), max_listings=int(max_listings),
                date_start=d_start, date_end=d_end, progress_cb=_cb,
                should_stop=lambda: st.session_state.get("cancel_scrape", False),
            )

            if st.session_state.get("cancel_scrape"):
                status.update(label="✅ Scrape cancelled. Processing collected data...", state="running")
            else:
                status.update(label="✅ Scrape complete. Processing data...", state="running")

            if not rows:
                st.warning("No jobs were collected.")
                st.session_state["df"] = pd.DataFrame()
                st.session_state["meta"] = meta
                status.update(label="No data to process.", state="complete")
                return

            if openai_key and len(openai_key) > 10:
                status.update(label=f"✨ Enriching {len(rows)} jobs with OpenAI...", state="running")
                extraction.enrich_jobs_with_openai(rows, openai_key)

            status.update(label="⚙️ Normalizing data...", state="running")
            df = pd.DataFrame(rows)
            df = data_processing.normalize_enhanced_columns(df)
            try:
                df, _ = data_processing.apply_quality_normalization(df)
            except Exception as e:
                st.warning(f"Could not apply quality normalization: {e}")

            # --- MODIFIED SAVING LOGIC ---
            if save_files:
                status.update(label="💾 Saving files to disk...", state="running")
                
                # Convert the final, enhanced DataFrame back to a list of dictionaries
                enriched_rows = df.to_dict(orient="records")
                
                json_path = config.EXPORTS_DIR / f"{output_filename_base}.json"
                csv_path = config.EXPORTS_DIR / f"{output_filename_base}.csv"
                
                # Pass the ENRICHED data to the write function
                li.write_outputs(enriched_rows, meta, str(json_path), str(csv_path))
                
                st.write("Wrote files to `exports` directory:")
                st.code(f"{json_path.name}\n{csv_path.name}")

            st.session_state["df"] = df
            st.session_state["meta"] = meta
            status.update(label="🎉 All done!", state="complete")

        except Exception as e:
            status.update(label="An error occurred", state="error")
            st.exception(e)
        finally:
            st.session_state["cancel_scrape"] = False


if submitted:
    run_and_load()

# ---- Demo Data Loading ----
@st.cache_data
def load_demo_json(json_data):
    """Cached function to load and process JSON data."""
    df, meta = data_processing.load_json_data(json.loads(json_data))
    try:
        df, _ = data_processing.apply_quality_normalization(df)
    except Exception as e:
        st.warning(f"Could not apply quality normalization on demo data: {e}")
    return df, meta


def handle_demo_load(json_content):
    """Helper to process and load demo data into session state."""
    # The content is already a file-like object from st.file_uploader or open()
    # We read its content to pass to the cached function
    json_string = json_content.read()
    j = json.loads(json_string)
    rows = j.get("data", j)

    # Only enrich those rows that lack 'extracted_info'
    to_enrich = [r for r in rows if not r.get("extracted_info")]
    if openai_key and len(openai_key) > 10 and to_enrich:
        with st.spinner(f"Enriching {len(to_enrich)} new jobs with OpenAI..."):
            extraction.enrich_jobs_with_openai(rows, openai_key)
        st.info(f"Enriched {len(to_enrich)} new jobs with OpenAI extraction.")
    
    # Use the cached function to process the data, passing the original string
    df, meta = load_demo_json(json.dumps({"data": rows, "meta": j.get("meta", {})}))

    st.session_state["df"] = df
    st.session_state["meta"] = meta
    st.success("Demo data loaded successfully.")

# ---- MODIFIED: Auto-load latest file on start ----
if "df" not in st.session_state:
    latest_file = find_latest_run_file()
    if latest_file:
        try:
            with open(latest_file, "r", encoding="utf-8") as f:
                handle_demo_load(f)
            st.toast(f"Loaded latest run: {latest_file.name}")
        except Exception as e:
            st.error(f"Failed to auto-load latest run: {e}")

if demo_upload is not None:
    try:
        handle_demo_load(demo_upload)
    except Exception as e:
        st.exception(e)


# ---- Main UI: Explore, Insights, Graphs, Workflow ----
with right:
    meta = st.session_state.get("meta", {})
    df = st.session_state.get("df")

    # Defensive: if an earlier run stored (df, meta) as a tuple, fix it now.
    if isinstance(df, tuple):
        try:
            df_candidate, meta_candidate = df
            if isinstance(df_candidate, pd.DataFrame):
                df = df_candidate
                if isinstance(meta_candidate, dict):
                    meta = meta_candidate
                st.session_state["df"] = df
                st.session_state["meta"] = meta
        except Exception:
            # leave df as-is; downstream guards will handle
            pass
        
    st.markdown(components.render_app_header(meta, df), unsafe_allow_html=True)

    if df is None or (isinstance(df, pd.DataFrame) and df.empty):
        st.info("No data loaded yet. Configure parameters on the left and click **Run scrape**.")
        with st.expander("📘 Notes", expanded=False):
            st.markdown(
                "* **No subprocesses.** The app imports your scraper and calls `run_scrape(...)` directly.\n"
                f"* **Defaults:** `GEOID` prefilled from country, `FIELD` defaults to *{config.DEFAULT_FIELD}*.\n"
                "* **Credit saver:** `MAX_OVERVIEWS` caps overview calls (the costly ones).\n"
                f"* **File writes:** Enable the checkbox to emit files to the `exports` directory."
            )
    else:
        tab1, tab2, tab3, tab4 = st.tabs(["🔎 Explore", "📈 Insights", "📊 Graphs", "⚙️ Workflow"])

        with tab1:
            # --- Filtering/Search UI ---
            view_mode = st.radio("View", ["Cards", "Table"], horizontal=True, index=0, key="view_mode")
            with st.expander("🔍 Filter & search", expanded=True):
                q = st.text_input("Search in title/company/description", value="")
                companies = []
                if isinstance(df, pd.DataFrame) and "company_name" in df.columns:
                    companies = sorted(df["company_name"].dropna().unique().tolist())
                company_filter = st.multiselect("Company filter", companies, default=[])
                min_desc = st.slider("Min. description length (chars)", 0, 2000, 0, 50)

                # Extra guard: ensure df is a DataFrame
                if not isinstance(df, pd.DataFrame):
                    st.error(f"Internal: expected DataFrame, got {type(df).__name__}. "
                            "Resetting view—try reloading or reloading data.")
                    # Try to coerce (best-effort); else show empty frame
                    try:
                        df = pd.DataFrame(df) if not isinstance(df, tuple) else pd.DataFrame(df[0])
                    except Exception:
                        df = pd.DataFrame()


                fdf = data_processing.filter_dataframe(
                    df,
                    search_query=q,
                    company_filter=company_filter,
                    min_desc_length=min_desc
                )
            if fdf.empty:
                st.warning("No rows after filtering.")
            else:
                # Use a more generic filtered filename for downloads
                filtered_filename_base = output_filename_base + "_filtered" if 'output_filename_base' in locals() else "filtered_export"

                if view_mode == "Cards":
                    # Pagination logic for cards
                    cards_per_page = config.CARDS_PER_PAGE
                    records = fdf.to_dict(orient="records")
                    total_pages = (len(records) + cards_per_page - 1) // cards_per_page
                    page = st.number_input("Page", min_value=1, max_value=max(1, total_pages), value=1, step=1, key="card_page")
                    start_idx = (page - 1) * cards_per_page
                    end_idx = start_idx + cards_per_page
                    page_records = records[start_idx:end_idx]
                    for rec in page_records:
                        st.markdown(components.render_card(card_tpl, rec), unsafe_allow_html=True)
                    st.caption(f"Page {page} of {total_pages} — Showing {len(page_records)} of {len(records)} results")
                else:
                    # Table view
                    tcol, dcol = st.columns([2, 1], gap="large")
                    with tcol:
                        df_show = data_processing.prepare_table_view(fdf)
                        st.dataframe(
                            df_show,
                            hide_index=False,
                            use_container_width=True,
                            column_config={"job_link": st.column_config.LinkColumn("job_link", display_text="Open")},
                        )
                        st.number_input(
                            "Row to inspect",
                            min_value=0,
                            max_value=max(0, len(fdf) - 1),
                            value=0,
                            step=1,
                            key="rowpick",
                        )
                    with dcol:
                        # Add a check to ensure rowpick is valid
                        if 'rowpick' in st.session_state and 0 <= st.session_state.rowpick < len(fdf):
                            row = fdf.iloc[int(st.session_state["rowpick"])]
                            st.subheader("Details")
                            st.write(f"**{row.get('job_position','(no title)')}**")
                            st.caption(f"{row.get('company_name','—')} — {row.get('job_location','—')} — {row.get('job_posting_date','?')}")
                            link = row.get("job_link")
                            if isinstance(link, str) and link:
                                st.markdown(f"[Open in new tab]({link})")
                            st.divider()
                            st.markdown(
                                f'<div class="desc-box">{row.get("description", "_No description_")}</div>',
                                unsafe_allow_html=True
                            )
                        else:
                            st.info("Select a valid row to inspect.")


                # Export buttons
                st.divider()
                c1, c2 = st.columns(2)
                with c1:
                    st.download_button(
                        "Download CSV (filtered)",
                        data_processing.export_to_csv(fdf),
                        file_name=f"{filtered_filename_base}.csv",
                        mime="text/csv",
                    )
                with c2:
                    st.download_button(
                        "Download JSON (filtered)",
                        data_processing.export_to_json(fdf, meta),
                        file_name=f"{filtered_filename_base}.json",
                        mime="application/json",
                    )

        with tab2:
            # ---- Visualizations ----
            st.subheader("Top companies")
            fig1 = visualization.create_company_chart(df)
            if fig1:
                st.plotly_chart(fig1, use_container_width=True)
            else:
                st.info("No company data available.")

            st.subheader("Posting dates")
            fig2 = visualization.create_timeline_chart(df)
            if fig2:
                st.plotly_chart(fig2, use_container_width=True)
            else:
                st.info("No posting date data available.")

        with tab3:
            # ---- All graphs + DQ ----
            graphs_page.render_page()

        with tab4:
            # ---- Workflow diagram ----
            workflow_page.render_page()