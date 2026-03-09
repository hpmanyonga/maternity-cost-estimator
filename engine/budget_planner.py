"""Monthly savings calculator and payment milestone planner."""

from dataclasses import dataclass


@dataclass
class SavingsPlan:
    monthly_low: int
    monthly_high: int
    months_remaining: float
    milestones: list[dict]
    total_low: int
    total_high: int


def calculate_savings_plan(
    total_low: int,
    total_high: int,
    weeks_remaining: int,
) -> SavingsPlan:
    """
    Calculate monthly savings targets and payment milestones.

    Args:
        total_low: Lower bound of estimated total cost (ZAR).
        total_high: Upper bound of estimated total cost (ZAR).
        weeks_remaining: Weeks until due date. 0 = planning (assume 40 weeks).
    """
    if weeks_remaining <= 0:
        weeks_remaining = 40

    months_remaining = max(1, weeks_remaining / 4.33)
    monthly_low = int(total_low / months_remaining)
    monthly_high = int(total_high / months_remaining)

    milestones = [
        {
            "milestone": "Obstetrician booking deposit",
            "when": "First visit (6-8 weeks)",
            "estimate": "10-20% of OB delivery fee",
            "week": 8,
        },
        {
            "milestone": "Antenatal visits (ongoing)",
            "when": "Monthly from booking to 28 weeks, then fortnightly",
            "estimate": "R800-R1,150 per visit",
            "week": None,
        },
        {
            "milestone": "Hospital deposit",
            "when": "Around 30 weeks",
            "estimate": "Varies by hospital — usually R5,000-R15,000",
            "week": 30,
        },
        {
            "milestone": "Balance due",
            "when": "Before admission (34-36 weeks)",
            "estimate": "Remaining hospital + professional fees",
            "week": 36,
        },
    ]

    return SavingsPlan(
        monthly_low=monthly_low,
        monthly_high=monthly_high,
        months_remaining=round(months_remaining, 1),
        milestones=milestones,
        total_low=total_low,
        total_high=total_high,
    )


def calculate_noh_payment_plan(
    noh_total_low: int,
    noh_total_high: int,
    months: int = 12,
    deposit_pct: int = 10,
) -> dict:
    """Calculate NOH deposit + monthly instalment plan."""
    deposit_low = int(noh_total_low * deposit_pct / 100)
    deposit_high = int(noh_total_high * deposit_pct / 100)
    balance_low = noh_total_low - deposit_low
    balance_high = noh_total_high - deposit_high
    monthly_low = int(balance_low / months)
    monthly_high = int(balance_high / months)
    return {
        "deposit_low": deposit_low,
        "deposit_high": deposit_high,
        "monthly_low": monthly_low,
        "monthly_high": monthly_high,
        "months": months,
    }
