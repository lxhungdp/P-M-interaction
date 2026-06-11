"""Right output panel: preview, cache, result tabs."""

from __future__ import annotations

import matplotlib.pyplot as plt
import streamlit as st

from pm_app.export_workbook import build_calc_workbook_bytes
from pm_app.models import AnalysisInputs
from pm_app.pipeline import run_pm_analysis
from pm_app.ui.context import OutputContext
from pm_app.ui.tabs.tab_detail import render_tab_detail
from pm_app.ui.tabs.tab_geometry import render_tab_geometry
from pm_app.ui.tabs.tab_pm import render_tab_pm
from pm_app.ui.tabs.tab_section import render_tab_section
from pm_app.ui.tabs.tab_strain import render_tab_strain
from pm_app.ui.tabs.tab_verify import render_tab_verify
from pm_app.viz.section_draw import draw_section_preview


def render_output_panel(inputs: AnalysisInputs, run: bool, code) -> None:
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

    st.markdown("#### 단면 P-M상관도 검토")

    if st.session_state.show_preview:
        with st.expander("👁  단면 미리보기", expanded=True):
            fig_pv, ax_pv = plt.subplots(figsize=(4.5, 4.5))
            draw_section_preview(
                ax_pv, sec_type, b, h, rb_list, cover,
                poly_outer, poly_holes,
                theta_rad, bar_dia,
                n_top, n_bot, n_left, n_right,
                poly_rebar_positions, avg_Mx, avg_My,
            )
            ax_pv.set_title(
                f"{sec_type}  b={b:.0f}×h={h:.0f}mm  θ={theta_deg_auto:.1f}°",
                fontsize=8,
            )
            plt.tight_layout()
            st.pyplot(fig_pv, use_container_width=False)
            plt.close(fig_pv)
            st.markdown("""
**좌표계 안내**
- 🔴 **X →** : 수평 (Mx = X축 중립축, Y방향 휨)
- 🔵 **Y ↑** : 수직 (My = Y축 중립축, X방향 휨)
- 🟢 **y'** : 압축 방향 (θ 자동계산)

**하중 부호 규약**
| 하중 | 압축 | 인장 |
|------|------|------|
| +Mx | 상단(+Y) | 하단 |
| +My | 우측(+X) | 좌측 |
""")
            if st.button("닫기", key="close_preview"):
                st.session_state.show_preview = False
                st.rerun()

    if run:
        with st.spinner("🔄 파이버 단면 해석 중..."):
            st.session_state["pm_cache"] = run_pm_analysis(inputs)
        st.session_state["v_analysis_done"] = False

    cache = st.session_state.get("pm_cache")
    if cache is None:
        st.info("👈 왼쪽에서 입력 후 **P-M 상관도 계산** (또는 Ctrl+S)")
        st.stop()

    ctx = OutputContext.from_cache(cache, inputs)

    if cache.get("mesh_warn"):
        st.warning(cache["mesh_warn"])
    if ctx.ny_fiber_req is not None and int(ctx.ny_fiber_req) != ctx.ny_fiber_used:
        st.caption(
            f"파이버 분할(ny): 입력 **{int(ctx.ny_fiber_req)}** → 해석 **{ctx.ny_fiber_used}** "
            f"(Ag≤0.001%, cb≤0.001% 상대오차 목표로 자동 조정)")
    if cache.get("Ag_mesh_normalized"):
        st.caption(
            "콘크리트 파이버 면적을 이론 Ag에 맞게 보정했습니다. "
            "철근·강연선 면적은 그대로입니다.")

    _xl_col1, _xl_col2 = st.columns([3, 1])
    with _xl_col2:
        try:
            _xlsx = build_calc_workbook_bytes(cache, inputs, code)
            st.download_button(
                "📥 전체 계산 Excel",
                data=_xlsx,
                file_name="pm_calc_full.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                help="입력·출력·메시·P-M 데이터·P-M 차트(이미지+엑셀) 포함",
            )
        except ImportError:
            st.caption("Excel: pip install openpyxl Pillow")

    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(
        ["📊 P-M 상관도", "🔍 단면 시각화", "🧮 변형률 해석",
         "📐 기하 특성", "📋 계산 상세", "🔬 검증"],
    )

    with tab1:
        render_tab_pm(ctx)
    with tab2:
        render_tab_section(ctx)
    with tab3:
        render_tab_strain(ctx)
    with tab4:
        render_tab_geometry(ctx)
    with tab5:
        render_tab_detail(ctx, code)
    with tab6:
        render_tab_verify(ctx.to_verify())
