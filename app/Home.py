"""Landing page for the NOH Maternity Platform."""

import os
import streamlit as st

st.set_page_config(
    page_title="Network One Health — Maternity Care",
    page_icon="🍼",
    layout="wide",
)

LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "noh_logo.png")

# Hide sidebar on public pages
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] { display: none; }
    [data-testid="stSidebarCollapsedControl"] { display: none; }
    .block-container { max-width: 900px; padding-top: 2rem; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Header ──
col_logo, col_title = st.columns([1, 4])
with col_logo:
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=140)
with col_title:
    st.title("Network One Health")
    st.caption("South Africa's only risk-rated maternity bundle")

st.markdown(
    "One fee covers your full maternity journey — antenatal visits, delivery, "
    "anaesthetist, scans, blood tests, and doula support. No separate bills."
)

st.divider()

# ── Navigation cards ──
col1, col2 = st.columns(2)

with col1:
    st.subheader("Estimate Your Costs")
    st.markdown(
        "Compare **separate bills** (6-7 providers) against the "
        "NOH all-in-one bundle. See what you could save."
    )
    st.page_link("pages/1_Cost_Estimator.py", label="Open Cost Estimator", icon="📊")

with col2:
    st.subheader("Get a QuickQuote")
    st.markdown(
        "Answer a few questions about your pregnancy and health "
        "to get a risk-rated estimate in under a minute."
    )
    st.page_link("pages/2_QuickQuote.py", label="Open QuickQuote", icon="⚡")

st.divider()

# ── What's included ──
st.subheader("What's included in the NOH bundle")

inc1, inc2, inc3 = st.columns(3)
with inc1:
    st.markdown("**Antenatal care**")
    st.markdown("- 10-14 visits\n- All scans\n- Booking blood tests")
with inc2:
    st.markdown("**Delivery**")
    st.markdown("- Hospital facility\n- Obstetrician\n- Anaesthetist")
with inc3:
    st.markdown("**Support**")
    st.markdown("- Doula birth support\n- Antenatal classes\n- Prenatal vitamins guidance")

# ── Footer ──
st.divider()
st.caption(
    "Estimates are based on publicly available 2024-2026 pricing data. "
    "Actual costs depend on your clinical profile, hospital, and specialist."
)
st.caption("Network One Health · Info@networkonehealth.co.za · 011 458 2497")
