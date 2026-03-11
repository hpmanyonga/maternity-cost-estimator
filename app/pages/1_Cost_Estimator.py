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


# ── Helpers ──
def _show_breakdown(breakdown: CostBreakdown):
    """Render a cost breakdown as a clean table."""
    labels = {
        "hospital": "Hospital",
        "obstetrician": "Obstetrician",
        "anaesthetist": "Anaesthetist",
        "paediatrician": "Paediatrician (newborn check)",
        "pathology": "Blood tests and lab tests",
        "ultrasound": "Scans",
        "medication": "Medicines",
        "midwife": "Midwife",
        "doula": "Doula",
    }
    rows = []
    for attr, label in labels.items():
        low, high = getattr(breakdown, attr)
        if low > 0 or high > 0:
            rows.append({"Service": label, "Low (R)": f"R {low:,}", "High (R)": f"R {high:,}"})

    rows.append({
        "Service": "TOTAL",
        "Low (R)": f"R {breakdown.total[0]:,}",
        "High (R)": f"R {breakdown.total[1]:,}",
    })

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ── Hide sidebar on this public page ──
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] { display: none; }
    [data-testid="stSidebarCollapsedControl"] { display: none; }
    .block-container { max-width: 1100px; padding-top: 2rem; }
    .noh-result-card {
        border: 2px solid #10b981;
        border-radius: 16px;
        padding: 24px;
        background: linear-gradient(135deg, #f0fdf4 0%, #ffffff 100%);
        position: sticky;
        top: 3.5rem;
    }
    .noh-price-big {
        font-size: 1.6rem;
        font-weight: 700;
        color: #102a43;
        margin: 0.15rem 0;
    }
    .noh-price-label {
        font-size: 0.85rem;
        color: #486581;
        margin: 0;
        text-transform: uppercase;
        letter-spacing: 0.03em;
    }
    .noh-savings {
        font-size: 1.1rem;
        font-weight: 600;
        color: #059669;
        margin: 0.3rem 0;
    }
    .noh-monthly {
        font-size: 1rem;
        color: #102a43;
        margin: 0.2rem 0;
    }
    .noh-card-section {
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 18px 20px;
        background: #fff;
    }
    .noh-trust {
        font-size: 0.85rem;
        color: #64748b;
        line-height: 1.5;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Top bar ──
top_left, top_right = st.columns([5, 1])
with top_left:
    st.markdown("## Maternity Cost Estimator")
    st.markdown(
        "Estimate what private maternity care could cost, then compare "
        "separate bills with the NOH all-in-one bundle."
    )
with top_right:
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=90)

st.markdown(
    '<p class="noh-trust">Based on published South African private-sector pricing. '
    "Final quote depends on your hospital, doctor, and clinical needs.</p>",
    unsafe_allow_html=True,
)

# ── Inputs + Result card (two-column hero) ──
input_col, spacer, result_col = st.columns([1.1, 0.05, 0.85])

with input_col:
    region = st.selectbox(
        "Where will you deliver?",
        ["Gauteng", "Western Cape", "KwaZulu-Natal", "Other"],
        help="Costs vary by province.",
    )

    delivery_labels = {
        "NVD": "Vaginal birth",
        "CS": "Planned caesarean",
        "Undecided": "Not sure yet",
    }
    delivery_type = st.segmented_control(
        "Planned birth type",
        options=list(delivery_labels.keys()),
        format_func=lambda x: delivery_labels[x],
        default="Undecided",
    )

    risk_level = st.selectbox(
        "Care complexity",
        ["low", "medium", "high"],
        format_func=lambda x: x.capitalize(),
        help=(
            "**Low** = routine pregnancy, no complications expected.\n\n"
            "**Medium** = extra scans or monitoring needed.\n\n"
            "**High** = more medical complexity (chronic conditions, twins, etc.)."
        ),
    )

    provider_tier = st.selectbox(
        "Hospital price level",
        ["budget", "mid-range", "premium"],
        index=1,
        format_func=lambda x: x.capitalize(),
        help=(
            "**Budget** — Life Healthcare, independent hospitals.\n\n"
            "**Mid-range** — Mediclinic.\n\n"
            "**Premium** — Netcare."
        ),
    )

    opts_left, opts_right = st.columns(2)
    with opts_left:
        wants_epidural = False
        if delivery_type in ("NVD", "Undecided"):
            wants_epidural = st.checkbox(
                "Epidural during labour",
                help="Pain relief during vaginal birth. Adds anaesthetist fee.",
            )
    with opts_right:
        wants_doula = st.checkbox(
            "Doula support",
            help="Already included in the NOH bundle.",
        )

    timing_choice = st.segmented_control(
        "Are you pregnant now?",
        options=["Pregnant now", "Planning pregnancy"],
        default="Pregnant now",
    )

    gestation_group = "Under 12 weeks"
    gestational_weeks = 0
    weeks_remaining = 40

    if timing_choice == "Pregnant now":
        gestation_group = st.select_slider(
            "How far along are you?",
            options=["Under 12 weeks", "12 to 20 weeks", "20 to 28 weeks", "28+ weeks"],
            value="Under 12 weeks",
        )
        week_map = {
            "Under 12 weeks": 8,
            "12 to 20 weeks": 16,
            "20 to 28 weeks": 24,
            "28+ weeks": 32,
        }
        gestational_weeks = week_map[gestation_group]
        weeks_remaining = 40 - gestational_weeks
    else:
        weeks_remaining = 40 + 24

# ── Run estimates ──
inp = EstimatorInput(
    region=region,
    delivery_type=delivery_type,
    risk_level=risk_level,
    provider_tier=provider_tier,
    wants_epidural=wants_epidural,
    wants_midwife=False,
    wants_doula=wants_doula,
    gestational_weeks=gestational_weeks,
)

noh = estimate_noh(inp)
ffs_result = noh["ffs_result"]

if isinstance(ffs_result, dict):
    ffs_display_low = noh["ffs_total_low"]
    ffs_display_high = noh["ffs_total_high"]
else:
    ffs_display_low = ffs_result.total[0]
    ffs_display_high = ffs_result.total[1]

noh_plan = calculate_noh_payment_plan(noh["noh_total_low"], noh["noh_total_high"])

# ── Sticky result card ──
with result_col:
    st.markdown('<div class="noh-result-card">', unsafe_allow_html=True)

    st.markdown("**Your estimate**")

    st.markdown('<p class="noh-price-label">Separate bills</p>', unsafe_allow_html=True)
    st.markdown(
        f'<p class="noh-price-big">R {ffs_display_low:,.0f} — R {ffs_display_high:,.0f}</p>',
        unsafe_allow_html=True,
    )

    st.markdown('<p class="noh-price-label">NOH all-in-one bundle</p>', unsafe_allow_html=True)
    st.markdown(
        f'<p class="noh-price-big" style="color:#059669">'
        f"R {noh['noh_total_low']:,.0f} — R {noh['noh_total_high']:,.0f}</p>",
        unsafe_allow_html=True,
    )

    if noh["savings_high"] > 0:
        st.markdown(
            f'<p class="noh-savings">You could save up to R {noh["savings_high"]:,.0f}</p>',
            unsafe_allow_html=True,
        )

    st.markdown(
        f'<p class="noh-monthly">From <strong>R {noh_plan["monthly_low"]:,}/month</strong> '
        f'over {noh_plan["months"]} months</p>',
        unsafe_allow_html=True,
    )

    st.markdown("")

    st.markdown(
        '<a href="#get-your-personalised-quote" style="display:block;text-align:center;'
        "background:#059669;color:white;padding:0.6rem 1rem;border-radius:8px;"
        'text-decoration:none;font-weight:600;margin-top:0.5rem;">Request my quote</a>',
        unsafe_allow_html=True,
    )

    st.caption("See what's included below")

    st.markdown("</div>", unsafe_allow_html=True)

# ── Comparison: Separate bills vs NOH bundle ──
st.markdown("")
st.markdown("---")
st.markdown("### Separate bills vs NOH bundle")

card_left, card_right = st.columns(2)

with card_left:
    st.markdown('<div class="noh-card-section">', unsafe_allow_html=True)
    st.markdown("**Separate bills**")
    st.markdown(
        "- Hospital facility\n"
        "- Obstetrician\n"
        "- Anaesthetist\n"
        "- Blood tests and scans\n"
        "- Medicines\n"
        "- Paid to different providers"
    )
    st.markdown(
        f"**R {ffs_display_low:,.0f} — R {ffs_display_high:,.0f}**"
    )
    st.markdown("</div>", unsafe_allow_html=True)

with card_right:
    st.markdown('<div class="noh-card-section" style="border-color:#10b981">', unsafe_allow_html=True)
    st.markdown("**NOH bundle** :green[Recommended]")
    st.markdown(
        "- One combined fee\n"
        "- Antenatal visits\n"
        "- Delivery care\n"
        "- Anaesthetist\n"
        "- Scans and blood tests\n"
        "- Fewer billing surprises"
    )
    st.markdown(
        f"**:green[R {noh['noh_total_low']:,.0f} — R {noh['noh_total_high']:,.0f}]**"
    )
    st.markdown("</div>", unsafe_allow_html=True)

# ── Cost breakdown (accordion) ──
with st.expander("See cost breakdown"):
    st.markdown(
        f"**Separate bills total: R {ffs_display_low:,.0f} — R {ffs_display_high:,.0f}**"
    )
    if isinstance(ffs_result, dict):
        tab_vaginal, tab_cs = st.tabs(["Vaginal birth", "Planned caesarean"])
        with tab_vaginal:
            _show_breakdown(ffs_result["NVD"])
        with tab_cs:
            _show_breakdown(ffs_result["CS"])
    else:
        _show_breakdown(ffs_result)

# ── Why separate bills feel unpredictable ──
st.info(
    "**Why separate bills feel unpredictable**\n\n"
    "- Different providers bill separately\n"
    "- Deposits and payment dates vary\n"
    "- Final gaps depend on your cover and care needs"
)

# ── Quote form (moved up) ──
st.markdown("---")
st.markdown("### Get your personalised quote")
st.markdown("We'll review your details and send you a tailored estimate.")

with st.form("noh_lead_form"):
    fc1, fc2 = st.columns(2)
    with fc1:
        lead_name = st.text_input("Name")
        lead_email = st.text_input("Email")
    with fc2:
        lead_phone = st.text_input("Phone")
        lead_province = st.selectbox(
            "Province",
            ["Gauteng", "Western Cape", "KwaZulu-Natal", "Other"],
            key="lead_province",
        )

    lead_timing = st.selectbox(
        "Pregnancy timing",
        ["Planning pregnancy", "Under 12 weeks", "12 to 20 weeks", "20 to 28 weeks", "28+ weeks"],
    )

    submitted = st.form_submit_button("Request my quote", type="primary")
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
                        "province": lead_province,
                        "gestational_weeks": gestational_weeks,
                        "delivery_preference": delivery_type,
                        "risk_level": risk_level,
                        "noh_estimate_low": noh["noh_total_low"],
                        "noh_estimate_high": noh["noh_total_high"],
                        "ffs_estimate_low": noh["ffs_total_low"],
                        "ffs_estimate_high": noh["ffs_total_high"],
                    }).execute()
                    lead_saved = True
                except Exception:
                    pass
            if lead_saved:
                st.success(
                    f"Thanks, {lead_name}! Your details have been sent to "
                    f"Network One Health. We'll contact you at {lead_email}."
                )
            else:
                st.success(
                    f"Thanks, {lead_name}! We'll be in touch at {lead_email} "
                    "with a personalised quote."
                )
        else:
            st.warning("Please enter your name and email.")

