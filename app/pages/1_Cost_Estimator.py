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
NOH_DARK = "#2d6e64"
NOH_LIGHT = "#e8f4f1"
NOH_BG = "#f0f7f5"
SLATE = "#475569"
MUTED = "#94a3b8"


def _fmt(n: int) -> str:
    return f"R{n:,}"


def _show_breakdown(breakdown: CostBreakdown):
    labels = {
        "hospital": "Hospital facility",
        "obstetrician": "Obstetrician",
        "anaesthetist": "Anaesthetist",
        "paediatrician": "Paediatrician",
        "pathology": "Blood tests & pathology",
        "ultrasound": "Ultrasound scans",
        "medication": "Medicines & supplements",
        "midwife": "Midwife",
        "doula": "Doula support",
    }
    rows = []
    for attr, label in labels.items():
        low, high = getattr(breakdown, attr)
        if low > 0 or high > 0:
            rows.append({"Service": label, "Low": _fmt(low), "High": _fmt(high)})
    rows.append({"Service": "TOTAL", "Low": _fmt(breakdown.total[0]), "High": _fmt(breakdown.total[1])})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════
# GLOBAL STYLES
# ══════════════════════════════════════════════════
st.markdown(
    f"""<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    [data-testid="stSidebar"],
    [data-testid="stSidebarCollapsedControl"],
    [data-testid="stToolbar"],
    header[data-testid="stHeader"] {{display:none !important}}

    .block-container {{
        max-width:940px;
        padding:0 1rem 2rem;
        font-family:'Inter',sans-serif;
    }}

    /* Hero banner */
    .hero {{
        background: linear-gradient(135deg, {NOH} 0%, {NOH_DARK} 100%);
        border-radius: 0 0 20px 20px;
        padding: 32px 36px 28px;
        margin: 0 -1rem 24px;
        text-align: center;
    }}
    .hero-title {{
        color: #fff;
        font-size: 1.8rem;
        font-weight: 700;
        margin: 12px 0 4px;
        letter-spacing: -0.02em;
    }}
    .hero-sub {{
        color: #c5e8e1;
        font-size: 0.95rem;
        margin: 0;
    }}

    /* Section labels */
    .section-label {{
        font-size: 0.7rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: {MUTED};
        margin: 0 0 4px;
    }}

    /* FFS card */
    .ffs-card {{
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 24px 24px 18px;
        background: #fff;
        height: 100%;
    }}
    .ffs-price {{
        font-size: 1.65rem;
        font-weight: 700;
        color: #1e293b;
        margin: 4px 0 10px;
        line-height: 1.15;
    }}

    /* NOH card */
    .noh-card {{
        border: 2px solid {NOH};
        border-radius: 16px;
        padding: 24px 24px 18px;
        background: {NOH_BG};
        position: relative;
        height: 100%;
    }}
    .noh-card::before {{
        content: "RECOMMENDED";
        position: absolute;
        top: -11px;
        left: 24px;
        background: {NOH};
        color: #fff;
        font-size: 0.65rem;
        font-weight: 600;
        letter-spacing: 0.08em;
        padding: 3px 12px;
        border-radius: 10px;
    }}
    .noh-price {{
        font-size: 1.65rem;
        font-weight: 700;
        color: {NOH};
        margin: 4px 0 10px;
        line-height: 1.15;
    }}
    .noh-label {{
        font-size: 0.7rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: {NOH};
        margin: 0 0 4px;
    }}

    /* Save badge */
    .save-pill {{
        display: inline-block;
        background: {NOH};
        color: #fff;
        font-size: 0.8rem;
        font-weight: 600;
        padding: 4px 16px;
        border-radius: 20px;
        margin: 0 0 10px;
    }}

    /* Detail text */
    .detail {{
        font-size: 0.85rem;
        color: {SLATE};
        line-height: 1.5;
        margin: 0 0 3px;
    }}

    /* Quote section */
    .quote-header {{
        text-align: center;
        margin: 8px 0 4px;
    }}
    .quote-title {{
        font-size: 1.3rem;
        font-weight: 700;
        color: {NOH};
        margin: 0 0 2px;
    }}
    .quote-sub {{
        font-size: 0.85rem;
        color: {SLATE};
        margin: 0;
    }}

    /* Button overrides */
    .stFormSubmitButton>button[kind="primary"] {{
        background: linear-gradient(135deg, {NOH} 0%, {NOH_DARK} 100%) !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 12px !important;
        font-size: 1rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.01em !important;
    }}
    .stFormSubmitButton>button[kind="primary"]:hover {{
        background: linear-gradient(135deg, {NOH_DARK} 0%, #245c53 100%) !important;
    }}

    /* Disclaimer */
    .disclaimer {{
        text-align: center;
        font-size: 0.73rem;
        color: {MUTED};
        line-height: 1.45;
        margin: 12px 0 0;
    }}

    /* Footer */
    .footer {{
        text-align: center;
        font-size: 0.75rem;
        color: {MUTED};
        padding: 16px 0 0;
        border-top: 1px solid #e2e8f0;
        margin-top: 24px;
    }}
    </style>""",
    unsafe_allow_html=True,
)

