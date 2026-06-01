"""Shared context dataclasses for output / verification tabs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional

import numpy as np

from pm_app.models import AnalysisInputs
from pm_app.section_builder import ag_theory_mm2


@dataclass
class VerifyContext:
    """Inputs required by the verification tab (tab 6)."""

    code_name: str
    section: Any
    geo: Any
    b: float
    h: float
    sec_type: str
    theta_rad: float
    fck: float
    fy: float
    fcd_val: float
    fyd_val: float
    ecu_val: float
    N_max_v: float
    N_bal: float
    M_bal: float
    eps_bal_top: float
    eps_bal_bot: float
    load_cases: list
    lc1_Pn_cap: Optional[float]
    lc1_Mn_cap: Optional[float]
    lc1_eps_bot: Optional[float]
    N_des: np.ndarray
    M_des: np.ndarray
    n_pts: int
    n_top: int
    n_bot: int
    n_left: int
    n_right: int
    Ag_theory_cached: float


@dataclass
class OutputContext:
    """Unpacked pm_cache + display fields for result tabs."""

    N_des: np.ndarray
    M_des: np.ndarray
    N_nom: np.ndarray
    M_nom: np.ndarray
    N_max_v: float
    N_bal: float
    M_bal: float
    M_p0: float
    N_p0: float
    n_pts: int
    c_bal_mm: float
    eps_bal_top: float
    eps_bal_bot: float
    lc1_Pn_cap: Optional[float]
    lc1_Mn_cap: Optional[float]
    lc1_eps_bot: Optional[float]
    section: Any
    geo: Any
    solver_out: Any
    pos_res: Any
    load_cases: list
    theta_rad: float
    theta_deg_auto: float
    sec_type: str
    b: float
    h: float
    poly_outer: Optional[list]
    poly_holes: list
    strand_dia_val: float
    use_strand: bool
    bar_dia: float
    n_top: int
    n_bot: int
    n_left: int
    n_right: int
    code_name: str
    fck: float
    fy: float
    fcd_val: float
    fyd_val: float
    ecu_val: float
    Ec_val: float
    ny_fiber_used: int
    ny_fiber_req: Optional[int]
    Ag_theory_cached: float
    sym_check: bool

    @classmethod
    def from_cache(cls, cache: dict, inputs: AnalysisInputs) -> OutputContext:
        sec_type = cache["sec_type"]
        b, h = cache["b"], cache["h"]
        poly_outer = cache["poly_outer"]
        poly_holes = cache["poly_holes"]
        ag = float(
            cache.get(
                "Ag_theory",
                ag_theory_mm2(sec_type, b, h, poly_outer, poly_holes),
            )
        )
        return cls(
            N_des=np.array(cache["N_des"]),
            M_des=np.array(cache["M_des"]),
            N_nom=np.array(cache["N_nom"]),
            M_nom=np.array(cache["M_nom"]),
            N_max_v=cache["N_max_v"],
            N_bal=cache["N_bal"],
            M_bal=cache["M_bal"],
            M_p0=cache["M_p0"],
            N_p0=cache["N_p0"],
            n_pts=int(cache.get("n_pts", 200)),
            c_bal_mm=cache["c_bal_mm"],
            eps_bal_top=cache["eps_bal_top"],
            eps_bal_bot=cache["eps_bal_bot"],
            lc1_Pn_cap=cache.get("lc1_Pn_cap"),
            lc1_Mn_cap=cache.get("lc1_Mn_cap"),
            lc1_eps_bot=cache.get("lc1_eps_bot"),
            section=cache["section"],
            geo=cache["geo"],
            solver_out=cache["solver_out"],
            pos_res=cache["pos_res"],
            load_cases=cache["load_cases"],
            theta_rad=cache["theta_rad"],
            theta_deg_auto=cache["theta_deg_auto"],
            sec_type=sec_type,
            b=b,
            h=h,
            poly_outer=poly_outer,
            poly_holes=poly_holes,
            strand_dia_val=cache["strand_dia_val"],
            use_strand=cache["use_strand"],
            bar_dia=cache["bar_dia"],
            n_top=cache["n_top"],
            n_bot=cache["n_bot"],
            n_left=cache["n_left"],
            n_right=cache["n_right"],
            code_name=cache.get("code_name", inputs.code_name),
            fck=cache["fck"],
            fy=cache["fy"],
            fcd_val=cache["fcd_val"],
            fyd_val=cache["fyd_val"],
            ecu_val=cache["ecu_val"],
            Ec_val=cache["Ec_val"],
            ny_fiber_used=int(cache.get("ny_fiber_used", 120)),
            ny_fiber_req=cache.get("ny_fiber_req"),
            Ag_theory_cached=ag,
            sym_check=cache.get("sym_check", inputs.sym_check),
        )

    def to_verify(self) -> VerifyContext:
        return VerifyContext(
            code_name=self.code_name,
            section=self.section,
            geo=self.geo,
            b=self.b,
            h=self.h,
            sec_type=self.sec_type,
            theta_rad=self.theta_rad,
            fck=self.fck,
            fy=self.fy,
            fcd_val=self.fcd_val,
            fyd_val=self.fyd_val,
            ecu_val=self.ecu_val,
            N_max_v=self.N_max_v,
            N_bal=self.N_bal,
            M_bal=self.M_bal,
            eps_bal_top=self.eps_bal_top,
            eps_bal_bot=self.eps_bal_bot,
            load_cases=self.load_cases,
            lc1_Pn_cap=self.lc1_Pn_cap,
            lc1_Mn_cap=self.lc1_Mn_cap,
            lc1_eps_bot=self.lc1_eps_bot,
            N_des=self.N_des,
            M_des=self.M_des,
            n_pts=self.n_pts,
            n_top=self.n_top,
            n_bot=self.n_bot,
            n_left=self.n_left,
            n_right=self.n_right,
            Ag_theory_cached=self.Ag_theory_cached,
        )
