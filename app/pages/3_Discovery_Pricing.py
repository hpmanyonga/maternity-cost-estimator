"""Discovery Global Fee pricing workbench — admin page."""

import sys
import os
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from auth import require_auth
from engine.pricing_engine import PricingEngine
from engine.models import PatientProfile
from engine.config import PRIVATE_ROOM_FEE
from engine.coopland_engine import CooplandEngine, COOPLAND_FACTORS
from engine.eligibility_engine import EligibilityEngine
from engine.hrantn_document import generate_hrantn_pdf
from engine.msa_document import generate_discovery_msa_docx
import tempfile

if not require_auth():
    st.stop()

st.title("Discovery Global Fee Pricing")
st.markdown("Discovery-aligned global fee pricing with additive risk loadings.")

OUTPUTS_DIR = Path(__file__).resolve().parent.parent.parent / "outputs"


@st.cache_resource
def load_engine():
    return PricingEngine(outputs_dir=str(OUTPUTS_DIR))


@st.cache_data
def load_table(name):
    return pd.read_csv(OUTPUTS_DIR / name)


discovery_engine = load_engine()
coopland_engine = CooplandEngine()

# ==============================
# Coopland factor groups
# ==============================
FACTOR_GROUPS = {
    "Demographic": [
        "maternal_age_extremes", "teenage_pregnancy", "short_stature",
        "extreme_weight", "poor_socioeconomic_status",
    ],
    "Obstetric History": [
        "grand_multiparity", "primigravida", "previous_cs",
        "previous_stillbirth", "previous_preterm_delivery", "previous_pph",
        "previous_low_birth_weight", "previous_macrosomia", "history_of_infertility",
    ],
    "Medical Conditions": [
        "chronic_hypertension", "diabetes_mellitus", "cardiac_disease",
        "renal_disease", "epilepsy", "mental_illness", "hiv_positive",
        "anaemia", "rh_negative", "tb_or_recent_infection", "malaria",
    ],
    "Current Pregnancy": [
        "multiple_pregnancy", "abnormal_lie", "recurrent_uti",
        "poor_anc_attendance", "poor_nutrition",
    ],
    "Social / Behavioural": [
        "smoking_or_substance_use", "domestic_violence",
    ],
}

# ==============================
# SIDEBAR – Patient Input
# ==============================
st.sidebar.header("Patient Profile")

plan_type = st.sidebar.selectbox(
    "Discovery Plan",
    options=["KEYCARE", "SMART", "COASTAL_ESSENTIAL", "CLASSIC", "EXECUTIVE"],
    format_func=lambda x: {
        "KEYCARE": "KeyCare (R48,000)",
        "SMART": "Smart (R50,000)",
        "COASTAL_ESSENTIAL": "Coastal & Essential (R52,000)",
        "CLASSIC": "Classic (R55,000)",
        "EXECUTIVE": "Executive (R58,000)",
    }[x],
    index=0,
)

enrollment_route = st.sidebar.radio(
    "Enrollment Window",
    options=["ANTN1A", "ANTN1B"],
    format_func=lambda x: {
        "ANTN1A": "Early (≤15+6 weeks) — ANTN1A",
        "ANTN1B": "Late (16+1 to 20 weeks) — ANTN1B",
    }[x],
    index=0,
)

st.sidebar.divider()
st.sidebar.subheader("Eligibility")

maternal_age = st.sidebar.number_input("Maternal Age", min_value=12, max_value=55, value=28)
booking_weeks = st.sidebar.number_input("Booking Gestation (weeks)", min_value=4.0, max_value=40.0, value=12.0, step=0.5)
multiple_pregnancy = st.sidebar.checkbox("Multiple Pregnancy (twins+)")
uncontrolled_chronic = st.sidebar.checkbox("Uncontrolled Chronic Disease")

st.sidebar.divider()
st.sidebar.subheader("Coopland Risk Assessment")

factors_present = {}
for group_name, factor_keys in FACTOR_GROUPS.items():
    with st.sidebar.expander(group_name):
        for key in factor_keys:
            weight = COOPLAND_FACTORS[key]
            label = key.replace("_", " ").title() + f" (+{weight})"
            factors_present[key] = st.checkbox(label, value=False, key=f"disc_coop_{key}")

