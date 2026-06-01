"""
콘크리트 기둥 단면 P-M상관도 검토  v6
════════════════════════════════════════
• "<<" / ">>" 버튼으로 좌측 입력창 전체 접기/펼치기 (컬럼폭 변경)
• 설계기준 선택 + KDS 계수 설명을 fck/fy 아래에 배치
• 단면형상 expander: 첫 행에 [콤보박스]+[👁] 배치 (제목 셀)
• 철근 배치: 데이터 테이블 (위치/갯수/직경/피복)
• 피복 → 철근 배치 테이블로 이동
• 단면 미리보기: 하중부호규약을 그림 아래로 배치
• P-M 탭: 주요값 카드 제거, 인장 철근 최대 변형률 표기
"""
import math, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))

import numpy as np
import pandas as pd
import streamlit as st
import streamlit.components.v1 as stc
import plotly.graph_objects as go
import matplotlib, matplotlib.ticker, matplotlib.path as mpath, matplotlib.patches as mpatches
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon as MplPolygon

from src.materials.concrete       import Concrete
from src.materials.rebar          import Rebar
from src.materials.strand         import Strand
from src.section.fiber_section    import FiberSection
from src.geometry.polygon_section import PolygonSection, compute_geo_props
from src.analysis.engine          import (
    PM_DIAGRAM_ETU,
    compute_pm_diagram,
    axial_force_split_materials_kn,
    diagram_max_positive_moment_strain,
    diagram_closest_strain_to_nm,
)
from src.analysis.solver          import (
    compute_pm_solver,
    pm_result_at_strains,
    pm_results_to_dataframe,
    position_summary_to_dataframe,
    eps_bot_for_tension_yield_at_depth,
)
from src.codes import CODES

# ══════════════════════════════════════════════════════════════════════
# 페이지 설정
# ══════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="단면 P-M상관도 검토", page_icon="🏗️",
    layout="wide", initial_sidebar_state="collapsed",
)
plt.rcParams.update({"font.family": "Malgun Gothic", "axes.unicode_minus": False})

st.markdown("""
<style>
div[data-testid="stExpander"] summary p {font-size:12px!important;font-weight:700;margin:0;}
div[data-testid="stExpander"] details {border:1px solid #dce0e8!important;border-radius:4px!important;margin-bottom:4px!important;}
label[data-testid="stWidgetLabel"]>p {font-size:13px!important;margin-bottom:1px!important;}
div[data-testid="stNumberInput"] input {padding:2px 6px!important;font-size:14px!important;}
div[data-testid="stSelectbox"]>div>div {font-size:14px!important;}
div[data-testid="stCaptionContainer"] p {font-size:13px!important;}
div[data-testid="stDataEditor"] {font-size:12px!important;}
/* 좌우 구분선: 메인 분할 컬럼(JS가 pm-main-col0 클래스 부여)에만 적용 */
.pm-main-col0 {
    border-right: 3px solid #90a4ae !important;
    padding-right: 10px !important;
}
/* 엔진 계산 code 블록: 참조값 입력과 유사한 크기 */
div[data-testid="stCode"] code {font-size:0.82rem!important;line-height:1.55!important;}
.pm-verify-lbl {font-size:0.82rem!important;line-height:1.55!important;}
div[data-testid="stNumberInput"] button {display:none!important;width:0!important;height:0!important;padding:0!important;min-height:0!important;}
/* 검증 업데이트 알림/성공/오류 텍스트 크기 */
div[data-testid="stAlert"] p, div[data-testid="stAlert"] li {font-size:16px!important;}
div[data-testid="stMarkdownContainer"] p {font-size:13px!important;}
.pm-verify-msg {font-size:16px!important;line-height:1.5!important;}
/* 1px JS iframe 숨김 */
iframe[height="1"]{display:none!important;margin:0!important;padding:0!important;}
</style>
""", unsafe_allow_html=True)

stc.html("""
<script>
// ── Ctrl+S → P-M 계산 ───────────────────────────────────────────────
document.addEventListener('keydown',function(e){
  if((e.ctrlKey||e.metaKey)&&e.key==='s'){
    e.preventDefault();
    var pb=window.parent.document.querySelectorAll('[data-testid="baseButton-primary"]');
    if(pb.length>0){pb[pb.length-1].click();return;}
    var btns=window.parent.document.querySelectorAll('button');
    for(var b of btns){if(b.innerText&&b.innerText.includes('계산')){b.click();break;}}
  }
},true);

// ── 좌우 드래그 리사이즈 ─────────────────────────────────────────
var _rz={w0:null,w1:null,drag:false,sx:0,sw0:0,sw1:0,bound:false};
function getMainBlock(){
  // stHorizontalBlock 중 직계 자식이 2개 이상인 첫 번째 블록
  var doc=window.parent.document;
  var blocks=doc.querySelectorAll('[data-testid="stHorizontalBlock"]');
  for(var i=0;i<blocks.length;i++){
    if(blocks[i].children.length>=2) return blocks[i];
  }
  return null;
}
function applyRz(block){
  if(!_rz.w0||!block) return;
  var c0=block.children[0], c1=block.children[block.children.length-1];
  c0.style.flex='0 0 '+_rz.w0+'px';c0.style.minWidth=_rz.w0+'px';c0.style.maxWidth=_rz.w0+'px';
  c1.style.flex='0 0 '+_rz.w1+'px';c1.style.minWidth=_rz.w1+'px';c1.style.maxWidth=_rz.w1+'px';
}
function initDrag(){
  if(_rz.bound) return true;
  var doc=window.parent.document;
  var block=getMainBlock(); if(!block) return false;
  // 구분선 역할: 첫 번째 자식에 클래스 부여 + 오른쪽 경계 위에 투명 오버레이 삽입
  var overlay=doc.createElement('div');
  overlay.id='_pm_drag_overlay';
  overlay.style.cssText='position:absolute;top:0;bottom:0;right:-6px;width:12px;'
    +'cursor:col-resize;z-index:9999;background:transparent;';
  var c0=block.children[0];
  c0.classList.add('pm-main-col0');
  if(getComputedStyle(c0).position==='static') c0.style.position='relative';
  c0.appendChild(overlay);
  _rz.bound=true;
  overlay.addEventListener('mousedown',function(e){
    var b=getMainBlock(); if(!b) return;
    _rz.drag=true; _rz.sx=e.clientX;
    _rz.sw0=b.children[0].getBoundingClientRect().width;
    _rz.sw1=b.children[b.children.length-1].getBoundingClientRect().width;
    doc.body.style.cursor='col-resize'; doc.body.style.userSelect='none';
    e.preventDefault();
  });
  doc.addEventListener('mousemove',function(e){
    if(!_rz.drag) return;
    var b=getMainBlock(); if(!b) return;
    var dx=e.clientX-_rz.sx, tot=_rz.sw0+_rz.sw1;
    var w0=Math.max(180,Math.min(tot-250,_rz.sw0+dx)), w1=tot-w0;
    _rz.w0=w0; _rz.w1=w1;
    b.children[0].style.flex='0 0 '+w0+'px';
    b.children[0].style.minWidth=w0+'px';b.children[0].style.maxWidth=w0+'px';
    var last=b.children[b.children.length-1];
    last.style.flex='0 0 '+w1+'px';last.style.minWidth=w1+'px';last.style.maxWidth=w1+'px';
  });
  doc.addEventListener('mouseup',function(){
    if(!_rz.drag) return;
    _rz.drag=false; doc.body.style.cursor=''; doc.body.style.userSelect='';
  });
  new MutationObserver(function(){
    var b=getMainBlock(); if(b) applyRz(b);
  }).observe(doc.body,{childList:true,subtree:false});
  return true;
}
var _bt=0;
(function retry(){if(_bt++>100)return;try{if(!initDrag())setTimeout(retry,300);}catch(e){setTimeout(retry,300);}})();
</script>
""", height=1)

for _k, _v in [("show_preview", False), ("inp_expand", True), ("inp_width", 3)]:
    if _k not in st.session_state:
        st.session_state[_k] = _v

# Verification: reference error badge threshold [percent]
VERIFY_REF_ERR_PCT = 3.0
# Mesh auto-tune: Ag(theory) vs gross mesh rel.err. [fraction]; cb balanced depth [fraction]
MESH_AG_TOL = 1e-5   # 0.001 %
MESH_CB_TOL = 1e-5   # 0.001 % (engine vs theory cb)

# ══════════════════════════════════════════════════════════════════════
# 유틸 / 철근 위치 계산 (면별 독립 파라미터)
# ══════════════════════════════════════════════════════════════════════
def compute_rebar_positions(b, h,
                             n_top,  dia_top,  cov_top,
                             n_bot,  dia_bot,  cov_bot,
                             n_left, dia_left, cov_left,
                             n_right,dia_right,cov_right):
    """
    직사각형 단면 철근 위치 (x, y, dia) 반환
    ─ 피복(cov): 콘크리트 표면 → 철근 중심까지의 거리 (철근 중심 위치를 직접 지정)
    ─ 상단/하단 우선 배치
    ─ 좌측/우측면은 상단·하단 철근과 겹치지 않도록 [1:-1] 구간에만 배치
    """
    yt = h/2  - cov_top    # 상단 철근 중심 y 좌표
    yb = -h/2 + cov_bot    # 하단 철근 중심 y 좌표
    pos = []
    if n_top > 0:
        xl = -b/2 + cov_top   # 좌끝 철근 중심 x
        xr =  b/2 - cov_top   # 우끝 철근 중심 x
        for x in np.linspace(xl, xr, n_top):
            pos.append((float(x), yt, float(dia_top)))
    if n_bot > 0:
        xl = -b/2 + cov_bot
        xr =  b/2 - cov_bot
        for x in np.linspace(xl, xr, n_bot):
            pos.append((float(x), yb, float(dia_bot)))
    if n_left > 0:
        xl = -b/2 + cov_left
        for y in np.linspace(yb, yt, n_left + 2)[1:-1]:
            pos.append((xl, float(y), float(dia_left)))
    if n_right > 0:
        xr =  b/2 - cov_right
        for y in np.linspace(yb, yt, n_right + 2)[1:-1]:
            pos.append((xr, float(y), float(dia_right)))
    return pos  # list of (x, y, dia)


