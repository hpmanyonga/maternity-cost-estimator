"""Load and normalize data from Supabase (with CSV fallback for local dev)."""

from __future__ import annotations

import os
import pandas as pd
import streamlit as st
from engine.config import REGIONS, NATIONAL_MARKERS, PROVIDER_TIERS

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

# ---------------------------------------------------------------------------
# Supabase connection (lazy init)
# ---------------------------------------------------------------------------
_sb_client = None


def _resolve_env(key: str) -> str:
    """Read from Streamlit secrets first, then env vars as fallback."""
    try:
        val = st.secrets.get(key, "")
        if val:
            return val
    except Exception:
        pass
    return os.getenv(key, "")


def _get_supabase():
    """Return a Supabase client if credentials are available, else None."""
    global _sb_client
    if _sb_client is not None:
        return _sb_client

    url = _resolve_env("SUPABASE_URL")
    key = _resolve_env("SUPABASE_KEY") or _resolve_env("SUPABASE_SERVICE_KEY")

    if url and key:
        try:
            from supabase import create_client
            _sb_client = create_client(url, key)
            return _sb_client
        except Exception:
            pass
    return None


_supabase_available: bool | None = None


def _fetch_table(table_name: str, columns: str = "*") -> pd.DataFrame | None:
    """Fetch a full table from Supabase. Returns None on failure. Skips if previous attempt failed."""
    global _supabase_available
    if _supabase_available is False:
        return None
    sb = _get_supabase()
    if sb is None:
        _supabase_available = False
        return None
    try:
        result = sb.table(table_name).select(columns).execute()
        if result.data:
            _supabase_available = True
            return pd.DataFrame(result.data)
    except Exception:
        _supabase_available = False
    return None


# ---------------------------------------------------------------------------
# Helpers (unchanged)
# ---------------------------------------------------------------------------

def _safe_numeric(series: pd.Series) -> pd.Series:
    """Convert price column to numeric, coercing percentages and non-numeric to NaN."""
    return pd.to_numeric(
        series.astype(str).str.replace(r"[^\d.]", "", regex=True),
        errors="coerce",
    )


def _assign_region_group(region_value: str) -> str:
    """Map a CSV region/location string to a region group."""
    if pd.isna(region_value):
        return "National"
    region_value = str(region_value).strip()
    if region_value in NATIONAL_MARKERS:
        return "National"
    for group, markers in REGIONS.items():
        if region_value in markers:
            return group
    # Fuzzy fallback: check if any marker is a substring
    region_lower = region_value.lower()
    for group, markers in REGIONS.items():
        for marker in markers:
            if marker.lower() in region_lower or region_lower in marker.lower():
                return group
    return "National"


def _assign_provider_tier(provider_value: str, category: str) -> str:
    """Map a CSV provider string to a provider tier."""
    if pd.isna(provider_value):
        return "mid-range"
    provider_value = str(provider_value).strip()
    tier_key_map = {
        "hospital": "hospitals",
        "obstetrician": "hospitals",
        "anaesthetist": "hospitals",
        "paediatrician": "hospitals",
        "pathology": "pathology",
        "ultrasound": "ultrasound",
        "midwife": "midwife",
        "doula": "doula",
    }
    lookup_key = tier_key_map.get(category, "hospitals")
    for tier, providers in PROVIDER_TIERS.items():
        tier_providers = providers.get(lookup_key, [])
        for tp in tier_providers:
            if tp.lower() in provider_value.lower() or provider_value.lower() in tp.lower():
                return tier
    return "mid-range"


# ---------------------------------------------------------------------------
# Loaders — each tries Supabase first, falls back to local CSV
# ---------------------------------------------------------------------------

def _apply_hospital_transforms(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns={
        "provider": "provider",
        "hospital_or_region": "region",
        "service_description": "service",
        "price_low_rands": "price_low",
        "price_high_rands": "price_high",
    })
    df["category"] = "hospital"
    df["price_low"] = _safe_numeric(df["price_low"])
    df["price_high"] = _safe_numeric(df["price_high"])
    df["region_group"] = df["region"].apply(_assign_region_group)
    df["provider_tier"] = df["provider"].apply(lambda x: _assign_provider_tier(x, "hospital"))
    return df


def load_hospital_packages() -> pd.DataFrame:
    df = _fetch_table("hospital_packages")
    if df is not None:
        return _apply_hospital_transforms(df)
    return _apply_hospital_transforms(pd.read_csv(os.path.join(DATA_DIR, "01_hospital_packages.csv")))


def _apply_professional_transforms(df: pd.DataFrame, category: str) -> pd.DataFrame:
    df = df.rename(columns={
        "provider_name_or_region": "region",
        "service_description": "service",
        "price_low_rands": "price_low",
        "price_high_rands": "price_high",
    })
    df["category"] = category
    df["provider"] = df["region"]
    df["price_low"] = _safe_numeric(df["price_low"])
    df["price_high"] = _safe_numeric(df["price_high"])
    df["region_group"] = df["region"].apply(_assign_region_group)
    df["provider_tier"] = df["provider"].apply(lambda x: _assign_provider_tier(x, category))
    return df


