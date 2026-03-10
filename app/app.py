"""Streamlit web app for the Maternity Cost Estimator."""

import sys
import os
import pandas as pd
import streamlit as st

# Add project root to path so engine imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from engine.estimator import estimate, estimate_noh, EstimatorInput, CostBreakdown
from engine.budget_planner import calculate_savings_plan, calculate_noh_payment_plan
from engine.data_loader import load_sources
from engine.config import PROVIDER_TIERS, NOH_PRICING

# --- Page config ---
st.set_page_config(
    page_title="Maternity Cost Estimator — South Africa",
    page_icon="🍼",
    layout="wide",
)

# --- Section 1: Welcome ---
st.title("Maternity Cost Estimator")
st.markdown(
    "In South Africa's private sector, there is **no single price list** for having a baby. "
    "You receive separate bills from your hospital, obstetrician, anaesthetist, paediatrician, "
    "pathology lab, and radiology practice — typically **6-7 separate accounts** that you must "
    "research and coordinate yourself."
)
st.markdown(
    "This tool does that work for you. It assembles 250+ data points from hospital groups, "
    "specialists, and labs into a single estimate — then compares it against Network One Health's "
    "**all-inclusive global fee**, the only risk-rated maternity bundle in SA's private sector."
)
st.divider()

# --- Section 2: Sidebar inputs ---
st.sidebar.header("Your details")

region = st.sidebar.selectbox(
    "Province",
    ["Gauteng", "Western Cape", "KwaZulu-Natal", "Other"],
    help="Costs vary by region. Select the province where you plan to deliver.",
)

delivery_type = st.sidebar.selectbox(
    "Delivery preference",
    ["NVD", "CS", "Undecided"],
    format_func=lambda x: {
        "NVD": "Natural vaginal delivery (NVD)",
        "CS": "Caesarean section (CS)",
        "Undecided": "Not sure yet — show me both",
    }[x],
)

risk_level = st.sidebar.selectbox(
    "Risk level",
    ["low", "medium", "high"],
    format_func=lambda x: x.capitalize(),
    help=(
        "**Low:** Healthy pregnancy, no complications expected. 3 scans.\n\n"
        "**Medium:** Some risk factors (age, BMI, previous CS). 5 scans, extra bloods.\n\n"
        "**High:** Known complications, chronic conditions. 7 scans, extra bloods, NICU awareness."
    ),
)

st.sidebar.markdown("---")
st.sidebar.subheader("Fee-for-service options")

provider_tier = st.sidebar.selectbox(
    "Hospital group (fee-for-service)",
    ["budget", "mid-range", "premium"],
    index=1,
    format_func=lambda x: x.capitalize(),
    help=(
        "If going fee-for-service, which hospital group?\n\n"
        "**Budget:** Life Healthcare, independent hospitals.\n\n"
        "**Mid-range:** Mediclinic group.\n\n"
        "**Premium:** Netcare group."
    ),
)

wants_epidural = False
if delivery_type in ("NVD", "Undecided"):
    wants_epidural = st.sidebar.checkbox(
        "Epidural (NVD)",
        help="Epidural anaesthesia for pain relief during natural delivery. Adds anaesthetist fee.",
    )

wants_doula = st.sidebar.checkbox(
    "Doula support (fee-for-service only)",
    help="Additional birth companion. Already included in the NOH bundle.",
)

st.sidebar.markdown("---")
st.sidebar.subheader("Budget planner")

planning_mode = st.sidebar.radio(
    "Timing",
    ["Currently pregnant", "Planning ahead"],
)

if planning_mode == "Currently pregnant":
    gestational_weeks = st.sidebar.slider(
        "Current gestational weeks",
        min_value=4, max_value=40, value=12,
    )
    weeks_remaining = 40 - gestational_weeks
else:
    months_until = st.sidebar.slider(
        "Months until planned pregnancy",
        min_value=1, max_value=24, value=6,
    )
    weeks_remaining = int(months_until * 4.33) + 40

