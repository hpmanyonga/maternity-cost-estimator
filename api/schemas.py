"""Pydantic request/response models for the estimator API."""

from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Union


class EstimateRequest(BaseModel):
    region: str = Field("Gauteng", pattern="^(Gauteng|Western Cape|KwaZulu-Natal|Other)$")
    delivery_type: str = Field("NVD", pattern="^(NVD|CS|Undecided)$")
    risk_level: str = Field("low", pattern="^(low|medium|high)$")
    provider_tier: str = Field("mid-range", pattern="^(budget|mid-range|premium)$")
    wants_epidural: bool = False
    wants_doula: bool = False
    gestational_weeks: int = Field(0, ge=0, le=40)
    planning_months: int = Field(0, ge=0, le=24)


class CostRange(BaseModel):
    low: int
    high: int


class LineItem(BaseModel):
    category: str
    service: str
    provider: str
    low: int
    high: int


class CostBreakdownResponse(BaseModel):
    hospital: CostRange
    obstetrician: CostRange
    anaesthetist: CostRange
    paediatrician: CostRange
    pathology: CostRange
    ultrasound: CostRange
    medication: CostRange
    midwife: CostRange
    doula: CostRange
    total: CostRange
    line_items: List[LineItem]


class PaymentPlan(BaseModel):
    deposit_low: int
    deposit_high: int
    monthly_low: int
    monthly_high: int
    months: int


class SavingsPlanResponse(BaseModel):
    monthly_low: int
    monthly_high: int
    months_remaining: float
    milestones: List[dict]
    total_low: int
    total_high: int


class TierComparison(BaseModel):
    tier: str
    label: str
    example: str
    total: CostRange
    monthly: CostRange
    description: str


class EstimateResponse(BaseModel):
    """Full response combining FFS breakdown, NOH comparison, budget plans, and tier comparison."""
    # FFS breakdown (NVD or CS or both if Undecided)
    ffs: Union[Dict[str, CostBreakdownResponse], CostBreakdownResponse]
    ffs_total: CostRange
    is_undecided: bool

    # NOH bundle
    noh_fee: CostRange
    noh_total: CostRange
    paediatrician: CostRange
    savings: CostRange
    savings_percent: CostRange
    inclusions: List[str]
    exclusions: List[str]

    # Payment plans
    noh_payment_plan: PaymentPlan
    ffs_savings_plan: SavingsPlanResponse

    # Tier comparison
    tier_comparison: List[TierComparison]


class FFSEstimateResponse(BaseModel):
    """FFS-only estimate for a specific tier."""
    breakdown: CostBreakdownResponse
    total: CostRange


class LeadRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    email: str = Field(..., min_length=3, max_length=200)
    phone: Optional[str] = None
    province: str = Field("Gauteng", pattern="^(Gauteng|Western Cape|KwaZulu-Natal|Other)$")
    gestational_weeks: int = Field(0, ge=0, le=40)
    delivery_preference: str = Field("Undecided", pattern="^(NVD|CS|Undecided)$")
    risk_level: str = Field("low", pattern="^(low|medium|high)$")
    noh_estimate_low: Optional[int] = None
    noh_estimate_high: Optional[int] = None
    ffs_estimate_low: Optional[int] = None
    ffs_estimate_high: Optional[int] = None


class LeadResponse(BaseModel):
    success: bool
    message: str


class SourceEntry(BaseModel):
    source_id: Optional[str] = None
    source_name: str
    url: Optional[str] = None
    date_accessed: Optional[str] = None
    data_year: Optional[str] = None
    reliability: Optional[str] = None
    notes: Optional[str] = None


class SourcesResponse(BaseModel):
    sources: List[SourceEntry]
    count: int
