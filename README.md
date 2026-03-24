# 🛡️ ClearRate — Personal Lines Auto Insurance Rating Engine

> A production-grade actuarial rating engine and interactive web application, built to demonstrate how modern insurtech platforms price personal auto insurance policies.

[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.35+-FF4B4B?style=flat&logo=streamlit&logoColor=white)](https://streamlit.io)
[![Plotly](https://img.shields.io/badge/Plotly-5.20+-3F4F75?style=flat&logo=plotly&logoColor=white)](https://plotly.com)
[![Actuarial Science](https://img.shields.io/badge/Domain-P%26C-0D2340?style=flat)](https://www.casact.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-22C55E?style=flat)](LICENSE)

---

## Overview

ClearRate is a full-stack actuarial application that simulates how a personal lines insurer calculates an auto insurance premium — from a flat-file rate manual all the way through to a live, interactive web quote. It is built with clean object-oriented Python and a Streamlit front-end, and is structured to reflect real-world insurance rating workflows.

The project covers three layers of actuarial practice:

1. **Rate Manual** — a CSV-based rate table encoding base premiums and relativities for every rating variable, mirroring the ISO rate-filing format used by carriers in production.
2. **Rating Engine** — a multiplicative model that resolves each risk characteristic to a relativity factor and produces a fully auditable premium step-down.
3. **GLM Credibility Adjustment** — a simulated Poisson log-link Generalized Linear Model that blends statistical model output with manual rates, the standard approach in modern actuarial pricing.

---

## Live Demo

> **[→ Launch on Streamlit Community Cloud](https://flynn-auto-insurance-rating-engine.streamlit.app/)**

---

## Features

### Core Rating Engine (`rating_engine.py`)
- **Multiplicative pricing model**: `Final Premium = Base × ∏(Relativities) × GLM_Adjustment`
- **Six rating variables**: Driver Age, Vehicle Value (ISO symbols), Territory, Safety Features, Deductible, Coverage Type
- **Two-tier input validation**: hard stops for uninsurable risks (`OutOfBoundsError`) and soft underwriting notices for edge cases
- **GLM credibility adjustment**: 60/40 blend of a synthetic Poisson log-link model against manual relativities, applied to the three primary risk dimensions
- **Full audit trail**: every intermediate step is captured in a typed `QuoteResult` dataclass

### Streamlit Web Application (`app.py`)
- **Real-time premium calculation** — quote updates instantly as sidebar inputs change
- **Premium hero banner** — annual and monthly premium displayed prominently alongside combined factor and GLM adjustment badges
- **Impact factor chart** — horizontal Plotly bar chart showing the *dollar impact* of each rating variable (surcharges in red, discounts in green)
- **Actuarial step-down table** — running premium total after each factor is applied, exactly as it would appear in a rate filing exhibit
- **Sensitivity analysis** — sweep any variable across all valid values and see the premium delta in both a chart and a formatted table
- **Scenario comparison** — configure a fully independent alternative quote and compare relativities side-by-side

---

## Project Structure

```
clearrate/
│
├── app.py                  # Streamlit UI — all pages and visualisations
├── rating_engine.py        # Core library
│   ├── RateTable           # Pandas-backed CSV loader with O(1) index
│   ├── AgeBandMapper       # Continuous age → ISO band key
│   ├── VehicleSymbolMapper # Vehicle value → ISO symbol tier
│   ├── InputValidator      # Two-tier validation (hard errors + soft warnings)
│   ├── GLMRateAdjuster     # Poisson log-link credibility model
│   ├── SensitivityAnalyser # Single-variable sweep → DataFrame
│   └── RatingEngine        # Public API — calculate_premium(), print_*()
│
├── generate_rate_table.py  # Helper: writes rate_table.csv
├── rate_table.csv          # Flat-file rate manual (auto-generated)
├── requirements.txt        # Python dependencies
└── README.md
```

---

## Rating Model Detail

### Variables and Relativities

| Variable | Key | Relativity | Notes |
|---|---|---|---|
| **Base Premium** | — | $800.00 | Statewide annual base rate |
| **Driver Age** | 16–17 | 2.40× | Teen surcharge |
| | 18–20 | 1.95× | Young adult |
| | 21–25 | 1.40× | Early adult |
| | 26–64 | 1.00× | Base band |
| | 65–74 | 1.10× | Mild senior surcharge |
| | 75+ | 1.30× | Elevated senior surcharge |
| **Vehicle Value** | symbol_1 (<$10k) | 0.75× | |
| | symbol_3 ($20–35k) | 1.00× | Base symbol |
| | symbol_6 (>$80k) | 1.75× | Luxury surcharge |
| **Territory** | Urban | 1.30× | Elevated theft/collision |
| | Suburban | 1.00× | Base territory |
| | Rural | 0.85× | Lower traffic density |
| **Safety Features** | Full ADAS | 0.80× | Max telematics discount |
| **Deductible** | $2,000 | 0.73× | Maximum credit |
| **Coverage Type** | Liability Only | 0.55× | |

### GLM Credibility Blend

```
GLM_factor    = exp(β_age + β_territory + β_vehicle)   # Poisson log-link prediction
Manual_factor = Driver_Age × Vehicle × Territory        # Manual relativities only

Blended       = 0.60 × GLM_factor + 0.40 × Manual_factor
GLM_Adjustment = Blended / Manual_factor
```

The 60/40 split represents a credibility weight — in production this is derived from the statistical significance of the GLM fit and the volume of underlying claims data.

---

## Technical Notes

### Why a flat-file rate manual?

In production, personal lines carriers maintain their rate tables in actuarial systems (e.g., Guidewire, Duck Creek, or proprietary platforms) that export to structured formats for state filing. A CSV rate manual mirrors this pattern at small scale and makes the rate logic fully transparent and auditable — a regulator, actuary, or developer can inspect every number without touching the code.

### Why simulate a GLM rather than fit one?

A real GLM requires a credible claims dataset (typically 50,000+ exposures). The synthetic coefficients here are derived from the same manual relativities, intentionally offset slightly to show a non-trivial adjustment. The architecture — coefficient loading, log-link prediction, credibility blending — is identical to how a production GLM artefact would be consumed by a rating engine.

### Validation design

The two-tier validation approach — `OutOfBoundsError` for hard failures vs. warning strings for soft notices — reflects real underwriting workflow. Hard stops prevent the engine from producing a mathematically undefined rate; soft warnings surface underwriting flags (minor drivers, high-value vehicles) without blocking the quote.

---

## Getting Started

### Prerequisites

- Python 3.11 or higher
- pip

### Local Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/clearrate.git
cd clearrate

# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run app.py
```

The app opens at `http://localhost:8501`. The `rate_table.csv` is generated automatically on first run. To regenerate it manually:

```bash
python generate_rate_table.py
```

### Using the Rating Engine Directly

```python
from rating_engine import RatingEngine

engine = RatingEngine("rate_table.csv")

quote = engine.calculate_premium({
    "driver_age":      28,
    "vehicle_value":   32_000,
    "territory":       "suburban",
    "safety_features": "advanced",
    "deductible":      500,
    "coverage_type":   "full_coverage",
})

engine.print_quote_summary(quote)
# → Full actuarial step-down printed to stdout

# Sensitivity analysis
engine.print_sensitivity_report(
    base_inputs=quote.inputs,
    variables=["deductible", "territory"],
)
```

---

## Author

**Christopher Flynn**
- 🌐 [Website](christopherflynn.dev)
- 💼 [LinkedIn](https://www.linkedin.com/in/christopherflynndev/)
- 🐙 [GitHub](https://github.com/christopherFlynn)

---

## Disclaimer

This project is a portfolio demonstration. It is not a licensed insurance product and the rates shown have no actuarial basis for real-world use. It should not be used for actual underwriting or pricing decisions.

---

## License

This project is open source and available under the [MIT License](LICENSE).
