# ui/config.py
"""
Configuration and constants for the LinkedIn (ScrapingDog) browser + graphs.

This file centralizes:
- App/UI constants
- File paths / exports
- Data/quality settings (enhancement columns, canonical vocab)
- Normalization dictionaries and thresholds (for fuzzy + AI fallback pipelines)

Nothing here executes network calls; it’s safe to import anywhere.
"""

from pathlib import Path

# ──────────────────────────────────────────────────────────────────────────────
# App / UI
# ──────────────────────────────────────────────────────────────────────────────
APP_TITLE = "LinkedIn (ScrapingDog) — July 2025 Browser"

GEOIDS = {
    "Netherlands": "102890719",
    "Belgium": "100565514",
    "Germany": "101282230",
    "France": "103620260",
    "United Kingdom": "101165590",
    "Spain": "105646813",
    "Italy": "103350119",
}

# Default scraping/demo behavior
DEFAULT_FIELD = "data engineer"
DEFAULT_BASE_DELAY = 1.0
DEFAULT_OV_DELAY = 0.6
DEFAULT_MAX_OVERVIEWS = 2
DEFAULT_MAX_LISTINGS = 0
CARDS_PER_PAGE = 3

# ──────────────────────────────────────────────────────────────────────────────
# Files & Paths
# ──────────────────────────────────────────────────────────────────────────────
CSS_PATH = "css/app.css"
CARD_TEMPLATE_PATH = "templates/card.html"

# Exports (root folder + filenames)
EXPORTS_DIR = Path(__file__).resolve().parent.parent / "exports"
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

# Data source defaults (the app can override these via session state)
DATA_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DATA_FILE = None  # e.g., DATA_DIR / "li_jobs_sample_with_desc.csv"

# Where to drop “unknown token” audit CSVs when normalizers can’t decide
UNKNOWN_BUCKETS_DIR = EXPORTS_DIR / "unknowns"
UNKNOWN_BUCKETS_DIR.mkdir(parents=True, exist_ok=True)

# ──────────────────────────────────────────────────────────────────────────────
# Columns / Schema
# ──────────────────────────────────────────────────────────────────────────────
# Raw multivalue columns coming from the enhancement step that may contain
# comma/semicolon separated values. (Back-compat list; don’t remove lightly.)
ENHANCEMENT_COLUMNS = [
    "enhanced_languages",
    "enhanced_tools",
    "enhanced_tech_skill",
    "enhanced_contact",
]

# Candidate unique-id columns present in datasets; first one found is used.
PROFILE_ID_CANDIDATES = ["profile_url", "linkedin_url", "job_link", "job_url"]

# Date columns we treat as “freshness candidates” (first present wins).
FRESHNESS_CANDIDATES = ["job_posting_date", "date_collected", "scrape_date"]

# If/when you split languages cleanly, these are the canonical output columns.
LANGUAGE_SPLIT_OUTPUTS = ["natural_languages", "programming_languages"]

# ──────────────────────────────────────────────────────────────────────────────
# Normalization dictionaries (rules-first, then fuzzy/AI fallback)
# ──────────────────────────────────────────────────────────────────────────────
# General synonym map used by token normalizers (safe, low-risk rewrites).
SYNONYMS = {
    "js": "javascript",
    "ts": "typescript",
    "ms sql": "sql server",
    "postgres": "postgresql",
    "gcp": "google cloud",
    "google cloud platform": "google cloud",
    "aws s3": "s3",
    "k8s": "kubernetes",
}

# --- Job Type canonicalization ------------------------------------------------
JOB_TYPE_CANON = {"remote", "on-site", "hybrid"}

# Keywords (substring match) that map messier phrases into the 3 canonical types
JOB_TYPE_KEYWORDS = {
    "remote": {
        "remote",
        "remoto",
        "work from home",
        "wfh",
        "anywhere",
        "home office",
        "fully remote",
    },
    "on-site": {
        "onsite",
        "on site",
        "on-site",
        "presencial",
        "office-based",
    },
    "hybrid": {
        "hybrid",
        "híbrido",
        "partly remote",
        "days in office",
        "x days onsite",
        "mix of remote and onsite",
    },
}

# --- Location canonicalization ------------------------------------------------
# Tokens that *aren’t* locations (drop them from enhanced_location)
NON_LOCATION_TOKENS = {"remote", "global", "worldwide", "not specified", "n/a", "na"}

# Common city/country typos → canonical form (extend as you observe new ones)
CITY_ALIASES = {
    "utrech": "utrecht",
    "utrecht, netherlands": "utrecht",
    "netherlands utrech": "utrecht",
    "schiphol-rijik": "schiphol-rijk",
    "schiphol rijk": "schiphol-rijk",
}
COUNTRY_ALIASES = {
    "nl": "netherlands",
    "the netherlands": "netherlands",
    "holland": "netherlands",
    "uk": "united kingdom",
    "u.k.": "united kingdom",
    "england": "united kingdom",  # keep only if you want country-level rollup
}

# Optional “preferred cities” list; if set, fuzzy will prefer these
PREFERRED_CITIES = {
    "amsterdam",
    "utrecht",
    "eindhoven",
    "rotterdam",
    "the hague",
    "groningen",
    "berlin",
    "munich",
    "london",
    "paris",
    "brussels",
}

# --- Language separation ------------------------------------------------------
# Natural (human) languages vs programming languages; used to split fields cleanly
NATURAL_LANGS = {
    "dutch",
    "english",
    "german",
    "french",
    "spanish",
    "portuguese",
    "italian",
}
PROG_LANGS = {
    "python",
    "r",
    "java",
    "scala",
    "go",
    "javascript",
    "typescript",
    "c",
    "c++",
    "c#",
    "sql",
    "bash",
}

# --- Tools normalization ------------------------------------------------------
TOOL_SYNONYMS = {
    "gcp": "google cloud",
    "google cloud platform": "google cloud",
    "ms sql": "sql server",
    "postgres": "postgresql",
    "k8s": "kubernetes",
    "apache airflow": "airflow",
}

# ──────────────────────────────────────────────────────────────────────────────
# Fuzzy / AI thresholds (tune cautiously)
# ──────────────────────────────────────────────────────────────────────────────
# RapidFuzz score cutoffs for different domains
FUZZY_SCORE_JOBTYPE = 80     # 0–100; lower is looser
FUZZY_SCORE_CITY = 88
FUZZY_SCORE_LANGUAGE = 90

# Embedding fallback (optional). Disabled by default for speed/cost determinism.
USE_EMBEDDINGS_FALLBACK = False
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_MIN_COS_JOBTYPE = 0.45   # cosine threshold when guessing job type
EMBEDDING_MIN_COS_LANGUAGE = 0.50  # for routing ambiguous tokens

# ──────────────────────────────────────────────────────────────────────────────
# Graphs defaults
# ──────────────────────────────────────────────────────────────────────────────
TOPN_DEFAULT = 20  # default “Top-N” for bar charts