# --- Run estimates ---
inp = EstimatorInput(
    region=region,
    delivery_type=delivery_type,
    risk_level=risk_level,
    provider_tier=provider_tier,
    wants_epidural=wants_epidural,
    wants_midwife=False,
    wants_doula=wants_doula,
    gestational_weeks=gestational_weeks if planning_mode == "Currently pregnant" else 0,
)

noh = estimate_noh(inp)
ffs_result = noh["ffs_result"]


def _display_breakdown(breakdown: CostBreakdown, label: str = ""):
    """Display a cost breakdown as a table."""
    if label:
        st.subheader(label)

    rows = []
    fields = [
        ("Hospital", breakdown.hospital),
        ("Obstetrician", breakdown.obstetrician),
        ("Anaesthetist", breakdown.anaesthetist),
        ("Paediatrician", breakdown.paediatrician),
        ("Pathology", breakdown.pathology),
        ("Ultrasound", breakdown.ultrasound),
        ("Medication", breakdown.medication),
        ("Midwife", breakdown.midwife),
        ("Doula", breakdown.doula),
    ]

    for name, (low, high) in fields:
        if low > 0 or high > 0:
            rows.append({
                "Category": name,
                "Low estimate (R)": f"R {low:,}",
                "High estimate (R)": f"R {high:,}",
            })

    rows.append({
        "Category": "TOTAL",
        "Low estimate (R)": f"R {breakdown.total[0]:,}",
        "High estimate (R)": f"R {breakdown.total[1]:,}",
    })

    df = pd.DataFrame(rows)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
    )

    with st.expander("View detailed line items"):
        if breakdown.line_items:
            items_df = pd.DataFrame(breakdown.line_items)
            items_df["low"] = items_df["low"].apply(lambda x: f"R {x:,}")
            items_df["high"] = items_df["high"].apply(lambda x: f"R {x:,}")
            items_df.columns = ["Category", "Service", "Provider", "Low (R)", "High (R)"]
            st.dataframe(items_df, use_container_width=True, hide_index=True)
        else:
            st.info("No detailed items available for this estimate.")


# --- Section 3: The Comparison ---
st.header("Fee-for-service vs. NOH Maternity Bundle")

col_ffs, col_noh = st.columns(2)

# --- Left column: Fee-for-service ---
with col_ffs:
    st.subheader("Fee-for-service")
    st.markdown(
        "Each row below is a **separate provider** billing you independently. "
        "No hospital in SA gives you this total upfront — we assembled it from public data."
    )

    if isinstance(ffs_result, dict):
        tab_nvd, tab_cs = st.tabs(["NVD estimate", "CS estimate"])
        with tab_nvd:
            _display_breakdown(ffs_result["NVD"])
        with tab_cs:
            _display_breakdown(ffs_result["CS"])
        ffs_display_low = noh["ffs_total_low"]
        ffs_display_high = noh["ffs_total_high"]
    else:
        _display_breakdown(ffs_result)
        ffs_display_low = ffs_result.total[0]
        ffs_display_high = ffs_result.total[1]

    st.markdown(f"**Estimated total: R {ffs_display_low:,} — R {ffs_display_high:,}**")
    st.warning(
        "This total is an estimate we've compiled for you. In practice you'd receive "
        "**6-7 separate bills** from independent providers — hospital, obstetrician, "
        "anaesthetist, paediatrician, pathology lab, and radiology — each with their own "
        "deposit schedule, payment terms, and potential for gap payments above medical aid rates."
    )

