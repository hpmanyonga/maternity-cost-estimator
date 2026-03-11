"""NOH Cash Programme pricing workbench — admin page."""

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from auth import require_auth
from engine.models import NOHCashProfile
from engine.config import NOH_ADDITIONAL_TESTS, PRIVATE_ROOM_FEE
from engine.coopland_engine import CooplandEngine, COOPLAND_FACTORS
from engine.noh_cash_eligibility import NOHCashEligibilityEngine
from engine.noh_cash_engine import NOHCashPricingEngine
from engine.msa_document import generate_msa_docx

if not require_auth():
    st.stop()

st.title("NOH Cash Programme Pricing")
st.markdown(
    "**NOH Cash Maternity Programme (v1)** — "
    "Separate from Discovery. Internal Network One Health rules."
)

coopland_engine = CooplandEngine()

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

# ----------------------------------------------------------
# Three-column layout
# ----------------------------------------------------------
noh_col1, noh_col2, noh_col3 = st.columns(3)

# ==================
# LEFT: INTAKE & ELIGIBILITY
# ==================
with noh_col1:
    st.subheader("Intake & Eligibility")

    noh_gravida = st.number_input(
        "Gravida", min_value=1, max_value=20, value=1, key="noh_gravida",
    )
    noh_parity = st.number_input(
        "Parity", min_value=0, max_value=20, value=0, key="noh_parity",
    )
    noh_ga = st.number_input(
        "GA at Booking (weeks)", min_value=4.0, max_value=40.0,
        value=14.0, step=0.5, key="noh_ga",
    )
    noh_baby_ma = st.radio(
        "Baby Medical Aid Secured?",
        options=["Yes", "No"],
        index=0,
        key="noh_baby_ma",
    )
    baby_ma_secured = noh_baby_ma == "Yes"

    has_full_record = False
    has_complications = False
    if noh_ga > 26:
        has_full_record = st.checkbox(
            "Full clinical record available", key="noh_full_record",
        )
        has_complications = st.checkbox(
            "Complications present", key="noh_complications",
        )

    noh_elig_engine = NOHCashEligibilityEngine()
    noh_eligibility = noh_elig_engine.evaluate(
        booking_weeks=noh_ga,
        baby_medical_aid_secured=baby_ma_secured,
        has_full_clinical_record=has_full_record,
        has_complications=has_complications,
    )

    st.divider()
    if noh_eligibility.eligible_for_global_fee:
        st.success("Eligible for NOH Cash Programme")
    else:
        st.error(f"Not eligible — {noh_eligibility.exclusion_reason}")

# ==================
# MIDDLE: RISK CLASSIFICATION
# ==================
with noh_col2:
    st.subheader("Risk Classification")

    is_primigravida = noh_gravida == 1

    if is_primigravida:
        st.warning("**Primigravida** — automatic HIGH risk classification")

    st.markdown("**Coopland Assessment** (secondary)")
    noh_factors = {}
    for group_name, factor_keys in FACTOR_GROUPS.items():
        with st.expander(group_name, expanded=False):
            for key in factor_keys:
                weight = COOPLAND_FACTORS[key]
                label = key.replace("_", " ").title() + f" (+{weight})"
                noh_factors[key] = st.checkbox(
                    label, value=False, key=f"noh_coop_{key}",
                )

    noh_coopland = coopland_engine.score(noh_factors)

    noh_cash_engine = NOHCashPricingEngine()
    noh_profile = NOHCashProfile(
        gravida=noh_gravida,
        parity=noh_parity,
        gestational_age_weeks=noh_ga,
        planned_delivery_mode="NVD",
        baby_medical_aid_secured=baby_ma_secured,
    )
    eff_risk, eff_reason = noh_cash_engine.classify_risk(
        noh_profile, noh_coopland.risk_band,
    )

    st.divider()
    st.metric("Risk Classification", eff_risk)
    st.caption(eff_reason)
    if noh_coopland.total_score > 0:
        st.info(f"Coopland Score: {noh_coopland.total_score} ({noh_coopland.risk_band})"
                + (" — overridden by primigravida" if is_primigravida else ""))