def _m_cap(N_u, N_half, M_half):
    try:
        order = np.argsort(N_half)
        return abs(float(np.interp(N_u, N_half[order], M_half[order])))
    except Exception:
        return 0.0

def _is_safe(N_u, M_u, N_half, M_half):
    if N_u > max(N_half)+1e-3 or N_u < min(N_half)-1e-3: return False
    return abs(M_u) <= _m_cap(N_u, N_half, M_half)

def _utilization(N_u, M_u, N_half, M_half):
    mc = _m_cap(N_u, N_half, M_half)
    return abs(M_u)/mc if mc > 1e-6 else float("inf")

def _p0_point(N_half, M_half):
    for i in range(len(N_half)-1):
        n0, n1 = N_half[i], N_half[i+1]
        if n0*n1 <= 0 and abs(n0-n1) > 1e-9:
            t = -n0/(n1-n0); return M_half[i]+t*(M_half[i+1]-M_half[i]), 0.0
    idx = int(np.argmin(np.abs(N_half)))
    return M_half[idx], N_half[idx]


def _ray_intersect_pm_curve(M_lc, N_lc, M_arr, N_arr):
    """원점에서 (M_lc, N_lc) 방향으로의 반직선과 P-M 곡선의 교점 반환."""
    if abs(M_lc) < 1e-6:
        return 0.0, float(np.max(N_arr))
    results = []
    for i in range(len(M_arr) - 1):
        M0, N0 = float(M_arr[i]), float(N_arr[i])
        dM = float(M_arr[i+1]) - M0
        dN = float(N_arr[i+1]) - N0
        # 연립방정식: M0+s*dM = t*M_lc,  N0+s*dN = t*N_lc
        det = -dM * N_lc + M_lc * dN
        if abs(det) < 1e-15:
            continue
        s = (M0 * N_lc - M_lc * N0) / det
        t = (-dM * N0 + M0 * dN) / det
        if -1e-9 <= s <= 1.0 + 1e-9 and t > 0.01:
            results.append((t, M0 + s * dM, N0 + s * dN))
    if not results:
        return None, None
    # t=1이 LC1 위치 → t>0에서 가장 의미있는 교점(설계 용량점)
    results.sort(key=lambda r: abs(r[0] - 1.0))
    return results[0][1], results[0][2]


# ══════════════════════════════════════════════════════════════════════
# 단면 생성
# ══════════════════════════════════════════════════════════════════════
def build_section(b, h, cover, fck, fcd, fy, fyd,
                  rb_list, bar_dia,
                  n_top, n_bot, n_left, n_right,
                  curve_conc, use_strand, strand_params, ny, sec_type,
                  poly_outer=None, poly_holes=None, poly_rb_pos=None):
    """
    rb_list : list of (x, y, dia) for rectangular section
    bar_dia : single diameter for circle/polygon sections
    """
    from src.geometry.shapes import make_rectangle, make_circle
    from itertools import groupby
    conc = Concrete(fck=fck, fcd=fcd, curve_type=curve_conc)
    rb   = Rebar(fy=fy, fyd=fyd)
    st_obj = st_pos = None; st_dia = 15.2
    if use_strand and strand_params:
        p = strand_params
        st_obj = Strand(fpk=p["fpk"], fp01k=p["fp01k"], Ep=p["Ep"],
                        fpd=p["fpd"], eps_pe=p["eps_pe"])
        st_pos = p["positions"]; st_dia = p["dia"]

    if sec_type == "임의 다각형" and poly_outer:
        ps = PolygonSection(poly_outer, poly_holes or [])
        sec = FiberSection.from_polygon_section(
            ps, conc, rebar=rb if poly_rb_pos else None,
            rebar_positions=poly_rb_pos or [], bar_dia=bar_dia,
            strand=st_obj, strand_positions=st_pos, strand_dia=st_dia,
            mesh_type="slice", ny=ny,
        )
        ag_poly = _ag_theory_mm2(sec_type, b, h, poly_outer, poly_holes)
        sec.normalize_concrete_to_ag_theory(ag_poly)
        return sec, conc, rb

    if sec_type == "원형":
        sec = FiberSection()
        poly = make_circle(radius=b / 2, n_seg=256)
        circle_ps = PolygonSection(poly.vertices, [])
        sec.add_concrete_polygon_slices(circle_ps, conc, ny)
        n_rb = n_top + n_bot + n_left + n_right
        if n_rb > 0:
            r_rb = b/2 - cover   # 피복 = 표면 → 철근중심
            ang  = np.linspace(0, 2*math.pi, n_rb, endpoint=False)
            sec.add_rebar([(r_rb*math.cos(a), r_rb*math.sin(a)) for a in ang], rb, bar_dia)
        if st_obj and st_pos: sec.add_strand(st_pos, st_obj, st_dia)
        sec.normalize_concrete_to_ag_theory(math.pi * (b / 2) ** 2)
        return sec, conc, rb

    # 직사각형: rb_list 사용 (면별 직경/피복 지원)
    sec = FiberSection()
    rect_ps = PolygonSection(make_rectangle(b, h).vertices, [])
    sec.add_concrete_polygon_slices(rect_ps, conc, ny)
    if rb_list:
        sorted_rb = sorted(rb_list, key=lambda t: t[2])
        for dia, items in groupby(sorted_rb, key=lambda t: t[2]):
            positions = [(x, y) for x, y, _ in items]
            sec.add_rebar(positions, rb, dia)
    if st_obj and st_pos: sec.add_strand(st_pos, st_obj, st_dia)
    sec.normalize_concrete_to_ag_theory(b * h)
    return sec, conc, rb


def _ag_theory_mm2(sec_type, b, h, poly_outer, poly_holes) -> float:
    """Nominal gross area [mm^2] from geometry (for mesh convergence)."""
    if sec_type == "직사각형":
        return float(b * h)
    if sec_type == "원형":
        r = float(b) / 2.0
        return math.pi * r * r
    if sec_type == "임의 다각형" and poly_outer is not None and len(poly_outer) >= 3:
        holes = poly_holes or []
        ps = PolygonSection(
            np.asarray(poly_outer, dtype=float),
            [np.asarray(h, dtype=float) for h in holes],
        )
        a = float(ps.outer.area())
        for ho in ps.holes:
            a -= float(ho.area())
        return max(a, 0.0)
    return float(b * h)


def _h_eff_and_cb_theory(
    section: FiberSection,
    theta_rad: float,
    ecu_val: float,
    fyd_val: float,
    sec_type: str,
    b: float,
    h: float,
) -> tuple[float, float]:
    """Effective d and theoretical balanced cb [mm] (verification tab logic)."""
    _eyd = fyd_val / 200000.0
    if sec_type == "직사각형" and abs(theta_rad) < 1e-9:
        _y_prime_top_ref = float(h) / 2.0
        _y_prime_bot_ref = -float(h) / 2.0
    else:
        _y_prime_top_ref, _y_prime_bot_ref = section.rotated_y_extremes(theta_rad)
    _rb_yp_list = []
    for _f in section.fibers:
        if isinstance(_f.material, Rebar):
            _yp = -_f.x * math.sin(theta_rad) + _f.y * math.cos(theta_rad)
            _rb_yp_list.append((_yp, _f.area))
    if _rb_yp_list:
        _rb_yp_sorted = sorted(_rb_yp_list, key=lambda x: x[0])
        _min_yp_rb = _rb_yp_sorted[0][0]
        _dia_ref = 2 * math.sqrt(max(a for _, a in _rb_yp_list) / math.pi)
        _tol_d = max(_dia_ref * 1.5, 30.0)
        _tens_rb = [(yp, a) for yp, a in _rb_yp_list if yp <= _min_yp_rb + _tol_d]
        _At_tot = sum(a for _, a in _tens_rb)
        _yp_tens = sum(yp * a for yp, a in _tens_rb) / _At_tot if _At_tot > 0 else _min_yp_rb
        _h_eff = _y_prime_top_ref - _yp_tens
    else:
        _h_eff = _y_prime_top_ref - _y_prime_bot_ref
    _cb_est = ecu_val / (ecu_val + _eyd) * _h_eff
    return _h_eff, _cb_est


# ══════════════════════════════════════════════════════════════════════
# 단면 미리보기 그리기 (좌표축 + 철근)
# ══════════════════════════════════════════════════════════════════════
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


# ══════════════════════════════════════════════════════════════════════
# ┌────────────────── 기본값 (접힌 상태 대응) ───────────────────────┐
# ══════════════════════════════════════════════════════════════════════
code_name   = "KDS 24 14 21:2025"
fck         = 30;  fy = 400;  curve_conc = "parabolic_rectangular"
sec_type    = "직사각형";  b = 400.;  h = 600.
n_top=4;  dia_top=32;  cov_top=70
n_bot=4;  dia_bot=32;  cov_bot=70
n_left=0; dia_left=25; cov_left=40
n_right=0; dia_right=25; cov_right=40
cover = 70;  bar_dia = 32
rb_list: list = []
poly_outer = None;  poly_holes = [];  poly_rebar_positions = []
use_strand  = False; strand_params = None; strand_dia_val = 15.2
fpk_val = fp01k_val = Ep_val = fpe_val = eps_pe_val = 0
df_loads = pd.DataFrame({
    "극단": [False], "케이스":["LC1"],
    "Pu [kN]":[3000.], "Mx [kN·m]":[450.], "My [kN·m]":[0.],
})
avg_Mx=1.0; avg_My=0.0; theta_rad=0.0; theta_deg_auto=0.0
sym_check=False; n_pts=200; ny_fiber=120
run = False

