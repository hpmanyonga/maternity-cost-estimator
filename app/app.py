"""Streamlit web app for the Maternity Cost Estimator."""

import sys
import os
import pandas as pd
import streamlit as st

# Add project root to path so engine imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from engine.estimator import estimate, EstimatorInput, CostBreakdown
from engine.budget_planner import calculate_savings_plan
from engine.data_loader import load_sources
from engine.config import PROVIDER_TIERS

# --- Page config ---
st.set_page_config(
    page_title="Maternity Cost Estimator — South Africa",
    page_icon="🍼",
    layout="wide",
)

# --- Welcome ---
st.title("Maternity Cost Estimator")
st.markdown(
    "Estimate the cost of having a baby in a **South African private hospital**. "
    "Based on 250+ data points from hospital groups, specialists, and pathology labs."
)
st.divider()

# --- Sidebar: Your Details ---
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

provider_tier = st.sidebar.selectbox(
    "Provider tier",
    ["budget", "mid-range", "premium"],
    index=1,
    format_func=lambda x: x.capitalize(),
    help=(
        "**Budget:** Life Healthcare, independent hospitals.\n\n"
        "**Mid-range:** Mediclinic group.\n\n"
        "**Premium:** Netcare group."
    ),
)

st.sidebar.markdown("---")
st.sidebar.subheader("Optional add-ons")

wants_epidural = False
if delivery_type in ("NVD", "Undecided"):
    wants_epidural = st.sidebar.checkbox(
        "Epidural (NVD)",
        help="Epidural anaesthesia for pain relief during natural delivery. Adds anaesthetist fee.",
    )

wants_midwife = st.sidebar.checkbox(
    "Midwife-led birth",
    help="Replaces hospital + obstetrician with a midwife-led package. Usually lower cost.",
)

wants_doula = st.sidebar.checkbox(
    "Doula support",
    help="Additional birth companion for emotional and physical support during labour.",
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
    weeks_remaining = int(months_until * 4.33) + 40  # months before + 40 weeks pregnancy

# --- Run estimate ---
inp = EstimatorInput(
    region=region,
    delivery_type=delivery_type,
    risk_level=risk_level,
    provider_tier=provider_tier,
    wants_epidural=wants_epidural,
    wants_midwife=wants_midwife,
    wants_doula=wants_doula,
    gestational_weeks=gestational_weeks if planning_mode == "Currently pregnant" else 0,
)

result = estimate(inp)


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

    # Detailed line items
    with st.expander("View detailed line items"):
        if breakdown.line_items:
            items_df = pd.DataFrame(breakdown.line_items)
            items_df["low"] = items_df["low"].apply(lambda x: f"R {x:,}")
            items_df["high"] = items_df["high"].apply(lambda x: f"R {x:,}")
            items_df.columns = ["Category", "Service", "Provider", "Low (R)", "High (R)"]
            st.dataframe(items_df, use_container_width=True, hide_index=True)
        else:
            st.info("No detailed items available for this estimate.")


# --- Cost Breakdown ---
st.header("Cost breakdown")

if isinstance(result, dict):
    # Undecided — show both NVD and CS
    col1, col2 = st.columns(2)
    with col1:
        _display_breakdown(result["NVD"], "Natural vaginal delivery (NVD)")
    with col2:
        _display_breakdown(result["CS"], "Caesarean section (CS)")
    # Use the higher estimate for budget planning
    budget_total_low = max(result["NVD"].total[0], result["CS"].total[0])
    budget_total_high = max(result["NVD"].total[1], result["CS"].total[1])
else:
    _display_breakdown(result)
    budget_total_low = result.total[0]
    budget_total_high = result.total[1]

# --- Budget Planner ---
st.header("Budget planner")

plan = calculate_savings_plan(budget_total_low, budget_total_high, weeks_remaining)

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Monthly savings target (low)", f"R {plan.monthly_low:,}")
with col2:
    st.metric("Monthly savings target (high)", f"R {plan.monthly_high:,}")
with col3:
    st.metric("Months to save", f"{plan.months_remaining}")

st.subheader("Payment milestones")
for m in plan.milestones:
    week_str = f" (week {m['week']})" if m["week"] else ""
    st.markdown(f"- **{m['milestone']}** — {m['when']}{week_str}: _{m['estimate']}_")

# --- Compare ---
st.header("Compare provider tiers")

compare_cols = st.columns(3)
tiers = ["budget", "mid-range", "premium"]
tier_labels = ["Budget", "Mid-range", "Premium"]
tier_examples = {
    "budget": "Life Healthcare, independent hospitals",
    "mid-range": "Mediclinic group",
    "premium": "Netcare group",
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
            wants_midwife=wants_midwife,
            wants_doula=wants_doula,
        )
        compare_result = estimate(compare_inp)
        if isinstance(compare_result, dict):
            compare_result = compare_result.get("NVD", list(compare_result.values())[0])
        st.metric("Low", f"R {compare_result.total[0]:,}")
        st.metric("High", f"R {compare_result.total[1]:,}")

# --- Sources ---
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
