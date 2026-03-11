from pathlib import Path
from engine.models import PatientProfile, PricingResult
from engine.config import (
    DISCOVERY_GLOBAL_FEES,
    DISCOVERY_STAGE_PROPORTIONS,
    DISCOVERY_ANTN1B_DISCOUNT,
    DISCOVERY_RISK_ADDONS,
    DISCOVERY_CONSULT_FEE,
    DISCOVERY_SCAN_FEE,
    DISCOVERY_CS_ADDON,
    DISCOVERY_CHRONIC_EXTRA_CONSULTS,
    DISCOVERY_COMPLICATION_EXTRA_CONSULTS,
    DISCOVERY_COMPLICATION_EXTRA_SCANS,
    PRIVATE_ROOM_FEE,
)
from engine.rules import (
    compute_stage_amounts,
    compute_risk_addon,
    compute_chronic_addon,
    compute_complication_addon,
    compute_cs_addon,
    compute_private_room_addon,
    sum_addons,
)


class PricingEngine:
    """
    Discovery-aligned pricing engine for maternity care.
    Uses plan-based global fees with additive risk/chronic/complication loadings.
    All constants imported from engine.config (single source of truth).
    """

    GLOBAL_FEES = DISCOVERY_GLOBAL_FEES
    STAGE_PROPORTIONS = DISCOVERY_STAGE_PROPORTIONS
    ANTN1B_DISCOUNT = DISCOVERY_ANTN1B_DISCOUNT
    RISK_ADDONS = DISCOVERY_RISK_ADDONS
    CONSULT_FEE = DISCOVERY_CONSULT_FEE
    SCAN_FEE = DISCOVERY_SCAN_FEE
    CS_ADDON = DISCOVERY_CS_ADDON
    PRIVATE_ROOM_FEE = PRIVATE_ROOM_FEE
    CHRONIC_EXTRA_CONSULTS = DISCOVERY_CHRONIC_EXTRA_CONSULTS
    COMPLICATION_EXTRA_CONSULTS = DISCOVERY_COMPLICATION_EXTRA_CONSULTS
    COMPLICATION_EXTRA_SCANS = DISCOVERY_COMPLICATION_EXTRA_SCANS

    def __init__(self, outputs_dir="outputs"):
        self.outputs_dir = Path(outputs_dir)

    def price_patient(self, profile):
        """Price a single patient. Accepts a PatientProfile or keyword args."""
        if isinstance(profile, dict):
            profile = PatientProfile(**profile)
        profile.validate()

        plan = profile.plan_type
        global_fee = self.GLOBAL_FEES[plan]
        consult_fee = self.CONSULT_FEE[plan]

        # Stage breakdown
        stages = compute_stage_amounts(
            global_fee, profile.enrollment_route,
            self.STAGE_PROPORTIONS, self.ANTN1B_DISCOUNT,
        )

        # Add-ons
        risk_addon = compute_risk_addon(
            profile.risk_category, consult_fee, self.SCAN_FEE, self.RISK_ADDONS,
        )
        chronic_addon = compute_chronic_addon(
            profile.chronic_flag, consult_fee, self.CHRONIC_EXTRA_CONSULTS,
        )
        complication_addon = compute_complication_addon(
            profile.complication_flag, consult_fee, self.SCAN_FEE,
            self.COMPLICATION_EXTRA_CONSULTS, self.COMPLICATION_EXTRA_SCANS,
        )
        cs_addon = compute_cs_addon(profile.delivery_mode, self.CS_ADDON)
        private_room_addon = compute_private_room_addon(
            profile.private_room, self.PRIVATE_ROOM_FEE, profile.private_room_discount,
        )

        total_addons = sum_addons(risk_addon, chronic_addon, complication_addon, cs_addon, private_room_addon)
        final_price = stages["total_global"] + total_addons

        return PricingResult(
            plan_type=plan,
            enrollment_route=profile.enrollment_route,
            global_fee=stages["total_global"],
            antn1_amount=stages["antn1_amount"],
            antn2_amount=stages["antn2_amount"],
            delivery_amount=stages["delivery_amount"],
            risk_category=profile.risk_category,
            risk_addon=risk_addon,
            chronic_addon=chronic_addon,
            complication_addon=complication_addon,
            cs_addon=cs_addon,
            private_room_addon=private_room_addon,
            total_addons=total_addons,
            final_price=round(final_price, 0),
        )
