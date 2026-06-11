"""Domain helpers: rebar layout and fiber section assembly."""

from __future__ import annotations

import math
from itertools import groupby
from typing import List, Optional, Tuple

import numpy as np

from src.geometry.polygon_section import PolygonSection
from src.geometry.shapes import make_circle, make_rectangle
from src.materials.concrete import Concrete
from src.materials.rebar import Rebar
from src.materials.strand import Strand
from src.section.fiber_section import FiberSection


def compute_rebar_positions(
    b,
    h,
    n_top,
    dia_top,
    cov_top,
    n_bot,
    dia_bot,
    cov_bot,
    n_left,
    dia_left,
    cov_left,
    n_right,
    dia_right,
    cov_right,
):
    """Rectangular section rebar (x, y, dia) list; cover = surface to bar center."""
    yt = h / 2 - cov_top
    yb = -h / 2 + cov_bot
    pos = []
    if n_top > 0:
        xl = -b / 2 + cov_top
        xr = b / 2 - cov_top
        for x in np.linspace(xl, xr, n_top):
            pos.append((float(x), yt, float(dia_top)))
    if n_bot > 0:
        xl = -b / 2 + cov_bot
        xr = b / 2 - cov_bot
        for x in np.linspace(xl, xr, n_bot):
            pos.append((float(x), yb, float(dia_bot)))
    if n_left > 0:
        xl = -b / 2 + cov_left
        for y in np.linspace(yb, yt, n_left + 2)[1:-1]:
            pos.append((xl, float(y), float(dia_left)))
    if n_right > 0:
        xr = b / 2 - cov_right
        for y in np.linspace(yb, yt, n_right + 2)[1:-1]:
            pos.append((xr, float(y), float(dia_right)))
    return pos


def ag_theory_mm2(sec_type, b, h, poly_outer, poly_holes) -> float:
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
            [np.asarray(ho, dtype=float) for ho in holes],
        )
        a = float(ps.outer.area())
        for ho in ps.holes:
            a -= float(ho.area())
        return max(a, 0.0)
    return float(b * h)


def h_eff_and_cb_theory(
    section: FiberSection,
    theta_rad: float,
    ecu_val: float,
    fyd_val: float,
    sec_type: str,
    b: float,
    h: float,
) -> tuple[float, float]:
    """Effective d and theoretical balanced cb [mm]."""
    _eyd = fyd_val / 200000.0
    if sec_type == "직사각형" and abs(theta_rad) < 1e-9:
        y_prime_top_ref = float(h) / 2.0
        y_prime_bot_ref = -float(h) / 2.0
    else:
        y_prime_top_ref, y_prime_bot_ref = section.rotated_y_extremes(theta_rad)

    rb_yp_list = []
    for f in section.fibers:
        if isinstance(f.material, Rebar):
            yp = -f.x * math.sin(theta_rad) + f.y * math.cos(theta_rad)
            rb_yp_list.append((yp, f.area))

    if rb_yp_list:
        rb_yp_sorted = sorted(rb_yp_list, key=lambda x: x[0])
        min_yp_rb = rb_yp_sorted[0][0]
        dia_ref = 2 * math.sqrt(max(a for _, a in rb_yp_list) / math.pi)
        tol_d = max(dia_ref * 1.5, 30.0)
        tens_rb = [(yp, a) for yp, a in rb_yp_list if yp <= min_yp_rb + tol_d]
        at_tot = sum(a for _, a in tens_rb)
        yp_tens = sum(yp * a for yp, a in tens_rb) / at_tot if at_tot > 0 else min_yp_rb
        h_eff = y_prime_top_ref - yp_tens
    else:
        h_eff = y_prime_top_ref - y_prime_bot_ref

    cb_est = ecu_val / (ecu_val + _eyd) * h_eff
    return h_eff, cb_est


def polygon_section_for_inputs(
    sec_type: str,
    b: float,
    h: float,
    poly_outer: Optional[list],
    poly_holes: list,
) -> Optional[PolygonSection]:
    """Outer polygon for mesh slice export (input coordinates, centroid at origin later)."""
    if sec_type == "직사각형":
        return PolygonSection(make_rectangle(b, h).vertices, [])
    if sec_type == "원형":
        return PolygonSection(make_circle(radius=b / 2, n_seg=256).vertices, [])
    if sec_type == "임의 다각형" and poly_outer and len(poly_outer) >= 3:
        holes = [np.asarray(ho, dtype=float) for ho in (poly_holes or [])]
        return PolygonSection(np.asarray(poly_outer, dtype=float), holes)
    return None


def build_section(
    b,
    h,
    cover,
    fck,
    fcd,
    fy,
    fyd,
    rb_list,
    bar_dia,
    n_top,
    n_bot,
    n_left,
    n_right,
    curve_conc,
    use_strand,
    strand_params,
    ny,
    sec_type,
    poly_outer=None,
    poly_holes=None,
    poly_rb_pos=None,
):
    """Assemble FiberSection: concrete mesh + rebar + optional strand."""
    conc = Concrete(fck=fck, fcd=fcd, curve_type=curve_conc)
    rb = Rebar(fy=fy, fyd=fyd)
    st_obj = st_pos = None
    st_dia = 15.2
    if use_strand and strand_params:
        p = strand_params
        st_obj = Strand(
            fpk=p["fpk"],
            fp01k=p["fp01k"],
            Ep=p["Ep"],
            fpd=p["fpd"],
            eps_pe=p["eps_pe"],
        )
        st_pos = p["positions"]
        st_dia = p["dia"]

    if sec_type == "임의 다각형" and poly_outer:
        ps = PolygonSection(poly_outer, poly_holes or [])
        sec = FiberSection.from_polygon_section(
            ps,
            conc,
            rebar=rb if poly_rb_pos else None,
            rebar_positions=poly_rb_pos or [],
            bar_dia=bar_dia,
            strand=st_obj,
            strand_positions=st_pos,
            strand_dia=st_dia,
            mesh_type="slice",
            ny=ny,
        )
        ag_poly = ag_theory_mm2(sec_type, b, h, poly_outer, poly_holes)
        sec.normalize_concrete_to_ag_theory(ag_poly)
        return sec, conc, rb

    if sec_type == "원형":
        sec = FiberSection()
        poly = make_circle(radius=b / 2, n_seg=256)
        circle_ps = PolygonSection(poly.vertices, [])
        sec.add_concrete_polygon_slices(circle_ps, conc, ny)
        n_rb = n_top + n_bot + n_left + n_right
        if n_rb > 0:
            r_rb = b / 2 - cover
            ang = np.linspace(0, 2 * math.pi, n_rb, endpoint=False)
            sec.add_rebar([(r_rb * math.cos(a), r_rb * math.sin(a)) for a in ang], rb, bar_dia)
        if st_obj and st_pos:
            sec.add_strand(st_pos, st_obj, st_dia)
        sec.normalize_concrete_to_ag_theory(math.pi * (b / 2) ** 2)
        return sec, conc, rb

    sec = FiberSection()
    rect_ps = PolygonSection(make_rectangle(b, h).vertices, [])
    sec.add_concrete_polygon_slices(rect_ps, conc, ny)
    if rb_list:
        sorted_rb = sorted(rb_list, key=lambda t: t[2])
        for dia, items in groupby(sorted_rb, key=lambda t: t[2]):
            positions = [(x, y) for x, y, _ in items]
            sec.add_rebar(positions, rb, dia)
    if st_obj and st_pos:
        sec.add_strand(st_pos, st_obj, st_dia)
    sec.normalize_concrete_to_ag_theory(b * h)
    return sec, conc, rb