# --- Right column: NOH Bundle ---
with col_noh:
    st.subheader("Network One Health — All-inclusive global fee")
    st.markdown("**:green[Recommended]** · South Africa's only risk-rated maternity bundle")

    st.markdown(
        "This is a **single, all-inclusive fee** — not a hospital-only quote. "
        "There are **no additional bills** from the hospital, obstetrician, anaesthetist, "
        "pathology lab, or any other provider listed below. Everything is covered."
    )

    # Single fee display
    st.metric(
        "NOH all-inclusive fee",
        f"R {noh['noh_fee_low']:,} — R {noh['noh_fee_high']:,}",
    )

    # What's included checklist
    st.markdown("**Everything included in one fee — no separate bills:**")
    for item in noh["inclusions"]:
        st.markdown(f"- :green[**+**] {item}")

    # What's not included
    st.markdown("**Not included** (added to your estimate separately):")
    for item in noh["exclusions"]:
        st.markdown(f"- {item} (R {noh['paediatrician'][0]:,} — R {noh['paediatrician'][1]:,})")

    st.divider()

    # Total with paed
    st.metric(
        "Your total (NOH bundle + paediatrician)",
        f"R {noh['noh_total_low']:,} — R {noh['noh_total_high']:,}",
    )

    # Savings callout
    if noh["savings_high"] > 0:
        st.success(
            f"**Save R {noh['savings_low']:,} — R {noh['savings_high']:,}** "
            f"vs. fee-for-service ({noh['savings_percent_low']}–{noh['savings_percent_high']}%)"
        )

    # Monthly payment
    noh_plan = calculate_noh_payment_plan(noh["noh_total_low"], noh["noh_total_high"])
    st.info(
        f"**From R {noh_plan['monthly_low']:,}/month** over {noh_plan['months']} months "
        f"(after R {noh_plan['deposit_low']:,} deposit)"
    )

    st.markdown(
        "**How this differs from hospital 'packages':** Hospital groups like Netcare, "
        "Mediclinic, and Life Healthcare may quote a facility fee, but that excludes "
        "your obstetrician, anaesthetist, pathology, and scans — you still get 5-6 "
        "separate bills. The NOH global fee covers all of these in one price, "
        "set at booking based on your clinical profile. No surprises."
    )
    st.caption("Antenatal classes included — not available fee-for-service")

# --- Section 4: Budget planner comparison ---
st.divider()
st.header("Budget planner")

col_ffs_plan, col_noh_plan = st.columns(2)

# Fee-for-service budget plan
with col_ffs_plan:
    st.subheader("Fee-for-service payments")

    ffs_plan = calculate_savings_plan(
        noh["ffs_total_low"], noh["ffs_total_high"], weeks_remaining,
    )

    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("Monthly savings target", f"R {ffs_plan.monthly_low:,} — R {ffs_plan.monthly_high:,}")
    with m2:
        st.metric("Months to save", f"{ffs_plan.months_remaining}")
    with m3:
        st.metric("Total", f"R {noh['ffs_total_low']:,} — R {noh['ffs_total_high']:,}")

    st.markdown("**Payment milestones:**")
    for m in ffs_plan.milestones:
        week_str = f" (week {m['week']})" if m["week"] else ""
        st.markdown(f"- **{m['milestone']}** — {m['when']}{week_str}: _{m['estimate']}_")

    st.caption(
        "Multiple lump-sum payments to different providers at different times. "
        "Each provider sets their own deposit and payment schedule independently."
    )

# NOH payment plan
with col_noh_plan:
    st.subheader("NOH payment plan")

    noh_plan = calculate_noh_payment_plan(noh["noh_total_low"], noh["noh_total_high"])

    n1, n2, n3 = st.columns(3)
    with n1:
        st.metric("Monthly payment", f"R {noh_plan['monthly_low']:,} — R {noh_plan['monthly_high']:,}")
    with n2:
        st.metric("Deposit (10%)", f"R {noh_plan['deposit_low']:,} — R {noh_plan['deposit_high']:,}")
    with n3:
        st.metric("Over", f"{noh_plan['months']} months")

    st.markdown("**Simple payment schedule:**")
    st.markdown(f"1. **Deposit** at booking: R {noh_plan['deposit_low']:,} — R {noh_plan['deposit_high']:,}")
    st.markdown(f"2. **Monthly instalments** x{noh_plan['months']}: R {noh_plan['monthly_low']:,} — R {noh_plan['monthly_high']:,}/month")
    st.markdown("3. **No surprise bills** — everything covered in the bundle")

    st.caption(
        "One fixed monthly payment to one provider. No separate deposits to "
        "hospital, OB, or anaesthetist. No coordination needed."
    )

