"""
rating_engine.py
────────────────
Personal Lines Auto Insurance — Rating Engine (v1.0)

Architecture
────────────
  RateTable        – thin wrapper around the CSV rate manual
  GLMRateAdjuster  – simulates a Poisson/log-link GLM credibility adjustment
  RatingEngine     – orchestrates loading, validation, calculation, and output
  SensitivityAnalyser – sweeps one or more factors and reports premium deltas

Multiplicative model
────────────────────
  Final Premium = Base × ∏(Relativityᵢ) × GLM_Adjustment

Usage
─────
    from rating_engine import RatingEngine

    engine = RatingEngine("rate_table.csv")
    quote  = engine.calculate_premium({
        "driver_age":      28,
        "vehicle_value":   32_000,
        "territory":       "suburban",
        "safety_features": "advanced",
        "deductible":      500,
        "coverage_type":   "full_coverage",
    })
    engine.print_quote_summary(quote)
"""

from __future__ import annotations

import math
import textwrap
from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd


# ══════════════════════════════════════════════════════════════════════════════
# Custom Exceptions
# ══════════════════════════════════════════════════════════════════════════════

class RatingError(ValueError):
    """Raised for inputs that cannot be rated under the current rate manual."""


class OutOfBoundsError(RatingError):
    """Raised when an input value is outside the permissible range."""


# ══════════════════════════════════════════════════════════════════════════════
# Data Structures
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class RatingFactor:
    """One resolved rating factor contributing to the final premium."""
    variable: str
    key: str
    relativity: float
    description: str


@dataclass
class QuoteResult:
    """Full output of a single rating calculation."""
    base_premium: float
    factors: list[RatingFactor]
    glm_adjustment: float
    final_premium: float
    inputs: dict[str, Any]
    warnings: list[str] = field(default_factory=list)

    @property
    def multiplicative_factor(self) -> float:
        """Product of all relativities (excluding GLM adjustment)."""
        product = 1.0
        for f in self.factors:
            product *= f.relativity
        return product


# ══════════════════════════════════════════════════════════════════════════════
# Rate Table
# ══════════════════════════════════════════════════════════════════════════════

class RateTable:
    """
    Loads and indexes the flat-file rate manual (CSV).

    The CSV must contain columns: Variable, Key, Relativity, Description.
    """

    REQUIRED_COLUMNS = {"Variable", "Key", "Relativity", "Description"}

    def __init__(self, csv_path: str) -> None:
        self._df = self._load(csv_path)
        self._index = self._build_index()

    # ── Public ────────────────────────────────────────────────────────────────

    def get_base_premium(self) -> float:
        """Return the statewide base annual premium."""
        return float(self._index["Base_Premium"]["base"]["relativity"])

    def get_relativity(self, variable: str, key: str) -> RatingFactor:
        """
        Look up a single relativity.

        Parameters
        ----------
        variable : str  e.g. "Driver_Age"
        key      : str  e.g. "26-64"

        Returns
        -------
        RatingFactor

        Raises
        ------
        RatingError  if the variable/key combination is not in the manual.
        """
        var_block = self._index.get(variable)
        if var_block is None:
            raise RatingError(
                f"Variable '{variable}' not found in rate table. "
                f"Available: {sorted(self._index)}"
            )
        entry = var_block.get(key)
        if entry is None:
            raise RatingError(
                f"Key '{key}' not found for variable '{variable}'. "
                f"Available keys: {sorted(var_block)}"
            )
        return RatingFactor(
            variable=variable,
            key=key,
            relativity=float(entry["relativity"]),
            description=str(entry["description"]),
        )

    def available_keys(self, variable: str) -> list[str]:
        """Return all keys defined for a given rating variable."""
        return sorted(self._index.get(variable, {}).keys())

    # ── Private ───────────────────────────────────────────────────────────────

    def _load(self, path: str) -> pd.DataFrame:
        df = pd.read_csv(path)
        missing = self.REQUIRED_COLUMNS - set(df.columns)
        if missing:
            raise ValueError(f"Rate table missing columns: {missing}")
        df["Relativity"] = pd.to_numeric(df["Relativity"], errors="raise")
        return df

    def _build_index(self) -> dict:
        """Convert the flat DataFrame into a nested dict for O(1) lookup."""
        index: dict = {}
        for _, row in self._df.iterrows():
            var = row["Variable"]
            key = str(row["Key"])
            index.setdefault(var, {})[key] = {
                "relativity": row["Relativity"],
                "description": row["Description"],
            }
        return index


