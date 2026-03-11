"""Maternity Cost Estimator — public guided quote tool."""

import sys
import os
import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from engine.estimator import estimate, estimate_noh, EstimatorInput, CostBreakdown
from engine.budget_planner import calculate_savings_plan, calculate_noh_payment_plan
from engine.data_loader import load_sources
from engine.config import NOH_PRICING

LOGO_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "noh_logo.png")

NOH = "#40887d"
NOH_LIGHT = "#e8f4f1"
NOH_BORDER = "#40887d"


def _fmt(n: int) -> str:
    return f"R{n:,}"


def _show_breakdown(breakdown: CostBreakdown):
    labels = {
        "hospital": "Hospital",
        "obstetrician": "Obstetrician",
        "anaesthetist": "Anaesthetist",
        "paediatrician": "Paediatrician",
        "pathology": "Blood tests",
        "ultrasound": "Scans",
        "medication": "Medicines",
        "midwife": "Midwife",
        "doula": "Doula",
    }
    rows = []
    for attr, label in labels.items():
        low, high = getattr(breakdown, attr)
        if low > 0 or high > 0:
            rows.append({"Service": label, "Low": _fmt(low), "High": _fmt(high)})
    rows.append({"Service": "TOTAL", "Low": _fmt(breakdown.total[0]), "High": _fmt(breakdown.total[1])})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ── Page config + CSS ──
st.markdown(
    f"""<style>
    [data-testid="stSidebar"]{{display:none}}
    [data-testid="stSidebarCollapsedControl"]{{display:none}}
    .block-container{{max-width:1200px;padding-top:1rem}}

    /* Primary color overrides */
    .stButton>button[kind="primary"],
    .stFormSubmitButton>button[kind="primary"] {{
        background-color: {NOH} !important;
        border-color: {NOH} !important;
    }}
    .stButton>button[kind="primary"]:hover,
    .stFormSubmitButton>button[kind="primary"]:hover {{
        background-color: #357a6f !important;
        border-color: #357a6f !important;
    }}

    /* Segmented control active */
    [data-testid="stSegmentedControl"] button[aria-pressed="true"] {{
        background-color: {NOH} !important;
        color: white !important;
    }}
    </style>""",
    unsafe_allow_html=True,
)

# ── Header ──
h1, h2 = st.columns([4, 1])
with h1:
    st.markdown(f'<h3 style="margin:0;color:{NOH}">Maternity Cost Estimator</h3>', unsafe_allow_html=True)
    st.caption("Compare separate bills with the NOH all-in-one bundle.")
with h2:
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=70)

# ══════════════════════════════════════════════════
# 3-column layout: Inputs | Separate bills | NOH
# ══════════════════════════════════════════════════
col_in, col_ffs, col_noh = st.columns([1.0, 0.9, 0.9], gap="medium")