# ══════════════════════════════════════════════════
# HERO BANNER
# ══════════════════════════════════════════════════
logo_html = ""
if os.path.exists(LOGO_PATH):
    import base64
    with open(LOGO_PATH, "rb") as f:
        logo_b64 = base64.b64encode(f.read()).decode()
    logo_html = f'<img src="data:image/png;base64,{logo_b64}" style="height:52px;margin-bottom:4px" alt="NOH">'

st.markdown(
    f'<div class="hero">'
    f'{logo_html}'
    f'<p class="hero-title">What will your maternity care cost?</p>'
    f'<p class="hero-sub">Get an instant estimate — compare separate bills with one bundled fee</p>'
    f'</div>',
    unsafe_allow_html=True,
)

# ══════════════════════════════════════════════════
# INPUTS — compact rows
# ══════════════════════════════════════════════════
i1, i2, i3, i4 = st.columns(4, gap="medium")
with i1:
    region = st.selectbox(
        "Province",
        ["Gauteng", "Western Cape", "KwaZulu-Natal", "Other"],
        help="Costs vary by province.",
    )
with i2:
    delivery_labels = {"NVD": "Vaginal", "CS": "Caesarean", "Undecided": "Not sure yet"}
    delivery_type = st.selectbox(
        "Birth type",
        options=list(delivery_labels.keys()),
        format_func=lambda x: delivery_labels[x],
        index=2,
    )
with i3:
    risk_level = st.selectbox(
        "Care complexity",
        ["low", "medium", "high"],
        format_func=lambda x: x.capitalize(),
        help="**Low** = routine. **Medium** = extra monitoring (35+, prev CS). **High** = diabetes, twins.",
    )
with i4:
    provider_tier = st.selectbox(
        "Hospital level",
        ["budget", "mid-range", "premium"],
        index=1,
        format_func=lambda x: x.capitalize(),
        help="**Budget** = Life. **Mid** = Mediclinic. **Premium** = Netcare.",
    )

j1, j2, j3, j4 = st.columns(4, gap="medium")
with j1:
    wants_epidural = False
    if delivery_type in ("NVD", "Undecided"):
        wants_epidural = st.checkbox("Epidural", help="Adds anaesthetist fee. NOH +R3,500.")
with j2:
    wants_doula = st.checkbox("Doula", help="Included in NOH bundle.")
with j3:
    timing_choice = st.selectbox("Timing", ["Pregnant now", "Planning"])
with j4:
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
        st.caption("")

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

# ══════════════════════════════════════════════════
# RESULTS — 2 columns
# ══════════════════════════════════════════════════
st.markdown("")
col_ffs, col_noh = st.columns(2, gap="large")