# ── Plan your payments (collapsed) ──
with st.expander("Plan your payments"):
    pay_left, pay_right = st.columns(2)

    with pay_left:
        st.markdown("**Separate bills**")
        ffs_plan = calculate_savings_plan(
            noh["ffs_total_low"], noh["ffs_total_high"], weeks_remaining,
        )
        st.markdown(
            f"Save **R {ffs_plan.monthly_low:,} — R {ffs_plan.monthly_high:,}/month** "
            f"over {ffs_plan.months_remaining} months"
        )
        st.markdown("**Payment milestones:**")
        for m in ffs_plan.milestones:
            st.markdown(f"- **{m['milestone']}** — {m['when']}")
        st.caption("Multiple payments to different providers at different times.")

    with pay_right:
        st.markdown("**NOH payment plan**")
        st.markdown(
            f"Deposit (10%): **R {noh_plan['deposit_low']:,} — R {noh_plan['deposit_high']:,}**"
        )
        st.markdown(
            f"Then **R {noh_plan['monthly_low']:,} — R {noh_plan['monthly_high']:,}/month** "
            f"for {noh_plan['months']} months"
        )
        st.caption("One fixed payment to one provider. No separate deposits.")

# ── Compare hospital pricing scenarios (collapsed) ──
with st.expander("Compare hospital pricing scenarios"):
    tiers = ["budget", "mid-range", "premium"]
    tier_labels = ["Budget hospitals", "Mid-range hospitals", "Premium hospitals"]
    tier_examples = {
        "budget": "Life Healthcare",
        "mid-range": "Mediclinic",
        "premium": "Netcare",
    }

    compare_cols = st.columns(4)
    for i, (tier, label) in enumerate(zip(tiers, tier_labels)):
        with compare_cols[i]:
            st.markdown(f"**{label}**")
            st.caption(tier_examples[tier])
            compare_inp = EstimatorInput(
                region=region,
                delivery_type=delivery_type if delivery_type != "Undecided" else "NVD",
                risk_level=risk_level,
                provider_tier=tier,
                wants_epidural=wants_epidural,
                wants_midwife=False,
                wants_doula=wants_doula,
            )
            compare_result = estimate(compare_inp)
            if isinstance(compare_result, dict):
                compare_result = compare_result.get("NVD", list(compare_result.values())[0])
            st.markdown(f"**R {compare_result.total[0]:,} — R {compare_result.total[1]:,}**")
            tier_plan = calculate_noh_payment_plan(compare_result.total[0], compare_result.total[1])
            st.caption(f"~R {tier_plan['monthly_low']:,}—R {tier_plan['monthly_high']:,}/mo")
            st.caption("Paid as 6-7 separate bills")

    with compare_cols[3]:
        st.markdown("**:green[NOH bundle]**")
        st.caption("Recommended")
        st.markdown(
            f"**:green[R {noh['noh_total_low']:,} — R {noh['noh_total_high']:,}]**"
        )
        st.caption(
            f"R {noh_plan['monthly_low']:,}—R {noh_plan['monthly_high']:,}/mo "
            f"over {noh_plan['months']} months"
        )
        st.caption("All-inclusive — no separate bills")

