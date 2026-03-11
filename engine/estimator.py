"""Core cost estimation logic."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union
import pandas as pd
from engine.config import RISK_PROFILES, PRENATAL_VITAMIN_MONTHS, NOH_PRICING
from engine.data_loader import load_all


@dataclass
class EstimatorInput:
    region: str = "Gauteng"                # Gauteng | Western Cape | KwaZulu-Natal | Other
    delivery_type: str = "NVD"             # NVD | CS | Undecided
    risk_level: str = "low"                # low | medium | high
    provider_tier: str = "mid-range"       # budget | mid-range | premium
    wants_epidural: bool = False
    wants_midwife: bool = False
    wants_doula: bool = False
    gestational_weeks: int = 0             # 0 = planning


@dataclass
class CostBreakdown:
    hospital: tuple[int, int] = (0, 0)
    obstetrician: tuple[int, int] = (0, 0)
    anaesthetist: tuple[int, int] = (0, 0)
    paediatrician: tuple[int, int] = (0, 0)
    pathology: tuple[int, int] = (0, 0)
    ultrasound: tuple[int, int] = (0, 0)
    medication: tuple[int, int] = (0, 0)
    midwife: tuple[int, int] = (0, 0)
    doula: tuple[int, int] = (0, 0)
    total: tuple[int, int] = (0, 0)
    line_items: list[dict] = field(default_factory=list)


# Cache loaded data at module level
_data_cache: dict[str, pd.DataFrame] | None = None


def _get_data() -> dict[str, pd.DataFrame]:
    global _data_cache
    if _data_cache is None:
        _data_cache = load_all()
    return _data_cache


def _filter_by_region(df: pd.DataFrame, region: str) -> pd.DataFrame:
    """Filter dataframe to rows matching the region or national data."""
    return df[(df["region_group"] == region) | (df["region_group"] == "National")]


def _filter_by_tier(df: pd.DataFrame, tier: str, fallback: bool = True) -> pd.DataFrame:
    """Filter dataframe to rows matching the provider tier. Falls back to all if empty."""
    filtered = df[df["provider_tier"] == tier]
    if filtered.empty and fallback:
        return df  # sparse data — use all available
    return filtered


def _filter_by_delivery(df: pd.DataFrame, delivery_type: str) -> pd.DataFrame:
    """Filter dataframe to rows matching delivery type (includes NaN/N/A/Both)."""
    if "delivery_type" not in df.columns:
        return df
    return df[
        (df["delivery_type"] == delivery_type) |
        (df["delivery_type"] == "Both") |
        (df["delivery_type"] == "N/A") |
        (df["delivery_type"].isna())
    ]


def _get_range(df: pd.DataFrame) -> tuple[int, int]:
    """Get (min low, max high) price range from filtered data."""
    if df.empty:
        return (0, 0)
    low = int(df["price_low"].min())
    high = int(df["price_high"].max())
    return (low, high)


def _get_median_range(df: pd.DataFrame) -> tuple[int, int]:
    """Get median-based range — more representative than min/max for sparse data."""
    if df.empty:
        return (0, 0)
    low = int(df["price_low"].median())
    high = int(df["price_high"].median())
    return (low, max(low, high))


FACILITY_FRACTION = 0.60  # When only all-in totals exist, ~60% is facility


def _estimate_hospital(data: dict, inp: EstimatorInput) -> tuple[tuple[int, int], list[dict]]:
    """Estimate hospital facility costs (excluding professional fees)."""
    df = data["hospital"]
    df = _filter_by_region(df, inp.region)
    df = _filter_by_tier(df, inp.provider_tier)
    df = _filter_by_delivery(df, inp.delivery_type)

    # Try facility-only rows first (avoids double-counting with OB/anaesthetist)
    facility_rows = df[df["service"].str.contains(
        "facility|Hospital facility|ward fee", case=False, na=False,
    )]
    # Also include ward-type rows (e.g. "NVD shared ward", "CS semi-private ward")
    ward_rows = df[df["service"].str.contains(
        r"^(?:NVD|CS)\s+(?:shared|semi-private|private)\s+ward$",
        case=False, na=False,
    )]
    facility_rows = pd.concat([facility_rows, ward_rows]).drop_duplicates()

    if not facility_rows.empty:
        cost_range = _get_median_range(facility_rows)
        label = f"Hospital facility fees ({inp.delivery_type})"
    else:
        # Only all-in totals available — extract facility portion
        total_rows = df[df["service"].str.contains("Total|total", case=False, na=False)]
        if not total_rows.empty:
            all_in = _get_median_range(total_rows)
            cost_range = (int(all_in[0] * FACILITY_FRACTION),
                          int(all_in[1] * FACILITY_FRACTION))
            label = f"Hospital facility fees ({inp.delivery_type}, estimated)"
        else:
            cost_range = _get_median_range(df)
            label = f"Hospital fees ({inp.delivery_type})"

    items = [{
        "category": "Hospital",
        "service": label,
        "provider": "",
        "low": cost_range[0],
        "high": cost_range[1],
    }]
    return cost_range, items


def _estimate_obstetrician(data: dict, inp: EstimatorInput) -> tuple[tuple[int, int], list[dict]]:
    """Estimate obstetrician costs (delivery fee + antenatal visits)."""
    df = data["obstetrician"]
    df = _filter_by_region(df, inp.region)
    df = _filter_by_tier(df, inp.provider_tier)

    # Exclude assistant surgeon, after-hours surcharges, and medical aid rates
    df = df[~df["service"].str.contains(
        "assistant|surcharge|reimbursement", case=False, na=False
    )]

    items = []

    # Check for "all-in" total rows first
    all_in = df[df["service"].str.contains("all-in|total obstetrician", case=False, na=False)]
    all_in = _filter_by_delivery(all_in, inp.delivery_type)
    if not all_in.empty:
        total_range = _get_median_range(all_in)
        items.append({
            "category": "Obstetrician",
            "service": f"Obstetrician total (delivery + antenatal)",
            "provider": "",
            "low": total_range[0],
            "high": total_range[1],
        })
        return total_range, items

    # Delivery fee — only rows describing the delivery itself
    delivery_df = _filter_by_delivery(df, inp.delivery_type)
    delivery_df = delivery_df[delivery_df["service"].str.contains(
        "delivery fee|vaginal delivery|caesarean|NVD delivery|CS delivery",
        case=False, na=False,
    )]
    delivery_range = _get_median_range(delivery_df)
    if delivery_range != (0, 0):
        items.append({
            "category": "Obstetrician",
            "service": f"Delivery fee ({inp.delivery_type})",
            "provider": "",
            "low": delivery_range[0],
            "high": delivery_range[1],
        })

    # Antenatal care — prefer "Total antenatal visits" rows over per-visit
    total_antenatal = df[df["service"].str.contains(
        "total antenatal", case=False, na=False
    )]
    if not total_antenatal.empty:
        antenatal_range = _get_median_range(total_antenatal)
    else:
        # Fall back to per-visit × count
        per_visit = df[df["service"].str.contains(
            "per antenatal|follow-up|consultation", case=False, na=False
        )]
        per_visit = per_visit[~per_visit["service"].str.contains(
            "total|booking|first|initial", case=False, na=False
        )]
        per_visit_range = _get_median_range(per_visit)

        booking = df[df["service"].str.contains(
            "booking|first visit|initial", case=False, na=False
        )]
        booking_range = _get_median_range(booking)

        num_visits = 9
        antenatal_range = (
            booking_range[0] + per_visit_range[0] * num_visits,
            booking_range[1] + per_visit_range[1] * num_visits,
        )

    if antenatal_range != (0, 0):
        items.append({
            "category": "Obstetrician",
            "service": "Antenatal care (~10 visits)",
            "provider": "",
            "low": antenatal_range[0],
            "high": antenatal_range[1],
        })

    total_low = delivery_range[0] + antenatal_range[0]
    total_high = delivery_range[1] + antenatal_range[1]
    return (total_low, total_high), items


def _estimate_anaesthetist(data: dict, inp: EstimatorInput) -> tuple[tuple[int, int], list[dict]]:
    """Estimate anaesthetist costs."""
    # Only needed for CS (spinal) or NVD with epidural
    if inp.delivery_type == "NVD" and not inp.wants_epidural:
        return (0, 0), []

    df = data["anaesthetist"]
    df = _filter_by_region(df, inp.region)
    df = _filter_by_tier(df, inp.provider_tier)

    if inp.delivery_type == "CS":
        # Spinal anaesthesia for CS
        cs_df = df[df["service"].str.contains("spinal|general|CS|caesarean", case=False, na=False)]
        if cs_df.empty:
            cs_df = _filter_by_delivery(df, "CS")
        cost_range = _get_median_range(cs_df) if not cs_df.empty else _get_median_range(df)
        service_desc = "Spinal anaesthesia (CS)"
    else:
        # Epidural for NVD
        epi_df = df[df["service"].str.contains("epidural", case=False, na=False)]
        if epi_df.empty:
            epi_df = _filter_by_delivery(df, "NVD")
        cost_range = _get_median_range(epi_df) if not epi_df.empty else _get_median_range(df)
        service_desc = "Epidural anaesthesia (NVD)"

    items = []
    if cost_range != (0, 0):
        items.append({
            "category": "Anaesthetist",
            "service": service_desc,
            "provider": "",
            "low": cost_range[0],
            "high": cost_range[1],
        })
    return cost_range, items


def _estimate_paediatrician(data: dict, inp: EstimatorInput) -> tuple[tuple[int, int], list[dict]]:
    """Estimate paediatrician costs — newborn assessment always included."""
    df = data["paediatrician"]
    df = _filter_by_region(df, inp.region)
    df = _filter_by_tier(df, inp.provider_tier)

    # Filter to newborn assessment rows (not NICU)
    assess_df = df[df.get("provider_type", pd.Series(dtype=str)).str.contains(
        "Paediatrician", case=False, na=True
    )]
    if assess_df.empty:
        assess_df = df

    cost_range = _get_median_range(assess_df)
    items = []
    if cost_range != (0, 0):
        items.append({
            "category": "Paediatrician",
            "service": "Newborn assessment",
            "provider": "",
            "low": cost_range[0],
            "high": cost_range[1],
        })
    return cost_range, items


def _estimate_pathology(data: dict, inp: EstimatorInput) -> tuple[tuple[int, int], list[dict]]:
    """Estimate pathology costs based on risk level."""
    from engine.config import STANDARD_TESTS, EXTRA_TESTS

    df = data["pathology"]
    df = _filter_by_tier(df, inp.provider_tier)

    items = []
    total_low, total_high = 0, 0

    # Check for antenatal panel rows first (aggregated pricing)
    panel_df = df[df.get("test_category", pd.Series(dtype=str)).str.contains(
        "Antenatal panel", case=False, na=False
    )]
    if not panel_df.empty:
        panel_range = _get_median_range(panel_df)
        items.append({
            "category": "Pathology",
            "service": "Antenatal booking bloods (panel)",
            "provider": "",
            "low": panel_range[0],
            "high": panel_range[1],
        })
        total_low += panel_range[0]
        total_high += panel_range[1]
    else:
        # Sum individual standard tests
        for test in STANDARD_TESTS:
            test_df = df[df["service"].str.contains(test, case=False, na=False)]
            if not test_df.empty:
                r = _get_median_range(test_df)
                total_low += r[0]
                total_high += r[1]
        if total_low > 0:
            items.append({
                "category": "Pathology",
                "service": "Standard booking bloods",
                "provider": "",
                "low": total_low,
                "high": total_high,
            })

    # Extra tests for medium/high risk
    risk = RISK_PROFILES[inp.risk_level]
    if risk["extra_bloods"]:
        extra_low, extra_high = 0, 0
        for test in EXTRA_TESTS:
            test_df = df[df["service"].str.contains(test, case=False, na=False)]
            if not test_df.empty:
                r = _get_median_range(test_df)
                extra_low += r[0]
                extra_high += r[1]
        if extra_low > 0:
            items.append({
                "category": "Pathology",
                "service": "Additional bloods (iron, thyroid)",
                "provider": "",
                "low": extra_low,
                "high": extra_high,
            })
            total_low += extra_low
            total_high += extra_high

    return (total_low, total_high), items


def _estimate_ultrasound(data: dict, inp: EstimatorInput) -> tuple[tuple[int, int], list[dict]]:
    """Estimate ultrasound costs based on risk level (number of scans)."""
    df = data["ultrasound"]
    df = _filter_by_tier(df, inp.provider_tier)

    # Filter to standard pregnancy scans (not totals or surcharges)
    scan_df = df[df.get("scan_category", pd.Series(dtype=str)).str.contains(
        "Ultrasound", case=False, na=True
    )]
    # Exclude "total" rows
    scan_df = scan_df[~scan_df["service"].str.contains("total|package", case=False, na=False)]
    if scan_df.empty:
        scan_df = df

    per_scan = _get_median_range(scan_df)
    num_scans = RISK_PROFILES[inp.risk_level]["scans"]
    total_low = per_scan[0] * num_scans
    total_high = per_scan[1] * num_scans

    items = [{
        "category": "Ultrasound",
        "service": f"Pregnancy scans ({num_scans} scans)",
        "provider": "",
        "low": total_low,
        "high": total_high,
    }]
    return (total_low, total_high), items


def _estimate_medication(data: dict, inp: EstimatorInput) -> tuple[tuple[int, int], list[dict]]:
    """Estimate medication and supplement costs."""
    df = data["medication"]
    items = []
    total_low, total_high = 0, 0

    # Prenatal vitamins — mid-range option × months
    vitamin_df = df[df["med_category"].str.contains("Prenatal vitamin", case=False, na=False)]
    if not vitamin_df.empty:
        per_month = _get_median_range(vitamin_df)
        vit_low = per_month[0] * PRENATAL_VITAMIN_MONTHS
        vit_high = per_month[1] * PRENATAL_VITAMIN_MONTHS
        items.append({
            "category": "Medication",
            "service": f"Prenatal vitamins ({PRENATAL_VITAMIN_MONTHS} months)",
            "provider": "",
            "low": vit_low,
            "high": vit_high,
        })
        total_low += vit_low
        total_high += vit_high

    # Discharge medication
    discharge_df = df[df["med_category"].str.contains("Discharge", case=False, na=False)]
    if not discharge_df.empty:
        d_range = _get_median_range(discharge_df)
        items.append({
            "category": "Medication",
            "service": "Discharge medications",
            "provider": "",
            "low": d_range[0],
            "high": d_range[1],
        })
        total_low += d_range[0]
        total_high += d_range[1]

    return (total_low, total_high), items


def _estimate_midwife(data: dict, inp: EstimatorInput) -> tuple[tuple[int, int], list[dict]]:
    """Estimate midwife-led birth costs."""
    if not inp.wants_midwife:
        return (0, 0), []

    df = data["midwife_doula"]
    df = df[df["category"] == "midwife"]
    df = _filter_by_region(df, inp.region)
    df = _filter_by_tier(df, inp.provider_tier)

    # Look for birth/global fee rows
    birth_df = df[df["service"].str.contains("birth|global|package|delivery", case=False, na=False)]
    if not birth_df.empty:
        cost_range = _get_median_range(birth_df)
    else:
        cost_range = _get_median_range(df)

    items = []
    if cost_range != (0, 0):
        items.append({
            "category": "Midwife",
            "service": "Midwife-led birth package",
            "provider": "",
            "low": cost_range[0],
            "high": cost_range[1],
        })
    return cost_range, items


def _estimate_doula(data: dict, inp: EstimatorInput) -> tuple[tuple[int, int], list[dict]]:
    """Estimate doula costs."""
    if not inp.wants_doula:
        return (0, 0), []

    df = data["midwife_doula"]
    df = df[df["category"] == "doula"]
    df = _filter_by_region(df, inp.region)

    # Look for package/birth support rows
    pkg_df = df[df["service"].str.contains("package|birth|support|full", case=False, na=False)]
    if not pkg_df.empty:
        cost_range = _get_median_range(pkg_df)
    else:
        cost_range = _get_median_range(df)

    items = []
    if cost_range != (0, 0):
        items.append({
            "category": "Doula",
            "service": "Doula birth support package",
            "provider": "",
            "low": cost_range[0],
            "high": cost_range[1],
        })
    return cost_range, items


def estimate(inp: EstimatorInput) -> CostBreakdown | dict[str, CostBreakdown]:
    """
    Estimate maternity costs based on user inputs.

    If delivery_type is "Undecided", returns a dict with keys "NVD" and "CS",
    each containing a CostBreakdown.
    """
    if inp.delivery_type == "Undecided":
        nvd_input = EstimatorInput(
            region=inp.region, delivery_type="NVD", risk_level=inp.risk_level,
            provider_tier=inp.provider_tier, wants_epidural=inp.wants_epidural,
            wants_midwife=inp.wants_midwife, wants_doula=inp.wants_doula,
            gestational_weeks=inp.gestational_weeks,
        )
        cs_input = EstimatorInput(
            region=inp.region, delivery_type="CS", risk_level=inp.risk_level,
            provider_tier=inp.provider_tier, wants_epidural=False,
            wants_midwife=False, wants_doula=inp.wants_doula,
            gestational_weeks=inp.gestational_weeks,
        )
        return {
            "NVD": estimate(nvd_input),
            "CS": estimate(cs_input),
        }

    data = _get_data()
    result = CostBreakdown()
    all_items = []

    # Hospital (skip if midwife-led)
    if not inp.wants_midwife:
        result.hospital, items = _estimate_hospital(data, inp)
        all_items.extend(items)
    else:
        result.midwife, items = _estimate_midwife(data, inp)
        all_items.extend(items)

    # Obstetrician (skip if midwife-led — midwife replaces OB)
    if not inp.wants_midwife:
        result.obstetrician, items = _estimate_obstetrician(data, inp)
        all_items.extend(items)

    # Anaesthetist
    result.anaesthetist, items = _estimate_anaesthetist(data, inp)
    all_items.extend(items)

    # Paediatrician
    result.paediatrician, items = _estimate_paediatrician(data, inp)
    all_items.extend(items)

    # Pathology
    result.pathology, items = _estimate_pathology(data, inp)
    all_items.extend(items)

    # Ultrasound
    result.ultrasound, items = _estimate_ultrasound(data, inp)
    all_items.extend(items)

    # Medication
    result.medication, items = _estimate_medication(data, inp)
    all_items.extend(items)

    # Doula
    if inp.wants_doula:
        result.doula, items = _estimate_doula(data, inp)
        all_items.extend(items)

    # Total
    components = [
        result.hospital, result.obstetrician, result.anaesthetist,
        result.paediatrician, result.pathology, result.ultrasound,
        result.medication, result.midwife, result.doula,
    ]
    result.total = (
        sum(c[0] for c in components),
        sum(c[1] for c in components),
    )
    result.line_items = all_items
    return result


def estimate_noh(inp: EstimatorInput) -> dict:
    """Return NOH bundled fee and comparison metrics vs fee-for-service."""
    # NOH base fee
    noh_low = NOH_PRICING["global_fee_low"]
    noh_high = NOH_PRICING["global_fee_high"]

    # CS add-on
    if inp.delivery_type == "CS":
        noh_low += NOH_PRICING["cs_addon"]
        noh_high += NOH_PRICING["cs_addon"]

    # Epidural add-on (vaginal only — CS already includes anaesthetist)
    if inp.wants_epidural and inp.delivery_type != "CS":
        noh_low += NOH_PRICING["epidural_addon"]
        noh_high += NOH_PRICING["epidural_addon"]

    # Risk add-on
    risk_addon = NOH_PRICING["risk_addon"].get(inp.risk_level, 0)
    noh_low += risk_addon
    noh_high += risk_addon

    # Paediatrician is NOT included in NOH bundle — estimate separately
    data = _get_data()
    paed_range, _ = _estimate_paediatrician(data, inp)

    # Fee-for-service estimate for comparison
    ffs_result = estimate(inp)

    # Handle Undecided (use the higher of NVD/CS for ffs)
    if isinstance(ffs_result, dict):
        ffs_total_low = max(ffs_result["NVD"].total[0], ffs_result["CS"].total[0])
        ffs_total_high = max(ffs_result["NVD"].total[1], ffs_result["CS"].total[1])
    else:
        ffs_total_low = ffs_result.total[0]
        ffs_total_high = ffs_result.total[1]

    noh_total_low = noh_low + paed_range[0]
    noh_total_high = noh_high + paed_range[1]

    savings_low = ffs_total_low - noh_total_high  # conservative savings
    savings_high = ffs_total_high - noh_total_low  # max savings

    return {
        "noh_fee_low": noh_low,
        "noh_fee_high": noh_high,
        "noh_total_low": noh_total_low,
        "noh_total_high": noh_total_high,
        "paediatrician": paed_range,
        "ffs_result": ffs_result,
        "ffs_total_low": ffs_total_low,
        "ffs_total_high": ffs_total_high,
        "savings_low": max(0, savings_low),
        "savings_high": max(0, savings_high),
        "savings_percent_low": max(0, round(savings_low / ffs_total_high * 100)) if ffs_total_high else 0,
        "savings_percent_high": max(0, round(savings_high / ffs_total_high * 100)) if ffs_total_high else 0,
        "inclusions": NOH_PRICING["inclusions"],
        "exclusions": NOH_PRICING["exclusions"],
    }
