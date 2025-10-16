# ui/data_processing.py
"""Data processing and transformation utilities"""

from __future__ import annotations

import json
import re
from typing import Dict, Any, List, Optional, Iterable, Tuple

import pandas as pd
import streamlit as st # Added for caching

# Fuzzy match: tenta rapidfuzz (rápido/preciso); se não tiver, usa difflib.
try:
    from rapidfuzz import process as rf_process, fuzz as rf_fuzz  # type: ignore
    _HAS_RF = True
except Exception:
    import difflib  # fallback
    _HAS_RF = False

# ---------------------------------------------------------------------------
# Config imports (vocabulários, sinônimos, limiares, paths)
# ---------------------------------------------------------------------------
from .config import (
    ENHANCEMENT_COLUMNS,                # lista dos multivalores brutos
    FRESHNESS_CANDIDATES,
    UNKNOWN_BUCKETS_DIR,
    # normalização geral
    SYNONYMS,
    # job type
    JOB_TYPE_CANON, JOB_TYPE_KEYWORDS, FUZZY_SCORE_JOBTYPE,
    # localização
    NON_LOCATION_TOKENS, CITY_ALIASES, COUNTRY_ALIASES, PREFERRED_CITIES, FUZZY_SCORE_CITY,
    # linguagens
    NATURAL_LANGS, PROG_LANGS, FUZZY_SCORE_LANGUAGE,
    # tools
    TOOL_SYNONYMS,
)

# ---------------------------------------------------------------------------
# Colunas enhanced (compat com seu app atual)
# ---------------------------------------------------------------------------
ENHANCED_COLS = [
    "enhanced_period_contract", "enhanced_location", "enhanced_type",
    "enhanced_hours_per_week", "enhanced_languages", "enhanced_tools",
    "enhanced_tech_skill", "enhanced_contact",
]

# Novas saídas sugeridas (não quebram o app): split de linguagens
NAT_LANG_COL = "natural_languages"
PROG_LANG_COL = "programming_languages"


# ============================== Helpers base =============================== #

def _tok(s: str) -> str:
    """Tokenização simples: lower, limpa caracteres e normaliza espaços."""
    s = s.strip().lower()
    s = re.sub(r"[^\w+.\-#/ ,]", "", s)
    s = re.sub(r"\s+", " ", s)
    return s


def _to_list(cell: Any) -> List[str]:
    """Converte cell -> lista de strings (aceita list/dict/str)."""
    if isinstance(cell, list):
        return [str(v) for v in cell if f"{v}".strip()]
    if isinstance(cell, dict):
        return [f"{k}: {v}" for k, v in cell.items()]
    if isinstance(cell, str):
        parts = [p.strip() for p in re.split(r"[;,/|]", cell) if p.strip()]
        return parts
    return []


def _dedupe_keep_order(items: Iterable[str]) -> List[str]:
    seen, out = set(), []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def _fuzzy_pick(query: str, choices: Iterable[str], score_cutoff: int) -> Optional[str]:
    """Escolhe melhor rótulo via fuzzy se acima do corte."""
    if not query:
        return None
    if _HAS_RF:
        match = rf_process.extractOne(query, list(choices), scorer=rf_fuzz.token_set_ratio, score_cutoff=score_cutoff)
        return match[0] if match else None
    # fallback difflib
    best = difflib.get_close_matches(query, list(choices), n=1, cutoff=score_cutoff / 100.0)
    return best[0] if best else None


# =========================== Normalizadores core =========================== #

# --- JOB TYPE -------------------------------------------------------------- #
def normalize_job_type(text: Any) -> Optional[str]:
    """Mapeia para {remote,on-site,hybrid} usando keywords → fuzzy."""
    if not isinstance(text, str):
        return None
    t = _tok(text)
    # 1) keywords (substring)
    for canon, kws in JOB_TYPE_KEYWORDS.items():
        if any(kw in t for kw in kws):
            return canon
    # 2) fuzzy sobre o próprio texto (curto)
    guess = _fuzzy_pick(t, JOB_TYPE_CANON, FUZZY_SCORE_JOBTYPE)
    return guess


