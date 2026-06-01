"""Smoke tests — always run in CI."""

from __future__ import annotations

from pm_app.models import analysis_inputs_from_defaults
from pm_app.pipeline import run_pm_analysis


def test_run_pm_analysis_smoke() -> None:
    inputs = analysis_inputs_from_defaults()
    cache = run_pm_analysis(inputs)
    assert cache["N_max_v"] > 0
    assert len(cache["N_des"]) == len(cache["M_des"])
    assert cache["section"] is not None