# ══════════════════════════════════════════════════════════════════════════════
# GLM Rate Adjuster
# ══════════════════════════════════════════════════════════════════════════════

class GLMRateAdjuster:
    """
    Simulates the output of a fitted Generalised Linear Model (Poisson,
    log-link) that actuaries use to verify that multiplicative manual rates
    are credible.

    In production this class would hold the *fitted* GLM coefficients loaded
    from a model artefact.  Here we derive synthetic coefficients from the
    same relativities in the rate manual so the demo is self-contained.

    The log-link model:
        log(E[claims]) = β₀ + β_age·X_age + β_veh·X_veh + β_terr·X_terr + …

    The adjustment factor is:
        GLM_adj = exp(Σ βᵢ·Xᵢ) / manual_factor

    Where manual_factor is the product of manual relativities so any
    residual after the GLM is applied as a credibility correction.
    """

    # Synthetic GLM coefficients (log-scale), derived from actuarial judgment.
    # These represent the "fitted" beta parameters an actuary would load from
    # a production GLM artefact.
    _COEFFICIENTS: dict[str, float] = {
        # Driver age log-relativities
        "age_16-17":   math.log(2.35),
        "age_18-20":   math.log(1.90),
        "age_21-25":   math.log(1.38),
        "age_26-64":   math.log(1.00),
        "age_65-74":   math.log(1.08),
        "age_75+":     math.log(1.28),
        # Territory
        "terr_urban":    math.log(1.28),
        "terr_suburban": math.log(1.00),
        "terr_rural":    math.log(0.84),
        # Vehicle symbol
        "veh_symbol_1":  math.log(0.76),
        "veh_symbol_2":  math.log(0.91),
        "veh_symbol_3":  math.log(1.00),
        "veh_symbol_4":  math.log(1.19),
        "veh_symbol_5":  math.log(1.44),
        "veh_symbol_6":  math.log(1.74),
    }

    def compute_adjustment(
        self,
        age_band: str,
        territory: str,
        vehicle_symbol: str,
        manual_relativity_product: float,
    ) -> float:
        """
        Return the GLM credibility multiplier.

        Parameters
        ----------
        age_band               : e.g. "26-64"
        territory              : e.g. "suburban"
        vehicle_symbol         : e.g. "symbol_3"
        manual_relativity_product : product of manual relativities for these
                                    three variables only

        Returns
        -------
        float  GLM adjustment factor (≈1.00 if model agrees with manual)
        """
        log_pred = (
            self._COEFFICIENTS.get(f"age_{age_band}", 0.0)
            + self._COEFFICIENTS.get(f"terr_{territory}", 0.0)
            + self._COEFFICIENTS.get(f"veh_{vehicle_symbol}", 0.0)
        )
        glm_factor = math.exp(log_pred)
        # Credibility blend: 60% GLM, 40% manual
        credibility = 0.60
        blended = (credibility * glm_factor
                   + (1 - credibility) * manual_relativity_product)
        adjustment = blended / manual_relativity_product
        return round(adjustment, 6)


# ══════════════════════════════════════════════════════════════════════════════
# Input Validator
# ══════════════════════════════════════════════════════════════════════════════