# ── Methodology (collapsed) ──
with st.expander("How we estimate"):
    st.markdown(
        "Based on **250+ published data points** from Netcare, Mediclinic, Life Healthcare, "
        "independent hospitals, specialist practices, pathology labs, and radiology groups."
    )
    st.caption("Last updated: March 2026. Sources verified against published 2025-2026 pricing.")

    st.markdown("**Why your final quote may differ:**")
    st.markdown(
        "- Hospital choice\n"
        "- Doctor fees\n"
        "- Medical aid rules\n"
        "- Clinical complexity\n"
        "- Unplanned changes during care"
    )

    try:
        sources_df = load_sources()
        st.markdown("**Source list:**")
        for _, row in sources_df.iterrows():
            url = row.get("url", "")
            name = row.get("source_name", "Unknown")
            year = row.get("data_year", "")
            if url:
                st.markdown(f"- [{name}]({url}) ({year})")
            else:
                st.markdown(f"- {name} ({year})")
    except Exception:
        st.caption("Source data not available.")

# ── Footer ──
st.markdown("---")
st.caption(
    "These estimates are for planning purposes only. Actual costs depend on your "
    "clinical profile, hospital, and specialist. Confirm fees directly with your providers."
)
st.caption("Network One Health · Info@networkonehealth.co.za · 011 458 2497")
