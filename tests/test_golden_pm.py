"""Golden regression tests for run_pm_analysis."""

from __future__ import annotations

import pathlib

import pandas as pd
import pytest
import yaml

from pm_app.models import AnalysisInputs
from pm_app.pipeline import run_pm_analysis

GOLDEN_DIR = pathlib.Path(__file__).parent / "golden"


def _load_cases():
    cases = []
    for path in sorted(GOLDEN_DIR.glob("*.yaml")):
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        data["_path"] = path
        cases.append(data)
    return cases


def _build_inputs(raw: dict) -> AnalysisInputs:
    df_raw = raw.get("df_loads", {})
    df = pd.DataFrame(df_raw) if df_raw else pd.DataFrame()
    return AnalysisInputs(
        code_name=raw["code_name"],
        fck=float(raw["fck"]),
        fy=float(raw["fy"]),
        curve_conc=raw["curve_conc"],
        sec_type=raw["sec_type"],
        b=float(raw["b"]),
        h=float(raw["h"]),
        cover=float(raw["cover"]),
        bar_dia=float(raw["bar_dia"]),
        rb_list=raw.get("rb_list", []),
        n_top=int(raw["n_top"]),
        n_bot=int(raw["n_bot"]),
        n_left=int(raw["n_left"]),
        n_right=int(raw["n_right"]),
        poly_outer=raw.get("poly_outer"),
        poly_holes=raw.get("poly_holes", []),
        poly_rebar_positions=raw.get("poly_rebar_positions", []),
        use_strand=bool(raw.get("use_strand", False)),
        strand_params=None,
        strand_dia_val=float(raw.get("strand_dia_val", 15.2)),
        strand_pos=raw.get("strand_pos", []),
        fpk_val=float(raw.get("fpk_val", 0)),
        fp01k_val=float(raw.get("fp01k_val", 0)),
        Ep_val=float(raw.get("Ep_val", 0)),
        fpe_val=float(raw.get("fpe_val", 0)),
        eps_pe_val=float(raw.get("eps_pe_val", 0)),
        df_loads=df,
        avg_Mx=float(raw.get("avg_Mx", 1.0)),
        avg_My=float(raw.get("avg_My", 0.0)),
        theta_rad=float(raw.get("theta_rad", 0.0)),
        theta_deg_auto=float(raw.get("theta_deg_auto", 0.0)),
        sym_check=bool(raw.get("sym_check", False)),
        n_pts=int(raw.get("n_pts", 200)),
        ny_fiber=int(raw.get("ny_fiber", 120)),
    )


def _check_value(actual: float, spec: dict, name: str) -> None:
    if "abs_tol" in spec:
        assert abs(actual - spec["value"]) <= spec["abs_tol"], (
            f"{name}: {actual} vs {spec['value']} (abs_tol={spec['abs_tol']})"
        )
    elif "rel_pct" in spec:
        ref = spec["value"]
        if abs(ref) < 1e-9:
            assert abs(actual - ref) <= spec.get("abs_tol", 1e-6), f"{name}: {actual} vs {ref}"
        else:
            err_pct = abs(actual - ref) / abs(ref) * 100
            assert err_pct <= spec["rel_pct"], (
                f"{name}: {err_pct:.2f}% > {spec['rel_pct']}% ({actual} vs {ref})"
            )


@pytest.mark.parametrize("case", _load_cases(), ids=lambda c: c["id"])
def test_golden_pm(case: dict) -> None:
    expected = case.get("expected", {})
    if expected.get("skip"):
        pytest.skip(f"Case {case['id']} not yet confirmed — set expected.skip: false")

    inputs = _build_inputs(case["inputs"])
    cache = run_pm_analysis(inputs)

    for key, spec in expected.items():
        if key in ("skip",):
            continue
        if not isinstance(spec, dict) or "value" not in spec:
            continue
        assert key in cache, f"Missing cache key: {key}"
        _check_value(float(cache[key]), spec, key)