class InputValidator:
    """
    Validates raw user input before it reaches the rating logic.

    Rules
    -----
    - driver_age   : integer 16–120
    - vehicle_value: positive number
    - territory    : one of {urban, suburban, rural}
    - safety_features: one of {none, basic, advanced, full_adas}
    - deductible   : one of {250, 500, 1000, 2000}
    - coverage_type: one of {liability_only, full_coverage}
    """

    VALID_TERRITORIES    = {"urban", "suburban", "rural"}
    VALID_SAFETY         = {"none", "basic", "advanced", "full_adas"}
    VALID_DEDUCTIBLES    = {250, 500, 1000, 2000}
    VALID_COVERAGE_TYPES = {"liability_only", "full_coverage"}

    MIN_INSURABLE_AGE = 16
    MAX_INSURABLE_AGE = 120
    MIN_VEHICLE_VALUE = 1.0

    def validate(self, inputs: dict[str, Any]) -> list[str]:
        """
        Run all validation rules.

        Returns
        -------
        list[str]  List of warning messages (non-fatal oddities).

        Raises
        ------
        OutOfBoundsError  for inputs that cannot be rated at all.
        RatingError       for missing required fields.
        """
        warnings: list[str] = []
        self._check_required_fields(inputs)
        self._validate_age(inputs["driver_age"])
        self._validate_vehicle_value(inputs["vehicle_value"])
        self._validate_enum("territory",     inputs["territory"],     self.VALID_TERRITORIES)
        self._validate_enum("safety_features", inputs["safety_features"], self.VALID_SAFETY)
        self._validate_deductible(inputs["deductible"])
        self._validate_enum("coverage_type", inputs["coverage_type"], self.VALID_COVERAGE_TYPES)

        # Soft warnings (rated but flagged)
        age = int(inputs["driver_age"])
        if age < 18:
            warnings.append(
                f"Driver age {age} is below 18 — parental consent or named exclusion may be required."
            )
        if age >= 75:
            warnings.append(
                f"Driver age {age} ≥ 75 — additional medical certification may be required in some states."
            )
        if inputs["vehicle_value"] > 150_000:
            warnings.append(
                f"Vehicle value ${inputs['vehicle_value']:,.0f} exceeds $150 000 — "
                "refer to high-value vehicle underwriting guidelines."
            )
        return warnings

    # ── Private helpers ───────────────────────────────────────────────────────

    def _check_required_fields(self, inputs: dict) -> None:
        required = {
            "driver_age", "vehicle_value", "territory",
            "safety_features", "deductible", "coverage_type",
        }
        missing = required - inputs.keys()
        if missing:
            raise RatingError(f"Missing required input fields: {sorted(missing)}")

    def _validate_age(self, age: Any) -> None:
        try:
            age = int(age)
        except (TypeError, ValueError):
            raise OutOfBoundsError(f"driver_age must be a whole number, got: {age!r}")
        if age < self.MIN_INSURABLE_AGE:
            raise OutOfBoundsError(
                f"driver_age {age} is below the minimum insurable age of {self.MIN_INSURABLE_AGE}. "
                "Cannot produce a quote."
            )
        if age > self.MAX_INSURABLE_AGE:
            raise OutOfBoundsError(
                f"driver_age {age} exceeds the maximum insurable age of {self.MAX_INSURABLE_AGE}."
            )

    def _validate_vehicle_value(self, value: Any) -> None:
        try:
            value = float(value)
        except (TypeError, ValueError):
            raise OutOfBoundsError(f"vehicle_value must be numeric, got: {value!r}")
        if value < self.MIN_VEHICLE_VALUE:
            raise OutOfBoundsError(
                f"vehicle_value ${value:,.2f} is below the minimum insurable value."
            )

    def _validate_enum(self, field: str, value: Any, valid: set) -> None:
        if value not in valid:
            raise RatingError(
                f"'{field}' value '{value}' is not recognised. "
                f"Valid options: {sorted(valid)}"
            )

    def _validate_deductible(self, value: Any) -> None:
        try:
            value = int(value)
        except (TypeError, ValueError):
            raise RatingError(f"deductible must be an integer, got: {value!r}")
        if value not in self.VALID_DEDUCTIBLES:
            raise RatingError(
                f"Deductible ${value} is not on the rating schedule. "
                f"Valid options: {sorted(self.VALID_DEDUCTIBLES)}"
            )


