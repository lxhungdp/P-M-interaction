"""P-M interaction diagram tab."""

from __future__ import annotations

import math

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from pm_app.pm_checks import is_safe, m_cap, ray_intersect_pm_curve, utilization
from pm_app.ui.context import OutputContext
from pm_app.viz.section_draw import draw_section_with_na


def render_tab_pm(ctx: OutputContext) -> None:
    N_des, M_des, N_nom, M_nom = ctx.N_des, ctx.M_des, ctx.N_nom, ctx.M_nom
    N_max_v, N_bal, M_bal, M_p0, N_p0 = ctx.N_max_v, ctx.N_bal, ctx.M_bal, ctx.M_p0, ctx.N_p0
    c_bal_mm = ctx.c_bal_mm
    eps_bal_top, eps_bal_bot = ctx.eps_bal_top, ctx.eps_bal_bot
    section = ctx.section
    geo = ctx.geo
    load_cases = ctx.load_cases
    theta_rad, theta_deg_auto = ctx.theta_rad, ctx.theta_deg_auto
    sec_type, b, h = ctx.sec_type, ctx.b, ctx.h
    poly_outer, poly_holes = ctx.poly_outer, ctx.poly_holes
    strand_dia_val = ctx.strand_dia_val
    sym_check = ctx.sym_check

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