# ── INPUTS ──
with col_in:
    region = st.selectbox(
        "Where will you deliver?",
        ["Gauteng", "Western Cape", "KwaZulu-Natal", "Other"],
        help="Costs vary by province.",
    )

    delivery_labels = {"NVD": "Vaginal birth", "CS": "Planned caesarean", "Undecided": "Not sure yet"}
    delivery_type = st.segmented_control(
        "Birth type",
        options=list(delivery_labels.keys()),
        format_func=lambda x: delivery_labels[x],
        default="Undecided",
    )

    risk_level = st.selectbox(
        "Care complexity",
        ["low", "medium", "high"],
        format_func=lambda x: x.capitalize(),
        help="How much monitoring your pregnancy needs.",
    )
    with st.expander("What does care complexity mean?", expanded=False):
        st.markdown(
            "**Low** — Routine pregnancy, no extra monitoring\n\n"
            "**Medium** — Extra scans or monitoring (age 35+, previous caesarean, BMI concerns)\n\n"
            "**High** — Close management needed (diabetes, hypertension, twins)"
        )

    provider_tier = st.selectbox(
        "Hospital price level",
        ["budget", "mid-range", "premium"],
        index=1,
        format_func=lambda x: x.capitalize(),
        help="**Budget** = Life. **Mid-range** = Mediclinic. **Premium** = Netcare.",
    )

    c1, c2 = st.columns(2)
    with c1:
        wants_epidural = False
        if delivery_type in ("NVD", "Undecided"):
            wants_epidural = st.checkbox("Epidural", help="Adds anaesthetist fee. NOH adds R3,500.")
    with c2:
        wants_doula = st.checkbox("Doula", help="Included in NOH bundle.")

    timing_choice = st.segmented_control(
        "Timing", options=["Pregnant now", "Planning"], default="Pregnant now",
    )

    gestational_weeks = 0
    weeks_remaining = 40
    gestation_group = "Under 12 weeks"
    if timing_choice == "Pregnant now":
        gestation_group = st.select_slider(
            "How far along?",
            options=["Under 12 wks", "12-20 wks", "20-28 wks", "28+ wks"],
            value="Under 12 wks",
        )
        wk = {"Under 12 wks": 8, "12-20 wks": 16, "20-28 wks": 24, "28+ wks": 32}
        gestational_weeks = wk[gestation_group]
        weeks_remaining = 40 - gestational_weeks
    else:
        weeks_remaining = 64

# ── COMPUTE ──
inp = EstimatorInput(
    region=region, delivery_type=delivery_type, risk_level=risk_level,
    provider_tier=provider_tier, wants_epidural=wants_epidural,
    wants_midwife=False, wants_doula=wants_doula, gestational_weeks=gestational_weeks,
)
noh = estimate_noh(inp)
ffs_result = noh["ffs_result"]
ffs_low = noh["ffs_total_low"]
ffs_high = noh["ffs_total_high"]
noh_plan = calculate_noh_payment_plan(noh["noh_total_low"], noh["noh_total_high"])
ffs_plan = calculate_savings_plan(ffs_low, ffs_high, weeks_remaining)

# ── SEPARATE BILLS column ──
with col_ffs:
    with st.container(border=True):
        st.markdown(
            '<p style="font-size:0.75rem;font-weight:600;text-transform:uppercase;'
            'letter-spacing:.04em;color:#64748b;margin:0 0 2px">'
            'Separate bills</p>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<p style="font-size:1.5rem;font-weight:700;line-height:1.2;'
            f'margin:0 0 8px;color:#1e293b">'
            f'{_fmt(ffs_low)} — {_fmt(ffs_high)}</p>',
            unsafe_allow_html=True,
        )
        st.caption(
            "6-7 bills from hospital, OB, anaesthetist, "
            "paediatrician, lab, radiology"
        )
        st.caption(
            f"Savings target: ~{_fmt(ffs_plan.monthly_low)}—"
            f"{_fmt(ffs_plan.monthly_high)}/mo"
        )

    with st.expander("See cost breakdown"):
        if isinstance(ffs_result, dict):
            t1, t2 = st.tabs(["Vaginal", "Caesarean"])
            with t1:
                _show_breakdown(ffs_result["NVD"])
            with t2:
                _show_breakdown(ffs_result["CS"])
        else:
            _show_breakdown(ffs_result)

