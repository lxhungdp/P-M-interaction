"""Calculation detail tab."""

from __future__ import annotations

import streamlit as st

from pm_app.ui.context import OutputContext


def render_tab_detail(ctx: OutputContext, code) -> None:
    fck, fy = ctx.fck, ctx.fy
    fcd_val, fyd_val, ecu_val, Ec_val = ctx.fcd_val, ctx.fyd_val, ctx.ecu_val, ctx.Ec_val
    theta_deg_auto = ctx.theta_deg_auto
    N_max_v, N_bal, M_bal, M_p0 = ctx.N_max_v, ctx.N_bal, ctx.M_bal, ctx.M_p0
    N_nom = ctx.N_nom
    c_bal_mm = ctx.c_bal_mm
    solver_out = ctx.solver_out
    section = ctx.section
    ny_fiber_req, ny_fiber_used = ctx.ny_fiber_req, ctx.ny_fiber_used

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
