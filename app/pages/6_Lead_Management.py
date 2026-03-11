"""Unified lead and quote request management — admin page."""

import sys
import os
from pathlib import Path
from typing import Optional

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from auth import require_auth, get_service_client
from engine.storage import NetworkOneStorage, resolve_database_url


if not require_auth():
    st.stop()

st.title("Lead Management")
st.caption("View and manage leads from Cost Estimator and QuickQuote requests.")


@st.cache_resource(show_spinner=False)
def _get_storage() -> Optional[NetworkOneStorage]:
    database_url = resolve_database_url()
    if not database_url:
        return None
    return NetworkOneStorage(database_url=database_url)


# ==============================
# COST ESTIMATOR LEADS (Supabase `leads` table)
# ==============================
st.header("Cost Estimator Leads")
st.caption("Leads captured from the public Cost Estimator page.")

sb = get_service_client()  # service key for admin reads; falls back to anon
if sb:
    try:
        result = sb.table("leads").select("*").order("created_at", desc=True).limit(500).execute()
        if result.data:
            leads_df = pd.DataFrame(result.data)
            st.dataframe(leads_df, use_container_width=True, hide_index=True)
            st.download_button(
                "Download leads CSV",
                data=leads_df.to_csv(index=False).encode("utf-8"),
                file_name="cost_estimator_leads.csv",
                mime="text/csv",
                key="dl_leads",
            )
            st.metric("Total leads", len(result.data))
        else:
            st.info("No leads captured yet.")
    except Exception as e:
        st.error(f"Could not load leads: {e}")
else:
    st.warning("Supabase not configured. Set SUPABASE_URL and SUPABASE_KEY environment variables.")

# ==============================
# QUICKQUOTE REQUESTS (PostgreSQL `quote_requests` table)
# ==============================
st.divider()
st.header("QuickQuote Requests")
st.caption("Quote requests captured from the public QuickQuote page.")

storage = _get_storage()
if storage:
    try:
        requests = storage.list_quote_requests(limit=500)
        if requests:
            req_df = pd.DataFrame(requests)
            st.dataframe(req_df, use_container_width=True, hide_index=True)
            st.download_button(
                "Download quote requests CSV",
                data=req_df.to_csv(index=False).encode("utf-8"),
                file_name="quickquote_requests.csv",
                mime="text/csv",
                key="dl_requests",
            )
            st.metric("Total requests", len(requests))
        else:
            st.info("No quote requests captured yet.")
    except Exception as e:
        st.error(f"Could not load quote requests: {e}")
else:
    st.warning(
        "Database not configured. Set SUPABASE_DB_PASSWORD (or DATABASE_URL) "
        "to enable QuickQuote request tracking."
    )

# ==============================
# COMBINED SUMMARY
# ==============================
st.divider()
st.header("Summary")

total_leads = 0
total_requests = 0

if sb:
    try:
        result = sb.table("leads").select("id", count="exact").execute()
        total_leads = result.count or 0
    except Exception:
        pass

if storage:
    try:
        reqs = storage.list_quote_requests(limit=1)
        # Use the full count query
        total_requests = len(storage.list_quote_requests(limit=10000))
    except Exception:
        pass

col1, col2, col3 = st.columns(3)
col1.metric("Cost Estimator Leads", total_leads)
col2.metric("QuickQuote Requests", total_requests)
col3.metric("Total", total_leads + total_requests)