def load_obstetrician_fees() -> pd.DataFrame:
    df = _fetch_table("obstetrician_fees")
    if df is not None:
        return _apply_professional_transforms(df, "obstetrician")
    return _apply_professional_transforms(
        pd.read_csv(os.path.join(DATA_DIR, "02_obstetrician_fees.csv")), "obstetrician"
    )


def load_anaesthetist_fees() -> pd.DataFrame:
    df = _fetch_table("anaesthetist_fees")
    if df is not None:
        return _apply_professional_transforms(df, "anaesthetist")
    return _apply_professional_transforms(
        pd.read_csv(os.path.join(DATA_DIR, "03_anaesthetist_fees.csv")), "anaesthetist"
    )


def load_paediatrician_fees() -> pd.DataFrame:
    df = _fetch_table("paediatrician_fees")
    if df is not None:
        return _apply_professional_transforms(df, "paediatrician")
    return _apply_professional_transforms(
        pd.read_csv(os.path.join(DATA_DIR, "04_paediatrician_fees.csv")), "paediatrician"
    )


def load_pathology_fees() -> pd.DataFrame:
    df = _fetch_table("pathology_fees")
    if df is None:
        df = pd.read_csv(os.path.join(DATA_DIR, "05_pathology_fees.csv"))
    df = df.rename(columns={
        "category": "test_category",
        "provider_name": "provider",
        "test_name": "service",
        "price_low_rands": "price_low",
        "price_high_rands": "price_high",
    })
    df["category"] = "pathology"
    df["region"] = "National"
    df["price_low"] = _safe_numeric(df["price_low"])
    df["price_high"] = _safe_numeric(df["price_high"])
    df["region_group"] = "National"
    df["provider_tier"] = df["provider"].apply(lambda x: _assign_provider_tier(x, "pathology"))
    return df


def load_ultrasound_fees() -> pd.DataFrame:
    df = _fetch_table("ultrasound_radiology")
    if df is None:
        df = pd.read_csv(os.path.join(DATA_DIR, "06_ultrasound_radiology.csv"))
    df = df.rename(columns={
        "category": "scan_category",
        "provider_name": "provider",
        "service_description": "service",
        "price_low_rands": "price_low",
        "price_high_rands": "price_high",
    })
    df["category"] = "ultrasound"
    df["region"] = df["provider"]
    df["price_low"] = _safe_numeric(df["price_low"])
    df["price_high"] = _safe_numeric(df["price_high"])
    df = df.dropna(subset=["price_low", "price_high"])
    df["region_group"] = df["provider"].apply(_assign_region_group)
    df["provider_tier"] = df["provider"].apply(lambda x: _assign_provider_tier(x, "ultrasound"))
    return df


def load_midwife_doula_fees() -> pd.DataFrame:
    df = _fetch_table("midwife_doula_fees")
    if df is None:
        df = pd.read_csv(os.path.join(DATA_DIR, "07_midwife_doula_fees.csv"))
    df = df.rename(columns={
        "category": "service_category",
        "provider_name": "provider",
        "location": "region",
        "service_description": "service",
        "price_low_rands": "price_low",
        "price_high_rands": "price_high",
    })
    df["category"] = df["service_category"].str.lower()
    df["price_low"] = _safe_numeric(df["price_low"])
    df["price_high"] = _safe_numeric(df["price_high"])
    df = df.dropna(subset=["price_low", "price_high"])
    df["region_group"] = df["region"].apply(_assign_region_group)
    df["provider_tier"] = df.apply(
        lambda row: _assign_provider_tier(row["provider"], row["category"]), axis=1
    )
    return df


def load_medication_fees() -> pd.DataFrame:
    df = _fetch_table("medications_supplements")
    if df is None:
        df = pd.read_csv(os.path.join(DATA_DIR, "08_medication_supplements.csv"))
    df = df.rename(columns={
        "category": "med_category",
        "product_name": "provider",
        "description": "service",
        "price_low_rands": "price_low",
        "price_high_rands": "price_high",
    })
    df["category"] = "medication"
    df["region"] = "National"
    df["price_low"] = _safe_numeric(df["price_low"])
    df["price_high"] = _safe_numeric(df["price_high"])
    df["region_group"] = "National"
    df["provider_tier"] = "mid-range"
    return df


def load_sources() -> pd.DataFrame:
    df = _fetch_table("pricing_sources")
    if df is not None:
        return df
    return pd.read_csv(os.path.join(DATA_DIR, "00_sources_and_notes.csv"))


_all_cache: dict[str, pd.DataFrame] | None = None


def load_all() -> dict[str, pd.DataFrame]:
    """Load all data files and return a dict keyed by category. Cached after first call."""
    global _all_cache
    if _all_cache is not None:
        return _all_cache
    _all_cache = {
        "hospital": load_hospital_packages(),
        "obstetrician": load_obstetrician_fees(),
        "anaesthetist": load_anaesthetist_fees(),
        "paediatrician": load_paediatrician_fees(),
        "pathology": load_pathology_fees(),
        "ultrasound": load_ultrasound_fees(),
        "midwife_doula": load_midwife_doula_fees(),
        "medication": load_medication_fees(),
        "sources": load_sources(),
    }
    return _all_cache
