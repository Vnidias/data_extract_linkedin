# scrapping-linkedin 🔎💼

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)  
![Requests](https://img.shields.io/badge/requests-%E2%9C%93-lightgrey)  
![dateutil](https://img.shields.io/badge/python--dateutil-%E2%9C%93-lightgrey)  
![Streamlit](https://img.shields.io/badge/streamlit-UI-orange)  
![OS](https://img.shields.io/badge/Windows%20%7C%20macOS%20%7C%20Linux-OK-success)

Scrape **LinkedIn Jobs** through **ScrapingDog** for the Netherlands and export results to **JSON** and **CSV**.  
Includes a **description fetch** step (via job overview), a **July 2025 filter**, and an optional **Streamlit UI** for interactive browsing.

> **Zero BS goal:** Run in minutes, control API usage, browse jobs with a clean UI.

---

## ✨ Features

* 🇳🇱 Focus on the **Netherlands** (`geoId = 102890719`).
* 🔁 Auto-pagination until no more results.
* 📝 Job **descriptions** pulled via overview calls (per `job_id`).
* 📅 **July 2025 filter** baked in (01–31 inclusive).
* 🧯 Rate-limit safe: exponential backoff + jitter, honors `Retry-After`.
* 🧰 Clean outputs:
  * `li_jobs_2025-07_with_desc.json`
  * `li_jobs_2025-07_with_desc.csv`
* 🎛️ **Credit saver**: limit to *N* descriptions or *N* listings via env vars.
* 🎨 **Streamlit app**: friendly UI for filters, search, expandable descriptions, and downloads.

---

## 🗂️ Repo contents

```
.
├─ li_july_2025_with_desc.py       # Full July-only scrape (env-driven)
├─ li_test_2_jobs_with_desc.py     # Minimal test (2 jobs)
├─ streamlit_app.py                # Streamlit UI wrapper
├─ requirements.txt                # CLI scraper deps
├─ requirements_streamlit.txt      # Streamlit UI deps
├─ .env.example                    # template for env vars
├─ .gitignore                      # ignores outputs, .env, cache
└─ README.md                       # this file
```

---

## ✅ Prerequisites

* **Python 3.10+**  
* **ScrapingDog API key** with LinkedIn Jobs enabled  
* Basic terminal usage (PowerShell on Windows / bash on macOS/Linux)

---

## 🚀 Quick start (CLI)

### Windows (PowerShell)

```powershell
# Install deps
python -m pip install -r requirements.txt

# Set env vars
$env:SCRAPINGDOG_API_KEY = "YOUR_KEY"
$env:FIELD = "data engineer"
# Optional:
# $env:LOCATION = "Amsterdam"
# $env:SORT_BY = "month"
# $env:JOB_TYPE = "full_time"
# $env:EXP_LEVEL = "associate"
# $env:WORK_TYPE = "hybrid"
# $env:FILTER_BY_COMPANY = "123456"

# Optional credit caps
$env:MAX_OVERVIEWS = "2"   # stop after 2 descriptions
$env:MAX_LISTINGS  = "20"  # stop after 20 listings

# Sanity test
python .\li_test_2_jobs_with_desc.py

# Full run
python .\li_july_2025_with_desc.py
```

### macOS / Linux (bash)

```bash
# Install deps
python3 -m pip install -r requirements.txt

# Set env vars
export SCRAPINGDOG_API_KEY="YOUR_KEY"
export FIELD="data engineer"

# Optional filters...
# export LOCATION="Amsterdam"
# export SORT_BY="month"
# export JOB_TYPE="full_time"
# export EXP_LEVEL="associate"
# export WORK_TYPE="hybrid"
# export FILTER_BY_COMPANY="123456"

# Optional credit caps
export MAX_OVERVIEWS=2
export MAX_LISTINGS=20

# Sanity test
python3 li_test_2_jobs_with_desc.py

# Full run
python3 li_july_2025_with_desc.py
```

---

## ⚙️ Environment variables

| Variable              | Required | Example          | Purpose                                    |
|-----------------------|----------|------------------|--------------------------------------------|
| `SCRAPINGDOG_API_KEY` | ✅        | `sk_live_...`    | Auth token for ScrapingDog                 |
| `FIELD`               | ✅        | `data engineer`  | Search keywords                            |
| `LOCATION`            | ❌        | `Amsterdam`      | Free-text location filter                  |
| `SORT_BY`             | ❌        | `month`          | Time filter: `day` / `week` / `month`      |
| `JOB_TYPE`            | ❌        | `full_time`      | Job type filter                            |
| `EXP_LEVEL`           | ❌        | `associate`      | Experience level filter                    |
| `WORK_TYPE`           | ❌        | `hybrid`         | On-site / Remote / Hybrid                  |
| `FILTER_BY_COMPANY`   | ❌        | `123456`         | LinkedIn company ID                        |
| `BASE_DELAY`          | ❌        | `1.0`            | Delay between listing page calls (seconds) |
| `OV_DELAY`            | ❌        | `0.6`            | Delay between overview calls               |
| `MAX_OVERVIEWS`       | ❌        | `2`              | Hard cap on description fetches (credits)  |
| `MAX_LISTINGS`        | ❌        | `20`             | Hard cap on listing rows scanned           |

---

## 🧠 How it works

1. **List phase** → query jobs by keyword + filters.  
2. **Filter** → keep only jobs posted in **July 2025**.  
3. **Overview** → fetch job descriptions for those jobs (capped by `MAX_OVERVIEWS` if set).  
4. **Export** → save as `.json` and `.csv`.

---

## 📤 Outputs

* `li_jobs_2025-07_with_desc.json` → JSON with `job_id`, `job_position`, `company_name`, `job_location`, `job_link`, `job_posting_date`, `description`.  
* `li_jobs_2025-07_with_desc.csv` → CSV version of the same.  
* `li_jobs_sample_with_desc.*` → test run with 2 jobs.

---

## 🧪 Troubleshooting

**429 Too Many Requests** → raise `BASE_DELAY` / `OV_DELAY`.  
**Empty results** → try different `FIELD`, add `LOCATION`, or change `SORT_BY`.  
**Descriptions missing** → not all overview payloads are consistent; parser has fallbacks.  
**Windows**: use `$env:NAME = "value"`, not `export`.

---

## 🔒 Secrets

* Don’t commit your real `.env` with the API key.  
* `.env.example` is just a template.  
* Already git-ignored: outputs, `.env`, caches.

---

## 🖥️ Streamlit UI

### Quickstart
```bash
python -m pip install -r requirements_streamlit.txt
streamlit run streamlit_app.py
```

### Features
* Sidebar inputs map directly to env vars (`FIELD`, `LOCATION`, `MAX_OVERVIEWS`, etc).  
* One-click scrape and load.  
* Interactive filters (search, company, description length).  
* Expandable job rows with links and full text.  
* CSV/JSON download of filtered results.  
* File uploader to browse old outputs without re-scraping.

---

## 📜 License

MIT (recommended) or Apache-2.0. Add a LICENSE file.

---

## 📣 Credits

* [ScrapingDog LinkedIn Jobs API](https://docs.scrapingdog.com/linkedin-jobs-scraper/scrape-linkedin-jobs)  
* [ScrapingDog Job Overview API](https://docs.scrapingdog.com/linkedin-jobs-scraper/scrape-linkedin-job-overview)  
