"""P-M analysis pipeline (mesh tune → diagram → solver → cache)."""

from __future__ import annotations

import math
from typing import Any, Dict, Optional

import numpy as np

from src.analysis.engine import (
    PM_DIAGRAM_ETU,
    compute_pm_diagram,
    diagram_closest_strain_to_nm,
    diagram_max_positive_moment_strain,
)
from src.analysis.solver import (
    compute_pm_solver,
    eps_bot_for_tension_yield_at_depth,
    pm_result_at_strains,
)
from src.codes import CODES
from src.materials.rebar import Rebar
from src.materials.strand import Strand

from pm_app.config import MESH_AG_TOL, MESH_CB_TOL, MESH_MAX_ITER, MESH_NY_CAP
from pm_app.models import AnalysisInputs
from pm_app.pm_checks import half_pm_curve, p0_point, ray_intersect_pm_curve
from pm_app.section_builder import ag_theory_mm2, build_section, h_eff_and_cb_theory


def run_pm_analysis(inputs: AnalysisInputs) -> Dict[str, Any]:
    """Run full fiber P-M analysis; returns pm_cache dict for session_state."""
    code = CODES[inputs.code_name]()
    fcd_val = code.fcd(inputs.fck)
    ecu_val = code.epsilon_cu(inputs.fck)
    Ec_val = code.elastic_modulus_concrete(inputs.fck)
    fyd_val = code.fyd(inputs.fy)

    strand_params = None
    if inputs.use_strand and inputs.strand_pos:
        strand_params = dict(
            fpk=inputs.fpk_val,
            fp01k=inputs.fp01k_val,
            Ep=inputs.Ep_val,
            fpd=code.fpd(inputs.fp01k_val),
            eps_pe=inputs.eps_pe_val,
            positions=inputs.strand_pos,
            dia=inputs.strand_dia_val,
        )

    ag_theory_run = ag_theory_mm2(
        inputs.sec_type, inputs.b, inputs.h, inputs.poly_outer, inputs.poly_holes
    )
    ny_try = max(50, int(inputs.ny_fiber))
    ny_used = ny_try
    mesh_warn: Optional[str] = None
    section = None
    section_nom = None
    ag_mesh_normalized = False

    for _ in range(MESH_MAX_ITER):
        ny_cur = min(int(ny_try), MESH_NY_CAP)
        section, _, _ = build_section(
            inputs.b,
            inputs.h,
            inputs.cover,
            inputs.fck,
            fcd_val,
            inputs.fy,
            fyd_val,
            inputs.rb_list,
            inputs.bar_dia,
            inputs.n_top,
            inputs.n_bot,
            inputs.n_left,
            inputs.n_right,
            inputs.curve_conc,
            inputs.use_strand,
            strand_params,
            ny_cur,
            inputs.sec_type,
            inputs.poly_outer,
            inputs.poly_holes,
            inputs.poly_rebar_positions if inputs.sec_type == "임의 다각형" else None,
        )
        section_nom, _, _ = build_section(
            inputs.b,
            inputs.h,
            inputs.cover,
            inputs.fck,
            inputs.fck,
            inputs.fy,
            inputs.fy,
            inputs.rb_list,
            inputs.bar_dia,
            inputs.n_top,
            inputs.n_bot,
            inputs.n_left,
            inputs.n_right,
            inputs.curve_conc,
            False,
            None,
            ny_cur,
            inputs.sec_type,
            inputs.poly_outer,
            inputs.poly_holes,
            inputs.poly_rebar_positions if inputs.sec_type == "임의 다각형" else None,
        )
        ag_m = section.gross_area()
        ag_err_r = abs(ag_m - ag_theory_run) / ag_theory_run if ag_theory_run > 1e-9 else 0.0
        _, cb_t = h_eff_and_cb_theory(
            section,
            inputs.theta_rad,
            ecu_val,
            fyd_val,
            inputs.sec_type,
            inputs.b,
            inputs.h,
        )
        eps_bb, _, _ = diagram_max_positive_moment_strain(
            section, ecu_val, inputs.n_pts, inputs.theta_rad, phi=1.0
        )
        bpm = pm_result_at_strains(section, ecu_val, eps_bb, inputs.theta_rad, phi=1.0)
        ytr2, ybr2 = section.rotated_y_extremes(inputs.theta_rad)
        c_bal_try = float(bpm.c_mm) if bpm.c_mm < 1e8 else max(ytr2 - ybr2, 1.0) * 0.5
        cb_err_r = abs(c_bal_try - cb_t) / cb_t if cb_t > 1e-6 else 0.0
        ny_used = ny_cur
        if ag_err_r <= MESH_AG_TOL and cb_err_r <= MESH_CB_TOL:
            break
        if ny_cur >= MESH_NY_CAP:
            mesh_warn = (
                f"ny={MESH_NY_CAP} max: Ag rel.err.>{MESH_AG_TOL * 100:.4f}% or "
                f"cb rel.err.>{MESH_CB_TOL * 100:.4f}% "
                f"(Ag {ag_err_r * 100:.5f}%, cb {cb_err_r * 100:.5f}%)."
            )
            break
        ny_try = ny_cur + max(10, ny_cur // 8)
    else:
        mesh_warn = "Mesh auto-tune iteration limit; increase ny in solver settings."

    if ag_theory_run > 1e-9:
        ag_err_fin = abs(section.gross_area() - ag_theory_run) / ag_theory_run
        if ag_err_fin > MESH_AG_TOL:
            section.normalize_concrete_to_ag_theory(float(ag_theory_run))
            section_nom.normalize_concrete_to_ag_theory(float(ag_theory_run))
            ag_mesh_normalized = True

    geo = section.geometric_properties(theta=inputs.theta_rad)
    pm_des = compute_pm_diagram(
        section, ecu=ecu_val, n_pts=inputs.n_pts, theta=inputs.theta_rad
    )
    pm_nom = compute_pm_diagram(
        section_nom, ecu=ecu_val, n_pts=inputs.n_pts, theta=inputs.theta_rad
    )
    solver_out = compute_pm_solver(
        section,
        ecu=ecu_val,
        etu=PM_DIAGRAM_ETU,
        n_pts=inputs.n_pts,
        theta=inputs.theta_rad,
        store_fiber_states=True,
    )

    N_des, M_des = half_pm_curve(pm_des)
    N_nom, M_nom = half_pm_curve(pm_nom)
    N_max_v = float(N_des.max())
    M_p0, N_p0 = p0_point(N_des, M_des)
    pos_res = [r for r in solver_out.pm_results if r.M_kNm >= -1e-3]

    _, cb_theory_bal = h_eff_and_cb_theory(
        section, inputs.theta_rad, ecu_val, fyd_val, inputs.sec_type, inputs.b, inputs.h
    )
    ytr, ybr = section.rotated_y_extremes(inputs.theta_rad)
    ct_b, st_b = math.cos(inputs.theta_rad), math.sin(inputs.theta_rad)
    y_steel_primes = [
        -f.x * st_b + f.y * ct_b
        for f in section.fibers
        if isinstance(f.material, (Rebar, Strand))
    ]
    y_tens_out = min(y_steel_primes) if y_steel_primes else ybr
    eyd_bal = fyd_val / 200000.0
    eps_bal_bot = eps_bot_for_tension_yield_at_depth(ecu_val, ytr, ybr, y_tens_out, eyd_bal)
    eps_bal_bot = float(max(min(eps_bal_bot, ecu_val * (1.0 - 1e-12)), -PM_DIAGRAM_ETU))
    bal_pm = pm_result_at_strains(
        section, ecu_val, eps_bal_bot, inputs.theta_rad, phi=1.0
    )
    N_bal = float(bal_pm.N_kN)
    M_bal = float(bal_pm.M_kNm)
    c_bal_mm = float(bal_pm.c_mm) if bal_pm.c_mm < 1e8 else float(cb_theory_bal)
    eps_bal_top = float(bal_pm.eps_top)
    eps_bal_bot = float(bal_pm.eps_bot)

    try:
        load_cases = inputs.df_loads.dropna(
            subset=["Pu [kN]", "Mx [kN·m]", "My [kN·m]"]
        ).to_dict("records")
    except Exception:
        load_cases = []

    lc1_Pn_cap = lc1_Mn_cap = lc1_eps_bot = None
    if load_cases:
        lc0 = load_cases[0]
        Pu0 = float(lc0.get("Pu [kN]", 0))
        Mx0 = float(lc0.get("Mx [kN·m]", 0))
        My0 = float(lc0.get("My [kN·m]", 0))
        Mu0 = math.sqrt(Mx0**2 + My0**2)
        N0 = np.asarray(N_des, float)
        M0 = np.asarray(M_des, float)
        Mr, Pr = ray_intersect_pm_curve(Mu0, Pu0, M0, N0)
        if Mr is not None and abs(Pu0) > 1e-6:
            lc1_Pn_cap = float(Pr)
            lc1_Mn_cap = float(Mr)
            lc1_eps_bot, _, _ = diagram_closest_strain_to_nm(
                section, ecu_val, inputs.n_pts, inputs.theta_rad, 1.0,
                lc1_Pn_cap, lc1_Mn_cap,
            )
        elif abs(Pu0) > 1:
            e_arr0 = np.where(N0 > 10, M0 / (N0 + 1e-9), 1e12)
            ix0 = int(np.argmin(np.abs(e_arr0 - Mu0 / (Pu0 + 1e-9))))
            lc1_Pn_cap = float(N0[ix0])
            lc1_Mn_cap = float(M0[ix0])
            lc1_eps_bot, _, _ = diagram_closest_strain_to_nm(
                section, ecu_val, inputs.n_pts, inputs.theta_rad, 1.0,
                lc1_Pn_cap, lc1_Mn_cap,
            )
        else:
            lc1_Pn_cap = 0.0
            lc1_Mn_cap = float(M0[int(np.argmax(M0))])
            lc1_eps_bot, _, _ = diagram_closest_strain_to_nm(
                section, ecu_val, inputs.n_pts, inputs.theta_rad, 1.0,
                lc1_Pn_cap, lc1_Mn_cap,
            )

    return {
        "N_des": N_des.tolist(),
        "M_des": M_des.tolist(),
        "N_nom": N_nom.tolist(),
        "M_nom": M_nom.tolist(),
        "N_max_v": N_max_v,
        "N_bal": N_bal,
        "M_bal": M_bal,
        "M_p0": M_p0,
        "N_p0": N_p0,
        "n_pts": int(inputs.n_pts),
        "lc1_Pn_cap": lc1_Pn_cap,
        "lc1_Mn_cap": lc1_Mn_cap,
        "lc1_eps_bot": lc1_eps_bot,
        "c_bal_mm": c_bal_mm,
        "eps_bal_top": eps_bal_top,
        "eps_bal_bot": eps_bal_bot,
        "section": section,
        "geo": geo,
        "solver_out": solver_out,
        "pos_res": pos_res,
        "load_cases": load_cases,
        "theta_rad": inputs.theta_rad,
        "theta_deg_auto": inputs.theta_deg_auto,
        "sec_type": inputs.sec_type,
        "b": inputs.b,
        "h": inputs.h,
        "poly_outer": inputs.poly_outer,
        "poly_holes": inputs.poly_holes,
        "strand_dia_val": inputs.strand_dia_val,
        "use_strand": inputs.use_strand,
        "bar_dia": inputs.bar_dia,
        "n_top": inputs.n_top,
        "n_bot": inputs.n_bot,
        "n_left": inputs.n_left,
        "n_right": inputs.n_right,
        "fck": inputs.fck,
        "fy": inputs.fy,
        "fcd_val": fcd_val,
        "fyd_val": fyd_val,
        "ecu_val": ecu_val,
        "Ec_val": Ec_val,
        "code_name": inputs.code_name,
        "sym_check": inputs.sym_check,
        "ny_fiber_req": int(inputs.ny_fiber),
        "ny_fiber_used": int(ny_used),
        "mesh_warn": mesh_warn,
        "Ag_theory": float(ag_theory_run),
        "Ag_mesh_normalized": ag_mesh_normalized,
    }
