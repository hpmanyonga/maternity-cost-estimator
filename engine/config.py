"""Constants and mappings for the maternity cost estimator."""

# Regions — map user-selected province to strings found in CSV data
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

# Strings in CSV data that are national/non-regional (match any region)
NATIONAL_MARKERS = [
    "National", "National (Mediclinic data)", "National (Life Healthcare data)",
    "National estimate", "National Average", "Medical aid rate",
    "Envisionit (multi-region)", "Location not specified",
    "Private radiology general", "Private radiology", "Private lab",
]

# Provider tiers — map hospital groups and providers to budget/mid/premium
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

# Risk profiles — determine scan count and extra tests
RISK_PROFILES = {
    "low": {"scans": 3, "extra_bloods": False, "nicu_flag": False},
    "medium": {"scans": 5, "extra_bloods": True, "nicu_flag": True},
    "high": {"scans": 7, "extra_bloods": True, "nicu_flag": True},
}

# Standard antenatal blood tests (booking bloods)
STANDARD_TESTS = [
    "FBC", "Full Blood", "Blood Group", "Rh", "RPR", "Syphilis",
    "HIV", "Rubella", "Hepatitis B", "Glucose", "OGTT", "Urine",
]

# Extra tests for medium/high risk
EXTRA_TESTS = [
    "Iron", "Ferritin", "Thyroid", "TSH", "Platelet",
]

# Prenatal vitamins — months of pregnancy to budget for
PRENATAL_VITAMIN_MONTHS = 9
