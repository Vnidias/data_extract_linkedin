#!/usr/bin/env python3
"""
LinkedIn Jobs via ScrapingDog — JULY 2025 only.

Usable two ways:
1) As a library (import in Streamlit): call run_scrape(...) to get rows + meta in-memory.
2) As a CLI script (python li_july_2025_with_desc.py): reads env, runs, and writes JSON/CSV.

Env vars (when run as CLI):
  SCRAPINGDOG_API_KEY  (required)
  FIELD                (default: "data engineer")
  GEOID                (default: "102890719" -> Netherlands)
  LOCATION             (optional; e.g., "Amsterdam")
  SORT_BY              (optional: "", "day", "week", "month")
  JOB_TYPE             (optional: temporary|contract|volunteer|full_time|part_time)
  EXP_LEVEL            (optional: internship|entry_level|associate|mid_senior_level|director)
  WORK_TYPE            (optional: at_work|remote|hybrid)
  FILTER_BY_COMPANY    (optional: LinkedIn company ID)
  BASE_DELAY           (default: 1.0 seconds between listing pages)
  OV_DELAY             (default: 0.6 seconds between overview calls)
  MAX_OVERVIEWS        (default: 0 -> no cap) hard cap on overview (description) calls
  MAX_LISTINGS         (default: 0 -> no cap) hard cap on listing rows scanned
"""

from __future__ import annotations
import csv
import json
import os
import random
import time
from typing import Any, Dict, List, Optional, Tuple, Callable
from datetime import datetime, date, timezone
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from dateutil import parser as dtparser
from pathlib import Path

# ---- Constants ----
ENDPOINT = "https://api.scrapingdog.com/linkedinjobs"
TIMEOUT = 30
WIN_START, WIN_END = date(2025, 7, 1), date(2025, 7, 31)
GEOID_NL = "102890719"
DEFAULT_FIELD = "data engineer"