# ══════════════════════════════════════════════════════════════════════════════
# Symbol Mapper
# ══════════════════════════════════════════════════════════════════════════════

class VehicleSymbolMapper:
    """Maps a continuous vehicle value (USD) to the ISO symbol key used in the rate table."""

    _BANDS: list[tuple[float, float, str]] = [
        (0,       9_999.99,  "symbol_1"),
        (10_000,  19_999.99, "symbol_2"),
        (20_000,  34_999.99, "symbol_3"),
        (35_000,  54_999.99, "symbol_4"),
        (55_000,  79_999.99, "symbol_5"),
        (80_000,  math.inf,  "symbol_6"),
    ]

    def map(self, vehicle_value: float) -> str:
        """Return the symbol key for a given vehicle value."""
        for low, high, symbol in self._BANDS:
            if low <= vehicle_value <= high:
                return symbol
        raise OutOfBoundsError(f"Cannot map vehicle value ${vehicle_value:,.2f} to a symbol.")


# ══════════════════════════════════════════════════════════════════════════════
# Age Band Mapper
# ══════════════════════════════════════════════════════════════════════════════

class AgeBandMapper:
    """Maps an integer driver age to the rating band key used in the rate table."""

    _BANDS: list[tuple[int, int, str]] = [
        (16, 17, "16-17"),
        (18, 20, "18-20"),
        (21, 25, "21-25"),
        (26, 64, "26-64"),
        (65, 74, "65-74"),
        (75, 120, "75+"),
    ]

    def map(self, age: int) -> str:
        """Return the age-band key for an integer driver age."""
        for low, high, band in self._BANDS:
            if low <= age <= high:
                return band
        raise OutOfBoundsError(f"Age {age} does not map to any defined age band.")


# ══════════════════════════════════════════════════════════════════════════════
# Sensitivity Analyser
# ══════════════════════════════════════════════════════════════════════════════

class SensitivityAnalyser:
    """
    Sweeps one rating variable across all its permissible values and reports
    the resulting premium change relative to the base quote.

    Parameters
    ----------
    engine : RatingEngine  the engine instance to call for each scenario
    """

    def __init__(self, engine: "RatingEngine") -> None:
        self._engine = engine

    def analyse(
        self,
        base_inputs: dict[str, Any],
        variable: str,
        sweep_values: list[Any] | None = None,
    ) -> pd.DataFrame:
        """
        Produce a sensitivity table for one variable.

        Parameters
        ----------
        base_inputs   : the original quote inputs (will not be mutated)
        variable      : the input key to sweep (e.g. "deductible", "territory")
        sweep_values  : explicit list of values to test; if None the engine
                        auto-discovers them from the rate table

        Returns
        -------
        pd.DataFrame with columns:
            Value, Premium, Delta_vs_Base, Pct_Change
        """
        base_quote = self._engine.calculate_premium(base_inputs)
        base_prem  = base_quote.final_premium

        if sweep_values is None:
            sweep_values = self._default_sweep(variable)

        rows = []
        for val in sweep_values:
            trial = {**base_inputs, variable: val}
            try:
                q = self._engine.calculate_premium(trial)
                rows.append({
                    "Value":         val,
                    "Premium":       round(q.final_premium, 2),
                    "Delta_vs_Base": round(q.final_premium - base_prem, 2),
                    "Pct_Change":    round((q.final_premium - base_prem) / base_prem * 100, 2),
                })
            except RatingError as exc:
                rows.append({
                    "Value":         val,
                    "Premium":       None,
                    "Delta_vs_Base": None,
                    "Pct_Change":    None,
                })

        df = pd.DataFrame(rows)
        df.insert(0, "Variable", variable)
        return df

    def _default_sweep(self, variable: str) -> list[Any]:
        """Derive sensible sweep values from the engine's rate table."""
        lookup = {
            "deductible":     [250, 500, 1000, 2000],
            "territory":      ["urban", "suburban", "rural"],
            "coverage_type":  ["liability_only", "full_coverage"],
            "safety_features":["none", "basic", "advanced", "full_adas"],
        }
        if variable in lookup:
            return lookup[variable]
        raise RatingError(
            f"No default sweep defined for '{variable}'. Pass explicit sweep_values."
        )


