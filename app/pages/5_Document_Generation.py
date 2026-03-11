"""HRANTN + MSA document generation — admin page."""

import sys
import tempfile
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from auth import require_auth
from engine.hrantn_document import generate_hrantn_pdf
from engine.msa_document import generate_msa_docx, generate_discovery_msa_docx

if not require_auth():
    st.stop()

st.title("Document Generation")
st.caption("Generate HRANTN authorisation PDFs and Medical Service Agreements.")

tab_hrantn, tab_noh_msa, tab_disc_msa = st.tabs([
    "HRANTN Authorisation",
    "NOH Cash MSA",
    "Discovery MSA",
])

# ==============================
# HRANTN PDF
# ==============================
with tab_hrantn:
    st.subheader("HRANTN Authorisation Request")
    st.markdown("Generate a PDF authorisation request for Discovery maternity patients.")

    h_col1, h_col2 = st.columns(2)
    with h_col1:
        h_name = st.text_input("Patient Name", key="doc_h_name")
        h_aid = st.text_input("Medical Aid Number", key="doc_h_aid")
        h_plan = st.selectbox(
            "Plan", options=["KeyCare", "Smart", "Coastal & Essential", "Classic", "Executive"],
            key="doc_h_plan",
        )
    with h_col2:
        h_ga = st.number_input("GA at Booking (weeks)", min_value=4.0, max_value=40.0, value=12.0, step=0.5, key="doc_h_ga")
        h_route = st.selectbox("Booking Category", options=["ANTN1A", "ANTN1B"], key="doc_h_route")
        h_score = st.number_input("Coopland Score", min_value=0, max_value=30, value=5, key="doc_h_score")

    h_band = "LOW" if h_score <= 3 else ("MEDIUM" if h_score <= 6 else "HIGH")
    h_extra_consults = 0 if h_band == "LOW" else (2 if h_band == "MEDIUM" else 4)
    h_extra_scans = 0 if h_band == "LOW" else (1 if h_band == "MEDIUM" else 2)

    st.write(f"Risk band: **{h_band}** → {h_extra_consults} extra consults, {h_extra_scans} extra scans")

    h_drivers = st.text_input("Risk drivers (comma-separated factor keys)", key="doc_h_drivers",
                              placeholder="e.g. primigravida, chronic_hypertension")

    if h_name and h_aid:
        drivers = [d.strip() for d in h_drivers.split(",") if d.strip()] if h_drivers else []
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            generate_hrantn_pdf(
                output_path=Path(tmp.name),
                patient_name=h_name,
                medical_aid_number=h_aid,
                plan_name=h_plan,
                gestational_age_weeks=h_ga,
                booking_category=h_route,
                coopland_score=h_score,
                risk_band=h_band,
                risk_drivers=drivers,
                extra_consults=h_extra_consults,
                extra_ultrasounds=h_extra_scans,
            )
            pdf_bytes = Path(tmp.name).read_bytes()

        st.download_button(
            label="Download HRANTN PDF",
            data=pdf_bytes,
            file_name=f"HRANTN_{h_aid}_{h_name.replace(' ', '_')}.pdf",
            mime="application/pdf",
        )
    else:
        st.info("Enter patient name and medical aid number to generate the PDF.")

# ==============================
# NOH Cash MSA
# ==============================
with tab_noh_msa:
    st.subheader("NOH Cash Programme MSA")
    st.markdown("Generate a Medical Service Agreement for NOH Cash patients.")

    m_col1, m_col2 = st.columns(2)
    with m_col1:
        m_name = st.text_input("Patient Full Name (with title)", placeholder="e.g. Mrs Jane Doe", key="doc_m_name")
        m_id = st.text_input("ID / Passport Number", key="doc_m_id")
    with m_col2:
        m_ga = st.number_input("GA at Booking (weeks)", min_value=4.0, max_value=40.0, value=14.0, step=0.5, key="doc_m_ga")
        m_fee = st.number_input("Global Fee (R)", min_value=0.0, value=46_000.0, step=1000.0, key="doc_m_fee")
        m_months = st.number_input("Months to 34 weeks", min_value=1, max_value=12, value=5, key="doc_m_months")

    m_monthly = m_fee / m_months if m_months > 0 else 0

    st.write(f"Monthly payment: **R {m_monthly:,.0f}** x {m_months} months")

    if m_name and m_id:
        msa_buf = generate_msa_docx(
            patient_name=m_name,
            id_number=m_id,
            gestational_age_weeks=m_ga,
            global_fee=m_fee,
            months_to_34_weeks=m_months,
            monthly_payment=m_monthly,
        )
        st.download_button(
            label="Download NOH Cash MSA (.docx)",
            data=msa_buf,
            file_name=f"MSA_{m_name.replace(' ', '_')}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    else:
        st.info("Enter patient name and ID number to generate the MSA.")

# ==============================
# Discovery MSA
# ==============================
with tab_disc_msa:
    st.subheader("Discovery Global Fee MSA")
    st.markdown("Generate a Medical Service Agreement for Discovery patients.")

    d_col1, d_col2 = st.columns(2)
    with d_col1:
        d_title = st.selectbox("Title", options=["Mrs", "Ms", "Miss", "Dr", "Prof"], key="doc_d_title")
        d_first = st.text_input("First Name", key="doc_d_first")
        d_surname = st.text_input("Surname", key="doc_d_surname")
        d_id = st.text_input("ID / Passport Number", key="doc_d_id")
    with d_col2:
        d_mobile = st.text_input("Mobile Number", key="doc_d_mobile")
        d_email = st.text_input("Email", key="doc_d_email")
        d_member = st.text_input("Membership Number", key="doc_d_member")
        d_dep = st.text_input("Dependent Code", key="doc_d_dep")

    d_ga = st.number_input("GA at Booking (weeks)", min_value=4.0, max_value=40.0, value=12.0, step=0.5, key="doc_d_ga")
    d_plan = st.selectbox(
        "Discovery Plan",
        options=["KEYCARE", "SMART", "COASTAL_ESSENTIAL", "CLASSIC", "EXECUTIVE"],
        key="doc_d_plan",
    )
    d_route = st.selectbox("Enrollment Route", options=["ANTN1A", "ANTN1B"], key="doc_d_route")

    if all([d_first, d_surname, d_id, d_member]):
        dis_buf = generate_discovery_msa_docx(
            title=d_title,
            first_name=d_first,
            surname=d_surname,
            id_number=d_id,
            mobile=d_mobile,
            email=d_email,
            gestational_age_weeks=d_ga,
            plan_type=d_plan,
            membership_no=d_member,
            dependent_code=d_dep,
            enrollment_route=d_route,
        )
        st.download_button(
            label="Download Discovery MSA (.docx)",
            data=dis_buf,
            file_name=f"MSA_Discovery_{d_surname}_{d_first}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
    else:
        st.info("Fill in First Name, Surname, ID, and Membership Number to generate.")
