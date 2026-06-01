"""Strain compatibility solver tab."""

from __future__ import annotations

import matplotlib.pyplot as plt
import streamlit as st

from src.analysis.solver import pm_results_to_dataframe, position_summary_to_dataframe

from pm_app.ui.context import OutputContext


def render_tab_strain(ctx: OutputContext) -> None:
    solver_out = ctx.solver_out
    pos_res = ctx.pos_res

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
