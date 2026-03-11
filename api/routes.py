"""API route handlers wrapping the estimation engine."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from engine.estimator import estimate, estimate_noh, EstimatorInput, CostBreakdown
from engine.budget_planner import calculate_savings_plan, calculate_noh_payment_plan
from engine.data_loader import load_sources, _get_supabase

from api.schemas import (
    EstimateRequest, EstimateResponse, CostBreakdownResponse,
    CostRange, LineItem, PaymentPlan, SavingsPlanResponse,
    TierComparison, FFSEstimateResponse,
    LeadRequest, LeadResponse,
    SourcesResponse, SourceEntry,
)

router = APIRouter(prefix="/api")


def _breakdown_to_response(bd: CostBreakdown) -> CostBreakdownResponse:
    """Convert engine CostBreakdown dataclass to API response model."""
    return CostBreakdownResponse(
        hospital=CostRange(low=bd.hospital[0], high=bd.hospital[1]),
        obstetrician=CostRange(low=bd.obstetrician[0], high=bd.obstetrician[1]),
        anaesthetist=CostRange(low=bd.anaesthetist[0], high=bd.anaesthetist[1]),
        paediatrician=CostRange(low=bd.paediatrician[0], high=bd.paediatrician[1]),
        pathology=CostRange(low=bd.pathology[0], high=bd.pathology[1]),
        ultrasound=CostRange(low=bd.ultrasound[0], high=bd.ultrasound[1]),
        medication=CostRange(low=bd.medication[0], high=bd.medication[1]),
        midwife=CostRange(low=bd.midwife[0], high=bd.midwife[1]),
        doula=CostRange(low=bd.doula[0], high=bd.doula[1]),
        total=CostRange(low=bd.total[0], high=bd.total[1]),
        line_items=[LineItem(**item) for item in bd.line_items],
    )


def _calc_weeks_remaining(req: EstimateRequest) -> int:
    """Calculate weeks remaining until due date."""
    if req.gestational_weeks > 0:
        return 40 - req.gestational_weeks
    if req.planning_months > 0:
        return int(req.planning_months * 4.33) + 40
    return 40


def _calc_noh_instalment_months(req: EstimateRequest) -> int:
    """NOH instalments run from one month after booking to 34 weeks."""
    if req.gestational_weeks > 0:
        weeks_to_34 = max(0, 34 - req.gestational_weeks)
        months = max(1, round(weeks_to_34 / 4.33))
    else:
        # Planning ahead — assume booking at ~8 weeks, paying to 34 weeks
        months = round((34 - 8) / 4.33)  # ~6 months
    return months


@router.post("/estimate", response_model=EstimateResponse)
def api_estimate(req: EstimateRequest):
    """Full NOH vs FFS comparison — main endpoint."""
    inp = EstimatorInput(
        region=req.region,
        delivery_type=req.delivery_type,
        risk_level=req.risk_level,
        provider_tier=req.provider_tier,
        wants_epidural=req.wants_epidural,
        wants_midwife=False,
        wants_doula=req.wants_doula,
        gestational_weeks=req.gestational_weeks,
    )

    noh = estimate_noh(inp)
    ffs_result = noh["ffs_result"]
    is_undecided = isinstance(ffs_result, dict)

    # Convert FFS breakdown(s)
    if is_undecided:
        ffs = {k: _breakdown_to_response(v) for k, v in ffs_result.items()}
    else:
        ffs = _breakdown_to_response(ffs_result)

    # Payment plans
    weeks_remaining = _calc_weeks_remaining(req)
    noh_months = _calc_noh_instalment_months(req)
    noh_plan = calculate_noh_payment_plan(noh["noh_total_low"], noh["noh_total_high"], months=noh_months)
    ffs_plan = calculate_savings_plan(noh["ffs_total_low"], noh["ffs_total_high"], weeks_remaining)

    return EstimateResponse(
        ffs=ffs,
        ffs_total=CostRange(low=noh["ffs_total_low"], high=noh["ffs_total_high"]),
        is_undecided=is_undecided,
        noh_fee=CostRange(low=noh["noh_fee_low"], high=noh["noh_fee_high"]),
        noh_total=CostRange(low=noh["noh_total_low"], high=noh["noh_total_high"]),
        paediatrician=CostRange(low=noh["paediatrician"][0], high=noh["paediatrician"][1]),
        savings=CostRange(low=noh["savings_low"], high=noh["savings_high"]),
        savings_percent=CostRange(low=noh["savings_percent_low"], high=noh["savings_percent_high"]),
        inclusions=noh["inclusions"],
        exclusions=noh["exclusions"],
        noh_payment_plan=PaymentPlan(**noh_plan),
        ffs_savings_plan=SavingsPlanResponse(
            monthly_low=ffs_plan.monthly_low,
            monthly_high=ffs_plan.monthly_high,
            months_remaining=ffs_plan.months_remaining,
            milestones=ffs_plan.milestones,
            total_low=ffs_plan.total_low,
            total_high=ffs_plan.total_high,
        ),
        tier_comparison=[],
    )


@router.post("/estimate/ffs", response_model=FFSEstimateResponse)
def api_estimate_ffs(req: EstimateRequest):
    """FFS-only estimate for a specific tier."""
    inp = EstimatorInput(
        region=req.region,
        delivery_type=req.delivery_type if req.delivery_type != "Undecided" else "NVD",
        risk_level=req.risk_level,
        provider_tier=req.provider_tier,
        wants_epidural=req.wants_epidural,
        wants_midwife=False,
        wants_doula=req.wants_doula,
        gestational_weeks=req.gestational_weeks,
    )
    result = estimate(inp)
    if isinstance(result, dict):
        result = result.get("NVD", list(result.values())[0])
    bd = _breakdown_to_response(result)
    return FFSEstimateResponse(
        breakdown=bd,
        total=CostRange(low=result.total[0], high=result.total[1]),
    )


@router.post("/lead", response_model=LeadResponse)
def api_save_lead(req: LeadRequest):
    """Save a lead to the Supabase leads table."""
    sb = _get_supabase()
    if not sb:
        return LeadResponse(
            success=True,
            message=f"Thank you, {req.name}! We'll be in touch at {req.email} with a personalised quote.",
        )
    try:
        sb.table("leads").insert({
            "name": req.name,
            "email": req.email,
            "phone": req.phone,
            "province": req.province,
            "gestational_weeks": req.gestational_weeks,
            "delivery_preference": req.delivery_preference,
            "risk_level": req.risk_level,
            "noh_estimate_low": req.noh_estimate_low,
            "noh_estimate_high": req.noh_estimate_high,
            "ffs_estimate_low": req.ffs_estimate_low,
            "ffs_estimate_high": req.ffs_estimate_high,
        }).execute()
    except Exception:
        pass

    return LeadResponse(
        success=True,
        message=f"Thank you, {req.name}! Your details have been sent to Network One Health. We'll be in touch at {req.email} with a personalised quote.",
    )


@router.get("/sources", response_model=SourcesResponse)
def api_sources():
    """Return data sources for the credibility section."""
    df = load_sources()
    sources = []
    for _, row in df.iterrows():
        sources.append(SourceEntry(
            source_id=str(row.get("source_id", "")),
            source_name=str(row.get("source_name", "Unknown")),
            url=str(row.get("url", "")) or None,
            date_accessed=str(row.get("date_accessed", "")) or None,
            data_year=str(row.get("data_year", "")) or None,
            reliability=str(row.get("reliability", "")) or None,
            notes=str(row.get("notes", "")) or None,
        ))
    return SourcesResponse(sources=sources, count=len(sources))


@router.get("/health")
def api_health():
    """Health check — no data loading."""
    return {"status": "ok"}