# ══════════════════════════════════════════════════════════════════════
# ┌────────────────────── 좌우 2분할 레이아웃 ───────────────────────┐
# ══════════════════════════════════════════════════════════════════════
_exp   = st.session_state.inp_expand
_inp_w = st.session_state.inp_width   # 입력창 폭 (2~7)
if _exp:
    col_in, col_out = st.columns([_inp_w, 10 - _inp_w], gap="small")
else:
    col_in, col_out = st.columns([1, 11], gap="small")

# ─────────────────────────────────────────────────────────────────────
# ◀ 왼쪽 — 입력
# ─────────────────────────────────────────────────────────────────────
with col_in:

    # ══ 상단: 우측 정렬 접기/펼치기 버튼 ═══════════════════════════
    _sp, _bc = st.columns([5, 1])
    with _bc:
        if _exp:
            if st.button("<<", key="toggle_inp", use_container_width=True,
                         help="입력창 접기"):
                st.session_state.inp_expand = False; st.rerun()
        else:
            if st.button(">>", key="toggle_inp", use_container_width=True,
                         help="입력창 펼치기"):
                st.session_state.inp_expand = True; st.rerun()

    if _exp:
        # ══ ① 설계기준 & 재료 ══════════════════════════════════════
        with st.expander("🏛  설계기준 · 재료 강도", expanded=True):
            # 설계기준 선택 (전체 폭, 라벨 표시)
            code_name = st.selectbox("설계기준 선택", list(CODES.keys()), key="sel_code")
            _code_tmp = CODES[code_name]()
            # fck / fck응력곡선 / fy — 한 줄
            m1, m2, m3 = st.columns(3)
            fck        = m1.number_input("fck [MPa]", 18, 90, 30, 2, key="inp_fck")
            curve_conc = m2.selectbox("fck 응력곡선",
                                      ["parabolic_rectangular","bilinear","linear"],
                                      key="inp_curve")
            fy         = m3.number_input("fy [MPa]",  300, 600, 400, 50, key="inp_fy")
            # KDS 계수 설명 — fck/fy 아래
            _fcd_tmp = _code_tmp.fcd(fck)
            _ecu_tmp = _code_tmp.epsilon_cu(fck)
            _Ec_tmp  = _code_tmp.elastic_modulus_concrete(fck)
            _fyd_tmp = _code_tmp.fyd(fy)
            _mf      = _code_tmp.material_factors("ULS")
            _gc = _mf.gamma_c; _gs = _mf.gamma_s; _acc = _mf.alpha_cc
            st.caption(
                f"fcd = αcc·fck·Φc = {_acc}×{fck}×{_gc} = **{_fcd_tmp:.2f}** MPa  │  "
                f"εcu = **{_ecu_tmp*1e3:.2f}‰**  │  Ec = **{_Ec_tmp:.0f}** MPa"
            )
            st.caption(
                f"fyd = fy·Φs = {fy}×{_gs} = **{_fyd_tmp:.1f}** MPa  │  "
                f"Es = **200,000** MPa"
            )

        # ══ ② 단면 형상 ════════════════════════════════════════════
        # 제목 행: [📐 단면 형상] [콤보박스] [👁]  ← 같은 행에 모두 배치
        with st.container(border=True):
            poly_outer = None; poly_holes = []; poly_rebar_positions = []

            _h1, _h2, _h3 = st.columns([1.4, 3.2, 0.75])
            _h1.markdown("**📐 단면 형상**")
            sec_type = _h2.selectbox(
                "형상 선택", ["직사각형","원형","임의 다각형"],
                label_visibility="collapsed", key="sec_type_sel")
            if _h3.button("👁", key="prev_btn", help="단면 미리보기"):
                st.session_state.show_preview = True

            # ── 치수 (피복은 철근 배치 테이블로 이동) ──────────────
            diameter = None
            if sec_type == "직사각형":
                d1, d2 = st.columns(2)
                b = d1.number_input("b [mm]", 100, 5000, 400, 50, key="inp_b")
                h = d2.number_input("h [mm]", 100, 5000, 600, 50, key="inp_h")
            elif sec_type == "원형":
                d1, d2 = st.columns(2)
                diameter = d1.number_input("D [mm]", 200, 5000, 600, 50, key="inp_D")
                b = h = diameter
                cover = d2.number_input("피복 c [mm]", 20, 200, 40, 5, key="inp_cov_circ")
                bar_dia = 25  # circle uses single bar_dia
            else:
                cover = st.number_input("피복 c [mm]", 20, 200, 40, 5, key="inp_cov_poly")
                b, h = 400., 600.

            # 임의 다각형 전용 입력
            if sec_type == "임의 다각형":
                pf1,pf2 = st.columns([3,1])
                uploaded_outer = pf1.file_uploader(
                    "외곽 CSV", type=["csv","txt"],
                    label_visibility="collapsed", key="up_outer")
                pf2.download_button("📎외곽예제",
                    "x,y\n0,0\n400,0\n400,600\n0,600\n",
                    "outer.csv","text/csv", use_container_width=True)
                def_outer = pd.DataFrame({"x[mm]":[0.,400.,400.,0.],"y[mm]":[0.,0.,600.,600.]})
                if uploaded_outer:
                    try:
                        _df=pd.read_csv(uploaded_outer,header=0)
                        _df.columns=["x[mm]","y[mm]"]; def_outer=_df
                    except Exception: st.error("CSV 파싱 오류")
                df_outer = st.data_editor(def_outer, num_rows="dynamic",
                    use_container_width=True, key="df_outer", height=120)
                try:
                    poly_outer=df_outer[["x[mm]","y[mm]"]].dropna().values.tolist()
                    xs=[p[0] for p in poly_outer]; ys=[p[1] for p in poly_outer]
                    b=max(xs)-min(xs); h=max(ys)-min(ys)
                except Exception: poly_outer=[[0,0],[400,0],[400,600],[0,600]]

                if st.checkbox("중공 포함", key="cb_hole"):
                    hf1,hf2=st.columns([3,1])
                    uploaded_hole=hf1.file_uploader("중공 CSV", type=["csv","txt"],
                        label_visibility="collapsed", key="up_hole")
                    hf2.download_button("📎중공예제",
                        "x,y\n100,100\n300,100\n300,500\n100,500\n",
                        "hole.csv","text/csv", use_container_width=True)
                    def_hole=pd.DataFrame({"x[mm]":[100.,300.,300.,100.],"y[mm]":[100.,100.,500.,500.]})
                    if uploaded_hole:
                        try:
                            _dh=pd.read_csv(uploaded_hole,header=0); _dh.columns=["x[mm]","y[mm]"]; def_hole=_dh
                        except Exception: pass
                    df_hole=st.data_editor(def_hole, num_rows="dynamic",
                        use_container_width=True, key="df_hole", height=110)
                    try:
                        hp=df_hole[["x[mm]","y[mm]"]].dropna().values.tolist()
                        if len(hp)>=3: poly_holes=[hp]
                    except Exception: poly_holes=[]

                rb_f1,rb_f2=st.columns([3,1])
                uploaded_rb=rb_f1.file_uploader("철근 CSV", type=["csv","txt"],
                    label_visibility="collapsed", key="up_rb")
                rb_f2.download_button("📎철근예제",
                    "x,y\n50,50\n200,50\n350,50\n50,550\n200,550\n350,550\n",
                    "rebar.csv","text/csv", use_container_width=True)
                def_rb=pd.DataFrame({"x[mm]":[50.,200.,350.,50.,200.,350.],"y[mm]":[50.,50.,50.,550.,550.,550.]})
                if uploaded_rb:
                    try:
                        _dr=pd.read_csv(uploaded_rb,header=0); _dr.columns=["x[mm]","y[mm]"]; def_rb=_dr
                    except Exception: pass
                df_rb=st.data_editor(def_rb, num_rows="dynamic",
                    use_container_width=True, key="df_rb", height=120)
                try: poly_rebar_positions=df_rb[["x[mm]","y[mm]"]].dropna().values.tolist()
                except Exception: poly_rebar_positions=[]

        # ══ ③ 철근 배치 (테이블: 위치/갯수/직경/피복) ═══════════════
        with st.expander("🔩  철근 배치", expanded=True):
            if sec_type != "임의 다각형":
                _rebar_default = pd.DataFrame({
                    "위치":     ["상단",  "하단",  "좌측면", "우측면"],
                    "갯수":     [4,        4,        0,        0      ],
                    "D [mm]":   [32,       32,       25,       25     ],
                    "피복 [mm]":[70,       70,       40,       40     ],
                })
                df_rebar = st.data_editor(
                    _rebar_default,
                    column_config={
                        "위치":     st.column_config.TextColumn(
                                        "위치", disabled=True, width="small"),
                        "갯수":     st.column_config.NumberColumn(
                                        "갯수", min_value=0, max_value=30, step=1, width="small"),
                        "D [mm]":   st.column_config.NumberColumn(
                                        "D [mm]", min_value=6, max_value=51, step=1, width="small"),
                        "피복 [mm]":st.column_config.NumberColumn(
                                        "피복 [mm]", min_value=10, max_value=200, step=5, width="small"),
                    },
                    hide_index=True, use_container_width=True, key="df_rebar",
                )
                r = df_rebar
                n_top   = int(r.iloc[0]["갯수"]);  dia_top   = int(r.iloc[0]["D [mm]"]);  cov_top   = int(r.iloc[0]["피복 [mm]"])
                n_bot   = int(r.iloc[1]["갯수"]);  dia_bot   = int(r.iloc[1]["D [mm]"]);  cov_bot   = int(r.iloc[1]["피복 [mm]"])
                n_left  = int(r.iloc[2]["갯수"]);  dia_left  = int(r.iloc[2]["D [mm]"]);  cov_left  = int(r.iloc[2]["피복 [mm]"])
                n_right = int(r.iloc[3]["갯수"]);  dia_right = int(r.iloc[3]["D [mm]"]);  cov_right = int(r.iloc[3]["피복 [mm]"])
                cover   = cov_top      # 일반 피복 참조값 (강연선 등)
                bar_dia = dia_top      # 참조 직경
                if sec_type == "직사각형":
                    rb_list = compute_rebar_positions(
                        b, h,
                        n_top,  dia_top,  cov_top,
                        n_bot,  dia_bot,  cov_bot,
                        n_left, dia_left, cov_left,
                        n_right,dia_right,cov_right,
                    )
                st.caption(
                    f"총 {n_top+n_bot+n_left+n_right}개  │  "
                    f"좌·우면 철근은 상·하단 모서리와 겹치지 않게 배치"
                )
            else:
                n_top = n_bot = n_left = n_right = 0
                bar_dia = st.number_input("철근 직경 D [mm]", 10, 51, 25, 1)
                rb_list = []

        # ══ ④ 강연선 (접힘) ══════════════════════════════════════════
        use_strand = False; strand_pos = []; strand_dia_val = 15.2
        fpk_val = fp01k_val = Ep_val = fpe_val = eps_pe_val = 0
        with st.expander("🔗  강연선 (PSC)", expanded=False):
            use_strand = st.checkbox("강연선 포함", False, key="cb_strand")
            if use_strand:
                ss1,ss2=st.columns(2)
                fpk_val=ss1.number_input("fpk",1000,2100,1860,10)
                fp01k_val=ss2.number_input("fp0.1k",800,2000,1580,10)
                ss3,ss4=st.columns(2)
                Ep_val=ss3.number_input("Ep",180000,210000,195000,1000)
                fpe_val=ss4.number_input("fpe[MPa]",0,1500,900,50)
                eps_pe_val=fpe_val/Ep_val
                ss5,ss6=st.columns(2)
                strand_dia_val=ss5.number_input("직경[mm]",9.5,22.,15.2,0.1)
                n_strand=ss6.number_input("개수",1,30,4,1)
                y_strand=st.number_input("y[mm](도심기준)",value=int(-h//2+cover+50),step=10)
                xsp=(b-2*(cover+strand_dia_val))/max(n_strand-1,1)
                xst0=-(b/2-cover-strand_dia_val)
                strand_pos=[(xst0+i*xsp,float(y_strand)) for i in range(n_strand)]

        # ══ ⑤ 하중 케이스 ══════════════════════════════════════════
        with st.container(border=True):
            _lh1, _lh2 = st.columns([4.2, 0.8])
            _lh1.markdown("**📋 하중 케이스**")
            n_lc = _lh2.number_input(
                "갯수", min_value=1, max_value=30, value=3, step=1,
                key="n_lc", label_visibility="collapsed",
                help="하중 케이스 초기 행 수 (입력 후 Enter)"
            )
            # n_lc 변경 시 기본 행 수 재구성
            _prev_n = st.session_state.get("_prev_n_lc", 3)
            if n_lc != _prev_n:
                st.session_state["_prev_n_lc"] = n_lc
                st.session_state.pop("df_loads", None)  # 키 초기화
            st.session_state["_prev_n_lc"] = n_lc
            _default_lc = pd.DataFrame({
                "극단":      [False] * n_lc,
                "케이스":    [f"LC{i+1}" for i in range(n_lc)],
                "Pu [kN]":   [3000. - i*300 for i in range(n_lc)],
                "Mx [kN·m]": [450.  - i*50  for i in range(n_lc)],
                "My [kN·m]": [0.] * n_lc,
            })
            df_loads = st.data_editor(
                _default_lc,
                column_config={
                    "극단": st.column_config.CheckboxColumn(
                        "극단", help="극단한계상태/사고 하중", default=False, width="small"),
                    "케이스": st.column_config.TextColumn("케이스", width="small"),
                    "Pu [kN]":   st.column_config.NumberColumn("Pu [kN]",   width="small"),
                    "Mx [kN·m]": st.column_config.NumberColumn("Mx [kN·m]", width="small"),
                    "My [kN·m]": st.column_config.NumberColumn("My [kN·m]", width="small"),
                },
                num_rows="dynamic", use_container_width=True, key="df_loads",
            )
            try:
                vl=df_loads.dropna(subset=["Pu [kN]","Mx [kN·m]","My [kN·m]"])
                avg_Mx=float(vl["Mx [kN·m]"].abs().mean()) if not vl.empty else 1.0
                avg_My=float(vl["My [kN·m]"].abs().mean()) if not vl.empty else 0.0
                theta_rad=math.atan2(avg_My, avg_Mx)
                theta_deg_auto=math.degrees(theta_rad)
            except Exception:
                avg_Mx=1.0; avg_My=0.0; theta_rad=0.0; theta_deg_auto=0.0
            st.caption(f"θ = **{theta_deg_auto:.1f}°** (자동)  │  Ctrl+S = P-M 계산")
            sym_check = st.checkbox("2축 대칭 — 양/음 M 동시 표기")

        # ══ ⑥ 해석 설정 (접힘) ══════════════════════════════════════
        with st.expander("⚙️  해석 설정", expanded=False):
            an1,an2=st.columns(2)
            n_pts   =an1.number_input("포인트 수",50,500,200,50)
            ny_fiber=an2.number_input("파이버 분할",50,900,120,10)

        run = st.button("🚀  P-M 상관도 계산  (Ctrl+S)",
                        use_container_width=True, type="primary")
        if run:
            st.session_state.show_preview = False  # 계산 시 미리보기 자동 닫기

# 설계기준 재료 계수 (항상 계산)
code    = CODES[code_name]()
fcd_val = code.fcd(fck)
ecu_val = code.epsilon_cu(fck)
Ec_val  = code.elastic_modulus_concrete(fck)
fyd_val = code.fyd(fy)

# ─────────────────────────────────────────────────────────────────────
# ▶ 오른쪽 — 출력
# ─────────────────────────────────────────────────────────────────────
with col_out:
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
            strand_params = None
            if use_strand and strand_pos:
                strand_params = dict(fpk=fpk_val, fp01k=fp01k_val, Ep=Ep_val,
                    fpd=code.fpd(fp01k_val), eps_pe=eps_pe_val,
                    positions=strand_pos, dia=strand_dia_val)

            _ag_theory_run = _ag_theory_mm2(sec_type, b, h, poly_outer, poly_holes)
            _ny_cap = 900
            _ny_try = max(50, int(ny_fiber))
            ny_used = _ny_try
            mesh_warn = None
            section = None
            _ag_mesh_normalized = False
            for _mesh_it in range(48):
                _ny_cur = min(int(_ny_try), _ny_cap)
                section, conc_d, rebar_d = build_section(
                    b,h,cover,fck,fcd_val,fy,fyd_val,
                    rb_list, bar_dia, n_top,n_bot,n_left,n_right,
                    curve_conc, use_strand, strand_params, _ny_cur, sec_type,
                    poly_outer, poly_holes,
                    poly_rebar_positions if sec_type=="임의 다각형" else None)
                # ── 철근 파이버 타입 확인 디버그 ──────────────────────
                for _f in section.fibers[:10]:  # 처음 10개만 출력
                    print(f"  material type: {type(_f.material).__name__}, area: {_f.area:.1f}")
                # ────────────────────────────────────────────────────
                # ── 임시 디버그: strip 제거량 확인 ──────────────────────────
                _Ac_before_strip = sum(
                    f.area for f in section.fibers if isinstance(f.material, Concrete))
                _As_check = sum(
                    f.area for f in section.fibers if isinstance(f.material, Rebar))
                print(f"[STRIP DEBUG]")
                print(f"  Ac(strip 후) = {_Ac_before_strip:.1f} mm²")
                print(f"  As(철근)     = {_As_check:.1f} mm²")
                print(f"  Ag(전체)     = {_Ac_before_strip + _As_check:.1f} mm²")
                print(f"  이론 Ag      = {b*h:.1f} mm²")
                print(f"  이론 As      = {_As_check:.1f} mm²")
                print(f"  이론 Ac      = {b*h - _As_check:.1f} mm²")
                print(f"  Ac 차이      = {_Ac_before_strip - (b*h - _As_check):.1f} mm²")
                # ────────────────────────────────────────────────────────────
                # ── rb_list 좌표 확인 디버그 ──────────────────────────
                print("[RB_LIST DEBUG]")
                for _f in section.fibers:
                    if isinstance(_f.material, Rebar):
                        print(f"  rebar x={_f.x:.1f}, y={_f.y:.1f}, area={_f.area:.1f}")
                print(f"  단면범위: x={-b/2:.0f}~{b/2:.0f}, y={-h/2:.0f}~{h/2:.0f}")
                # ────────────────────────────────────────────────────

                section_nom, _, _ = build_section(
                    b,h,cover,fck,fck,fy,fy,
                    rb_list, bar_dia, n_top,n_bot,n_left,n_right,
                    curve_conc, False, None, _ny_cur, sec_type,
                    poly_outer, poly_holes,
                    poly_rebar_positions if sec_type=="임의 다각형" else None)
                ag_m = section.gross_area()
                ag_err_r = (
                    abs(ag_m - _ag_theory_run) / _ag_theory_run
                    if _ag_theory_run > 1e-9 else 0.0
                )
                _, cb_t = _h_eff_and_cb_theory(
                    section, theta_rad, ecu_val, fyd_val, sec_type, b, h)
                _eps_bb, _, _ = diagram_max_positive_moment_strain(
                    section, ecu_val, n_pts, theta_rad, phi=1.0)
                _bpm = pm_result_at_strains(
                    section, ecu_val, _eps_bb, theta_rad, phi=1.0)
                _ytr2, _ybr2 = section.rotated_y_extremes(theta_rad)
                c_bal_try = (
                    float(_bpm.c_mm)
                    if _bpm.c_mm < 1e8
                    else max(_ytr2 - _ybr2, 1.0) * 0.5
                )
                cb_err_r = (
                    abs(c_bal_try - cb_t) / cb_t if cb_t > 1e-6 else 0.0
                )
                ny_used = _ny_cur
                if ag_err_r <= MESH_AG_TOL and cb_err_r <= MESH_CB_TOL:
                    break
                if _ny_cur >= _ny_cap:
                    mesh_warn = (
                        f"ny={_ny_cap} max: Ag rel.err.>{MESH_AG_TOL*100:.4f}% or "
                        f"cb rel.err.>{MESH_CB_TOL*100:.4f}% "
                        f"(Ag {ag_err_r*100:.5f}%, cb {cb_err_r*100:.5f}%)."
                    )
                    break
                _ny_try = _ny_cur + max(10, _ny_cur // 8)
            else:
                mesh_warn = (
                    "Mesh auto-tune iteration limit; increase ny in solver settings."
                )

            if _ag_theory_run > 1e-9:
                _ag_err_fin = abs(section.gross_area() - _ag_theory_run) / _ag_theory_run
                if _ag_err_fin > MESH_AG_TOL:
                    section.normalize_concrete_to_ag_theory(float(_ag_theory_run))
                    section_nom.normalize_concrete_to_ag_theory(float(_ag_theory_run))
                    _ag_mesh_normalized = True

            geo        = section.geometric_properties(theta=theta_rad)
            pm_des     = compute_pm_diagram(section,     ecu=ecu_val, n_pts=n_pts, theta=theta_rad)
            pm_nom     = compute_pm_diagram(section_nom, ecu=ecu_val, n_pts=n_pts, theta=theta_rad)
            solver_out = compute_pm_solver(
                section, ecu=ecu_val, etu=PM_DIAGRAM_ETU,
                n_pts=n_pts, theta=theta_rad, store_fiber_states=True)

        def _half(pm_list):
            pts = sorted([(p.N_kN,p.M_kNm) for p in pm_list if p.M_kNm>=-1e-3],
                         key=lambda x:-x[0])
            return np.array([x[0] for x in pts]), np.array([x[1] for x in pts])

        N_des, M_des = _half(pm_des)
        N_nom, M_nom = _half(pm_nom)

        N_max_v  = float(N_des.max())
        M_p0, N_p0   = _p0_point(N_des, M_des)

        pos_res  = [r for r in solver_out.pm_results if r.M_kNm >= -1e-3]
        # Balanced Pb/Mb: εcu at y'_top, -εyd at outermost steel y' -> ε_bot at mesh y'_bot.
        _, _cb_theory_bal = _h_eff_and_cb_theory(
            section, theta_rad, ecu_val, fyd_val, sec_type, b, h)
        _ytr, _ybr = section.rotated_y_extremes(theta_rad)
        _ct_b, _st_b = math.cos(theta_rad), math.sin(theta_rad)
        _y_steel_primes = [
            -f.x * _st_b + f.y * _ct_b for f in section.fibers
            if isinstance(f.material, (Rebar, Strand))]
        _y_tens_out = min(_y_steel_primes) if _y_steel_primes else _ybr
        _eyd_bal = fyd_val / 200000.0
        _eps_bal_bot = eps_bot_for_tension_yield_at_depth(
            ecu_val, _ytr, _ybr, _y_tens_out, _eyd_bal)
        _eps_bal_bot = float(max(
            min(_eps_bal_bot, ecu_val * (1.0 - 1e-12)), -PM_DIAGRAM_ETU))
        _bal_pm = pm_result_at_strains(
            section, ecu_val, _eps_bal_bot, theta_rad, phi=1.0)
        N_bal = float(_bal_pm.N_kN)
        M_bal = float(_bal_pm.M_kNm)
        c_bal_mm = (
            float(_bal_pm.c_mm) if _bal_pm.c_mm < 1e8 else float(_cb_theory_bal))
        eps_bal_top = float(_bal_pm.eps_top)
        eps_bal_bot = float(_bal_pm.eps_bot)

        try:
            load_cases = df_loads.dropna(
                subset=["Pu [kN]","Mx [kN·m]","My [kN·m]"]).to_dict("records")
        except Exception:
            load_cases = []
        lc1_Pn_cap = lc1_Mn_cap = lc1_eps_bot = None
        if load_cases:
            _lc0 = load_cases[0]
            _Pu0 = float(_lc0.get("Pu [kN]", 0))
            _Mx0 = float(_lc0.get("Mx [kN·m]", 0))
            _My0 = float(_lc0.get("My [kN·m]", 0))
            _Mu0 = math.sqrt(_Mx0**2 + _My0**2)
            _N0 = np.asarray(N_des, float)
            _M0 = np.asarray(M_des, float)
            _Mr, _Pr = _ray_intersect_pm_curve(_Mu0, _Pu0, _M0, _N0)
            if _Mr is not None and abs(_Pu0) > 1e-6:
                lc1_Pn_cap = float(_Pr)
                lc1_Mn_cap = float(_Mr)
                lc1_eps_bot, _, _ = diagram_closest_strain_to_nm(
                    section, ecu_val, n_pts, theta_rad, 1.0, lc1_Pn_cap, lc1_Mn_cap)
            elif abs(_Pu0) > 1:
                _e_arr0 = np.where(_N0 > 10, _M0 / (_N0 + 1e-9), 1e12)
                _ix0 = int(np.argmin(np.abs(_e_arr0 - _Mu0 / (_Pu0 + 1e-9))))
                lc1_Pn_cap = float(_N0[_ix0])
                lc1_Mn_cap = float(_M0[_ix0])
                lc1_eps_bot, _, _ = diagram_closest_strain_to_nm(
                    section, ecu_val, n_pts, theta_rad, 1.0, lc1_Pn_cap, lc1_Mn_cap)
            else:
                lc1_Pn_cap = 0.0
                lc1_Mn_cap = float(_M0[int(np.argmax(_M0))])
                lc1_eps_bot, _, _ = diagram_closest_strain_to_nm(
                    section, ecu_val, n_pts, theta_rad, 1.0, lc1_Pn_cap, lc1_Mn_cap)



        # ── 계산 결과 캐시 ─────────────────────────────────────────
        st.session_state["pm_cache"] = dict(
            N_des=N_des.tolist(), M_des=M_des.tolist(),
            N_nom=N_nom.tolist(), M_nom=M_nom.tolist(),
            N_max_v=N_max_v, N_bal=N_bal, M_bal=M_bal, M_p0=M_p0, N_p0=N_p0,
            n_pts=int(n_pts),
            lc1_Pn_cap=lc1_Pn_cap, lc1_Mn_cap=lc1_Mn_cap, lc1_eps_bot=lc1_eps_bot,
            c_bal_mm=c_bal_mm, eps_bal_top=eps_bal_top, eps_bal_bot=eps_bal_bot,
            section=section, geo=geo, solver_out=solver_out, pos_res=pos_res,
            load_cases=load_cases,
            theta_rad=theta_rad, theta_deg_auto=theta_deg_auto,
            sec_type=sec_type, b=b, h=h,
            poly_outer=poly_outer, poly_holes=poly_holes,
            strand_dia_val=strand_dia_val, use_strand=use_strand, bar_dia=bar_dia,
            n_top=n_top, n_bot=n_bot, n_left=n_left, n_right=n_right,
            fck=fck, fy=fy, fcd_val=fcd_val, fyd_val=fyd_val,
            ecu_val=ecu_val, Ec_val=Ec_val,
            ny_fiber_req=int(ny_fiber),
            ny_fiber_used=int(ny_used),
            mesh_warn=mesh_warn,
            Ag_theory=float(_ag_theory_run),
            Ag_mesh_normalized=_ag_mesh_normalized,
        )
        # 검증 분석 플래그 초기화 (재계산 시 리셋)
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
    fck=_cache["fck"]; fy=_cache["fy"]
    fcd_val=_cache["fcd_val"]; fyd_val=_cache["fyd_val"]
    ecu_val=_cache["ecu_val"]; Ec_val=_cache["Ec_val"]
    ny_fiber_used = int(_cache.get("ny_fiber_used", 120))
    ny_fiber_req = _cache.get("ny_fiber_req")
    mesh_warn_msg = _cache.get("mesh_warn")
    Ag_theory_cached = float(_cache.get("Ag_theory", _ag_theory_mm2(
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
                M_cap, N_cap = _ray_intersect_pm_curve(M_lc1, N_lc1, M_des, N_des)
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
                safe=_is_safe(N_u,Mu,N_des,M_des)
                util=_utilization(N_u,Mu,N_des,M_des)
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
                    Mu=math.sqrt(Mx_u**2+My_u**2); safe=_is_safe(N_u,Mu,N_des,M_des)
                    util=_utilization(N_u,Mu,N_des,M_des)
                    rows.append({"케이스":lc.get("케이스","LC"),
                        "극단":"★" if lc.get("극단") else "",
                        "Pu [kN]":round(N_u,1),"Mx":round(Mx_u,1),"My":round(My_u,1),
                        "Mu [kN·m]":round(Mu,1),                        "M용량":round(_m_cap(N_u,N_des,M_des),1),
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
        # ── 저장용 세션키 초기화 (위젯 key와 분리, on_change로 동기화) ──
        _vref_store_defs = {
            # 1. 축압축강도
            "s_v_ag": 0.0, "s_v_as": 0.0, "s_v_fcd": 0.0, "s_v_fyd": 0.0,
            "s_v_pmax": 0.0,
            # 2. LC1 기준 (e값 기준 균형점 포함)
            "s_v_ecu": 0.0, "s_v_ey": 0.0, "s_v_cb": 0.0,
            "s_v_d": 0.0,
            "s_v_ccb": 0.0, "s_v_csb": 0.0, "s_v_tb": 0.0,
            "s_v_mb": 0.0, "s_v_pb": 0.0,
            "s_v_ccd": 0.0, "s_v_csd": 0.0, "s_v_td": 0.0,
            "s_v_mn1": 0.0, "s_v_pn1": 0.0,
            "v_analysis_done": False,
        }
        for _sk, _sv in _vref_store_defs.items():
            if _sk not in st.session_state:
                st.session_state[_sk] = _sv

        # ── 사전 계산 ──────────────────────────────────────────────
        # KDS ULS 재료계수 (코드 객체에서 직접 취득)
        _code_v  = CODES[code_name]()
        _mf_v    = _code_v.material_factors("ULS")
        _gc      = _mf_v.gamma_c    # 0.65
        _gs      = _mf_v.gamma_s    # 0.9
        _acc     = _mf_v.alpha_cc   # 0.85
        _Ag      = b * h
        _As      = sum(f.area for f in section.fibers if isinstance(f.material, Rebar))
        _Ac      = _Ag - _As
        _n_rb    = n_top + n_bot + n_left + n_right
        _Pn_calc = (fcd_val * _Ac + fyd_val * _As) / 1000.0
        _Pn_eng  = N_max_v   # P-M 상관도 최대값 (엔진 결과와 일치)
        _Nc_pmax, _Ns_pmax, _Nsum_pmax = axial_force_split_materials_kn(
            section, ecu_val, ecu_val, theta_rad, phi=1.0)
        _Ag_geo = float(geo.A)
        _Ag_mesh_tot = float(section.gross_area())
        _As_steel_tot = sum(
            f.area for f in section.fibers
            if isinstance(f.material, (Rebar, Strand)))
        _Ac_mesh = sum(
            f.area for f in section.fibers if isinstance(f.material, Concrete))
        _Ac_theory = max(Ag_theory_cached - _As_steel_tot, 0.0)
        _Cc_linear = fcd_val * _Ac_theory / 1000.0
        _Cs_hand = fyd_val * _As / 1000.0
        _eyd     = fyd_val / 200000.0   # 설계항복변형률 εyd = fyd/Es

        if sec_type == "직사각형" and abs(theta_rad) < 1e-9:
            _y_prime_top_ref = float(h) / 2.0
            _y_prime_bot_ref = -float(h) / 2.0
        else:
            _y_prime_top_ref, _y_prime_bot_ref = section.rotated_y_extremes(theta_rad)

        # d = 압축 극단면에서 인장철근 중심까지의 거리 (회전 좌표계 기준)
        _rb_yp_list = []
        for _f in section.fibers:
            if isinstance(_f.material, Rebar):
                _yp = -_f.x * math.sin(theta_rad) + _f.y * math.cos(theta_rad)
                _rb_yp_list.append((_yp, _f.area))
        _d_debug_lines = []   # d 계산 근거용
        if _rb_yp_list:
            _rb_yp_sorted = sorted(_rb_yp_list, key=lambda x: x[0])
            _min_yp_rb = _rb_yp_sorted[0][0]
            _max_yp_rb = _rb_yp_sorted[-1][0]
            # 가장 인장 측(y' 최소) 철근행을 직경 기준으로 묶음
            _dia_ref  = 2 * math.sqrt(max(a for _, a in _rb_yp_list) / math.pi)
            _tol_d    = max(_dia_ref * 1.5, 30.0)
            _tens_rb  = [(yp, a) for yp, a in _rb_yp_list if yp <= _min_yp_rb + _tol_d]
            _At_tot   = sum(a for _, a in _tens_rb)
            _yp_tens  = sum(yp * a for yp, a in _tens_rb) / _At_tot if _At_tot > 0 else _min_yp_rb
            _h_eff    = _y_prime_top_ref - _yp_tens
            _d_debug_lines = [
                f"  전체 철근 y'범위: {_min_yp_rb:.1f} ~ {_max_yp_rb:.1f} mm",
                f"  인장철근 묶음기준: y' ≤ {_min_yp_rb+_tol_d:.1f} mm (tol={_tol_d:.1f})",
                f"  인장철근 {len(_tens_rb)}개  As_tens={_At_tot:.0f}mm²",
                f"  인장철근 중심 y'={_yp_tens:.1f}mm",
                f"  압축극단 y'_top={_y_prime_top_ref:.1f}mm (P-M 엔진 기준)",
                f"  d = y'_top - y'_tens = {_h_eff:.1f} mm",
            ]
        else:
            _h_eff = _y_prime_top_ref - _y_prime_bot_ref
            _d_debug_lines = [f"  철근 없음 → d=h={_h_eff:.1f}mm"]
            _yp_tens = _y_prime_bot_ref
        _yp_tens_ui = _yp_tens
        _cb_est  = ecu_val / (ecu_val + _eyd) * _h_eff

        # Balanced: same eps_bot as P-M run (Pb, Mb, fibers 1:1).
        _bal_pm = pm_result_at_strains(
            section, ecu_val, eps_bal_bot, theta_rad, phi=1.0)

        def _fiber_forces_pm(pm):
            if pm is None or not pm.fiber_states:
                return 0.0, 0.0, 0.0
            _Cc = sum(fs.force_kn for fs in pm.fiber_states if fs.mat_type == "concrete")
            _Cs = sum(fs.force_kn for fs in pm.fiber_states
                      if fs.mat_type == "rebar" and fs.force_kn > 0)
            _T  = abs(sum(fs.force_kn for fs in pm.fiber_states
                          if fs.mat_type in ("rebar", "strand") and fs.force_kn < 0))
            return _Cc, _Cs, _T

        def _fiber_counts_pm(pm):
            if pm is None or not pm.fiber_states:
                return 0, 0, 0
            _nc = sum(1 for fs in pm.fiber_states if fs.mat_type == "concrete")
            _ncs = sum(1 for fs in pm.fiber_states
                       if fs.mat_type == "rebar" and fs.force_kn > 0)
            _nt = sum(1 for fs in pm.fiber_states
                      if fs.mat_type in ("rebar", "strand") and fs.force_kn < 0)
            return _nc, _ncs, _nt

        _Ccb, _Csb, _Tb = _fiber_forces_pm(_bal_pm)
        _Pb_eng = N_bal
        _Mb_eng = M_bal
        _cs_eps_bal = [
            fs.strain_geom for fs in (_bal_pm.fiber_states or [])
            if fs.mat_type == "rebar" and fs.force_kn > 0
        ]
        if _cs_eps_bal:
            _eps_csb_min, _eps_csb_max = min(_cs_eps_bal), max(_cs_eps_bal)
        else:
            _eps_csb_min = _eps_csb_max = float("nan")
        _tb_detail_lines = []
        for fs in _bal_pm.fiber_states or []:
            if fs.mat_type in ("rebar", "strand") and fs.force_kn < 0:
                _tb_detail_lines.append(
                    f"      #{fs.fiber_id:03d} y'={fs.y_prime_mm:.1f} A={fs.area_mm2:.0f} "
                    f"ε={fs.strain_geom*1000:.4f}‰ σ={fs.stress_mpa:.2f}MPa F={fs.force_kn:.4f}kN")
        _tb_detail_txt = (
            "\n".join(_tb_detail_lines)
            if _tb_detail_lines else "      (인장 철근·강연선 없음)")
        _tb_f_sum = sum(
            fs.force_kn for fs in (_bal_pm.fiber_states or [])
            if fs.mat_type in ("rebar", "strand") and fs.force_kn < 0)
        _steel_fs_bal = [
            fs for fs in (_bal_pm.fiber_states or [])
            if fs.mat_type in ("rebar", "strand")]
        _fs_tens_outer = (
            min(_steel_fs_bal, key=lambda fs: fs.y_prime_mm)
            if _steel_fs_bal else None)
        _eps_tens_outer_bal = (
            float(_fs_tens_outer.strain_geom) if _fs_tens_outer else float("nan"))
        _abs_diff_eyd = (
            abs(abs(_eps_tens_outer_bal) - _eyd)
            if _fs_tens_outer is not None else float("nan"))

        # LC1: P-M 그래프와 동일 — 원점–(Mu,Pu) 반직선 교점 + 동일 이산 스웨프
        _lc1_ok = bool(load_cases)
        _lc1_pm = None
        _Pn_lc1 = 0.0
        _Mn_lc1 = 0.0
        if _lc1_ok:
            _lc1     = load_cases[0]
            _Pu_lc1  = float(_lc1.get("Pu [kN]",   0))
            _Mxu_lc1 = float(_lc1.get("Mx [kN·m]", 0))
            _Myu_lc1 = float(_lc1.get("My [kN·m]", 0))
            _Mu_lc1  = math.sqrt(_Mxu_lc1**2 + _Myu_lc1**2)
            _e_lc1   = (_Mu_lc1 / abs(_Pu_lc1) * 1000) if abs(_Pu_lc1) > 1 else float("inf")
            if (lc1_Pn_cap is not None and lc1_Mn_cap is not None
                    and lc1_eps_bot is not None):
                _Pn_lc1 = float(lc1_Pn_cap)
                _Mn_lc1 = float(lc1_Mn_cap)
                _lc1_pm = pm_result_at_strains(
                    section, ecu_val, float(lc1_eps_bot), theta_rad, phi=1.0)
            else:
                _N_arr   = np.asarray(N_des, float)
                _M_arr   = np.asarray(M_des, float)
                _Mn_ray, _Pn_ray = _ray_intersect_pm_curve(_Mu_lc1, _Pu_lc1, _M_arr, _N_arr)
                if _Mn_ray is not None and abs(_Pu_lc1) > 1e-6:
                    _eb_lc, _, _ = diagram_closest_strain_to_nm(
                        section, ecu_val, n_pts, theta_rad, 1.0,
                        float(_Pn_ray), float(_Mn_ray))
                    _lc1_pm = pm_result_at_strains(
                        section, ecu_val, _eb_lc, theta_rad, phi=1.0)
                    _Pn_lc1, _Mn_lc1 = float(_Pn_ray), float(_Mn_ray)
                elif abs(_Pu_lc1) > 1:
                    _e_arr  = np.where(_N_arr > 10, _M_arr / (_N_arr + 1e-9), 1e12)
                    _idx_e  = int(np.argmin(np.abs(
                        _e_arr - _Mu_lc1 / (_Pu_lc1 + 1e-9))))
                    _Pn_lc1 = float(_N_arr[_idx_e])
                    _Mn_lc1 = float(_M_arr[_idx_e])
                    _eb_lc, _, _ = diagram_closest_strain_to_nm(
                        section, ecu_val, n_pts, theta_rad, 1.0, _Pn_lc1, _Mn_lc1)
                    _lc1_pm = pm_result_at_strains(
                        section, ecu_val, _eb_lc, theta_rad, phi=1.0)
                else:
                    _Pn_lc1 = 0.0
                    _Mn_lc1 = float(_M_arr[int(np.argmax(_M_arr))])
                    _eb_lc, _, _ = diagram_closest_strain_to_nm(
                        section, ecu_val, n_pts, theta_rad, 1.0, _Pn_lc1, _Mn_lc1)
                    _lc1_pm = pm_result_at_strains(
                        section, ecu_val, _eb_lc, theta_rad, phi=1.0)
        else:
            _Pu_lc1 = _Mu_lc1 = _e_lc1 = 0.0
            _Mxu_lc1 = _Myu_lc1 = 0.0

        if _lc1_pm is not None and _lc1_pm.c_mm < 1e8:
            _c_lc1 = float(_lc1_pm.c_mm)
        else:
            _c_lc1 = float(_cb_est)
        _state_lc1 = _lc1_pm.state if _lc1_pm is not None else "계산불가"
        _Ccd, _Csd, _Td = _fiber_forces_pm(_lc1_pm)


        # ── 오차 헬퍼 ─────────────────────────────────────────────
        def _verr(eng, ref):
            if ref is None or abs(ref) < 1e-9: return None
            return (eng - ref) / abs(ref) * 100.0

        def _err_badge(err):
            if err is None: return "&nbsp;"
            _thr = VERIFY_REF_ERR_PCT
            color = "#B71C1C" if abs(err) >= _thr else "#2E7D32"
            bg    = "#FFCDD2" if abs(err) >= _thr else "#C8E6C9"
            sign  = "+" if err >= 0 else ""
            return (f'<span style="background:{bg};color:{color};font-weight:bold;'
                    f'padding:2px 8px;border-radius:4px;font-size:0.82rem;white-space:nowrap;">'
                    f'{sign}{err:.3f}%</span>')

        def _save(store_key, widget_key):
            st.session_state[store_key] = st.session_state.get(widget_key, st.session_state[store_key])

        # ── 헤더 & 업데이트 버튼 ──────────────────────────────────
        _vh, _vbtn = st.columns([4, 1])
        _vh.markdown(f"### 검증 (참조 오차 ±{VERIFY_REF_ERR_PCT:.0f}%)")
        if _vbtn.button("🔄 검증 업데이트", use_container_width=True, key="do_verify_upd"):
            st.session_state.v_analysis_done = True
        _upd = st.session_state.v_analysis_done

        # ── 공통 on_change 팩토리 ──────────────────────────────────
        def _mk_save(sk, wk): return lambda: _save(sk, wk)

        # ── 참조값 인라인 입력 헬퍼 (레이블 | 입력 | 오차뱃지 | 검토메시지) ─
        def _ref_row(lbl, sk, wk, def_val, refs_dict, eng_val=None, warn_ctx=None, compact=False):
            _thr = VERIFY_REF_ERR_PCT
            _pt = "4px" if compact else "8px"
            _init = float(st.session_state[sk]) if st.session_state[sk] else float(def_val)
            _fmt  = "%.6f" if "ε" in lbl else ("%.3f" if abs(def_val) < 10 else "%.1f")
            _stp  = 0.0001 if "ε" in lbl else max(abs(def_val)*0.01, 0.1)
            # 레이블(좁게) | 입력(좁게) | 오차뱃지 | 검토메시지
            if compact:
                _la, _lb, _lc, _ld = st.columns([0.33, 0.46, 0.72, 1.74])
            else:
                _la, _lb, _lc, _ld = st.columns([0.35, 0.5, 0.62, 2.05])
            _la.markdown(
                f"<div class='pm-verify-lbl' style='padding-top:{_pt};white-space:nowrap;line-height:1.15;'>{lbl}</div>",
                unsafe_allow_html=True)
            _lb.number_input("", value=_init, step=_stp, format=_fmt,
                             key=wk, on_change=_mk_save(sk, wk),
                             label_visibility="collapsed")
            _cur_val = st.session_state.get(wk, _init)
            refs_dict[lbl] = _cur_val
            if eng_val is not None:
                _e = _verr(eng_val, _cur_val)
                _lc.markdown(
                    f"<div style='padding-top:{_pt};'>{_err_badge(_e)}</div>",
                    unsafe_allow_html=True)
                if _upd and warn_ctx and _e is not None and abs(_e) >= _thr:
                    _ld.markdown(
                        f'<div class="pm-verify-msg" style="padding-top:{_pt};color:#C62828;line-height:1.15;">⚠️ {warn_ctx}</div>',
                        unsafe_allow_html=True)
                elif _upd and _e is not None and abs(_e) < _thr:
                    _ld.markdown(
                        f'<div class="pm-verify-msg" style="padding-top:{_pt};color:#2E7D32;line-height:1.15;">✓</div>',
                        unsafe_allow_html=True)

        # ── 파란색 업데이트 출력 헬퍼 ─────────────────────────────────
        def _blue(text):
            st.markdown(
                f'<div class="pm-verify-msg" style="color:#1565C0;background:#E3F2FD;padding:8px 12px;'
                f'border-radius:5px;border-left:3px solid #1565C0;'
                f'margin:3px 0;">{text}</div>',
                unsafe_allow_html=True)

        # ══════════════════════════════════════════════════════════
        # ① 축압축강도 검증  Pn,max
        # ══════════════════════════════════════════════════════════
        with st.container(border=True):
            st.markdown(f"##### ① 축압축강도 검증 (Pn,max, 참조 ±{VERIFY_REF_ERR_PCT:.0f}%)")
            _ce, _cr = st.columns([3.35, 4.5])

            with _ce:
                st.markdown("**🔧 엔진 계산 과정**")
                st.code(
                    f"재료계수 (KDS 표 1.4-1)\n"
                    f"  Φc={_gc}, Φs={_gs}, αcc={_acc}\n"
                    f"fcd=αcc×fck×Φc={_acc}×{fck}×{_gc}={fcd_val:.3f} MPa\n"
                    f"fyd=fy×Φs={fy}×{_gs}={fyd_val:.1f} MPa\n"
                    f"\n"
                    f"Ag(이론·외곽기하)={Ag_theory_cached:,.0f} mm²\n"
                    f"Ag(메시)=Σ파이버면적={_Ag_mesh_tot:,.0f} mm² (=geo.A; 슬라이스·경계·ny 자동, 목표 |상대오차|≤0.001%)\n"
                    f"  As(철근)={_As:,.0f} mm²  ΣAs(철근·강연선)={_As_steel_tot:,.0f} mm²\n"
                    f"[참고] 이론상 순콘크리트 Ag(이론)−ΣAs={_Ac_theory:,.0f} mm²\n"
                    f"[참고] 파이버 ΣAc(메시)={_Ac_mesh:,.0f} mm² (슬라이스·스트립 근사)\n"
                    f"\n"
                    f"[순수압축 εcu — P-M 설계곡선 N_max와 동일 적분, φ=1.0]\n"
                    f"  Nc(콘크리트 파이버)={_Nc_pmax:,.1f} kN\n"
                    f"  Ns(철근·강연선)={_Ns_pmax:,.1f} kN\n"
                    f"  Nc+Ns={_Nsum_pmax:,.1f} kN (= P-M 탭 Pmax {_Pn_eng:.1f} kN)\n"
                    f"\n"
                    f"[참고] 선형근사 fcd×(Ag−ΣAs)={_Cc_linear:,.1f} kN (σ-ε 비선형·메시 차이로 Nc와 다름)\n"
                    f"[참고] 소계 철근 fyd×As={fyd_val:.1f}×{_As:,.0f}={_Cs_hand:,.1f} kN (강연선 별도)\n",
                    language="")
            with _cr:
                st.markdown(f"**\U0001f4d6 참조값 (기호 ｜ 입력 ｜ 오차율, ±{VERIFY_REF_ERR_PCT:.0f}%)**")
                _refs_1 = {}
                _ref_row("fck [MPa]",   "s_v_fcd",  "w_v_fcd",  float(fck),       _refs_1, float(fck))
                _ref_row("fy [MPa]",    "s_v_fyd",  "w_v_fyd",  float(fy),        _refs_1, float(fy))
                _ref_row("Ag [mm²]",    "s_v_ag",   "w_v_ag",   float(Ag_theory_cached), _refs_1,
                         float(_Ag_mesh_tot),
                         warn_ctx="Ag(이론·외곽기하) vs Ag(메시)=Σ파이버")
                _ref_row("As [mm²]",    "s_v_as",   "w_v_as",   float(round(_As)),_refs_1, float(_As))
                _ref_row("Pn,max [kN]", "s_v_pmax", "w_v_pmax", float(_Pn_eng),   _refs_1, _Pn_eng,
                         warn_ctx="fck/fy/As·Ag 또는 Φc·αcc 확인")

        # ══════════════════════════════════════════════════════════
        # ② LC1 기준 설계균형상태 및 강도 검증
        # ══════════════════════════════════════════════════════════
        with st.container(border=True):
            _lc1_name = load_cases[0].get("케이스","LC1") if _lc1_ok else "LC1"
            st.markdown(f"##### ② {_lc1_name} 기준 (Pn, Mn + 균형상태, 참조 ±{VERIFY_REF_ERR_PCT:.0f}%)")
            _ce, _cr = st.columns([3.35, 4.5])

            with _ce:
                st.markdown("**🔧 엔진 계산 과정**")
                if _lc1_ok:
                    _bal_region = ("압축지배" if _c_lc1 > _cb_est else "인장지배")
                    _d_code = "\n".join(_d_debug_lines)
                    _nc_b, _ncs_b, _nt_b = _fiber_counts_pm(_bal_pm)
                    _nc_d, _ncs_d, _nt_d = _fiber_counts_pm(_lc1_pm)
                    _csb_eps_ln = (
                        "    압축철근 ε: min={:.4f} max={:.4f}\n".format(
                            _eps_csb_min, _eps_csb_max)
                        if _cs_eps_bal else "    압축철근 ε: —\n")
                    _csb_strip_ln = (
                        "    ※ 콘크리트 파이버: "
                        "strip_concrete_overlapping_steel로 "
                        "철근 위치 슬라이스 "
                        "제거(철근/콘크리트 "
                        "이중면적 없음)\n")
                    st.code(
                        f"[LC1] Pu={_Pu_lc1:.1f}kN Mu={_Mu_lc1:.1f}kN·m e={_e_lc1:.1f}mm\n"
                        f"\n"
                        f"[d 산정 근거]\n"
                        f"{_d_code}\n"
                        f"\n"
                        f"[균형 중립축]\n"
                        f"  εcu={ecu_val:.6f}({ecu_val*1e3:.3f}‰)\n"
                        f"  εyd={_eyd:.6f}({_eyd*1e3:.4f}‰)\n"
                        f"  cb(이론, d=인장철근 centroid)={_cb_est:.1f}mm "
                        f"ε_bot(메시 극단)={eps_bal_bot:.6f}\n"
                        f"  설계항복 εyd=fyd/Es={_eyd:.6f}\n"
                        + (
                            f"  [균형 검증] 최외측 철근·강연선 y′={_fs_tens_outer.y_prime_mm:.1f}mm "
                            f"ε={_eps_tens_outer_bal:.6f} (|ε|−εyd={_abs_diff_eyd:.2e})\n"
                            if _fs_tens_outer is not None else
                            "  [균형 검증] 철근·강연선 없음\n")
                        + f"\n"
                        f"[균형점 파이버 상세]\n"
                        f"  콘크리트 {_nc_b}개: Ccb={_Ccb:.1f}kN\n"
                        f"  압축철근 {_ncs_b}개: Csb={_Csb:.1f}kN\n"
                        + _csb_eps_ln
                        + _csb_strip_ln
                        + f"  인장철근·강연선 {_nt_b}개: Tb={_Tb:.1f}kN\n"
                        + f"  [Tb 개별 파이버]\n{_tb_detail_txt}\n"
                        + f"  [Tb 검산] ΣF(인장·개별)={_tb_f_sum:.4f}kN  "
                        f"|ΣF|={abs(_tb_f_sum):.4f}kN  표시 Tb={_Tb:.4f}kN "
                        f"(인장력은 음의 부호)\n"
                        + f"  Pb=Ccb+Csb-Tb={_Ccb:.1f}+{_Csb:.1f}-{_Tb:.1f}="
                        f"{_Ccb+_Csb-_Tb:.1f}kN (P-M Pb={N_bal:.1f}kN)\n"
                        f"  Mb={_Mb_eng:.1f}kN·m\n"
                        f"\n"
                        f"[LC1 e기준] c={_c_lc1:.1f}mm → {_bal_region}({_state_lc1})\n"
                        f"\n"
                        f"[LC1 파이버 상세]\n"
                        f"  콘크리트 {_nc_d}개: Ccd={_Ccd:.1f}kN\n"
                        f"  압축철근 {_ncs_d}개: Csd={_Csd:.1f}kN\n"
                        f"  인장철근·강연선 {_nt_d}개: Td={_Td:.1f}kN\n"
                        f"  Pn=Ccd+Csd-Td={_Ccd:.1f}+{_Csd:.1f}-{_Td:.1f}="
                        f"{_Ccd+_Csd-_Td:.1f}kN (P-M 교점 Pn={_Pn_lc1:.1f}kN)\n"
                        f"  Mn={_Mn_lc1:.1f}kN·m",
                        language="")
                else:
                    st.info("하중 케이스 없음")

            with _cr:
                st.markdown(f"**\U0001f4d6 참조값 (기호 ｜ 입력 ｜ 오차율, ±{VERIFY_REF_ERR_PCT:.0f}%)**")
                _refs_2 = {}
                _ref_row("εcu",       "s_v_ecu",  "w_v_ecu",  round(ecu_val, 6), _refs_2, ecu_val,
                         warn_ctx="εcu 표 3.1-2 보간값 확인")
                _ref_row("εyd",       "s_v_ey",   "w_v_ey",   round(_eyd,   6),  _refs_2, _eyd,
                         warn_ctx="fyd=fy×Φs 확인")
                _ref_row("d [mm]",    "s_v_d",    "w_v_d",    round(_h_eff, 1),  _refs_2, _h_eff,
                         warn_ctx="피복(표면→철근중심) 및 단면치수 확인")
                _ref_row("cb [mm]",   "s_v_cb",   "w_v_cb",   round(_cb_est, 1), _refs_2, _cb_est,
                         warn_ctx="εcu/(εcu+εyd)×d 공식 확인")
                _ref_row("Ccb [kN]",  "s_v_ccb",  "w_v_ccb",  round(_Ccb, 1),    _refs_2, _Ccb,
                         warn_ctx="콘크리트 응력곡선/εcu 확인")
                _ref_row("Csb [kN]",  "s_v_csb",  "w_v_csb",  round(_Csb, 1),    _refs_2, _Csb,
                         warn_ctx="압축철근 위치/응력 확인")
                _ref_row("Tb [kN]",   "s_v_tb",   "w_v_tb",   round(_Tb,  1),    _refs_2, _Tb,
                         warn_ctx="인장철근 위치/εyd 확인")
                _ref_row("Pb [kN]",   "s_v_pb",   "w_v_pb",   round(_Pb_eng, 1), _refs_2, _Pb_eng,
                         warn_ctx="Ccb+Csb-Tb 합력 확인")
                _ref_row("Mb [kN·m]", "s_v_mb",   "w_v_mb",   round(_Mb_eng, 1), _refs_2, _Mb_eng,
                         warn_ctx="균형점 모멘트 확인")
                _ref_row("Ccd [kN]",  "s_v_ccd",  "w_v_ccd",  round(_Ccd, 1),    _refs_2, _Ccd,
                         warn_ctx="LC1 콘크리트 압축력 확인")
                _ref_row("Csd [kN]",  "s_v_csd",  "w_v_csd",  round(_Csd, 1),    _refs_2, _Csd,
                         warn_ctx="LC1 압축철근력 확인")
                _ref_row("Td [kN]",   "s_v_td",   "w_v_td",   round(_Td,  1),    _refs_2, _Td,
                         warn_ctx="LC1 인장철근력 확인")
                _ref_row("Pn [kN]",   "s_v_pn1",  "w_v_pn1",  round(_Pn_lc1, 1), _refs_2, _Pn_lc1,
                         warn_ctx="Ccd+Csd-Td 또는 편심 확인")
                _ref_row("Mn [kN·m]", "s_v_mn1",  "w_v_mn1",  round(_Mn_lc1, 1), _refs_2, _Mn_lc1,
                         warn_ctx=f"fcd={fcd_val:.2f}MPa 또는 응력분포 확인")

        # ══════════════════════════════════════════════════════════
        # 업데이트 종합 분석
        # ══════════════════════════════════════════════════════════
        if _upd:
            st.markdown("---")
            st.markdown("#### 🔍 종합 오차 분석")
            _all_refs = {
                "Pmax": (_Pn_eng,  _refs_1.get("Pn,max [kN]")),
                "Mn":   (_Mn_lc1,  _refs_2.get("Mn [kN·m]")),
                "Pn":   (_Pn_lc1,  _refs_2.get("Pn [kN]")),
            }
            _big = {k: _verr(v[0],v[1]) for k,v in _all_refs.items()
                    if _verr(v[0],v[1]) is not None
                    and abs(_verr(v[0],v[1])) >= VERIFY_REF_ERR_PCT}
            if not _big:
                _blue(f"✅ 주요 항목 오차 {VERIFY_REF_ERR_PCT:.0f}% 미만")
            else:
                _blue(f"❌ {len(_big)}개 항목 오차 ≥{VERIFY_REF_ERR_PCT:.0f}%")
                if "Pmax" in _big:
                    _blue(f"• Pmax ({_big['Pmax']:+.1f}%): fck/fy/As 재확인 — 엔진 αcc={_acc}, Φc={_gc}, Φs={_gs}")
                if "Mn" in _big or "Pn" in _big:
                    _blue(f"• LC1 강도: fcd={fcd_val:.2f}MPa (αcc={_acc}×Φc={_gc}×fck={fck}) — 참조값 αcc/Φc 확인")
                _blue("• εcu 표 3.1-2 보간값 및 응력곡선 유형(bilinear/parabolic) 확인")

st.divider()
st.caption("단면 P-M상관도 검토 v6.0  │  Fiber Section Analysis  │  "
           "KDS 24 14 21:2025 / ACI 318-19 / Eurocode 2")
