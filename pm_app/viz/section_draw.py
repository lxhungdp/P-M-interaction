"""Matplotlib section drawings."""

import math

import numpy as np
from matplotlib.patches import Circle, Polygon as MplPolygon

def draw_section_preview(ax, sec_type, b, h, rb_list, cover,
                          poly_outer, poly_holes,
                          theta_rad, bar_dia,
                          n_top, n_bot, n_left, n_right,
                          poly_rebar_positions, avg_Mx, avg_My):
    """
    rb_list : list of (x, y, dia) for rectangular section
    cover   : used for circle section rebar radius
    """
    ax.set_aspect("equal"); ax.set_facecolor("#F8F9FA")
    cos_t, sin_t = math.cos(theta_rad), math.sin(theta_rad)
    def rot(x, y): return x*cos_t+y*sin_t, -x*sin_t+y*cos_t

    # ─ 외곽 & 철근 ────────────────────────────────────────────────
    if sec_type == "임의 다각형" and poly_outer and len(poly_outer) >= 3:
        cx_r = sum(p[0] for p in poly_outer)/len(poly_outer)
        cy_r = sum(p[1] for p in poly_outer)/len(poly_outer)
        rp = [rot(p[0]-cx_r, p[1]-cy_r) for p in poly_outer]
        ax.add_patch(MplPolygon(rp, closed=True,
            facecolor="#CFD8DC", edgecolor="#37474F", lw=2, alpha=0.8))
        for hole in poly_holes:
            rh = [rot(p[0]-cx_r, p[1]-cy_r) for p in hole]
            ax.add_patch(MplPolygon(rh, closed=True,
                facecolor="#F8F9FA", edgecolor="#607D8B", lw=1.2, ls="--"))
        for px, py in poly_rebar_positions:
            rx, ry = rot(px-cx_r, py-cy_r)
            ax.add_patch(Circle((rx,ry), bar_dia/2,
                facecolor="#E53935", edgecolor="#B71C1C", lw=0.8, zorder=4))
    elif sec_type == "원형":
        ax.add_patch(Circle((0,0), b/2,
            facecolor="#CFD8DC", edgecolor="#37474F", lw=2, alpha=0.8))
        n_rb = n_top + n_bot + n_left + n_right
        if n_rb > 0:
            r_rb = b/2 - cover   # 피복 = 표면 → 철근중심
            for a in np.linspace(0, 2*math.pi, n_rb, endpoint=False):
                rx, ry = rot(r_rb*math.cos(a), r_rb*math.sin(a))
                ax.add_patch(Circle((rx,ry), bar_dia/2,
                    facecolor="#E53935", edgecolor="#B71C1C", lw=0.8, zorder=4))
    else:
        # 직사각형 외곽
        rect_pts = [(-b/2,-h/2),(b/2,-h/2),(b/2,h/2),(-b/2,h/2)]
        rr = [rot(x,y) for x,y in rect_pts]
        ax.add_patch(MplPolygon(rr, closed=True,
            facecolor="#CFD8DC", edgecolor="#37474F", lw=2, alpha=0.8))
        # 철근 (rb_list에서 직접)
        for rx_orig, ry_orig, d in rb_list:
            rx, ry = rot(rx_orig, ry_orig)
            ax.add_patch(Circle((rx,ry), d/2,
                facecolor="#E53935", edgecolor="#B71C1C", lw=0.8, zorder=4))

    # ─ 도심 ────────────────────────────────────────────────────────
    ax.plot(0, 0, "k+", ms=10, mew=2.5, zorder=6)

    # ─ 좌표축 ──────────────────────────────────────────────────────
    sc = max(b, h) * 0.30
    ax_xe, ax_ye = rot(sc, 0)
    ax.annotate("", xy=(ax_xe,ax_ye), xytext=(0,0),
        arrowprops=dict(arrowstyle="-|>", color="#C62828", lw=2.5))
    ax.text(ax_xe*1.15, ax_ye*1.15, "X", color="#C62828",
            fontsize=9, ha="center", va="center", fontweight="bold")
    ax_xn, ax_yn = rot(0, sc)
    ax.annotate("", xy=(ax_xn,ax_yn), xytext=(0,0),
        arrowprops=dict(arrowstyle="-|>", color="#1565C0", lw=2.5))
    ax.text(ax_xn*1.15, ax_yn*1.15, "Y", color="#1565C0",
            fontsize=9, ha="center", va="center", fontweight="bold")
    # y' (모멘트 방향)
    Mu_tot = math.sqrt(avg_Mx**2 + avg_My**2)
    if Mu_tot > 1e-6:
        ax.annotate("", xy=(ax_xn,ax_yn), xytext=(0,0),
            arrowprops=dict(arrowstyle="-|>", color="#2E7D32", lw=2, linestyle="dashed"))
        ax.text(ax_xn*1.15, ax_yn*1.15, "y'\n(압축)", color="#2E7D32",
                fontsize=8, ha="center", va="center")

    theta_deg = math.degrees(theta_rad)
    ax.text(0.03, 0.03,
            f"θ={theta_deg:.1f}°  Mx={avg_Mx:.0f}  My={avg_My:.0f} kN·m",
            transform=ax.transAxes, fontsize=7, color="#555",
            va="bottom", ha="left")

    mg = max(b, h)*0.22
    ax.set_xlim(-b/2-mg, b/2+mg); ax.set_ylim(-h/2-mg, h/2+mg)
    ax.set_xlabel("x [mm] →", fontsize=8); ax.set_ylabel("y [mm] ↑", fontsize=8)
    ax.grid(True, alpha=0.25, lw=0.6); ax.tick_params(labelsize=7)


