"""One-time helper: split app.py UI blocks into pm_app/ui modules. Safe to re-run."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.py").read_text(encoding="utf-8")
lines = APP.splitlines(keepends=True)

INPUT_HEADER = '''"""Left input panel (Streamlit widgets)."""

from __future__ import annotations

import math

import pandas as pd
import streamlit as st

from src.codes import CODES
from pm_app.models import AnalysisInputs
from pm_app.section_builder import compute_rebar_positions


def render_input_panel(expanded: bool) -> tuple[AnalysisInputs, bool]:
    """Render input widgets; return (inputs, run_clicked)."""
'''

INPUT_BODY = "".join(lines[633:872])  # inside if _exp + run button
INPUT_FOOTER = '''
    return AnalysisInputs(
        code_name=code_name, fck=fck, fy=fy, curve_conc=curve_conc,
        sec_type=sec_type, b=b, h=h, cover=cover, bar_dia=bar_dia,
        rb_list=rb_list, n_top=n_top, n_bot=n_bot, n_left=n_left, n_right=n_right,
        poly_outer=poly_outer, poly_holes=poly_holes,
        poly_rebar_positions=poly_rebar_positions,
        use_strand=use_strand, strand_params=None,
        strand_dia_val=strand_dia_val, strand_pos=strand_pos,
        fpk_val=fpk_val, fp01k_val=fp01k_val, Ep_val=Ep_val,
        fpe_val=fpe_val, eps_pe_val=eps_pe_val,
        df_loads=df_loads, avg_Mx=avg_Mx, avg_My=avg_My,
        theta_rad=theta_rad, theta_deg_auto=theta_deg_auto,
        sym_check=sym_check, n_pts=n_pts, ny_fiber=ny_fiber,
    ), run
'''

OUTPUT_HEADER = '''"""Right output panel: preview, cache, result tabs."""

from __future__ import annotations

import math

import matplotlib
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import matplotlib.ticker
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from matplotlib.patches import Circle, Polygon as MplPolygon

from src.analysis.solver import (
    pm_results_to_dataframe,
    position_summary_to_dataframe,
)
from src.codes import CODES
from src.materials.concrete import Concrete
from src.materials.rebar import Rebar

from pm_app.config import VERIFY_REF_ERR_PCT
from pm_app.models import AnalysisInputs
from pm_app.pipeline import run_pm_analysis
from pm_app.pm_checks import is_safe, m_cap, ray_intersect_pm_curve, utilization
from pm_app.section_builder import ag_theory_mm2
from pm_app.ui.tabs.tab_verify import render_tab_verify
from pm_app.viz.section_draw import draw_section_preview, draw_section_with_na


def render_output_panel(inputs: AnalysisInputs, run: bool, code) -> None:
    fcd_val = code.fcd(inputs.fck)
    ecu_val = code.epsilon_cu(inputs.fck)
    Ec_val = code.elastic_modulus_concrete(inputs.fck)
    fyd_val = code.fyd(inputs.fy)

    sec_type = inputs.sec_type
    b, h = inputs.b, inputs.h
    rb_list = inputs.rb_list
    cover = inputs.cover
    poly_outer = inputs.poly_outer
    poly_holes = inputs.poly_holes
    poly_rebar_positions = inputs.poly_rebar_positions
    theta_rad = inputs.theta_rad
    theta_deg_auto = inputs.theta_deg_auto
    bar_dia = inputs.bar_dia
    n_top, n_bot, n_left, n_right = inputs.n_top, inputs.n_bot, inputs.n_left, inputs.n_right
    avg_Mx, avg_My = inputs.avg_Mx, inputs.avg_My
    sym_check = inputs.sym_check
    strand_dia_val = inputs.strand_dia_val
    use_strand = inputs.use_strand

    st.markdown("#### 단면 P-M상관도 검토")
'''

OUTPUT_BODY = "".join(lines[886:1918])  # preview through tab6
REPLACEMENTS = [
    ("_is_safe", "is_safe"),
    ("_utilization", "utilization"),
    ("_m_cap", "m_cap"),
    ("_ray_intersect_pm_curve", "ray_intersect_pm_curve"),
    ("_ag_theory_mm2", "ag_theory_mm2"),
    ("VERIFY_REF_ERR_PCT", "VERIFY_REF_ERR_PCT"),
]
for old, new in REPLACEMENTS:
    if old != new:
        OUTPUT_BODY = OUTPUT_BODY.replace(old, new)

# Replace tab6 block with function call - find tab6 start
tab6_marker = "    with tab6:"
if tab6_marker in OUTPUT_BODY:
    pre, _ = OUTPUT_BODY.split(tab6_marker, 1)
    OUTPUT_BODY = pre + "    with tab6:\n        render_tab_verify(locals())\n"

(ROOT / "pm_app/ui").mkdir(parents=True, exist_ok=True)
(ROOT / "pm_app/ui/panel_input.py").write_text(
    INPUT_HEADER + INPUT_BODY + INPUT_FOOTER, encoding="utf-8"
)
(ROOT / "pm_app/ui/panel_output.py").write_text(
    OUTPUT_HEADER + OUTPUT_BODY, encoding="utf-8"
)
print("Wrote panel_input.py and panel_output.py")