# ══════════════════════════════════════════════════════════════════════════════
# Rating Engine  ← primary public API
# ══════════════════════════════════════════════════════════════════════════════

class RatingEngine:
    """
    Personal Lines Auto Insurance Rating Engine.

    Parameters
    ----------
    rate_table_path : str  Path to the CSV rate manual.

    Example
    -------
    >>> engine = RatingEngine("rate_table.csv")
    >>> quote  = engine.calculate_premium({
    ...     "driver_age":      28,
    ...     "vehicle_value":   32_000,
    ...     "territory":       "suburban",
    ...     "safety_features": "advanced",
    ...     "deductible":      500,
    ...     "coverage_type":   "full_coverage",
    ... })
    >>> engine.print_quote_summary(quote)
    """

    def __init__(self, rate_table_path: str = "rate_table.csv") -> None:
        self._table     = RateTable(rate_table_path)
        self._validator = InputValidator()
        self._glm       = GLMRateAdjuster()
        self._age_mapper = AgeBandMapper()
        self._sym_mapper = VehicleSymbolMapper()
        self.sensitivity = SensitivityAnalyser(self)

    # ── Public API ────────────────────────────────────────────────────────────

    def calculate_premium(self, inputs: dict[str, Any]) -> QuoteResult:
        """
        Rate a single risk and return a fully-detailed QuoteResult.

        Parameters
        ----------
        inputs : dict with keys:
            driver_age      (int)   : age of primary driver
            vehicle_value   (float) : market value of vehicle in USD
            territory       (str)   : "urban" | "suburban" | "rural"
            safety_features (str)   : "none" | "basic" | "advanced" | "full_adas"
            deductible      (int)   : 250 | 500 | 1000 | 2000
            coverage_type   (str)   : "liability_only" | "full_coverage"

        Returns
        -------
        QuoteResult

        Raises
        ------
        OutOfBoundsError  for uninsurable inputs
        RatingError       for unrecognised input values
        """
        # ── 1. Validate inputs ────────────────────────────────────────────────
        warnings = self._validator.validate(inputs)

        # ── 2. Resolve lookup keys ────────────────────────────────────────────
        age_band = self._age_mapper.map(int(inputs["driver_age"]))
        veh_sym  = self._sym_mapper.map(float(inputs["vehicle_value"]))
        territory = str(inputs["territory"])

        # ── 3. Look up each rating factor from the manual ─────────────────────
        factors: list[RatingFactor] = [
            self._table.get_relativity("Driver_Age",      age_band),
            self._table.get_relativity("Vehicle_Value",   veh_sym),
            self._table.get_relativity("Territory",       territory),
            self._table.get_relativity("Safety_Features", str(inputs["safety_features"])),
            self._table.get_relativity("Deductible",      str(inputs["deductible"])),
            self._table.get_relativity("Coverage_Type",   str(inputs["coverage_type"])),
        ]

        # ── 4. Compute manual product ─────────────────────────────────────────
        base = self._table.get_base_premium()
        manual_product = math.prod(f.relativity for f in factors)

        # GLM adjustment uses only the three primary risk dimensions
        primary_manual = math.prod(
            f.relativity for f in factors
            if f.variable in {"Driver_Age", "Vehicle_Value", "Territory"}
        )

        # ── 5. GLM credibility adjustment ─────────────────────────────────────
        glm_adj = self._glm.compute_adjustment(
            age_band=age_band,
            territory=territory,
            vehicle_symbol=veh_sym,
            manual_relativity_product=primary_manual,
        )

        # ── 6. Final premium ──────────────────────────────────────────────────
        final = round(base * manual_product * glm_adj, 2)

        return QuoteResult(
            base_premium   = base,
            factors        = factors,
            glm_adjustment = glm_adj,
            final_premium  = final,
            inputs         = dict(inputs),
            warnings       = warnings,
        )

    # ── Presentation ──────────────────────────────────────────────────────────

    def print_quote_summary(self, quote: QuoteResult) -> None:
        """Print a formatted actuarial quote summary to stdout."""
        SEP  = "─" * 72
        SEP2 = "═" * 72

        print()
        print(SEP2)
        print("  AUTO INSURANCE — PERSONAL LINES QUOTE SUMMARY")
        print(SEP2)

        # ── Input block ───────────────────────────────────────────────────────
        print("\n  ▸ RISK CHARACTERISTICS")
        print(SEP)
        for k, v in quote.inputs.items():
            label = k.replace("_", " ").title()
            val   = f"${v:,.0f}" if k == "vehicle_value" else str(v)
            print(f"    {label:<22} {val}")

        # ── Rating step-down ──────────────────────────────────────────────────
        print(f"\n  ▸ PREMIUM BUILD-UP")
        print(SEP)
        print(f"  {'Step':<4}  {'Variable':<20} {'Key':<18} {'Relativity':>10}  {'Running Total':>14}")
        print(SEP)

        running = quote.base_premium
        print(f"  {'0':<4}  {'Base Premium':<20} {'—':<18} {'—':>10}  ${running:>13,.2f}")

        for i, f in enumerate(quote.factors, start=1):
            running *= f.relativity
            print(
                f"  {i:<4}  {f.variable:<20} {f.key:<18} "
                f"{f.relativity:>10.4f}  ${running:>13,.2f}"
            )

        # ── GLM adjustment ────────────────────────────────────────────────────
        print(SEP)
        running *= quote.glm_adjustment
        print(
            f"  {'GLM':<4}  {'GLM Credibility Adj':<20} {'log-link model':<18} "
            f"{quote.glm_adjustment:>10.4f}  ${running:>13,.2f}"
        )

        # ── Final ─────────────────────────────────────────────────────────────
        print(SEP2)
        print(f"  {'FINAL ANNUAL PREMIUM':<44}        ${quote.final_premium:>13,.2f}")
        print(f"  {'FINAL MONTHLY PREMIUM':<44}        ${quote.final_premium/12:>13,.2f}")
        print(SEP2)

        # ── Warnings ──────────────────────────────────────────────────────────
        if quote.warnings:
            print("\n  ⚠  UNDERWRITING NOTICES")
            print(SEP)
            for w in quote.warnings:
                for line in textwrap.wrap(w, width=66):
                    print(f"    • {line}")

        print()

    def print_sensitivity_report(
        self,
        base_inputs: dict[str, Any],
        variables: list[str] | None = None,
    ) -> None:
        """
        Print a formatted sensitivity analysis for one or more variables.

        Parameters
        ----------
        base_inputs : original quote inputs
        variables   : list of keys to sweep; defaults to deductible + territory
        """
        if variables is None:
            variables = ["deductible", "territory", "coverage_type", "safety_features"]

        SEP  = "─" * 72
        SEP2 = "═" * 72
        base_prem = self.calculate_premium(base_inputs).final_premium

        print()
        print(SEP2)
        print("  SENSITIVITY ANALYSIS REPORT")
        print(f"  Base Annual Premium: ${base_prem:,.2f}")
        print(SEP2)

        for var in variables:
            df = self.sensitivity.analyse(base_inputs, var)
            print(f"\n  Variable: {var.upper()}")
            print(SEP)
            print(f"  {'Value':<18} {'Premium':>10} {'Delta ($)':>12} {'Delta (%)':>10}")
            print(SEP)
            for _, row in df.iterrows():
                marker = " ◄ current" if str(row["Value"]) == str(base_inputs.get(var)) else ""
                print(
                    f"  {str(row['Value']):<18} "
                    f"${row['Premium']:>9,.2f} "
                    f"${row['Delta_vs_Base']:>+11,.2f} "
                    f"{row['Pct_Change']:>+9.1f}%"
                    f"{marker}"
                )
        print()