# ── NOH BUNDLE column ──
with col_noh:
    # Green-tinted NOH card via inline style wrapper
    st.markdown(
        f'<div style="border:2px solid {NOH};border-radius:12px;'
        f'background:{NOH_LIGHT};padding:20px 18px 14px;margin-bottom:8px">'
        f'<p style="font-size:0.75rem;font-weight:600;text-transform:uppercase;'
        f'letter-spacing:.04em;color:{NOH};margin:0 0 2px">'
        f'NOH all-in-one bundle</p>'
        f'<p style="font-size:1.5rem;font-weight:700;line-height:1.2;'
        f'margin:0 0 6px;color:{NOH}">'
        f'{_fmt(noh["noh_total_low"])} — {_fmt(noh["noh_total_high"])}</p>'
        + (
            f'<span style="display:inline-block;background:{NOH};color:#fff;'
            f'font-size:0.78rem;font-weight:600;padding:3px 12px;'
            f'border-radius:20px;margin:2px 0 8px">'
            f'Save up to {_fmt(noh["savings_high"])}</span>'
            if noh["savings_high"] > 0 else ""
        )
        + f'<p style="font-size:0.82rem;color:#475569;margin:6px 0 0">'
        f'From <b>{_fmt(noh_plan["monthly_low"])}/mo</b> '
        f'over {noh_plan["months"]} months (10% deposit)</p>'
        f'</div>',
        unsafe_allow_html=True,
    )

    with st.expander("What's included in the NOH bundle"):
        st.markdown(
            "- All antenatal visits (10-14)\n"
            "- All ultrasound scans\n"
            "- Booking bloods and pathology\n"
            "- Hospital facility fees\n"
            "- Obstetrician delivery fee\n"
            "- Anaesthetist fee\n"
            "- Doula birth support\n"
            "- Antenatal classes\n"
            "- No separate bills — one predictable fee"
        )
        st.caption(f"Paediatrician billed separately: {_fmt(noh['paediatrician'][0])}—{_fmt(noh['paediatrician'][1])}")

# ── Disclaimer ──
st.caption(
    "Estimates only. Excludes special tests (e.g. Down syndrome screening, "
    "amniocentesis) and NICU costs. Final quote follows clinical review."
)

# ══════════════════════════════════════════════════
# Below-the-fold: quote form + collapsed sections
# ══════════════════════════════════════════════════

st.markdown("---")

# ── Quote form ──
st.markdown(f'<h4 style="color:{NOH};margin-bottom:0">Get your personalised quote</h4>', unsafe_allow_html=True)
st.caption("Our team will contact you to understand your clinical needs and provide a personalised quote.")

with st.form("noh_lead_form"):
    f1, f2, f3 = st.columns(3)
    with f1:
        lead_name = st.text_input("Name")
    with f2:
        lead_email = st.text_input("Email")
    with f3:
        lead_phone = st.text_input("Phone")

    submitted = st.form_submit_button("Request my quote", type="primary", use_container_width=True)
    if submitted:
        if lead_name and lead_email:
            # Save to Supabase
            from engine.data_loader import _get_supabase
            sb = _get_supabase()
            lead_saved = False
            if sb:
                try:
                    sb.table("leads").insert({
                        "name": lead_name,
                        "email": lead_email,
                        "phone": lead_phone or None,
                        "province": region,
                        "gestational_weeks": gestational_weeks,
                        "delivery_preference": delivery_type,
                        "risk_level": risk_level,
                        "noh_estimate_low": noh["noh_total_low"],
                        "noh_estimate_high": noh["noh_total_high"],
                        "ffs_estimate_low": ffs_low,
                        "ffs_estimate_high": ffs_high,
                    }).execute()
                    lead_saved = True
                except Exception:
                    pass

            # Save to Google Sheets
            try:
                from engine.sheets import append_lead
                append_lead({
                    "Name": lead_name,
                    "Email": lead_email,
                    "Phone": lead_phone or "",
                    "Province": region,
                    "Timing": gestation_group if timing_choice == "Pregnant now" else "Planning",
                    "Birth Type": delivery_type,
                    "Care Complexity": risk_level.capitalize(),
                    "NOH Low": str(noh["noh_total_low"]),
                    "NOH High": str(noh["noh_total_high"]),
                    "FFS Low": str(ffs_low),
                    "FFS High": str(ffs_high),
                    "Source Page": "Cost Estimator",
                })
            except Exception:
                pass

            # Send automated emails
            try:
                from engine.email_sender import send_client_confirmation, send_team_notification
                send_client_confirmation(
                    name=lead_name, email=lead_email,
                    noh_low=noh["noh_total_low"], noh_high=noh["noh_total_high"],
                    ffs_low=ffs_low, ffs_high=ffs_high,
                    source="Cost Estimator",
                )
                send_team_notification(
                    name=lead_name, email=lead_email, phone=lead_phone or "",
                    province=region,
                    timing=gestation_group if timing_choice == "Pregnant now" else "Planning",
                    birth_type=delivery_type, complexity=risk_level.capitalize(),
                    noh_low=noh["noh_total_low"], noh_high=noh["noh_total_high"],
                    ffs_low=ffs_low, ffs_high=ffs_high,
                    source="Cost Estimator",
                )
            except Exception:
                pass

            if lead_saved:
                st.success(f"Thanks, {lead_name}! We'll contact you at {lead_email}. Check your inbox for a confirmation.")
            else:
                st.success(f"Thanks, {lead_name}! We'll be in touch at {lead_email}. Check your inbox for a confirmation.")
        else:
            st.warning("Please enter your name and email.")

