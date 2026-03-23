"""
main.py
───────
Demonstration script for the Personal Lines Auto Rating Engine.

Scenarios
─────────
  1. Standard adult driver  – baseline quote
  2. Teen driver            – high-risk surcharge demonstration
  3. Senior driver          – moderate surcharge + underwriting notice
  4. High-value vehicle     – luxury SUV, urban territory
  5. Invalid input          – age 14 (below minimum) → graceful error
  6. Sensitivity Analysis   – shows premium impact of deductible / territory moves

Run
───
    python main.py
"""

from __future__ import annotations

from rating_engine import RatingEngine, OutOfBoundsError, RatingError

# ── Bootstrap ─────────────────────────────────────────────────────────────────
import generate_rate_table  # noqa: F401 — side-effect: writes rate_table.csv

engine = RatingEngine("rate_table.csv")


# ══════════════════════════════════════════════════════════════════════════════
# Scenario helpers
# ══════════════════════════════════════════════════════════════════════════════

def banner(title: str) -> None:
    print("\n" + "▓" * 72)
    print(f"  {title}")
    print("▓" * 72)


# ══════════════════════════════════════════════════════════════════════════════
# Scenario 1 — Standard adult, suburban, mid-range vehicle
# ══════════════════════════════════════════════════════════════════════════════

banner("SCENARIO 1 — Standard Adult Driver")
std_inputs = {
    "driver_age":      35,
    "vehicle_value":   28_000,   # symbol_3
    "territory":       "suburban",
    "safety_features": "advanced",
    "deductible":      500,
    "coverage_type":   "full_coverage",
}
quote_std = engine.calculate_premium(std_inputs)
engine.print_quote_summary(quote_std)


# ══════════════════════════════════════════════════════════════════════════════
# Scenario 2 — Teen driver (17), rural, economy car
# ══════════════════════════════════════════════════════════════════════════════

banner("SCENARIO 2 — Teen Driver")
teen_inputs = {
    "driver_age":      17,
    "vehicle_value":   8_500,    # symbol_1
    "territory":       "rural",
    "safety_features": "basic",
    "deductible":      1000,
    "coverage_type":   "full_coverage",
}
quote_teen = engine.calculate_premium(teen_inputs)
engine.print_quote_summary(quote_teen)


# ══════════════════════════════════════════════════════════════════════════════
# Scenario 3 — Senior driver (78), urban, mid-range
# ══════════════════════════════════════════════════════════════════════════════

banner("SCENARIO 3 — Senior Driver (underwriting notice expected)")
senior_inputs = {
    "driver_age":      78,
    "vehicle_value":   22_000,   # symbol_3
    "territory":       "urban",
    "safety_features": "none",
    "deductible":      500,
    "coverage_type":   "full_coverage",
}
quote_senior = engine.calculate_premium(senior_inputs)
engine.print_quote_summary(quote_senior)


# ══════════════════════════════════════════════════════════════════════════════
# Scenario 4 — High-value vehicle, urban, liability only
# ══════════════════════════════════════════════════════════════════════════════

banner("SCENARIO 4 — High-Value Luxury Vehicle, Urban Territory")
luxury_inputs = {
    "driver_age":      42,
    "vehicle_value":   95_000,   # symbol_6
    "territory":       "urban",
    "safety_features": "full_adas",
    "deductible":      2000,
    "coverage_type":   "full_coverage",
}
quote_luxury = engine.calculate_premium(luxury_inputs)
engine.print_quote_summary(quote_luxury)


# ══════════════════════════════════════════════════════════════════════════════
# Scenario 5 — Invalid input: driver aged 14 (below minimum insurable age)
# ══════════════════════════════════════════════════════════════════════════════

banner("SCENARIO 5 — Out-of-Bounds Input (age 14 — expect graceful error)")
invalid_inputs = {
    "driver_age":      14,   # ← below minimum insurable age of 16
    "vehicle_value":   15_000,
    "territory":       "suburban",
    "safety_features": "none",
    "deductible":      500,
    "coverage_type":   "full_coverage",
}
try:
    engine.calculate_premium(invalid_inputs)
except OutOfBoundsError as exc:
    print(f"\n  ✖  OutOfBoundsError caught (as expected):")
    print(f"     {exc}\n")


# ══════════════════════════════════════════════════════════════════════════════
# Scenario 6 — Invalid input: unrecognised territory
# ══════════════════════════════════════════════════════════════════════════════

banner("SCENARIO 6 — Out-of-Bounds Input (unrecognised territory)")
bad_territory = {**std_inputs, "territory": "mountain"}
try:
    engine.calculate_premium(bad_territory)
except RatingError as exc:
    print(f"\n  ✖  RatingError caught (as expected):")
    print(f"     {exc}\n")


# ══════════════════════════════════════════════════════════════════════════════
# Scenario 7 — Sensitivity Analysis on standard adult quote
# ══════════════════════════════════════════════════════════════════════════════

banner("SCENARIO 7 — Sensitivity Analysis (Standard Adult Quote)")
engine.print_sensitivity_report(
    base_inputs=std_inputs,
    variables=["deductible", "territory", "coverage_type", "safety_features"],
)
