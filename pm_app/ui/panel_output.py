"""Right output panel: preview, cache, result tabs."""

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
    # ── 미리보기 ────────────────────────────────────────────────
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
                fontsize=8)
            plt.tight_layout()
            # 그림 먼저 표시
            st.pyplot(fig_pv, use_container_width=False); plt.close(fig_pv)
            # 하중 부호 규약은 그림 아래에
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
                st.session_state.show_preview = False; st.rerun()

    # ══════════════════════════════════════════════════════════════
    # 계산 실행 (run=True 시 수행 후 session_state에 캐시)
    # ══════════════════════════════════════════════════════════════
    if run:
        with st.spinner("🔄 파이버 단면 해석 중..."):
            st.session_state["pm_cache"] = run_pm_analysis(inputs)
        st.session_state["v_analysis_done"] = False


    # ── 캐시에서 결과 복원 ─────────────────────────────────────────
    _cache = st.session_state.get("pm_cache")
    if _cache is None:
        st.info("👈 왼쪽에서 입력 후 **P-M 상관도 계산** (또는 Ctrl+S)")
        st.stop()

    # 캐시 언팩 (run=False 재실행 시에도 이전 계산 결과 사용)
    N_des = np.array(_cache["N_des"]);  M_des = np.array(_cache["M_des"])
    N_nom = np.array(_cache["N_nom"]);  M_nom = np.array(_cache["M_nom"])
    N_max_v      = _cache["N_max_v"];   N_bal = _cache["N_bal"]
    M_bal        = _cache["M_bal"];     M_p0  = _cache["M_p0"]
    N_p0         = _cache["N_p0"]
    n_pts        = int(_cache.get("n_pts", 200))
    c_bal_mm     = _cache["c_bal_mm"]
    eps_bal_top  = _cache["eps_bal_top"]
    eps_bal_bot  = _cache["eps_bal_bot"]
    lc1_Pn_cap   = _cache.get("lc1_Pn_cap")
    lc1_Mn_cap   = _cache.get("lc1_Mn_cap")
    lc1_eps_bot  = _cache.get("lc1_eps_bot")
    section      = _cache["section"];   geo         = _cache["geo"]
    solver_out   = _cache["solver_out"];pos_res     = _cache["pos_res"]
    load_cases   = _cache["load_cases"]
    theta_rad    = _cache["theta_rad"]; theta_deg_auto = _cache["theta_deg_auto"]
    sec_type     = _cache["sec_type"];  b   = _cache["b"];   h   = _cache["h"]
    poly_outer   = _cache["poly_outer"];poly_holes  = _cache["poly_holes"]
    strand_dia_val = _cache["strand_dia_val"]
    use_strand   = _cache["use_strand"];bar_dia     = _cache["bar_dia"]
    n_top=_cache["n_top"]; n_bot=_cache["n_bot"]
    n_left=_cache["n_left"]; n_right=_cache["n_right"]
    code_name = _cache.get("code_name", inputs.code_name)
    fck=_cache["fck"]; fy=_cache["fy"]
    fcd_val=_cache["fcd_val"]; fyd_val=_cache["fyd_val"]
    ecu_val=_cache["ecu_val"]; Ec_val=_cache["Ec_val"]
    ny_fiber_used = int(_cache.get("ny_fiber_used", 120))
    ny_fiber_req = _cache.get("ny_fiber_req")
    mesh_warn_msg = _cache.get("mesh_warn")
    Ag_theory_cached = float(_cache.get("Ag_theory", ag_theory_mm2(
        sec_type, b, h, poly_outer, poly_holes)))

    if mesh_warn_msg:
        st.warning(mesh_warn_msg)
    if ny_fiber_req is not None and int(ny_fiber_req) != ny_fiber_used:
        st.caption(
            f"파이버 분할(ny): 입력 **{int(ny_fiber_req)}** → 해석 **{ny_fiber_used}** "
            f"(Ag≤0.001%, cb≤0.001% 상대오차 목표로 자동 조정)")
    if _cache.get("Ag_mesh_normalized"):
        st.caption(
            "콘크리트 파이버 면적을 이론 Ag에 맞게 보정했습니다. "
            "철근·강연선 면적은 그대로입니다.")


    # ══════════════════════════════════════════════════════════════
    tab1,tab2,tab3,tab4,tab5,tab6 = st.tabs(
        ["📊 P-M 상관도","🔍 단면 시각화","🧮 변형률 해석","📐 기하 특성","📋 계산 상세","🔬 검증"])

    # ══════════════════════════════════════════════════════════════
    # 탭 1: P-M 상관도
    # ══════════════════════════════════════════════════════════════
    with tab1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=M_nom,y=N_nom,mode="lines",
            name="공칭강도 (φ=1.0)",
            line=dict(color="#90A4AE",width=1.8,dash="dash")))
        fig.add_trace(go.Scatter(x=M_des,y=N_des,mode="lines",
            name="설계강도",
            line=dict(color="#1565C0",width=2.5),
            fill="tozeroy",fillcolor="rgba(21,101,192,0.05)"))

        # ── 주요 특성점 (Pmax, 균형점) ────────────────────────────
        def _key_pt(mx, ny, sym, col, label, ax_off=40, ay_off=-30):
            fig.add_trace(go.Scatter(x=[mx],y=[ny],mode="markers",
                marker=dict(symbol=sym,size=14,color=col,
                            line=dict(color="white",width=1.5)),
                showlegend=False,hoverinfo="skip"))
            _txt = f"({mx:.1f}, {ny:.1f})" if not label else f"  {label}<br>  ({mx:.1f}, {ny:.1f})"
            fig.add_annotation(x=mx,y=ny,
                text=_txt,
                showarrow=True,arrowhead=2,arrowsize=0.8,arrowcolor=col,
                font=dict(size=13,color=col),ax=ax_off,ay=ay_off,
                bgcolor="rgba(255,255,255,0.85)")
        _key_pt(0, N_max_v, "star", "#C62828", "Pmax")
        _key_pt(M_bal, N_bal, "diamond", "#2E7D32", "(Mb,Pb)")
        # P=0 점: 주석을 점 아래쪽에 배치 (ay > 0 = 아래)
        _key_pt(M_p0, 0, "circle", "#E65100", "P=0", ax_off=20, ay_off=30)

        # ── 원점 → LC1 → 설계강도 교점 선 ────────────────────────
        if load_cases:
            try:
                lc1 = load_cases[0]
                N_lc1 = float(lc1["Pu [kN]"])
                M_lc1 = math.sqrt(float(lc1["Mx [kN·m]"])**2 + float(lc1["My [kN·m]"])**2)
                M_cap, N_cap = ray_intersect_pm_curve(M_lc1, N_lc1, M_des, N_des)
                if M_cap is not None:
                    fig.add_trace(go.Scatter(
                        x=[0, M_cap], y=[0, N_cap], mode="lines",
                        line=dict(color="rgba(183,28,28,0.55)", width=1.5, dash="dot"),
                        showlegend=False, hoverinfo="skip"))
                    fig.add_annotation(
                        x=M_cap, y=N_cap,
                        text=f"({M_cap:.1f}, {N_cap:.1f})",
                        showarrow=True, arrowhead=2, arrowsize=0.8,
                        arrowcolor="#B71C1C", font=dict(size=13, color="#B71C1C"),
                        ax=40, ay=-25, bgcolor="rgba(255,255,255,0.88)")
            except Exception:
                pass

        # ── LC 설계점 (빨간색, 크기 축소) ─────────────────────────
        for lc in load_cases:
            try:
                N_u=float(lc["Pu [kN]"]); Mx_u=float(lc["Mx [kN·m]"]); My_u=float(lc["My [kN·m]"])
                Mu=math.sqrt(Mx_u**2+My_u**2)
                is_ext=bool(lc.get("극단",False))
                case_name=str(lc.get("케이스","LC"))
                safe=is_safe(N_u,Mu,N_des,M_des)
                util=utilization(N_u,Mu,N_des,M_des)
                sym_mk="triangle-up" if is_ext else "circle"
                label=f"{case_name}{'[극단]' if is_ext else ''} {'✅' if safe else '❌'} U.R.={util:.1%}"
                for sign,sl in ([(1,True)]+([(-1,False)] if sym_check else [])):
                    fig.add_trace(go.Scatter(
                        x=[sign*Mu],y=[N_u],mode="markers+text",
                        marker=dict(symbol=sym_mk,size=6,color="#E53935",
                                    line=dict(color="#B71C1C",width=1.2)),
                        text=[label if sign==1 else ""],textposition="middle right",
                        textfont=dict(size=12),name=label if sl else "",showlegend=sl))
            except Exception: pass

        M_xlim=max(float(M_des.max()),float(M_nom.max()))*1.18
        N_lo=min(float(N_des.min()),float(N_nom.min()))
        N_hi=max(float(N_des.max()),float(N_nom.max())); pad=(N_hi-N_lo)*0.1
        # 가로:세로 1:1 비율 — scaleratio로 동일 픽셀/단위 강제 적용
        _M_range = M_xlim                          # x 범위
        _N_range = (N_hi + pad) - (N_lo - pad)     # y 범위
        fig.update_layout(
            height=700,
            xaxis=dict(title=dict(text="M [kN·m]", font=dict(size=15)),
                       range=[0,M_xlim],
                       zeroline=True,zerolinecolor="rgba(0,0,0,0.25)",
                       showgrid=True,gridcolor="#ECEFF1",
                       constrain="domain",
                       tickfont=dict(size=13)),
            yaxis=dict(title=dict(text="P [kN]  (압축 +)", font=dict(size=15)),
                       range=[N_lo-pad,N_hi+pad],
                       zeroline=True,zerolinecolor="rgba(0,0,0,0.4)",
                       zerolinewidth=1.5,showgrid=True,gridcolor="#ECEFF1",
                       scaleanchor="x",
                       scaleratio=_M_range/_N_range,
                       tickfont=dict(size=13)),
            legend=dict(orientation="h", yanchor="bottom", y=1.01,
                        x=0, xanchor="left",
                        font=dict(size=13),
                        bgcolor="rgba(255,255,255,0.9)"),
            hovermode="closest",
            autosize=True,
            plot_bgcolor="white",paper_bgcolor="white",
            margin=dict(t=50,b=50,l=75,r=20))
        fig.add_hline(y=0,line_dash="dot",line_color="rgba(0,0,0,0.3)",line_width=1)
        # PM그래프(좌) + 단면형상(우) 같은 행
        _pm_col, _sec_col = st.columns([3, 1.4])
        _pm_col.plotly_chart(fig, use_container_width=True)

        with _sec_col:
            st.markdown("**단면 형상 (균형점)**")
            _aspect = h / max(b, 1)
            _fw = 2.7; _fh = min(2.7, _fw * _aspect * 1.15)
            fig_na, ax_na = plt.subplots(figsize=(_fw, _fh))
            draw_section_with_na(
                ax_na, section, theta_rad, c_bal_mm,
                geo.y_prime_top, geo.y_prime_bot,
                sec_type, b, h, poly_outer, poly_holes, strand_dia_val,
                eps_top=eps_bal_top, eps_bot=eps_bal_bot, fs=0.5,
            )
            ax_na.set_title(
                f"c={c_bal_mm:.0f}mm  θ={theta_deg_auto:.1f}°\n"
                f"Mb={M_bal:.0f}kN·m  Pb={N_bal:.0f}kN",
                fontsize=4)
            plt.tight_layout()
            st.pyplot(fig_na, use_container_width=True); plt.close(fig_na)

        # 안전 판정 표
        if load_cases:
            rows=[]
            for lc in load_cases:
                try:
                    N_u=float(lc["Pu [kN]"]); Mx_u=float(lc["Mx [kN·m]"]); My_u=float(lc["My [kN·m]"])
                    Mu=math.sqrt(Mx_u**2+My_u**2); safe=is_safe(N_u,Mu,N_des,M_des)
                    util=utilization(N_u,Mu,N_des,M_des)
                    rows.append({"케이스":lc.get("케이스","LC"),
                        "극단":"★" if lc.get("극단") else "",
                        "Pu [kN]":round(N_u,1),"Mx":round(Mx_u,1),"My":round(My_u,1),
                        "Mu [kN·m]":round(Mu,1),                        "M용량":round(m_cap(N_u,N_des,M_des),1),
                        "U.R.":f"{util:.1%}","판정":"✅ OK" if safe else "❌ NG"})
                except Exception: pass
            if rows:
                st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)

        df_dl=pd.DataFrame({"N_설계[kN]":N_des,"M_설계[kNm]":M_des,
                             "N_공칭[kN]":N_nom,"M_공칭[kNm]":M_nom})
        st.download_button("📥 P-M 데이터 CSV",
            df_dl.to_csv(index=False).encode("utf-8-sig"),"pm_curve.csv","text/csv")

    # ══════════════════════════════════════════════════════════════
    # 탭 2: 단면 시각화
    # ══════════════════════════════════════════════════════════════
    with tab2:
        st.subheader(f"단면 시각화  (θ = {theta_deg_auto:.1f}°  모멘트 방향 기준)")
        from src.materials.rebar  import Rebar  as RebarMat
        from src.materials.strand import Strand as StrandMat
        fig2, ax2 = plt.subplots(figsize=(5.5,6))
        cos_t2,sin_t2=math.cos(theta_rad),math.sin(theta_rad)
        def rot2(fx,fy_): return fx*cos_t2+fy_*sin_t2, -fx*sin_t2+fy_*cos_t2

        if sec_type=="임의 다각형" and poly_outer and len(poly_outer)>=3:
            cx_r,cy_r=geo.cx,geo.cy
            rp=[rot2(p[0]-cx_r,p[1]-cy_r) for p in poly_outer]
            ax2.add_patch(MplPolygon(rp,closed=True,facecolor="#CFD8DC",edgecolor="#37474F",lw=2,alpha=0.8))
            for hole in poly_holes:
                rh=[rot2(p[0]-cx_r,p[1]-cy_r) for p in hole]
                ax2.add_patch(MplPolygon(rh,closed=True,facecolor="#F8F9FA",edgecolor="#607D8B",lw=1,ls="--"))
        elif sec_type=="원형":
            ax2.add_patch(Circle((0,0),b/2,facecolor="#CFD8DC",edgecolor="#37474F",lw=2,alpha=0.8))
        else:
            rr=[rot2(x,y) for x,y in [(-b/2,-h/2),(b/2,-h/2),(b/2,h/2),(-b/2,h/2)]]
            ax2.add_patch(MplPolygon(rr,closed=True,facecolor="#CFD8DC",edgecolor="#37474F",lw=2,alpha=0.8))

        for f in section.fibers:
            rx,ry=rot2(f.x,f.y)
            if isinstance(f.material,RebarMat):
                d = 2*math.sqrt(abs(f.area)/math.pi)
                ax2.add_patch(Circle((rx,ry),d/2,facecolor="#E53935",edgecolor="#B71C1C",lw=0.8,zorder=4))
            elif isinstance(f.material,StrandMat):
                ax2.add_patch(Circle((rx,ry),strand_dia_val/2,facecolor="#FDD835",edgecolor="#F57F17",lw=0.8,zorder=4))

        ax2.plot(0,0,"k+",ms=12,mew=2.5,zorder=6)
        sc2=min(b,h)*0.35
        ax2.annotate("",xy=(0,sc2),xytext=(0,0),arrowprops=dict(arrowstyle="->",color="#1565C0",lw=2))
        ax2.text(0,sc2*1.1,"y'\n(압축↑)",color="#1565C0",fontsize=8,ha="center")
        xs2=[rot2(f.x,f.y)[0] for f in section.fibers]
        ys2=[rot2(f.x,f.y)[1] for f in section.fibers]
        mg2=max(b,h)*0.15
        ax2.set_xlim(min(xs2)-mg2,max(xs2)+mg2); ax2.set_ylim(min(ys2)-mg2,max(ys2)+mg2)
        ax2.set_xlabel("x' [mm]"); ax2.set_ylabel("y' [mm]  (압축↑)")
        ax2.set_title(section.summary(), fontsize=8); ax2.grid(True, alpha=0.3)
        handles=[mpatches.Patch(color="#CFD8DC",label="콘크리트"),
                 mpatches.Patch(color="#E53935",label=f"철근 D{bar_dia}")]
        if use_strand: handles.append(mpatches.Patch(color="#FDD835",label=f"강연선 φ{strand_dia_val}"))
        ax2.legend(handles=handles, loc="upper right", fontsize=8)
        plt.tight_layout()
        st.pyplot(fig2, use_container_width=True); plt.close(fig2)

    # ══════════════════════════════════════════════════════════════
    # 탭 3: 변형률 해석
    # ══════════════════════════════════════════════════════════════
    with tab3:
        st.subheader("🧮 Strain-Compatibility Solver")
        df_sol=pm_results_to_dataframe(solver_out,half_only=True)
        state_colors={"순압축":"#FFCDD2","전단면압축":"#FFCCBC","압축지배":"#FFF9C4",
                       "균형":"#C8E6C9","인장지배":"#B3E5FC","순인장":"#E1BEE7"}
        st.dataframe(df_sol.style.map(
            lambda v:f"background-color:{state_colors.get(v,'white')}",subset=["단면상태"]),
            use_container_width=True,height=300)
        st.download_button("📥 상태표 CSV",
            df_sol.to_csv(index=False).encode("utf-8-sig"),"pm_solver.csv","text/csv")

        if pos_res:
            N_opts=sorted(set(round(r.N_kN,1) for r in pos_res),reverse=True)
            N_sel=st.select_slider("N [kN] 선택",options=N_opts,value=N_opts[len(N_opts)//2])
            sel_r=min(pos_res,key=lambda r:abs(r.N_kN-N_sel))
            if sel_r.fiber_states:
                fig_sd,ax_sd=plt.subplots(figsize=(4.5,5))
                fs_list=sel_r.fiber_states; yp_all=[fs.y_prime_mm for fs in fs_list]
                ax_sd.plot([sel_r.eps_top*1e3,sel_r.eps_bot*1e3],[max(yp_all),min(yp_all)],
                           color="#333",lw=2,label="변형률 분포")
                ax_sd.scatter([fs.strain_geom*1e3 for fs in fs_list if fs.mat_type=="concrete"],
                              [fs.y_prime_mm for fs in fs_list if fs.mat_type=="concrete"],
                              c="#78909C",s=5,alpha=0.4)
                ax_sd.scatter([fs.strain_geom*1e3 for fs in fs_list if fs.mat_type=="rebar"],
                              [fs.y_prime_mm for fs in fs_list if fs.mat_type=="rebar"],
                              c="red",s=70,marker="D",zorder=5,label="철근")
                kp=sel_r.kappa
                if abs(kp)>1e-15:
                    y_na2=max(yp_all)-sel_r.eps_top/kp
                    if min(yp_all)<=y_na2<=max(yp_all):
                        ax_sd.axhline(y_na2,color="black",ls="--",lw=1.2,
                                      label=f"NA c={sel_r.c_mm:.0f}mm")
                ax_sd.axvline(0,color="gray",ls=":",lw=1)
                ax_sd.set_xlabel("ε [‰] (압축+)"); ax_sd.set_ylabel("y' [mm]")
                ax_sd.set_title(f"N={sel_r.N_kN:.0f}kN | M={sel_r.M_kNm:.0f}kN·m\n"
                                 f"c={sel_r.c_mm:.0f}mm | {sel_r.state}",fontsize=8)
                ax_sd.legend(fontsize=7); ax_sd.grid(True,alpha=0.3); plt.tight_layout()
                sc_a,sc_b=st.columns([1,1])
                sc_a.pyplot(fig_sd); plt.close(fig_sd)
                if solver_out.position_summary:
                    sc_b.dataframe(position_summary_to_dataframe(solver_out.position_summary),
                                   use_container_width=True,height=320)

    # ══════════════════════════════════════════════════════════════
    # 탭 4: 기하 특성
    # ══════════════════════════════════════════════════════════════
    with tab4:
        st.subheader("단면 기하 특성")
        gp1,gp2=st.columns(2)
        gp1.markdown("**기본 특성**")
        gp1.table({"단면적 A [mm²]":f"{geo.A:,.1f}","도심 cx [mm]":f"{geo.cx:.2f}",
            "도심 cy [mm]":f"{geo.cy:.2f}","Ixx [mm⁴]":f"{geo.Ixx:.3e}",
            "Iyy [mm⁴]":f"{geo.Iyy:.3e}","Ixy [mm⁴]":f"{geo.Ixy:.3e}",
            "rx [mm]":f"{geo.rx:.2f}","ry [mm]":f"{geo.ry:.2f}"})
        gp2.markdown("**주관성모멘트 & 회전**")
        gp2.table({"I₁ [mm⁴]":f"{geo.I1:.3e}","I₂ [mm⁴]":f"{geo.I2:.3e}",
            "주축 θp [°]":f"{math.degrees(geo.theta_p):.2f}",
            f"I_y'y' θ={theta_deg_auto:.0f}°":f"{geo.Iy_prime:.3e}",
            "y'_top(압축) [mm]":f"{geo.y_prime_top:.2f}",
            "y'_bot(인장) [mm]":f"{geo.y_prime_bot:.2f}",
            "h_eff [mm]":f"{geo.y_prime_top-geo.y_prime_bot:.2f}"})
        fig_mc,ax_mc=plt.subplots(figsize=(5,4)); ax_mc.set_facecolor("#FAFAFA")
        Iavg=(geo.Ixx+geo.Iyy)/2; R_mc=math.sqrt(((geo.Ixx-geo.Iyy)/2)**2+geo.Ixy**2)
        th_c=np.linspace(0,2*math.pi,300)
        ax_mc.plot(Iavg+R_mc*np.cos(th_c),R_mc*np.sin(th_c),"#1E88E5",lw=2)
        ax_mc.plot([geo.Ixx,geo.Iyy],[geo.Ixy,-geo.Ixy],"o-",color="#333",ms=6)
        ax_mc.plot([geo.I1,geo.I2],[0,0],"Dr",ms=8,label="I₁, I₂")
        Iy_p=(geo.Iyy*math.sin(theta_rad)**2+geo.Ixx*math.cos(theta_rad)**2
              -geo.Ixy*math.sin(2*theta_rad))
        I_xy_p=((geo.Ixx-geo.Iyy)/2*math.sin(2*theta_rad)+geo.Ixy*math.cos(2*theta_rad))
        ax_mc.plot(Iy_p,I_xy_p,"^g",ms=10,label=f"I_y'y' θ={theta_deg_auto:.0f}°")
        ax_mc.axhline(0,color="gray",lw=0.8,ls="--")
        ax_mc.set_xlabel("I [mm⁴]"); ax_mc.set_ylabel("I_xy [mm⁴]")
        ax_mc.set_title("Mohr's Circle",fontsize=9); ax_mc.legend(fontsize=7)
        ax_mc.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x,_:f"{x:.1e}"))
        ax_mc.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x,_:f"{x:.1e}"))
        ax_mc.grid(True,alpha=0.3); plt.tight_layout()
        st.pyplot(fig_mc); plt.close(fig_mc)

    # ══════════════════════════════════════════════════════════════
    # 탭 5: 계산 상세
    # ══════════════════════════════════════════════════════════════
    with tab5:
        dt1,dt2=st.columns(2)
        with dt1:
            st.markdown("**설계기준 / 재료**"); st.code(code.summary(),language="")
            st.table({"fck":f"{fck}MPa","fcd":f"{fcd_val:.2f}MPa","εcu":f"{ecu_val*1e3:.2f}‰",
                      "Ec":f"{Ec_val:.0f}MPa","fy":f"{fy}MPa","fyd":f"{fyd_val:.2f}MPa",
                      "θ":f"{theta_deg_auto:.1f}°"})
        with dt2:
            st.markdown("**P-M 주요 결과**")
            st.table({"Pmax 설계 [kN]":f"{N_max_v:,.1f}",
                      "Pmax 공칭 [kN]":f"{float(N_nom.max()):,.1f}",
                      "균형 Pb [kN]":f"{N_bal:,.1f}","균형 Mb [kN·m]":f"{M_bal:,.1f}",
                      "P=0 M₀ [kN·m]":f"{M_p0:,.1f}","c_bal [mm]":f"{c_bal_mm:.1f}",
                      "h_eff [mm]":f"{solver_out.h_eff_mm:.1f}",
                      "파이버":f"{len(section.fibers)}개",
                      "ny (요청)":f"{int(ny_fiber_req) if ny_fiber_req is not None else '-'}",
                      "ny (해석)":f"{ny_fiber_used}"})
            st.info("Fiber Section Analysis\n\n"
                    "① Slice 메시 → 파이버\n② ε(y')=ε₀+κ·y' (평면유지)\n"
                    "③ N=Σσ·A, M=Σσ·A·y'\n④ c: ∞→0 로그스윕")

    # ══════════════════════════════════════════════════════════════
    # 탭 6: 검증
    # ══════════════════════════════════════════════════════════════
    with tab6:
        render_tab_verify(locals())
