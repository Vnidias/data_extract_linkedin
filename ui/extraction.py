# ui/extraction.py
"""OpenAI extraction utilities"""
import json
from typing import Dict, Any, List, Optional
import openai

def extract_structured_info(description: str, api_key: str) -> Dict[str, Any]:
    """Extract structured information from job description using OpenAI"""
    if not description or not api_key:
        return {}
    
    client = openai.OpenAI(api_key=api_key)
    
    prompt = f"""You are an information extractor for job postings.
    Given the following raw job description, extract as JSON:
    - period_contract (start, end)
    - location
    - type (hybrid, remote, onsite, etc.)
    - hours_per_week
    - languages
    - tools
    - tech_skill
    Output only JSON, nothing else.
    Description: '''{description}'''"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0,
        )
        content = response.choices[0].message.content
        return json.loads(content)
    except Exception:
        return {}

def enrich_jobs_with_openai(
    rows: List[Dict[str, Any]], 
    api_key: str,
    progress_callback: Optional[callable] = None
) -> List[Dict[str, Any]]:
    """Enrich multiple job rows with OpenAI extraction"""
    if not api_key or len(api_key) < 10:
        return rows
    
    for i, row in enumerate(rows):
        desc = row.get("description", "")
        if desc and not row.get("extracted_info"):
            row["extracted_info"] = extract_structured_info(desc, api_key)
            if progress_callback:
                progress_callback(i + 1, len(rows))
    
    return rows