with col_ffs:
    st.markdown(
        f'<div class="ffs-card">'
        f'<p class="section-label">SEPARATE BILLS</p>'
        f'<p class="ffs-price">{_fmt(ffs_low)} — {_fmt(ffs_high)}</p>'
        f'<p class="detail">6-7 separate bills from hospital, obstetrician, '
        f'anaesthetist, paediatrician, lab, and radiology</p>'
        f'<p class="detail" style="margin-top:8px">'
        f'Monthly savings target: <b>{_fmt(ffs_plan.monthly_low)} — {_fmt(ffs_plan.monthly_high)}</b></p>'
        f'</div>',
        unsafe_allow_html=True,
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

with col_noh:
    savings_html = ""
    if noh["savings_high"] > 0:
        savings_html = f'<span class="save-pill">Save up to {_fmt(noh["savings_high"])}</span><br>'

    st.markdown(
        f'<div class="noh-card">'
        f'<p class="noh-label">NOH ALL-IN-ONE BUNDLE</p>'
        f'<p class="noh-price">{_fmt(noh["noh_total_low"])} — {_fmt(noh["noh_total_high"])}</p>'
        f'{savings_html}'
        f'<p class="detail">Everything included — antenatal visits, scans, bloods, '
        f'hospital, delivery, anaesthetist, doula</p>'
        f'<p class="detail" style="margin-top:8px">'
        f'From <b>{_fmt(noh_plan["monthly_low"])}/mo</b> over {noh_plan["months"]} months '
        f'(10% deposit)</p>'
        f'</div>',
        unsafe_allow_html=True,
    )
    with st.expander("What's included in the NOH bundle"):
        for item in [
            "All antenatal visits (10-14 visits)",
            "All ultrasound scans",
            "Booking bloods and pathology",
            "Hospital facility fees",
            "Obstetrician delivery fee",
            "Anaesthetist fee",
            "Doula birth support",
            "Antenatal classes",
        ]:
            st.markdown(f"&check; &nbsp; {item}")
        st.caption(f"Paediatrician billed separately: {_fmt(noh['paediatrician'][0])}—{_fmt(noh['paediatrician'][1])}")

# ── Disclaimer ──
st.markdown(
    '<p class="disclaimer">'
    "Estimates only. Excludes special tests (e.g. Down syndrome screening, "
    "amniocentesis) and NICU costs. Final quote follows clinical review."
    "</p>",
    unsafe_allow_html=True,
)

# ══════════════════════════════════════════════════
# QUOTE FORM
# ══════════════════════════════════════════════════
st.markdown("")
st.markdown(
    '<div class="quote-header">'
    '<p class="quote-title">Get your personalised quote</p>'
    '<p class="quote-sub">Our team will review your details and contact you within 24 hours</p>'
    '</div>',
    unsafe_allow_html=True,
)

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

# ══════════════════════════════════════════════════
# COLLAPSED DETAIL SECTIONS
# ══════════════════════════════════════════════════
st.markdown("")

with st.expander("What does care complexity mean?"):
    st.markdown(
        "**Low** — Routine pregnancy, no extra monitoring needed\n\n"
        "**Medium** — Extra scans or monitoring recommended (age 35+, previous caesarean, BMI concerns)\n\n"
        "**High** — Close management needed (diabetes, hypertension, twins, other chronic conditions)"
    )

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
        st.markdown(f"**NOH payment plan**")
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
        st.markdown(f"**NOH bundle**")
        st.markdown(f"**{_fmt(noh['noh_total_low'])}—{_fmt(noh['noh_total_high'])}**")
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
st.markdown(
    '<p class="footer">'
    "For planning only. Confirm fees with your providers.<br>"
    "Network One Health · Info@networkonehealth.co.za · 011 458 2497"
    "</p>",
    unsafe_allow_html=True,
)