# ══════════════════════════════════════════════════════════════════════
# 단면 + 중립축 + C/T + 최대인장변형률 (P-M 그래프 아래)
# ══════════════════════════════════════════════════════════════════════
def draw_section_with_na(ax, section, theta_rad, c_mm, y_prime_top, y_prime_bot,
                          sec_type, b, h, poly_outer, poly_holes,
                          strand_dia_val,
                          eps_top=None, eps_bot=None, fs=1.0):
    from src.materials.rebar  import Rebar  as RebarMat
    from src.materials.strand import Strand as StrandMat

    ax.set_aspect("equal")

    cos_t, sin_t = math.cos(theta_rad), math.sin(theta_rad)
    def to_dp(x, y):
        return x*cos_t + y*sin_t, -x*sin_t + y*cos_t

    y_na = y_prime_top - c_mm  # 중립축 y' 위치

    # ─ 단면 외곽 결정 ──────────────────────────────────────────────
    if sec_type == "임의 다각형" and poly_outer and len(poly_outer) >= 3:
        cx_r = sum(p[0] for p in poly_outer)/len(poly_outer)
        cy_r = sum(p[1] for p in poly_outer)/len(poly_outer)
        outline_pts = [to_dp(p[0]-cx_r, p[1]-cy_r) for p in poly_outer]
    elif sec_type == "원형":
        angles = np.linspace(0, 2*math.pi, 120)
        outline_pts = [to_dp(b/2*math.cos(a), b/2*math.sin(a)) for a in angles]
    else:
        corners = [(-b/2,-h/2),(b/2,-h/2),(b/2,h/2),(-b/2,h/2)]
        outline_pts = [to_dp(x,y) for x,y in corners]

    xs_out = [p[0] for p in outline_pts]
    ys_out = [p[1] for p in outline_pts]
    x_lo, x_hi = min(xs_out)-5, max(xs_out)+5

    # ─ 단면 테두리 (배경색 없음) ────────────────────────────────────
    ax.add_patch(MplPolygon(outline_pts, closed=True,
        facecolor="#F5F5F5", edgecolor="#37474F", lw=2, zorder=5))
    if sec_type == "임의 다각형":
        for hole in poly_holes:
            rh = [to_dp(p[0], p[1]) for p in hole]
            ax.add_patch(MplPolygon(rh, closed=True,
                facecolor="#F8F9FA", edgecolor="#607D8B", lw=1, ls="--", zorder=4))

    # ─ 철근 & 강연선 (단면적에서 직경 복원) ──────────────────────
    for f in section.fibers:
        xp, yp = to_dp(f.x, f.y)
        if isinstance(f.material, RebarMat):
            d = 2 * math.sqrt(abs(f.area) / math.pi)
            ax.add_patch(Circle((xp,yp), d/2,
                facecolor="#E53935", edgecolor="#B71C1C", lw=0.8, zorder=6))
        elif isinstance(f.material, StrandMat):
            ax.add_patch(Circle((xp,yp), strand_dia_val/2,
                facecolor="#FDD835", edgecolor="#F57F17", lw=0.8, zorder=6))

    # ─ 중립축 선 ───────────────────────────────────────────────────
    ax.axhline(y_na, color="#B71C1C", lw=2.5, zorder=7,
               label=f"중립축  c={c_mm:.0f} mm")

    # ─ C / T 텍스트 ────────────────────────────────────────────────
    xmid = 0.0
    y_c  = (y_prime_top + y_na) / 2
    y_t  = (y_prime_bot  + y_na) / 2
    ax.text(xmid, y_c, "C", fontsize=int(26*fs), fontweight="bold",
            color="#0D47A1", ha="center", va="center", alpha=0.75, zorder=8)
    ax.text(xmid, y_t, "T", fontsize=int(26*fs), fontweight="bold",
            color="#B71C1C", ha="center", va="center", alpha=0.75, zorder=8)

    # ─ 인장 철근 최대 변형률 표기 ──────────────────────────────────
    if eps_top is not None and eps_bot is not None:
        h_eff = y_prime_top - y_prime_bot
        if abs(h_eff) > 1e-9:
            # kappa = dε/dy'  (ε = eps_top + kappa*(y' - y'_top))
            kappa = (eps_bot - eps_top) / (y_prime_bot - y_prime_top)
            # 철근 변형률 계산
            rebar_items = []
            for f in section.fibers:
                if isinstance(f.material, RebarMat):
                    # y' of this fiber
                    y_prime_f = -f.x * sin_t + f.y * cos_t
                    eps_f = eps_top + kappa * (y_prime_f - y_prime_top)
                    xp, yp = to_dp(f.x, f.y)
                    d = 2 * math.sqrt(abs(f.area) / math.pi)
                    rebar_items.append((xp, yp, eps_f, d))

            if rebar_items:
                min_eps = min(it[2] for it in rebar_items)
                if min_eps < 0:  # 인장 철근 존재
                    tol = max(abs(min_eps) * 0.005, 1e-7)
                    tensile = [(xp, yp, d) for xp, yp, eps, d in rebar_items
                               if abs(eps - min_eps) < tol]
                    # 1개만 표기 (x 기준 중앙 철근)
                    tensile.sort(key=lambda t: abs(t[0]))
                    xann, yann, dann = tensile[len(tensile)//2]
                    # 철근 아래쪽에 배치 (겹침 방지)
                    offset_y = -(dann * 2.0 + 30)
                    ax.annotate(
                        f"εs,max={min_eps:.4f}",
                        xy=(xann, yann),
                        xytext=(xann, yann + offset_y),
                        arrowprops=dict(arrowstyle="-|>", color="#B71C1C", lw=1.2),
                        fontsize=int(8*fs), color="#B71C1C", fontweight="bold",
                        ha="center", va="top",
                        bbox=dict(boxstyle="round,pad=0.25", facecolor="white",
                                  edgecolor="#B71C1C", alpha=0.88),
                        zorder=10,
                    )

    # ─ 레이아웃 ────────────────────────────────────────────────────
    mg = max(b,h)*0.18
    ax.set_xlim(x_lo-mg, x_hi+mg)
    ax.set_ylim(y_prime_bot-mg, y_prime_top+mg)
    _fs_lbl = max(int(8*fs), 4)
    ax.set_xlabel("x' [mm]", fontsize=_fs_lbl); ax.set_ylabel("y' [mm]  (압축↑)", fontsize=_fs_lbl)
    ax.legend(loc="upper right", fontsize=_fs_lbl)
    ax.grid(True, alpha=0.25, lw=0.6); ax.set_facecolor("#F8F9FA")
    ax.tick_params(labelsize=_fs_lbl)  # 틱 레이블 = 축제목과 동일 크기
    # 위·우측 spine → 연회색 (단면 외곽선과 혼동 방지)
    ax.spines['top'].set_color('#CCCCCC');   ax.spines['top'].set_linewidth(0.5)
    ax.spines['right'].set_color('#CCCCCC'); ax.spines['right'].set_linewidth(0.5)
    ax.spines['bottom'].set_color('#888888'); ax.spines['left'].set_color('#888888')