coopland_result = coopland_engine.score(factors_present)

risk_category = {
    "LOW": "BASE", "MEDIUM": "MEDIUM", "HIGH": "HIGH"
}[coopland_result.risk_band]

st.sidebar.divider()
st.sidebar.metric("Coopland Score", coopland_result.total_score)
st.sidebar.info(f"Risk band: **{coopland_result.risk_band}** → {coopland_result.extra_consults} extra consults, {coopland_result.extra_ultrasounds} extra scans")

delivery_mode = st.sidebar.selectbox(
    "Delivery Mode",
    options=["NVD", "CS"],
    format_func=lambda x: "Normal Vaginal (NVD)" if x == "NVD" else "Caesarean Section (CS)",
    index=0,
)

chronic_flag = st.sidebar.checkbox("Chronic Condition")
complication_flag = st.sidebar.checkbox("Complications")

st.sidebar.divider()
st.sidebar.subheader("Room & Extras")
private_room = st.sidebar.checkbox("Private Room (R4,000)")
private_room_discount = 0
if private_room:
    private_room_discount = st.sidebar.radio(
        "Private Room Discount",
        options=[0, 10, 15],
        format_func=lambda x: f"No discount" if x == 0 else f"{x}% discount (R{PRIVATE_ROOM_FEE * (1 - x/100):,.0f})",
        index=0,
        key="disc_pvt_discount",
    )

# ==============================
# ELIGIBILITY CHECK
# ==============================
eligibility_engine = EligibilityEngine()
eligibility = eligibility_engine.evaluate(
    coopland_score=coopland_result.total_score,
    maternal_age=maternal_age,
    multiple_pregnancy=multiple_pregnancy,
    uncontrolled_chronic_disease=uncontrolled_chronic,
    booking_weeks=booking_weeks,
)

st.header("Eligibility")

if eligibility.eligible_for_global_fee:
    st.success("**Eligible** for global fee")
    if eligibility.requires_authorisation:
        st.warning(f"Authorisation required: **{eligibility.authorisation_type}**")
else:
    st.error(f"**Not eligible** for global fee — {eligibility.exclusion_reason}")
    if eligibility.requires_authorisation:
        st.info(f"Authorisation type: **{eligibility.authorisation_type}**")

if eligibility.potential_delivery_carveouts:
    with st.expander(f"Potential Delivery Carve-outs ({len(eligibility.potential_delivery_carveouts)})"):
        for item in eligibility.potential_delivery_carveouts:
            st.markdown(f"- {item}")

# ==============================
# HRANTN AUTHORISATION DOCUMENT
# ==============================
if eligibility.requires_authorisation and coopland_result.risk_drivers:
    st.subheader("HRANTN Authorisation Request")
    st.markdown("Complete the fields below to generate a PDF authorisation request.")

    col_name, col_id = st.columns(2)
    with col_name:
        patient_name = st.text_input("Patient Name", value="", key="hrantn_name")
    with col_id:
        medical_aid_number = st.text_input("Medical Aid Number", value="", key="hrantn_id")

    plan_display = {
        "KEYCARE": "KeyCare", "SMART": "Smart",
        "COASTAL_ESSENTIAL": "Coastal & Essential",
        "CLASSIC": "Classic", "EXECUTIVE": "Executive",
    }

    if patient_name and medical_aid_number:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            generate_hrantn_pdf(
                output_path=Path(tmp.name),
                patient_name=patient_name,
                medical_aid_number=medical_aid_number,
                plan_name=plan_display.get(plan_type, plan_type),
                gestational_age_weeks=booking_weeks,
                booking_category=enrollment_route,
                coopland_score=coopland_result.total_score,
                risk_band=coopland_result.risk_band,
                risk_drivers=coopland_result.risk_drivers,
                extra_consults=coopland_result.extra_consults,
                extra_ultrasounds=coopland_result.extra_ultrasounds,
            )
            pdf_bytes = Path(tmp.name).read_bytes()

        st.download_button(
            label="Download HRANTN Authorisation PDF",
            data=pdf_bytes,
            file_name=f"HRANTN_{medical_aid_number}_{patient_name.replace(' ', '_')}.pdf",
            mime="application/pdf",
        )
    else:
        st.info("Enter patient name and medical aid number to generate the PDF.")

