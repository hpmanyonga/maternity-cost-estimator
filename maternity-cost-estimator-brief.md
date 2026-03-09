# Maternity Cost Estimator — Project Brief

## Goal
Build a public-facing web app that helps patients planning a pregnancy (or already pregnant) estimate the full cost of private maternity care in South Africa, compare providers, and create a budget/payment plan.

## Target Users
- Women planning a pregnancy who want to understand costs upfront
- Pregnant women comparing providers they can afford
- Couples budgeting for out-of-pocket (cash) maternity care

## Scope
End-to-end maternity cost estimation: from first consultation through delivery to 6-week postnatal check. All provider types, all cost categories, across major private hospital groups and independent providers.

---

## Phase 1: Deep Research & Data Collection

Scrape/collect publicly available South African maternity pricing data across these categories:

### 1. Hospital Fees (admission, theatre, ward)
- **Netcare** — maternity packages / tariff guides (netcare.co.za)
- **Mediclinic** — maternity packages (mediclinic.co.za)
- **Life Healthcare** — maternity packages (lifehealthcare.co.za)
- **Busamed, Lenmed, National Hospital Network** — smaller groups
- Break down: NVD vs CS, general ward vs private ward, average length of stay

### 2. Obstetrician / Gynaecologist Fees
- **BHF (Board of Healthcare Funders)** reference price list
- **SAMA** recommended tariffs
- Typical fee structures: initial consultation, follow-up visits (x10-14), delivery fee (NVD vs CS), 6-week postnatal
- Regional variation (Gauteng vs Western Cape vs KZN vs other)

### 3. Anaesthetist Fees
- Epidural anaesthesia (NVD)
- Spinal/general anaesthesia (CS)
- BHF reference rates

### 4. Paediatrician / Neonatologist
- Newborn assessment at delivery
- Follow-up visits
- NICU daily rates (for risk awareness / worst-case budgeting)

### 5. Pathology (Blood Tests)
- **NHLS** price list (public, for reference baseline)
- **Lancet, Ampath, PathCare** published rates
- Standard antenatal panel: FBC, blood group & Rh, RPR/VDRL, HIV, Hep B, rubella, urine MCS
- Additional: OGTT (gestational diabetes screen), iron studies, thyroid
- Genetic screening (NIPT, nuchal translucency) — optional but increasingly common

### 6. Ultrasound / Radiology
- Dating scan (8-12 weeks)
- Nuchal translucency (11-14 weeks)
- Anatomy scan (20-22 weeks)
- Growth scans (28, 32, 36 weeks for high-risk)
- Radiology groups: Drs Sobey, Morton & Partners, Envisionit, Lake Smit & Partners

### 7. Midwife Fees
- Independent midwife-led care packages
- Midwife associations (SAMA, private midwife networks)
- Doula fees (optional add-on)

### 8. Medication
- **SEP (Single Exit Price) database** from Department of Health
- Common antenatal meds: prenatal vitamins, iron, folic acid, calcium
- Chronic medication top-ups (hypertension, diabetes, thyroid)

### Data Output Format
For each provider/category, capture:
- Provider name, location/region
- Service description
- Price (Rands), year of pricing
- Source URL
- NVD vs CS distinction where applicable

Store as structured CSV/JSON in `data/` directory.

---

## Phase 2: Estimator Engine

Once research data is collected:

### Core Model
- Input: location (province/city), delivery preference (NVD/CS/undecided), risk level (low/medium/high), provider preference (budget/mid-range/premium)
- Output: itemised cost estimate with totals, monthly budget plan

### Cost Components
```
Total = Hospital + Obstetrician + Anaesthetist + Paediatrician + Pathology + Ultrasound + Medication + [Optional: Midwife/Doula]
```

### Budget Planner
- Input: current gestational age (or months until planned pregnancy)
- Output: monthly savings target, payment milestones
- Show: "If you start saving now, you need R X/month"

---

## Phase 3: Web App (Streamlit)

### UI Flow
1. **Welcome** — "Plan your maternity budget"
2. **Your Details** — Province, delivery preference, risk factors
3. **Choose Provider Level** — Budget / Mid-range / Premium (with hospital group examples)
4. **Cost Breakdown** — Itemised table with totals
5. **Budget Planner** — Monthly savings calculator
6. **Compare** — Side-by-side provider comparison

---

## Tech Stack
- Python 3.12+
- pandas, streamlit
- BeautifulSoup / requests for web scraping
- Data stored as CSV/Parquet in `data/`

## Project Structure
```
maternity-cost-estimator/
├── research/          # scraping scripts, raw data collection
├── data/              # cleaned pricing datasets (CSV/JSON)
├── engine/            # cost estimation logic
├── app/               # Streamlit web app
├── requirements.txt
└── README.md
```

---

## Instructions for Claude Code

When you start the new session, paste this prompt:

> I'm building a public maternity cost estimator for South Africa. Read the project brief at `~/maternity-cost-estimator-brief.md` for full context. Start with Phase 1: deep web research to collect current public pricing data for private maternity care across all provider categories (hospitals, obstetricians, anaesthetists, paediatricians, pathology, ultrasound, midwives, medication). Scrape publicly available tariffs and package prices. Save structured data to `data/`. Let's begin with hospital group maternity packages from Netcare, Mediclinic, and Life Healthcare.