# ---- Helpers ----
def _make_session() -> requests.Session:
    """Creates a requests session with retries."""
    s = requests.Session()
    retries = Retry(total=5, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
    s.mount("https://", HTTPAdapter(max_retries=retries))
    s.headers.update({"User-Agent": "ldata-scraper/1.0"})
    return s

def _api_call(session: requests.Session, params: Dict[str, Any]) -> Any:
    """Generic GET request handler for the ScrapingDog API with backoff."""
    for attempt in range(5):
        try:
            r = session.get(ENDPOINT, params=params, timeout=TIMEOUT)
            if r.status_code == 200:
                return r.json()
            if r.status_code in [429, 500, 502, 503, 504]:
                retry_after = r.headers.get("Retry-After")
                sleep_time = float(retry_after) if retry_after else (2 ** attempt) + random.uniform(0.2, 0.9)
                time.sleep(min(60.0, sleep_time))
        except requests.exceptions.RequestException:
            time.sleep((2 ** attempt) + random.uniform(0.2, 0.9))
    return None

def _extract_description(overview: Any) -> str:
    """Extracts description from various possible response structures."""
    if not overview: return ""
    items = overview if isinstance(overview, list) else [overview]
    for item in items:
        if not isinstance(item, dict): continue
        for key in ("description", "job_description", "full_description"):
            if isinstance(item.get(key), str) and item[key].strip():
                return item[key].strip()
    return ""

# ---- Public API ----
def run_scrape(
    *, api_key: str, field: str = DEFAULT_FIELD, geoid: str = GEOID_NL,
    location: str = "", sort_by: str = "", job_type: str = "", exp_level: str = "",
    work_type: str = "", filter_by_company: str = "", base_delay: float = 1.0,
    ov_delay: float = 0.6, max_overviews: int = 0, max_listings: int = 0,
    date_start: date = WIN_START, date_end: date = WIN_END,
    progress_cb: Optional[Callable[[Dict[str, Any]], None]] = None,
    should_stop: Optional[Callable[[], bool]] = None,
    session: Optional[requests.Session] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    if not api_key: raise ValueError("Missing SCRAPINGDOG_API_KEY")
    sess = session or _make_session()

    def in_window(d_str: Optional[str]) -> bool:
        if not d_str: return False
        try: return date_start <= dtparser.parse(d_str).date() <= date_end
        except Exception: return False

    results, seen_ids = [], set()
    total_seen, total_in_window, total_overviews = 0, 0, 0
    
    # Split the field string into a list of keywords
    keywords = [kw.strip() for kw in field.split(',') if kw.strip()]

    for keyword in keywords:
        page = 1
        while True:
            if (should_stop and should_stop()) or (max_listings and total_seen >= max_listings): break

            list_params = {
                "api_key": api_key, "field": keyword, "geoid": geoid, "location": location, 
                "sort_by": sort_by, "job_type": job_type, "exp_level": exp_level, 
                "work_type": work_type, "filter_by_company": filter_by_company, "page": page
            }
            
            jobs = _api_call(sess, {k: v for k, v in list_params.items() if v})
            if not jobs: break

            for job in jobs:
                total_seen += 1
                job_id = job.get("job_id")
                if not job_id or job_id in seen_ids: continue
                seen_ids.add(job_id)

                if in_window(job.get("job_posting_date")):
                    if max_overviews and total_overviews >= max_overviews:
                        total_seen = max_listings if max_listings else total_seen
                        break
                    
                    overview = _api_call(sess, {"api_key": api_key, "job_id": job_id})
                    if overview: total_overviews += 1

                    results.append({
                        "job_id": job_id, "job_position": job.get("job_position"),
                        "company_name": job.get("company_name"), "company_profile": job.get("company_profile"),
                        "job_location": job.get("job_location"), "job_link": job.get("job_link"),
                        "job_posting_date": job.get("job_posting_date"),
                        "description": _extract_description(overview),
                    })
                    total_in_window += 1

                    if progress_cb:
                        progress_cb({"page": page, "seen": total_seen, "in_window": total_in_window, "overviews": total_overviews})
                    time.sleep(ov_delay)
            
            if (max_listings and total_seen >= max_listings): break
            page += 1
            time.sleep(base_delay)
        
        if (should_stop and should_stop()) or (max_listings and total_seen >= max_listings): break

    meta = {
        "retrieved_at": datetime.now(timezone.utc).isoformat(), "field": field, "geoid": geoid,
        "location": location or None, "sort_by": sort_by or None,
        "records_total_seen": total_seen, "records_in_window": total_in_window,
        "overviews_fetched": total_overviews, "window_start": date_start.isoformat(),
        "window_end": date_end.isoformat(), "max_overviews": max_overviews, "max_listings": max_listings,
    }
    return results, meta

def write_outputs(rows: List[Dict[str, Any]], meta: Dict[str, Any], json_path: str, csv_path: str) -> None:
    """Writes data to specified JSON and CSV paths."""
    Path(json_path).parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        # JSON dump handles any dictionary structure automatically.
        json.dump({"meta": meta, "data": rows}, f, ensure_ascii=False, indent=2)
    
    # --- MODIFIED CSV FIELDNAMES ---
    # Define a comprehensive list of all possible columns to ensure the CSV is complete.
    fieldnames = [
        # Core fields
        "job_posting_date", "job_position", "company_name", "job_location", 
        "job_id", "job_link", "description", "company_profile",
        # Enhanced fields from normalization
        "enhanced_period_contract", "enhanced_location", "enhanced_type",
        "enhanced_hours_per_week", "enhanced_languages", "enhanced_tools",
        "enhanced_tech_skill", "enhanced_contact",
        # New language split fields
        "natural_languages", "programming_languages"
    ]
    
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        
        # Prepare rows for CSV to handle list/dict values gracefully
        csv_rows = []
        for row in rows:
            processed_row = {}
            for key, value in row.items():
                if isinstance(value, list):
                    processed_row[key] = ", ".join(map(str, value))
                elif isinstance(value, dict):
                    processed_row[key] = json.dumps(value)
                else:
                    processed_row[key] = value
            csv_rows.append(processed_row)
        
        writer.writerows(csv_rows)

# ---- CLI Entry Point ----
def main() -> None:
    """CLI execution function."""
    env = lambda name, default="": os.getenv(name, default)
    params = {
        "api_key": env("SCRAPINGDOG_API_KEY"), "field": env("FIELD", DEFAULT_FIELD),
        "geoid": env("GEOID", GEOID_NL), "location": env("LOCATION"),
        "sort_by": env("SORT_BY"), "job_type": env("JOB_TYPE"),
        "exp_level": env("EXP_LEVEL"), "work_type": env("WORK_TYPE"),
        "filter_by_company": env("FILTER_BY_COMPANY"),
        "base_delay": float(env("BASE_DELAY", "1.0")), "ov_delay": float(env("OV_DELAY", "0.6")),
        "max_overviews": int(env("MAX_OVERVIEWS", "0")), "max_listings": int(env("MAX_LISTINGS", "0")),
    }
    rows, meta = run_scrape(**params)
    
    cli_json_path = "li_jobs_2025-07_with_desc.json"
    cli_csv_path = "li_jobs_2025-07_with_desc.csv"
    write_outputs(rows, meta, cli_json_path, cli_csv_path)

    print(f"Seen total listings: {meta['records_total_seen']}")
    print(f"Matches in window: {meta['records_in_window']} (overviews fetched: {meta['overviews_fetched']})")
    print(f"Saved JSON => {cli_json_path}")
    print(f"Saved CSV  => {cli_csv_path}")

if __name__ == "__main__":
    main()