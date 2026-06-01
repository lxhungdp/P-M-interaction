"""Input defaults and analysis dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd


@dataclass
class AnalysisInputs:
    """All inputs required for run_pm_analysis (no Streamlit)."""

    code_name: str
    fck: float
    fy: float
    curve_conc: str
    sec_type: str
    b: float
    h: float
    cover: float
    bar_dia: float
    rb_list: list
    n_top: int
    n_bot: int
    n_left: int
    n_right: int
    poly_outer: Optional[list]
    poly_holes: list
    poly_rebar_positions: list
    use_strand: bool
    strand_params: Optional[dict]
    strand_dia_val: float
    strand_pos: list
    fpk_val: float
    fp01k_val: float
    Ep_val: float
    fpe_val: float
    eps_pe_val: float
    df_loads: pd.DataFrame
    avg_Mx: float
    avg_My: float
    theta_rad: float
    theta_deg_auto: float
    sym_check: bool
    n_pts: int
    ny_fiber: int


def analysis_inputs_from_defaults(d: Optional[Dict[str, Any]] = None) -> AnalysisInputs:
    """Build AnalysisInputs from default_input_values() dict."""
    if d is None:
        d = default_input_values()
    return AnalysisInputs(
        code_name=d["code_name"],
        fck=d["fck"],
        fy=d["fy"],
        curve_conc=d["curve_conc"],
        sec_type=d["sec_type"],
        b=d["b"],
        h=d["h"],
        cover=d["cover"],
        bar_dia=d["bar_dia"],
        rb_list=d["rb_list"],
        n_top=d["n_top"],
        n_bot=d["n_bot"],
        n_left=d["n_left"],
        n_right=d["n_right"],
        poly_outer=d["poly_outer"],
        poly_holes=d["poly_holes"],
        poly_rebar_positions=d["poly_rebar_positions"],
        use_strand=d["use_strand"],
        strand_params=d["strand_params"],
        strand_dia_val=d["strand_dia_val"],
        strand_pos=d.get("strand_pos", []),
        fpk_val=d["fpk_val"],
        fp01k_val=d["fp01k_val"],
        Ep_val=d["Ep_val"],
        fpe_val=d["fpe_val"],
        eps_pe_val=d["eps_pe_val"],
        df_loads=d["df_loads"],
        avg_Mx=d["avg_Mx"],
        avg_My=d["avg_My"],
        theta_rad=d["theta_rad"],
        theta_deg_auto=d["theta_deg_auto"],
        sym_check=d["sym_check"],
        n_pts=d["n_pts"],
        ny_fiber=d["ny_fiber"],
    )


def default_input_values() -> Dict[str, Any]:
    """Fallback values when input panel is collapsed."""
    return {
        "code_name": "KDS 24 14 21:2025",
        "fck": 30.0,
        "fy": 400.0,
        "curve_conc": "parabolic_rectangular",
        "sec_type": "직사각형",
        "b": 400.0,
        "h": 600.0,
        "n_top": 4,
        "dia_top": 32,
        "cov_top": 70,
        "n_bot": 4,
        "dia_bot": 32,
        "cov_bot": 70,
        "n_left": 0,
        "dia_left": 25,
        "cov_left": 40,
        "n_right": 0,
        "dia_right": 25,
        "cov_right": 40,
        "cover": 70,
        "bar_dia": 32,
        "rb_list": [],
        "poly_outer": None,
        "poly_holes": [],
        "poly_rebar_positions": [],
        "use_strand": False,
        "strand_params": None,
        "strand_dia_val": 15.2,
        "strand_pos": [],
        "fpk_val": 0,
        "fp01k_val": 0,
        "Ep_val": 0,
        "fpe_val": 0,
        "eps_pe_val": 0,
        "df_loads": pd.DataFrame({
            "극단": [False],
            "케이스": ["LC1"],
            "Pu [kN]": [3000.0],
            "Mx [kN·m]": [450.0],
            "My [kN·m]": [0.0],
        }),
        "avg_Mx": 1.0,
        "avg_My": 0.0,
        "theta_rad": 0.0,
        "theta_deg_auto": 0.0,
        "sym_check": False,
        "n_pts": 200,
        "ny_fiber": 120,
        "run": False,
    }
