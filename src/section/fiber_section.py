"""
Fiber section assembly: concrete mesh, rebar/strand point fibers.

- from_polygon_section: arbitrary polygon + holes
- geometric_properties: centroid, inertia (theta for bending axis)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np

from ..geometry.shapes import Polygon, make_rectangle, rebar_positions_rect
from ..geometry.polygon_section import PolygonSection, GeoProps, compute_geo_props
from ..materials.base import Material
from ..materials.concrete import Concrete
from ..materials.rebar import Rebar
from ..materials.strand import Strand


# =============================================================================
# Single fiber
# =============================================================================
@dataclass
class Fiber:
    """One fiber: centroid (x,y) mm, area mm2, material, optional eps_init (strand)."""
    x: float
    y: float
    area: float
    material: Material
    eps_init: float = 0.0


def _strip_concrete_at_steel(fibers: List[Fiber], margin_mm: float = 1.0) -> List[Fiber]:
    """
    콘크리트 파이버 중 철근/강연선과 면적이 겹치는 파이버를 제거.

    [수정] 도심(centroid) 기준 판정 → 파이버 면적 기반 등가 반경 판정으로 변경.
    콘크리트 슬라이스 파이버 도심이 철근 원 밖에 있어도
    스트립 면적 일부가 겹칠 수 있으므로,
    margin을 슬라이스 높이 절반(≈ 철근 반경)만큼 추가 확보.
    """
    circles: List[Tuple[float, float, float]] = []
    for f in fibers:
        if isinstance(f.material, (Rebar, Strand)):
            # 공칭 반경: 면적에서 역산
            r_steel = math.sqrt(max(abs(f.area), 1e-6) / math.pi)
            # margin = 입력값 + 철근 반경의 절반 (슬라이스 도심 오프셋 대응)
            R_eff = r_steel + r_steel * 0.5 + margin_mm
            circles.append((f.x, f.y, R_eff))
    if not circles:
        return fibers
    kept: List[Fiber] = []
    for f in fibers:
        if isinstance(f.material, Concrete):
            cx, cy = f.x, f.y
            if any(
                (cx - x0) ** 2 + (cy - y0) ** 2 <= R ** 2
                for x0, y0, R in circles
            ):
                continue
        kept.append(f)
    return kept



# =============================================================================
# FiberSection
# =============================================================================
class FiberSection:
    """Assembled section: list of Fiber objects."""

    def __init__(self):
        self._fibers: List[Fiber] = []
        self._concrete: Optional[Concrete] = None

    def add_concrete_fibers(
        self,
        polygon: Polygon,
        material: Concrete,
        nx: int = 20,
        ny: int = 100,
        holes: Optional[List[Polygon]] = None,
    ) -> "FiberSection":
        self._concrete = material
        raw = polygon.discretize(nx=nx, ny=ny, holes=holes)
        cx, cy = polygon.centroid()
        for xc, yc, area in raw:
            self._fibers.append(
                Fiber(x=xc - cx, y=yc - cy, area=area, material=material)
            )
        return self

    def add_concrete_polygon_slices(
        self,
        poly_sec: PolygonSection,
        material: Concrete,
        ny: int,
    ) -> "FiberSection":
        """Concrete fibers from PolygonSection.mesh_slices (trapezoid/clipped strips)."""
        raw = poly_sec.mesh_slices(ny=ny)
        A = sum(a for _, _, a in raw)
        if A < 1e-18:
            self._concrete = material
            return self
        cx = sum(x * a for x, _, a in raw) / A
        cy = sum(y * a for _, y, a in raw) / A
        self._concrete = material
        for xr, yr, area in raw:
            self._fibers.append(
                Fiber(x=xr - cx, y=yr - cy, area=area, material=material)
            )
        return self

    def add_rebar(
        self,
        positions: List[Tuple[float, float]],
        material: Rebar,
        dia: float,
    ) -> "FiberSection":
        # KS 공칭단면적 테이블 (mm²)
        NOMINAL_REBAR_AREAS = {
            10: 71.3, 13: 126.7, 16: 198.6, 19: 286.5,
            22: 387.1, 25: 506.7, 29: 642.4, 32: 794.2,
            35: 956.6, 38: 1140.0, 43: 1452.0, 51: 2027.0
        }
        area = NOMINAL_REBAR_AREAS.get(int(dia), math.pi * (dia / 2) ** 2)
        for (x, y) in positions:
            self._fibers.append(Fiber(x=x, y=y, area=area, material=material))
        return self


    def add_strand(
        self,
        positions: List[Tuple[float, float]],
        material: Strand,
        dia: float,
    ) -> "FiberSection":
        area = np.pi * (dia / 2) ** 2
        for (x, y) in positions:
            self._fibers.append(
                Fiber(x=x, y=y, area=area, material=material, eps_init=material.eps_pe)
            )
        return self

    @property
    def fibers(self) -> List[Fiber]:
        return self._fibers

    def strip_concrete_overlapping_steel(self, margin_mm: float = 1.0) -> "FiberSection":
        """Remove concrete fibers overlapping rebar/strand (net Ac)."""
        self._fibers = _strip_concrete_at_steel(self._fibers, margin_mm=margin_mm)
        return self

    def normalize_concrete_to_ag_theory(self, Ag_theory: float) -> float:
        """
        Scale concrete fiber areas so gross area matches nominal Ag_theory.

        gross = Ac + As stays equal to Ag_theory; steel/strand areas unchanged.
        Returns scale factor k (1.0 if skipped).
        """
        if Ag_theory < 1e-9:
            return 1.0
        A_st = sum(
            f.area for f in self._fibers
            if isinstance(f.material, (Rebar, Strand))
        )
        conc = [f for f in self._fibers if isinstance(f.material, Concrete)]
        Ac = sum(f.area for f in conc)
        target_Ac = Ag_theory - A_st
        if Ac < 1e-12 or target_Ac <= 0.0:
            return 1.0
        k = target_Ac / Ac
        for f in conc:
            f.area *= k
        return k

    @property
    def concrete(self) -> Optional[Concrete]:
        return self._concrete

    @property
    def y_top(self) -> float:
        return max(f.y for f in self._fibers)

    @property
    def y_bot(self) -> float:
        return min(f.y for f in self._fibers)

    @property
    def height(self) -> float:
        return self.y_top - self.y_bot

    def gross_area(self) -> float:
        return sum(f.area for f in self._fibers)

    @classmethod
    def from_rectangle(
        cls,
        b: float,
        h: float,
        cover: float,
        concrete: Concrete,
        rebar: Rebar,
        n_top: int = 2,
        n_bot: int = 2,
        n_side: int = 0,
        bar_dia: float = 25.0,
        strand: Optional[Strand] = None,
        strand_positions: Optional[List[Tuple[float, float]]] = None,
        strand_dia: float = 15.2,
        nx: int = 20,
        ny: int = 100,
    ) -> "FiberSection":
        sec = cls()
        poly = make_rectangle(b, h)
        sec.add_concrete_fibers(poly, concrete, nx=nx, ny=ny)
        rb_pos = rebar_positions_rect(b, h, cover, n_top, n_bot, n_side, bar_dia)
        sec.add_rebar(rb_pos, rebar, bar_dia)
        if strand is not None and strand_positions:
            sec.add_strand(strand_positions, strand, strand_dia)
        return sec

    @classmethod
    def from_polygon_section(
        cls,
        poly_sec: PolygonSection,
        concrete: Concrete,
        rebar: Optional[Rebar] = None,
        rebar_positions: Optional[List[Tuple[float, float]]] = None,
        bar_dia: float = 25.0,
        strand: Optional[Strand] = None,
        strand_positions: Optional[List[Tuple[float, float]]] = None,
        strand_dia: float = 15.2,
        mesh_type: str = "slice",
        ny: int = 120,
        nx: int = 30,
    ) -> "FiberSection":
        sec = cls()
        sec._concrete = concrete
        raw_fibers = (
            poly_sec.mesh_slices(ny=ny)
            if mesh_type == "slice"
            else poly_sec.mesh_grid(nx=nx, ny=ny)
        )
        A = sum(a for _, _, a in raw_fibers)
        cx = sum(x * a for x, _, a in raw_fibers) / A
        cy = sum(y * a for _, y, a in raw_fibers) / A
        for (xr, yr, area) in raw_fibers:
            sec._fibers.append(
                Fiber(x=xr - cx, y=yr - cy, area=area, material=concrete)
            )
        if rebar is not None and rebar_positions:
            # KS 철근 공칭단면적 표 (mm²)
            NOMINAL_REBAR_AREAS = {
                10: 71.3, 13: 126.7, 16: 198.6, 19: 286.5,
                22: 387.1, 25: 506.7, 29: 642.4, 32: 794.2,
                35: 956.6, 38: 1140.0, 43: 1452.0, 51: 2027.0
            }
            # 공칭단면적 적용 (표에 없으면 기하학적 계산)
            area_rb = NOMINAL_REBAR_AREAS.get(
                int(bar_dia), 
                math.pi * (bar_dia / 2) ** 2
            )
            print(f"[DEBUG] bar_dia={bar_dia}, area_rb={area_rb}")  # ← 추가
            for (xr, yr) in rebar_positions:
                sec._fibers.append(
                    Fiber(x=xr - cx, y=yr - cy, area=area_rb, material=rebar)
                )
        if strand is not None and strand_positions:
            area_st = math.pi * (strand_dia / 2) ** 2
            for (xr, yr) in strand_positions:
                sec._fibers.append(
                    Fiber(
                        x=xr - cx, y=yr - cy,
                        area=area_st, material=strand, eps_init=strand.eps_pe
                    )
                )
        return sec

    def geometric_properties(self, theta: float = 0.0) -> GeoProps:
        fibers_xyz = [(f.x, f.y, f.area) for f in self._fibers]
        return compute_geo_props(fibers_xyz, theta=theta)

    def rotated_y_extremes(self, theta: float = 0.0) -> Tuple[float, float]:
        cos_t = math.cos(theta)
        sin_t = math.sin(theta)
        y_primes = [-f.x * sin_t + f.y * cos_t for f in self._fibers]
        return max(y_primes), min(y_primes)

    def summary(self) -> str:
        n_conc = sum(1 for f in self._fibers if isinstance(f.material, Concrete))
        n_rb = sum(1 for f in self._fibers if isinstance(f.material, Rebar))
        n_st = sum(1 for f in self._fibers if isinstance(f.material, Strand))
        a_rb = sum(f.area for f in self._fibers if isinstance(f.material, Rebar))
        a_st = sum(f.area for f in self._fibers if isinstance(f.material, Strand))
        return (
            f"FiberSection | concrete: {n_conc} | rebar: {n_rb} (As={a_rb:.0f} mm2) | "
            f"strand: {n_st} (Aps={a_st:.0f} mm2) | h={self.height:.0f} mm"
        )

    def __repr__(self) -> str:
        return self.summary()