# --- LOCATION -------------------------------------------------------------- #
def normalize_location(text: Any) -> Optional[str]:
    """
    Normaliza localização:
    - remove tokens que não são lugar (remote/global/…)
    - corrige typos por CITY_ALIASES
    - escolhe UMA cidade (prioriza a primeira cidade-like)
    - fuzzy rescue para PREFERRED_CITIES e chaves de CITY_ALIASES
    """
    if not isinstance(text, str):
        return None
    t = _tok(text)

    # Se mencionar 'remote/global' etc → não é localização
    if any(bad in t for bad in NON_LOCATION_TOKENS):
        return None

    parts = [p.strip() for p in re.split(r"[;,/|]", t) if p.strip()]
    parts = [CITY_ALIASES.get(p, p) for p in parts]  # corrige typos comuns

    # Heurística de cidade: sem dígitos, poucas palavras, não igual a países
    def looks_like_city(p: str) -> bool:
        if p in NON_LOCATION_TOKENS:
            return False
        if re.search(r"\d", p):
            return False
        # ignora frases de país
        if p in COUNTRY_ALIASES.values():
            return False
        # algo tipo "netherlands utrecht" → já teria sido corrigido por CITY_ALIASES,
        # mas se passar aqui, pega a última palavra
        return True

    # 1) tenta pegar a primeira city-like
    for p in parts:
        if looks_like_city(p):
            # "netherlands utrecht berlin" → pegue o primeiro city-like limpo
            tokens = [CITY_ALIASES.get(w, w) for w in p.split()]
            # preferir último token se parece com cidade conhecida
            if len(tokens) > 1:
                # tenta fuzzy no último token
                candidate = tokens[-1]
                pref = _fuzzy_pick(candidate, PREFERRED_CITIES | set(CITY_ALIASES.values()), FUZZY_SCORE_CITY)
                if pref:
                    return pref
            return p

    # 2) fuzzy rescue com preferred cities e aliases
    universe = set(CITY_ALIASES.keys()) | set(CITY_ALIASES.values()) | PREFERRED_CITIES
    guess = _fuzzy_pick(t, universe, FUZZY_SCORE_CITY)
    return CITY_ALIASES.get(guess, guess) if guess else None


# --- LANGUAGES split ------------------------------------------------------- #
def split_languages_field(cell: Any) -> Tuple[List[str], List[str], List[str]]:
    """
    Separa linguagens em (naturais, programação, desconhecidas).
    Aceita string/list/dict. Aplica fuzzy leve.
    """
    tokens = [_tok(x) for x in _to_list(cell)]
    naturals, progs, unknowns = [], [], []
    for tok in tokens:
        if tok in NATURAL_LANGS:
            naturals.append(tok)
            continue
        if tok in PROG_LANGS:
            progs.append(tok)
            continue
        # tenta fuzzy
        p = _fuzzy_pick(tok, PROG_LANGS, FUZZY_SCORE_LANGUAGE)
        n = _fuzzy_pick(tok, NATURAL_LANGS, FUZZY_SCORE_LANGUAGE)
        if p and not n:
            progs.append(p)
        elif n and not p:
            naturals.append(n)
        else:
            unknowns.append(tok)
    return _dedupe_keep_order(naturals), _dedupe_keep_order(progs), _dedupe_keep_order(unknowns)


# --- TOOLS ----------------------------------------------------------------- #
def normalize_tools(cell: Any) -> Tuple[List[str], List[str]]:
    """
    Normaliza ferramentas por sinônimos.
    Retorna (tools_normalizadas, desconhecidas).
    """
    out, unk = [], []
    for tok in _to_list(cell):
        t = _tok(tok)
        t = TOOL_SYNONYMS.get(t, SYNONYMS.get(t, t))
        if t:
            out.append(t)
        else:
            unk.append(tok)
    return _dedupe_keep_order(out), _dedupe_keep_order(unk)


# =========================== Pipeline de preparo =========================== #

def normalize_enhanced_columns(df: pd.DataFrame) -> pd.DataFrame:
    """
    Achata extracted_info/enhanced_info → enhanced_* columns e garante presença.
    """
    if "extracted_info" in df.columns:
        extracted = pd.json_normalize(df["extracted_info"]).add_prefix("enhanced_")
        df = df.drop(columns=["extracted_info"]).join(extracted)
    elif "enhanced_info" in df.columns:
        enhanced = pd.json_normalize(df["enhanced_info"]).add_prefix("enhanced_")
        df = df.drop(columns=["enhanced_info"]).join(enhanced)

    for col in ENHANCED_COLS:
        if col not in df.columns:
            df[col] = ""

    return df


