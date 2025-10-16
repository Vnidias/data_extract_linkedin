# ui/components.py
"""UI Components for Streamlit App"""
import html
import json
from string import Template
from typing import Dict, Any, Optional
import pandas as pd

def load_css(path: str = "css/app.css") -> str:
    """Load and return CSS content"""
    with open(path, "r", encoding="utf-8") as f:
        return f"<style>{f.read()}</style>"

def load_card_template(path: str = "templates/card.html") -> Template:
    """Load card HTML template"""
    with open(path, "r", encoding="utf-8") as f:
        return Template(f.read())

def chip(text: str, kind: str = "") -> str:
    """Create HTML chip element"""
    klass = "chip" + (f" chip--{kind}" if kind else "")
    return f'<span class="{klass}">{html.escape(str(text))}</span>'

def render_enhanced_grid(row: Dict[str, Any]) -> str:
    """Render enhanced info grid for job card"""
    fields = [
        ("Period", "enhanced_period_contract"),
        ("Location", "enhanced_location"),
        ("Work Type", "enhanced_type"),
        ("Hours/Week", "enhanced_hours_per_week"),
        ("Languages", "enhanced_languages"),
        ("Tools", "enhanced_tools"),
        ("Tech Skills", "enhanced_tech_skill"),
        ("Contact", "enhanced_contact"),
    ]
    
    left, right = [], []
    for i, (label, key) in enumerate(fields):
        val = row.get(key, "")
        if isinstance(val, list):
            val = ", ".join(val)
        if isinstance(val, dict):
            val = "; ".join([f"{k}: {v}" for k, v in val.items()])
        if not val or val == "[]":
            val = "<span style='color:#64748b;'>—</span>"
        cell = f"<div><b>{label}:</b> {val}</div>"
        (left if i % 2 == 0 else right).append(cell)
    
    return (
        "<div class='enhanced-grid'>"
        f"<div>{''.join(left)}</div>"
        f"<div>{''.join(right)}</div>"
        "</div>"
    )

def render_card(tpl: Template, row: Dict[str, Any]) -> str:
    """Render job card HTML"""
    chips = [chip("July 2025", "ok")]
    view_btn = (
        f'<a class="view-btn" href="{html.escape(str(row.get("job_link","")))}" '
        f'target="_blank" rel="noopener">View ↗</a>'
        if row.get("job_link") else ""
    )
    
    values = {
        "job_position": html.escape(str(row.get("job_position", "(no title)"))),
        "company_name": html.escape(str(row.get("company_name", "—"))),
        "job_location": html.escape(str(row.get("job_location", "—"))),
        "job_posting_date": html.escape(str(row.get("job_posting_date", "?"))),
        "description": html.escape(str(row.get("description", ""))),
        "chips": " ".join(chips),
        "description_open": "open" if row.get("description") else "",
        "enhanced_grid": render_enhanced_grid(row),
    }
    
    return tpl.safe_substitute(values).replace("%VIEWBTN%", view_btn)

def render_app_header(meta: Dict[str, Any], df: Optional[pd.DataFrame]) -> str:
    """Render application header with metrics"""
    return """
<div class="app-header">
  <div>
    <h1 class="main-title">LinkedIn <span class="accent">Jobs Search</span></h1>
    <div class="subtitle">NL Focused on Netherlands &nbsp;•&nbsp; July 2025 &nbsp;•&nbsp; <span class="scrapingdog">ScrapingDog</span> Powered</div>
  </div>
  <div class="metric-row">
    <div class="metric-card">
      <div class="metric-label">Rows</div>
      <div class="metric-value">{rows}</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Overviews</div>
      <div class="metric-value">{overviews}</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Field</div>
      <div class="metric-value">{field}</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Location</div>
      <div class="metric-value">{location}</div>
    </div>
  </div>
</div>
""".format(
        rows=int(meta.get("records_in_july", (len(df) if isinstance(df, pd.DataFrame) else 0))),
        overviews=int(meta.get("overviews_fetched", 0)),
        field=meta.get("field", "-"),
        location=meta.get("location", "—") or "—"
    )