# --- Section 5: Compare tiers ---
st.divider()
st.header("Compare all options")

compare_cols = st.columns(4)
tiers = ["budget", "mid-range", "premium"]
tier_labels = ["FFS Budget", "FFS Mid-range", "FFS Premium"]
tier_examples = {
    "budget": "Life Healthcare",
    "mid-range": "Mediclinic",
    "premium": "Netcare",
}

for i, (tier, label) in enumerate(zip(tiers, tier_labels)):
    with compare_cols[i]:
        st.subheader(label)
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
        st.metric("Low", f"R {compare_result.total[0]:,}")
        st.metric("High", f"R {compare_result.total[1]:,}")

        tier_plan = calculate_noh_payment_plan(compare_result.total[0], compare_result.total[1])
        st.caption(f"~R {tier_plan['monthly_low']:,}—R {tier_plan['monthly_high']:,}/mo if spread over 12 months")
        st.caption("Assembled estimate — paid as 6-7 separate bills")

# NOH column in comparison
with compare_cols[3]:
    st.subheader(":green[NOH Bundle]")
    st.markdown("**:green[Recommended]**")
    st.metric("Low", f"R {noh['noh_total_low']:,}")
    st.metric("High", f"R {noh['noh_total_high']:,}")
    st.caption(f"R {noh_plan['monthly_low']:,}—R {noh_plan['monthly_high']:,}/mo over {noh_plan['months']} months")
    st.caption("All-inclusive global fee: hospital, OB, anaesthetist, scans, bloods, doula, classes — no separate bills")

# --- Section 6: Lead capture ---
st.divider()
st.header("Get started with Network One Health")

st.markdown(
    "Want a **personalised quote** from Network One Health? "
    "Fill in your details and we'll be in touch."
)

with st.form("noh_lead_form"):
    lc1, lc2 = st.columns(2)
    with lc1:
        lead_name = st.text_input("Name")
        lead_email = st.text_input("Email")
    with lc2:
        lead_phone = st.text_input("Phone (optional)")
        lead_province = st.selectbox(
            "Province",
            ["Gauteng", "Western Cape", "KwaZulu-Natal", "Other"],
            key="lead_province",
        )
    lead_weeks = st.slider(
        "Current gestational weeks (0 = planning)",
        min_value=0, max_value=40, value=0,
        key="lead_weeks",
    )

    submitted = st.form_submit_button("Request a quote")
    if submitted:
        if lead_name and lead_email:
            # Save lead to Supabase
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
                        "gestational_weeks": lead_weeks,
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
                    f"Thank you, {lead_name}! Your details have been sent to "
                    "Network One Health. We'll be in touch at "
                    f"{lead_email} with a personalised quote."
                )
            else:
                st.success(
                    f"Thank you, {lead_name}! We'll be in touch at {lead_email} "
                    "with a personalised quote from Network One Health."
                )
        else:
            st.warning("Please enter your name and email.")

st.caption("Or explore the fee-for-service breakdown in detail using the sidebar options above.")

# --- Section 7: Sources ---
st.divider()
st.header("Data sources")
with st.expander("View all data sources"):
    try:
        sources_df = load_sources()
        for _, row in sources_df.iterrows():
            url = row.get("url", "")
            name = row.get("source_name", "Unknown")
            year = row.get("data_year", "")
            reliability = row.get("reliability", "")
            notes = row.get("notes", "")
            st.markdown(f"- [{name}]({url}) ({year}, {reliability}) — {notes}")
    except Exception:
        st.info("Source data not available.")

st.divider()
st.caption(
    "Disclaimer: These estimates are based on publicly available 2024-2026 pricing data. "
    "Actual costs may vary. This tool is for planning purposes only — confirm fees directly "
    "with your healthcare providers."
)
