"""Section visualization tab."""

from __future__ import annotations

import math

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import streamlit as st
from matplotlib.patches import Circle, Polygon as MplPolygon

from src.materials.rebar import Rebar as RebarMat
from src.materials.strand import Strand as StrandMat

from pm_app.ui.context import OutputContext


def render_tab_section(ctx: OutputContext) -> None:
    sec_type = ctx.sec_type
    b, h = ctx.b, ctx.h
    poly_outer, poly_holes = ctx.poly_outer, ctx.poly_holes
    theta_rad = ctx.theta_rad
    theta_deg_auto = ctx.theta_deg_auto
    section = ctx.section
    geo = ctx.geo
    bar_dia = ctx.bar_dia
    strand_dia_val = ctx.strand_dia_val
    use_strand = ctx.use_strand

    st.subheader(f"단면 시각화  (θ = {theta_deg_auto:.1f}°  모멘트 방향 기준)")
    fig2, ax2 = plt.subplots(figsize=(5.5, 6))
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
