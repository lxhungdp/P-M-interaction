"""
콘크리트 기둥 단면 P-M상관도 검토 — Streamlit entry point.

Run: streamlit run app.py
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import streamlit as st

from src.codes import CODES
from pm_app.config import APP_FOOTER, PAGE_CONFIG
from pm_app.models import analysis_inputs_from_defaults
from pm_app.ui.assets import init_session_defaults, inject_assets
from pm_app.ui.panel_input import render_input_panel
from pm_app.ui.panel_output import render_output_panel

st.set_page_config(**PAGE_CONFIG)
plt.rcParams.update({"font.family": "Malgun Gothic", "axes.unicode_minus": False})

init_session_defaults()
inject_assets()

_exp = st.session_state.inp_expand
_inp_w = st.session_state.inp_width
if _exp:
    col_in, col_out = st.columns([_inp_w, 10 - _inp_w], gap="small")
else:
    col_in, col_out = st.columns([1, 11], gap="small")

with col_in:
    _sp, _bc = st.columns([5, 1])
    with _bc:
        if _exp:
            if st.button("<<", key="toggle_inp", use_container_width=True, help="입력창 접기"):
                st.session_state.inp_expand = False
                st.rerun()
        else:
            if st.button(">>", key="toggle_inp", use_container_width=True, help="입력창 펼치기"):
                st.session_state.inp_expand = True
                st.rerun()

    if _exp:
        inputs, run = render_input_panel(True)
    else:
        inputs = analysis_inputs_from_defaults()
        run = False

code = CODES[inputs.code_name]()

with col_out:
    render_output_panel(inputs, run, code)

st.markdown(
    f"<div style='text-align:center;color:#888;font-size:11px;margin-top:8px'>{APP_FOOTER}</div>",
    unsafe_allow_html=True,
)
