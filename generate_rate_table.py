"""
generate_rate_table.py
──────────────────────
Helper script that produces `rate_table.csv`, the flat-file rate manual
consumed by the Personal Lines Auto Rating Engine.

Each section of the file encodes one rating variable:
  • Base_Premium        – the statewide base rate before any relativities
  • Driver_Age          – age-band relativities (surcharge / discount vs. base)
  • Vehicle_Value       – symbol-tier relativities tied to vehicle cost bands
  • Territory           – geographic risk relativities (3 regions)
  • Safety_Features     – discount factor for advanced driver-assist tech
  • Deductible          – credit factor for chosen collision deductible
  • Coverage_Type       – multiplier for Liability-Only vs. Full Coverage

Usage
-----
    python generate_rate_table.py        → writes rate_table.csv
"""

import csv
import pathlib

OUTPUT_FILE = pathlib.Path("rate_table.csv")

# ──────────────────────────────────────────────────────────────────────────────
# Rate manual data
# Each row: (variable, key, relativity, description)
# ──────────────────────────────────────────────────────────────────────────────
ROWS: list[tuple[str, str, float, str]] = [

    # ── Base premium ──────────────────────────────────────────────────────────
    ("Base_Premium",     "base",          800.00,  "Annual base premium (USD)"),

    # ── Driver Age relativities ───────────────────────────────────────────────
    # Young / inexperienced drivers carry the highest surcharges.
    # A relativity of 1.00 is the base (indexed to the 26–64 age band).
    ("Driver_Age",       "16-17",         2.40,  "Teen driver surcharge"),
    ("Driver_Age",       "18-20",         1.95,  "Young adult surcharge"),
    ("Driver_Age",       "21-25",         1.40,  "Early adult surcharge"),
    ("Driver_Age",       "26-64",         1.00,  "Standard adult (base)"),
    ("Driver_Age",       "65-74",         1.10,  "Senior mild surcharge"),
    ("Driver_Age",       "75+",           1.30,  "Senior elevated surcharge"),

    # ── Vehicle Value (Symbol) relativities ───────────────────────────────────
    # Symbols represent cost-to-replace brackets used in ISO rating plans.
    ("Vehicle_Value",    "symbol_1",      0.75,  "Vehicle value < $10 000"),
    ("Vehicle_Value",    "symbol_2",      0.90,  "Vehicle value $10 000 – $19 999"),
    ("Vehicle_Value",    "symbol_3",      1.00,  "Vehicle value $20 000 – $34 999 (base)"),
    ("Vehicle_Value",    "symbol_4",      1.20,  "Vehicle value $35 000 – $54 999"),
    ("Vehicle_Value",    "symbol_5",      1.45,  "Vehicle value $55 000 – $79 999"),
    ("Vehicle_Value",    "symbol_6",      1.75,  "Vehicle value ≥ $80 000"),

    # ── Territory relativities ────────────────────────────────────────────────
    # Reflects claim frequency / severity differences across geographies.
    ("Territory",        "urban",         1.30,  "High-density urban — elevated theft/collision"),
    ("Territory",        "suburban",      1.00,  "Suburban — base territory"),
    ("Territory",        "rural",         0.85,  "Rural — lower traffic density"),

    # ── Safety Features discount ──────────────────────────────────────────────
    # Applied multiplicatively; values < 1.00 represent discounts.
    ("Safety_Features",  "none",          1.00,  "No advanced safety systems"),
    ("Safety_Features",  "basic",         0.95,  "ABS + airbags only"),
    ("Safety_Features",  "advanced",      0.88,  "ADAS (lane-keep, auto-brake, blind-spot)"),
    ("Safety_Features",  "full_adas",     0.80,  "Full ADAS + telematics discount"),

    # ── Deductible credits ────────────────────────────────────────────────────
    # Higher deductible → insurer pays less → lower premium.
    ("Deductible",       "250",           1.20,  "Deductible $250"),
    ("Deductible",       "500",           1.00,  "Deductible $500 (base)"),
    ("Deductible",       "1000",          0.85,  "Deductible $1 000"),
    ("Deductible",       "2000",          0.73,  "Deductible $2 000"),

    # ── Coverage Type ─────────────────────────────────────────────────────────
    ("Coverage_Type",    "liability_only", 0.55, "Liability-only coverage"),
    ("Coverage_Type",    "full_coverage",  1.00, "Full coverage — collision + comprehensive (base)"),
]

# ──────────────────────────────────────────────────────────────────────────────
# Write CSV
# ──────────────────────────────────────────────────────────────────────────────
HEADERS = ["Variable", "Key", "Relativity", "Description"]

with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as fh:
    writer = csv.writer(fh)
    writer.writerow(HEADERS)
    writer.writerows(ROWS)

print(f"✓  Rate table written → {OUTPUT_FILE.resolve()}  ({len(ROWS)} rows)")
