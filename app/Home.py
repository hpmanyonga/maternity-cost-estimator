"""Landing page for the NOH Maternity Platform."""

import os
import streamlit as st

st.set_page_config(
    page_title="Network One Health — Maternity Care",
    page_icon="🍼",
    layout="wide",
)

LOGO_PATH = os.path.join(os.path.dirname(__file__), "assets", "noh_logo.png")

# --- Header ---
col_logo, col_title = st.columns([1, 4])
with col_logo:
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=160)
with col_title:
    st.title("Network One Health")
    st.caption("South Africa's only risk-rated maternity bundle")

st.divider()

# --- Navigation cards ---
st.markdown(
    "Welcome to the NOH maternity platform. Use the tools below to understand "
    "your maternity care costs and get a personalised quote."
)

col1, col2 = st.columns(2)

with col1:
    st.subheader("Estimate Your Costs")
    st.markdown(
        "Compare **fee-for-service** costs (6-7 separate bills) against the "
        "NOH all-inclusive global fee. Based on 250+ data points from hospitals, "
        "specialists, and labs across South Africa."
    )
    st.page_link("pages/1_Cost_Estimator.py", label="Open Cost Estimator", icon="📊")

with col2:
    st.subheader("Get a QuickQuote")
    st.markdown(
        "Answer a few questions about your pregnancy and health factors to get "
        "a risk-rated estimate in under a minute. Request a personalised quote "
        "from the NOH care team."
    )
    st.page_link("pages/2_QuickQuote.py", label="Open QuickQuote", icon="⚡")

st.divider()

# --- What's included ---
st.subheader("What's included in the NOH maternity bundle")

inc_col1, inc_col2, inc_col3 = st.columns(3)
with inc_col1:
    st.markdown("**Antenatal care**")
    st.markdown("- 10-14 antenatal visits\n- All ultrasound scans\n- Booking bloods and pathology")
with inc_col2:
    st.markdown("**Delivery**")
    st.markdown("- Hospital facility fees\n- Obstetrician delivery fee\n- Anaesthetist fee")
with inc_col3:
    st.markdown("**Support**")
    st.markdown("- Doula birth support\n- Antenatal classes\n- Prenatal vitamins guidance")

st.divider()

# --- Footer ---
foot_col1, foot_col2 = st.columns([3, 1])
with foot_col1:
    st.caption(
        "Disclaimer: Estimates are based on publicly available 2024-2026 pricing data. "
        "Actual costs may vary depending on your clinical profile, hospital, and specialist. "
        "This tool is for planning purposes only."
    )
with foot_col2:
    st.caption("Network One Health")
    st.caption("Info@networkonehealth.co.za")
    st.caption("011 458 2497")
