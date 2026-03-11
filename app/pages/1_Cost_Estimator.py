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
            rows.append({"Service": label, "Low": f"R{low:,}", "High": f"R{high:,}"})
    rows.append({"Service": "TOTAL", "Low": f"R{breakdown.total[0]:,}", "High": f"R{breakdown.total[1]:,}"})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ── Page chrome ──
st.markdown(
    """<style>
    [data-testid="stSidebar"]{display:none}
    [data-testid="stSidebarCollapsedControl"]{display:none}
    .block-container{max-width:1200px;padding-top:1.2rem}
    .price-lg{font-size:1.35rem;font-weight:700;line-height:1.2;margin:0}
    .price-sm{font-size:0.82rem;color:#64748b;margin:0;text-transform:uppercase;letter-spacing:.03em}
    .save-tag{font-size:0.95rem;font-weight:600;color:#059669;margin:0.2rem 0}
    .ffs-box{border:1px solid #e2e8f0;border-radius:12px;padding:14px 16px;background:#fff}
    .noh-box{border:2px solid #10b981;border-radius:12px;padding:14px 16px;background:#f0fdf4}
    .compact-note{font-size:0.78rem;color:#64748b;line-height:1.4}
    </style>""",
    unsafe_allow_html=True,
)

# ── Minimal header ──
h1, h2 = st.columns([4, 1])
with h1:
    st.markdown("#### Maternity Cost Estimator")
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
        help="**Low** = routine. **Medium** = extra monitoring. **High** = chronic conditions, twins, etc.",
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
            wants_epidural = st.checkbox("Epidural", help="Adds anaesthetist fee for vaginal birth.")
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

# ── SEPARATE BILLS column ──
with col_ffs:
    st.markdown('<div class="ffs-box">', unsafe_allow_html=True)
    st.markdown('<p class="price-sm">Separate bills</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="price-lg">R{ffs_low:,.0f} — R{ffs_high:,.0f}</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="compact-note">6-7 bills from hospital, OB, anaesthetist, '
        "paediatrician, lab, radiology</p>",
        unsafe_allow_html=True,
    )

    ffs_plan = calculate_savings_plan(ffs_low, ffs_high, weeks_remaining)
    st.markdown(
        f'<p class="compact-note">Savings target: ~R{ffs_plan.monthly_low:,}—'
        f"R{ffs_plan.monthly_high:,}/mo</p>",
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    with st.expander("See breakdown"):
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
    st.markdown('<div class="noh-box">', unsafe_allow_html=True)
    st.markdown('<p class="price-sm">NOH all-in-one bundle</p>', unsafe_allow_html=True)
    st.markdown(
        f'<p class="price-lg" style="color:#059669">'
        f"R{noh['noh_total_low']:,.0f} — R{noh['noh_total_high']:,.0f}</p>",
        unsafe_allow_html=True,
    )

    if noh["savings_high"] > 0:
        st.markdown(
            f'<p class="save-tag">Save up to R{noh["savings_high"]:,.0f}</p>',
            unsafe_allow_html=True,
        )

    st.markdown(
        f'<p class="compact-note">From <b>R{noh_plan["monthly_low"]:,}/mo</b> '
        f'over {noh_plan["months"]} months (10% deposit)</p>',
        unsafe_allow_html=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

    with st.expander("What's included"):
        st.markdown(
            "- Antenatal visits (10-14)\n"
            "- All scans and blood tests\n"
            "- Delivery (hospital + OB)\n"
            "- Anaesthetist\n"
            "- Doula + antenatal classes\n"
            "- No separate bills"
        )
        st.caption(f"Paediatrician billed separately: R{noh['paediatrician'][0]:,}—R{noh['paediatrician'][1]:,}")

# ══════════════════════════════════════════════════
# Below-the-fold: quote form + optional sections
# ══════════════════════════════════════════════════

st.markdown("---")

# ── Quick comparison info ──
st.info(
    "**Why separate bills feel unpredictable** — "
    "Different providers bill separately. Deposits and payment dates vary. "
    "Final gaps depend on your cover and care needs."
)

# ── Quote form ──
st.markdown("#### Get your personalised quote")
st.caption("We'll review your details and send you a tailored estimate.")

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
            if lead_saved:
                st.success(f"Thanks, {lead_name}! We'll contact you at {lead_email}.")
            else:
                st.success(f"Thanks, {lead_name}! We'll be in touch at {lead_email}.")
        else:
            st.warning("Please enter your name and email.")

# ── Optional sections (all collapsed) ──
with st.expander("Plan your payments"):
    p1, p2 = st.columns(2)
    with p1:
        st.markdown("**Separate bills**")
        st.markdown(
            f"Target: **R{ffs_plan.monthly_low:,}—R{ffs_plan.monthly_high:,}/mo** "
            f"over {ffs_plan.months_remaining} months"
        )
        for m in ffs_plan.milestones:
            st.caption(f"{m['milestone']} — {m['when']}")
    with p2:
        st.markdown("**NOH payment plan**")
        st.markdown(f"Deposit: **R{noh_plan['deposit_low']:,}—R{noh_plan['deposit_high']:,}**")
        st.markdown(
            f"Then **R{noh_plan['monthly_low']:,}—R{noh_plan['monthly_high']:,}/mo** "
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
            st.markdown(f"R{cr.total[0]:,}—R{cr.total[1]:,}")
            tp = calculate_noh_payment_plan(cr.total[0], cr.total[1])
            st.caption(f"~R{tp['monthly_low']:,}/mo")
    with cc[3]:
        st.markdown("**:green[NOH bundle]**")
        st.markdown(f":green[R{noh['noh_total_low']:,}—R{noh['noh_total_high']:,}]")
        st.caption(f"R{noh_plan['monthly_low']:,}/mo x {noh_plan['months']}mo")

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