# ==============================
# COOPLAND SCORING DETAIL
# ==============================
if coopland_result.risk_drivers:
    st.subheader("Coopland Risk Factors")
    driver_rows = [
        {"Factor": d.replace("_", " ").title(), "Weight": COOPLAND_FACTORS[d]}
        for d in coopland_result.risk_drivers
    ]
    driver_rows.append({"Factor": "TOTAL", "Weight": coopland_result.total_score})
    st.dataframe(
        pd.DataFrame(driver_rows),
        use_container_width=True,
        hide_index=True,
    )

# ==============================
# PRICING RESULT
# ==============================
if eligibility.eligible_for_global_fee:
    profile = PatientProfile(
        plan_type=plan_type,
        enrollment_route=enrollment_route,
        risk_category=risk_category,
        delivery_mode=delivery_mode,
        chronic_flag=chronic_flag,
        complication_flag=complication_flag,
        private_room=private_room,
        private_room_discount=private_room_discount,
    )

    result = discovery_engine.price_patient(profile)

    st.header("Pricing Result")

    col1, col2, col3 = st.columns(3)
    col1.metric("Global Fee", f"R {result.global_fee:,.0f}")
    col2.metric("Total Add-ons", f"R {result.total_addons:,.0f}")
    col3.metric("Final Price", f"R {result.final_price:,.0f}")

    st.subheader("Line-Item Breakdown")
    line_items = result.to_line_items()
    line_df = pd.DataFrame(line_items)
    st.dataframe(
        line_df.style.format({"amount": "R {:,.0f}"}),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Payment Stages")
    stage_df = pd.DataFrame([
        {"Stage": result.enrollment_route, "Amount": result.antn1_amount},
        {"Stage": "ANTN2", "Amount": result.antn2_amount},
        {"Stage": "Delivery", "Amount": result.delivery_amount},
    ])
    st.dataframe(
        stage_df.style.format({"Amount": "R {:,.0f}"}),
        use_container_width=True,
        hide_index=True,
    )

    if result.total_addons > 0:
        st.subheader("Add-on Breakdown")
        addon_items = [
            {"Add-on": "Risk", "Amount": result.risk_addon},
            {"Add-on": "Chronic", "Amount": result.chronic_addon},
            {"Add-on": "Complication", "Amount": result.complication_addon},
            {"Add-on": "CS Differential", "Amount": result.cs_addon},
            {"Add-on": "Private Room", "Amount": result.private_room_addon},
        ]
        addon_df = pd.DataFrame([a for a in addon_items if a["Amount"] > 0])
        st.dataframe(
            addon_df.style.format({"Amount": "R {:,.0f}"}),
            use_container_width=True,
            hide_index=True,
        )
else:
    st.header("Pricing Result")
    st.warning("Global fee pricing not available — patient is excluded. "
               "This case would be billed on a fee-for-service basis.")

st.info("**Note:** Global fees do not include screening for Down's syndrome "
        "or epidural anaesthesia. These are billed separately if requested.")

# ==============================
# FEE SCHEDULE REFERENCE
# ==============================
st.header("Discovery Fee Schedule Reference")

ref_tab1, ref_tab2, ref_tab3, ref_tab4 = st.tabs([
    "Global Fees by Plan",
    "Risk Add-on Schedule",
    "Consult & Scan Fees",
    "Case Mix Distribution",
])

with ref_tab1:
    fee_df = load_table("global_fee_schedule.csv")
    fmt = {c: "R {:,.0f}" for c in fee_df.columns if c != "plan_type"}
    st.dataframe(fee_df.style.format(fmt), use_container_width=True, hide_index=True)

with ref_tab2:
    risk_df = load_table("risk_addon_schedule.csv")
    st.dataframe(risk_df.style.format({
        "addon_keycare": "R {:,.0f}",
        "addon_other": "R {:,.0f}",
    }), use_container_width=True, hide_index=True)

with ref_tab3:
    consult_df = load_table("consult_fees.csv")
    st.dataframe(consult_df.style.format({
        "consult_fee": "R {:,.0f}",
        "scan_fee": "R {:,.0f}",
    }), use_container_width=True, hide_index=True)

with ref_tab4:
    case_df = load_table("case_mix_distribution.csv")
    st.dataframe(case_df, use_container_width=True, hide_index=True)

# ==============================
# MSA — DISCOVERY GLOBAL FEE
# ==============================
st.divider()
st.header("Medical Service Agreement")

dis_msa_col1, dis_msa_col2 = st.columns(2)
with dis_msa_col1:
    dis_msa_title = st.selectbox(
        "Title", options=["Mrs", "Ms", "Miss", "Dr", "Prof"],
        key="dis_msa_title",
    )
    dis_msa_first = st.text_input(
        "First Name", placeholder="e.g. Jane", key="dis_msa_first",
    )
    dis_msa_surname = st.text_input(
        "Surname", placeholder="e.g. Doe", key="dis_msa_surname",
    )
    dis_msa_id = st.text_input(
        "ID / Passport Number", placeholder="e.g. 9001015000088",
        key="dis_msa_id",
    )
with dis_msa_col2:
    dis_msa_mobile = st.text_input(
        "Mobile Number", placeholder="e.g. 0821234567",
        key="dis_msa_mobile",
    )
    dis_msa_email = st.text_input(
        "Email", placeholder="e.g. jane@example.com",
        key="dis_msa_email",
    )
    dis_msa_member = st.text_input(
        "Membership Number", placeholder="e.g. DH-123456",
        key="dis_msa_member",
    )
    dis_msa_dep = st.text_input(
        "Dependent Code", placeholder="e.g. 00",
        key="dis_msa_dep",
    )

required_filled = all([dis_msa_first, dis_msa_surname, dis_msa_id, dis_msa_member])

if required_filled:
    dis_msa_buf = generate_discovery_msa_docx(
        title=dis_msa_title,
        first_name=dis_msa_first,
        surname=dis_msa_surname,
        id_number=dis_msa_id,
        mobile=dis_msa_mobile,
        email=dis_msa_email,
        gestational_age_weeks=booking_weeks,
        plan_type=plan_type,
        membership_no=dis_msa_member,
        dependent_code=dis_msa_dep,
        enrollment_route=enrollment_route,
    )
    st.download_button(
        label="Download Discovery MSA (.docx)",
        data=dis_msa_buf,
        file_name=f"MSA_Discovery_{dis_msa_surname}_{dis_msa_first}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
else:
    st.caption("Fill in First Name, Surname, ID, and Membership Number to generate the MSA.")

# ==============================
# BATCH PRICING
# ==============================
st.header("Batch Pricing — All Plan/Risk Combinations")

plan_filter = st.multiselect(
    "Filter by plan",
    options=["KEYCARE", "SMART", "COASTAL_ESSENTIAL", "CLASSIC", "EXECUTIVE"],
    default=["KEYCARE", "SMART", "COASTAL_ESSENTIAL", "CLASSIC", "EXECUTIVE"],
)

rows = []
for plan in plan_filter:
    for route in ["ANTN1A", "ANTN1B"]:
        for risk in ["BASE", "MEDIUM", "HIGH"]:
            for delivery in ["NVD", "CS"]:
                for chr_flag in [False, True]:
                    for comp in [False, True]:
                        p = PatientProfile(plan, route, risk, delivery, chr_flag, comp)
                        r = discovery_engine.price_patient(p)
                        rows.append({
                            "Plan": plan,
                            "Route": route,
                            "Risk": risk,
                            "Delivery": delivery,
                            "Chronic": chr_flag,
                            "Complication": comp,
                            "Global Fee (R)": r.global_fee,
                            "Add-ons (R)": r.total_addons,
                            "Final Price (R)": r.final_price,
                        })

batch_df = pd.DataFrame(rows)
st.dataframe(
    batch_df.style.format({
        "Global Fee (R)": "R {:,.0f}",
        "Add-ons (R)": "R {:,.0f}",
        "Final Price (R)": "R {:,.0f}",
    }),
    use_container_width=True,
    hide_index=True,
)