# ── Collapsed sections ──
with st.expander("Plan your payments"):
    p1, p2 = st.columns(2)
    with p1:
        st.markdown("**Separate bills**")
        st.markdown(
            f"Target: **{_fmt(ffs_plan.monthly_low)}—{_fmt(ffs_plan.monthly_high)}/mo** "
            f"over {ffs_plan.months_remaining} months"
        )
        for m in ffs_plan.milestones:
            st.caption(f"{m['milestone']} — {m['when']}")
    with p2:
        st.markdown(f"**:green[NOH payment plan]**")
        st.markdown(f"Deposit: **{_fmt(noh_plan['deposit_low'])}—{_fmt(noh_plan['deposit_high'])}**")
        st.markdown(
            f"Then **{_fmt(noh_plan['monthly_low'])}—{_fmt(noh_plan['monthly_high'])}/mo** "
            f"x {noh_plan['months']} months"
        )

with st.expander("Compare hospital scenarios"):
    tiers = ["budget", "mid-range", "premium"]
    tier_names = ["Budget (Life)", "Mid-range (Mediclinic)", "Premium (Netcare)"]
    cc = st.columns(4)
    for i, (tier, name) in enumerate(zip(tiers, tier_names)):
        with cc[i]:
            ci = EstimatorInput(
                region=region,
                delivery_type=delivery_type if delivery_type != "Undecided" else "NVD",
                risk_level=risk_level, provider_tier=tier,
                wants_epidural=wants_epidural, wants_midwife=False, wants_doula=wants_doula,
            )
            cr = estimate(ci)
            if isinstance(cr, dict):
                cr = cr.get("NVD", list(cr.values())[0])
            st.markdown(f"**{name}**")
            st.markdown(f"{_fmt(cr.total[0])}—{_fmt(cr.total[1])}")
            tp = calculate_noh_payment_plan(cr.total[0], cr.total[1])
            st.caption(f"~{_fmt(tp['monthly_low'])}/mo")
    with cc[3]:
        st.markdown(f"**:green[NOH bundle]**")
        st.markdown(f":green[{_fmt(noh['noh_total_low'])}—{_fmt(noh['noh_total_high'])}]")
        st.caption(f"{_fmt(noh_plan['monthly_low'])}/mo x {noh_plan['months']}mo")

with st.expander("How we estimate + sources"):
    st.markdown(
        "Based on **250+ data points** from Netcare, Mediclinic, Life Healthcare, "
        "specialist practices, pathology labs, and radiology groups."
    )
    st.markdown(
        "**Why your final quote may differ:** hospital choice, doctor fees, "
        "medical aid rules, clinical complexity, unplanned changes."
    )
    st.caption("Last updated: March 2026")
    try:
        sources_df = load_sources()
        for _, row in sources_df.iterrows():
            url = row.get("url", "")
            name = row.get("source_name", "Unknown")
            year = row.get("data_year", "")
            if url:
                st.caption(f"[{name}]({url}) ({year})")
            else:
                st.caption(f"{name} ({year})")
    except Exception:
        pass

# ── Footer ──
st.markdown("---")
st.caption(
    "For planning only. Confirm fees with your providers. "
    "Network One Health · Info@networkonehealth.co.za · 011 458 2497"
)