# ==================
# RIGHT: PRICING
# ==================
with noh_col3:
    st.subheader("Pricing")

    noh_delivery = st.selectbox(
        "Planned Delivery Mode",
        options=["NVD", "ELECTIVE_CS"],
        format_func=lambda x: "Normal Vaginal (NVD)" if x == "NVD" else "Elective Caesarean Section",
        index=0,
        key="noh_delivery",
    )

    noh_cs_conversion = False
    if noh_delivery == "NVD":
        noh_cs_conversion = st.checkbox(
            "CS Conversion (NVD → emergency CS, +R7,500)",
            key="noh_cs_conv",
        )

    st.markdown("**Clinical Add-ons**")
    noh_chronic = st.checkbox("Chronic Condition", key="noh_chronic")
    noh_chronic_consults = 0
    noh_chronic_scans = 0
    if noh_chronic:
        noh_chronic_consults = st.select_slider(
            "Extra chronic consults", options=[1, 2, 3, 4],
            value=2, key="noh_chronic_consults",
        )
        noh_chronic_scans = st.select_slider(
            "Extra chronic scans (R1,500 each)", options=[1, 2],
            value=2, key="noh_chronic_scans",
        )

    noh_complication = st.checkbox("Complications", key="noh_complication")
    noh_comp_consults = 0
    noh_comp_scans = 0
    if noh_complication:
        noh_comp_consults = st.select_slider(
            "Extra complication consults", options=[1, 2, 3, 4],
            value=1, key="noh_comp_consults",
        )
        noh_comp_scans = st.select_slider(
            "Extra complication scans (R1,500 each)", options=[1, 2],
            value=1, key="noh_comp_scans",
        )

    st.markdown("**Room**")
    noh_pvt_room = st.checkbox("Private Room (R4,000)", key="noh_pvt_room")
    noh_pvt_discount = 0
    if noh_pvt_room:
        noh_pvt_discount = st.radio(
            "Private Room Discount",
            options=[0, 10, 15],
            format_func=lambda x: f"No discount" if x == 0 else f"{x}% (R{PRIVATE_ROOM_FEE * (1 - x/100):,.0f})",
            index=0,
            key="noh_pvt_discount",
        )

    st.markdown("**Additional Tests**")
    selected_tests = []
    for test_key, test_info in NOH_ADDITIONAL_TESTS.items():
        if st.checkbox(
            f"{test_info['label']} (R{test_info['fee']:,.2f})",
            key=f"noh_test_{test_key}",
        ):
            selected_tests.append(test_key)

    if noh_eligibility.eligible_for_global_fee:
        full_profile = NOHCashProfile(
            gravida=noh_gravida,
            parity=noh_parity,
            gestational_age_weeks=noh_ga,
            planned_delivery_mode=noh_delivery,
            baby_medical_aid_secured=baby_ma_secured,
            chronic_flag=noh_chronic,
            chronic_consults=noh_chronic_consults,
            chronic_scans=noh_chronic_scans,
            complication_flag=noh_complication,
            complication_consults=noh_comp_consults,
            complication_scans=noh_comp_scans,
            cs_conversion=noh_cs_conversion,
            private_room=noh_pvt_room,
            private_room_discount=noh_pvt_discount,
            selected_tests=selected_tests,
        )

        noh_result = noh_cash_engine.price(full_profile, noh_coopland.risk_band)

        st.divider()

        st.metric("Package", f"{noh_result.package_code} — R{noh_result.package_price:,.0f}")
        st.caption(noh_result.package_label)

        line_items = noh_result.to_line_items()
        st.dataframe(
            pd.DataFrame(line_items).style.format({"amount": "R {:,.2f}"}),
            use_container_width=True,
            hide_index=True,
        )

        st.metric("Total", f"R {noh_result.total_price:,.2f}")
    else:
        st.divider()
        st.warning("Pricing not available — patient not eligible.")

st.info("**Note:** Package fees do not include screening for Down's syndrome "
        "or epidural anaesthesia. These are billed separately if requested.")

# ----------------------------------------------------------
# PAYMENT GOVERNANCE
# ----------------------------------------------------------
if noh_eligibility.eligible_for_global_fee:
    st.divider()
    st.subheader("Payment Governance")

    gov_col1, gov_col2 = st.columns([2, 1])

    with gov_col1:
        st.markdown("""
- Full global fee payable by **34 weeks** gestation
- Failure to complete payment results in **programme exit**
- CS conversion levy (**R7,500**) applies if planned NVD converts to emergency CS
- Baby medical aid must be secured by **34 weeks**
- No external authorisation required — internal NOH governance only
        """)

        st.checkbox(
            "I understand and accept these programme rules",
            key="noh_accept_rules",
        )

    with gov_col2:
        st.metric(
            "Monthly Payment",
            f"R {noh_result.monthly_payment:,.0f}/month",
        )
        st.caption(
            f"{noh_result.months_to_34_weeks} months to 34 weeks "
            f"(booking at {noh_ga:.0f} weeks)"
        )

    st.subheader("Payment Schedule")
    schedule_rows = []
    for m in range(1, noh_result.months_to_34_weeks + 1):
        schedule_rows.append({
            "Month": m,
            "Payment": noh_result.monthly_payment,
            "Cumulative": noh_result.monthly_payment * m,
        })
    schedule_df = pd.DataFrame(schedule_rows)
    st.dataframe(
        schedule_df.style.format({
            "Payment": "R {:,.0f}",
            "Cumulative": "R {:,.0f}",
        }),
        use_container_width=True,
        hide_index=True,
    )

# ----------------------------------------------------------
# MSA DOCUMENT GENERATION
# ----------------------------------------------------------
st.divider()
st.subheader("Medical Service Agreement")

msa_col1, msa_col2 = st.columns(2)
with msa_col1:
    msa_patient_name = st.text_input(
        "Patient Full Name (with title)",
        placeholder="e.g. Mrs Jane Doe",
        key="msa_patient_name",
    )
with msa_col2:
    msa_id_number = st.text_input(
        "ID / Passport Number",
        placeholder="e.g. 9001015000088",
        key="msa_id_number",
    )

if noh_eligibility.eligible_for_global_fee and msa_patient_name and msa_id_number:
    msa_buf = generate_msa_docx(
        patient_name=msa_patient_name,
        id_number=msa_id_number,
        gestational_age_weeks=noh_ga,
        global_fee=noh_result.total_price,
        months_to_34_weeks=noh_result.months_to_34_weeks,
        monthly_payment=noh_result.monthly_payment,
    )
    st.download_button(
        label="Download MSA (.docx)",
        data=msa_buf,
        file_name=f"MSA_{msa_patient_name.replace(' ', '_')}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
elif not noh_eligibility.eligible_for_global_fee:
    st.caption("Patient must be eligible for the programme to generate the MSA.")
else:
    st.caption("Enter patient name and ID above to generate the MSA.")
