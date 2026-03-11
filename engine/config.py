"""
Single source of truth for all pricing constants across the maternity platform.

Consolidates:
- FFS estimation data (regions, tiers, risk profiles)
- NOH consumer pricing (Cost Estimator public page)
- Discovery global fees and stage proportions
- NOH Cash packages and add-ons
"""

# ============================================================
# FFS ESTIMATION — Regions, Tiers, Risk Profiles
# ============================================================

REGIONS = {
    "Gauteng": [
        "Gauteng", "Gauteng (Johannesburg/Pretoria)", "Johannesburg", "Pretoria",
        "Sunninghill", "Waterfall", "Morningside", "Fourways", "Modderfontein",
        "Sandton", "Mediclinic Sandton", "Netcare Park Lane (Johannesburg)",
        "Gauteng & Western Cape",
    ],
    "Western Cape": [
        "Western Cape", "Cape Town", "Christiaan Barnard", "Constantiaberg",
        "Dr Gary Groenewald (Cape Town)", "Gauteng & Western Cape",
        "Morton & Partners (Western Cape)",
    ],
    "KwaZulu-Natal": [
        "KwaZulu-Natal", "KZN", "Durban", "Ethekwini",
        "Lake Smit & Partners (KZN)",
    ],
    "Other": [
        "Eastern Cape", "Free State", "Eastern Cape/Free State",
        "Port Elizabeth", "Mediclinic Nelspruit", "Other",
    ],
}

NATIONAL_MARKERS = [
    "National", "National (Mediclinic data)", "National (Life Healthcare data)",
    "National estimate", "National Average", "Medical aid rate",
    "Envisionit (multi-region)", "Location not specified",
    "Private radiology general", "Private radiology", "Private lab",
]

PROVIDER_TIERS = {
    "budget": {
        "hospitals": ["Life Healthcare", "Independent"],
        "pathology": ["Lister Clinic", "NHLS"],
        "ultrasound": ["SS Ultrasound", "Peek-a-Babe", "Lister Clinic"],
        "midwife": ["Protea Midwifery", "Alnisa Maternity Home", "PMB Care", "National estimate"],
        "doula": ["National estimate", "PMB Care"],
    },
    "mid-range": {
        "hospitals": ["Mediclinic"],
        "pathology": ["PathCare", "Ampath Laboratories"],
        "ultrasound": ["Peer Med Pretoria", "Life Healthcare data", "Mediclinic data",
                       "Obstetrician rooms (in-office)"],
        "midwife": ["Birth Divine Birth Center", "PMB Care", "National estimate"],
        "doula": ["National estimate", "PMB Care"],
    },
    "premium": {
        "hospitals": ["Netcare"],
        "pathology": ["Lancet Laboratories"],
        "ultrasound": ["Drs Sobey (Gauteng)", "Morton & Partners (Western Cape)",
                       "Lake Smit & Partners (KZN)", "Envisionit (multi-region)"],
        "midwife": ["Birth Divine Birth Center", "National estimate"],
        "doula": ["National estimate"],
    },
}

RISK_PROFILES = {
    "low": {"scans": 3, "extra_bloods": False, "nicu_flag": False},
    "medium": {"scans": 5, "extra_bloods": True, "nicu_flag": True},
    "high": {"scans": 7, "extra_bloods": True, "nicu_flag": True},
}

STANDARD_TESTS = [
    "FBC", "Full Blood", "Blood Group", "Rh", "RPR", "Syphilis",
    "HIV", "Rubella", "Hepatitis B", "Glucose", "OGTT", "Urine",
]

EXTRA_TESTS = [
    "Iron", "Ferritin", "Thyroid", "TSH", "Platelet",
]

PRENATAL_VITAMIN_MONTHS = 9

# ============================================================
# NOH CONSUMER PRICING — Cost Estimator (public page)
# Derived from NOH_PACKAGES min/max range
# ============================================================

NOH_PRICING = {
    "global_fee_low": 29_900,   # Mat001_LOW
    "global_fee_high": 64_000,  # Mat003
    "cs_addon": 2_000,
    "risk_addon": {"low": 0, "medium": 5_800, "high": 11_500},
    "regions": ["Gauteng", "Western Cape", "KwaZulu-Natal", "Other"],
    "inclusions": [
        "All antenatal visits (10-14 visits)",
        "All ultrasound scans",
        "Booking bloods and pathology",
        "Hospital facility fees",
        "Obstetrician delivery fee",
        "Anaesthetist fee",
        "Doula birth support",
        "Antenatal classes",
        "Prenatal vitamins guidance",
    ],
    "exclusions": [
        "Paediatrician newborn assessment",
    ],
    "payment_terms": {
        "months": 12,
        "deposit_percent": 10,
    },
}

# ============================================================
# DISCOVERY GLOBAL FEES — admin pricing workbench
# ============================================================

DISCOVERY_GLOBAL_FEES = {
    "KEYCARE":           48_000,
    "SMART":             50_000,
    "COASTAL_ESSENTIAL": 52_000,
    "CLASSIC":           55_000,
    "EXECUTIVE":         58_000,
}

DISCOVERY_STAGE_PROPORTIONS = {
    "ANTN1A":   0.25,
    "ANTN2":    0.20,
    "DELIVERY": 0.55,
}

DISCOVERY_ANTN1B_DISCOUNT = 0.50

DISCOVERY_RISK_ADDONS = {
    "BASE":   {"consults": 0, "scans": 0},
    "MEDIUM": {"consults": 2, "scans": 1},
    "HIGH":   {"consults": 4, "scans": 2},
}

DISCOVERY_CONSULT_FEE = {
    "KEYCARE": 1_689,
    "SMART": 2_300,
    "COASTAL_ESSENTIAL": 2_300,
    "CLASSIC": 2_300,
    "EXECUTIVE": 2_300,
}

DISCOVERY_SCAN_FEE = 1_800
DISCOVERY_CS_ADDON = 2_000
DISCOVERY_CHRONIC_EXTRA_CONSULTS = 1
DISCOVERY_COMPLICATION_EXTRA_CONSULTS = 1
DISCOVERY_COMPLICATION_EXTRA_SCANS = 1

# ============================================================
# NOH CASH PACKAGES — admin pricing workbench
# ============================================================

NOH_PACKAGES = {
    "Mat001_LOW": {"code": "Mat001", "label": "NVD (multiparous, low-risk)", "price": 29_900},
    "Mat001_HIGH": {"code": "Mat001", "label": "NVD (high-risk / primigravida)", "price": 46_000},
    "Mat002": {"code": "Mat002", "label": "Elective C/S", "price": 58_650},
    "Mat003": {"code": "Mat003", "label": "High Risk C/S", "price": 64_000},
}

NOH_CS_CONVERSION_LEVY = 7_500   # MAT004
NOH_CONSULT_FEE = 2_300
NOH_CHRONIC_SCAN_FEE = 1_500
PRIVATE_ROOM_FEE = 4_000         # shared across both programmes

NOH_ADDITIONAL_TESTS = {
    "Path1_OGTT": {"label": "OGTT", "code": "Path1", "fee": 173.00},
    "Path2_HIV_CD4": {"label": "HIV CD4 & Viral Load", "code": "Path2", "fee": 1_253.50},
    "Iron_Studies": {"label": "Iron Studies", "code": "Iron", "fee": 402.50},
    "Mat010_NST": {"label": "Non Stress Test", "code": "Mat010", "fee": 250.00},
}
