"""Smoke tests — always run in CI."""

from __future__ import annotations

from src.codes import CODES

from pm_app.export_workbook import build_calc_workbook_bytes
from pm_app.models import analysis_inputs_from_defaults
from pm_app.pipeline import run_pm_analysis


def test_run_pm_analysis_smoke() -> None:
    inputs = analysis_inputs_from_defaults()
    cache = run_pm_analysis(inputs)
    assert cache["N_max_v"] > 0
    assert len(cache["N_des"]) == len(cache["M_des"])
    assert cache["section"] is not None


def test_export_workbook_smoke() -> None:
    inputs = analysis_inputs_from_defaults()
    cache = run_pm_analysis(inputs)
    code = CODES[inputs.code_name]()
    xlsx = build_calc_workbook_bytes(cache, inputs, code)
    assert len(xlsx) > 5000
    assert xlsx[:2] == b"PK"  # xlsx zip header