def apply_quality_normalization(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, List[str]]]:
    """
    Aplica normalização de tipo/localização/linguagens/tools.
    Retorna df normalizado + dicionário de 'unknowns' para auditoria.
    """
    if df.empty:
        return df, {}

    out = df.copy()

    # --- Job type ---
    # usa enhanced_type; se vazio, tenta inferir a partir de job_location/descrição
    def _type_row(row) -> Optional[str]:
        candidates = []
        for col in ("enhanced_type", "job_type", "job_location", "description"):
            val = row.get(col)
            if isinstance(val, str) and val.strip():
                candidates.append(val)
        for c in candidates:
            val = normalize_job_type(c)
            if val:
                return val
        return None

    out["enhanced_type"] = out.apply(_type_row, axis=1).fillna(out.get("enhanced_type"))

    # --- Location ---
    def _loc_row(row) -> Optional[str]:
        for col in ("enhanced_location", "job_location"):
            val = row.get(col)
            if isinstance(val, str) and val.strip():
                loc = normalize_location(val)
                if loc:
                    return loc
        return None

    out["enhanced_location"] = out.apply(_loc_row, axis=1).fillna("")

    # --- Languages split ---
    naturals, progs, unknown_langs = [], [], []
    for cell in out.get("enhanced_languages", []):
        n, p, u = split_languages_field(cell)
        naturals.append(n)
        progs.append(p)
        unknown_langs.extend(u)
    if "enhanced_languages" in out.columns:
        out[NAT_LANG_COL] = naturals
        out[PROG_LANG_COL] = progs

    # --- Tools ---
    tools_norm, tools_unk = [], []
    if "enhanced_tools" in out.columns:
        for cell in out["enhanced_tools"]:
            n, u = normalize_tools(cell)
            tools_norm.append(n)
            tools_unk.extend(u)
        out["enhanced_tools"] = tools_norm

    # Unknown buckets (dedup)
    unknowns: Dict[str, List[str]] = {}
    if unknown_langs:
        unknowns["languages_unknown"] = _dedupe_keep_order(unknown_langs)
    if tools_unk:
        unknowns["tools_unknown"] = _dedupe_keep_order(tools_unk)

    # (Opcional) exporta CSVs de unknowns para facilitar curadoria
    for key, vals in unknowns.items():
        pd.DataFrame({key: vals}).to_csv(UNKNOWN_BUCKETS_DIR / f"{key}.csv", index=False)

    return out, unknowns


# ============================ basic load =========================== #

@st.cache_data
def load_json_data(json_data: Dict[str, Any]) -> tuple[pd.DataFrame, Dict[str, Any]]:
    """Load and normalize JSON data"""
    rows = json_data.get("data", json_data)
    if isinstance(rows, list):
        df = pd.json_normalize(rows)
        df = normalize_enhanced_columns(df)
        df, _ = apply_quality_normalization(df)
    else:
        df = pd.DataFrame()

    meta = json_data.get("meta", {})
    return df, meta


# =============================== Filters/Views ============================== #

def filter_dataframe(
    df: pd.DataFrame,
    search_query: str = "",
    company_filter: Optional[List[str]] = None,
    min_desc_length: int = 0
) -> pd.DataFrame:
    """Apply filters to dataframe"""
    if df.empty:
        return df

    filtered = df.copy()

    # Text search
    if search_query:
        sq = search_query.lower()
        mask = filtered.apply(
            lambda r: sq in f"{r.get('job_position','')} {r.get('company_name','')} {r.get('description','')}".lower(),
            axis=1
        )
        filtered = filtered[mask]

    # Company filter
    if company_filter:
        filtered = filtered[filtered["company_name"].isin(company_filter)]

    # Description length filter
    if min_desc_length:
        filtered = filtered[filtered["description"].fillna("").str.len() >= min_desc_length]

    return filtered


def prepare_table_view(df: pd.DataFrame) -> pd.DataFrame:
    """Prepare dataframe for table display"""
    df_show = df.copy()

    if "job_link" in df_show.columns:
        df_show["job_link"] = df_show["job_link"].fillna("")

    # Converte listas/dicts para string para exibir
    def _cell_to_str(v):
        if isinstance(v, list):
            return ", ".join(map(str, v))
        if isinstance(v, dict):
            return "; ".join([f"{k}: {v}" for k, v in v.items()])
        return v

    for col in ENHANCED_COLS + [NAT_LANG_COL, PROG_LANG_COL]:
        if col in df_show.columns and df_show[col].apply(lambda x: isinstance(x, (list, dict))).any():
            df_show[col] = df_show[col].apply(_cell_to_str)

    # Order columns
    main_fields = ["job_position", "company_name", "job_location", "job_posting_date", "job_link"]
    extra = [c for c in (ENHANCED_COLS + [NAT_LANG_COL, PROG_LANG_COL]) if c in df_show.columns]
    final_cols = [c for c in main_fields if c in df_show.columns] + extra
    df_show = df_show[final_cols]

    return df_show


# ================================ Exports ================================== #

def export_to_json(df: pd.DataFrame, meta: Dict[str, Any]) -> bytes:
    """Export dataframe to JSON bytes"""
    payload = {"meta": meta, "data": df.to_dict(orient="records")}
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def export_to_csv(df: pd.DataFrame) -> bytes:
    """Export dataframe to CSV bytes"""
    return df.to_csv(index=False).encode("utf-8")