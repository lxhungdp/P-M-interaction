"""Geometry properties tab."""

from __future__ import annotations

import math

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker
import numpy as np
import streamlit as st

from pm_app.ui.context import OutputContext


def render_tab_geometry(ctx: OutputContext) -> None:
    geo = ctx.geo
    theta_rad = ctx.theta_rad
    theta_deg_auto = ctx.theta_deg_auto

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
