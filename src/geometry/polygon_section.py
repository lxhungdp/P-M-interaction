"""
임의 다각형 단면 정의 및 메시 생성 모듈

핵심 기능:
  1. Outer Boundary + Inner Holes 다각형 입력
  2. Auto Meshing - Slice(스캔라인) 방식 + Grid 방식
  3. 중공 영역 파이버 자동 제외
  4. 기하 특성 계산 - 도심, 단면적, 관성모멘트
  5. 모멘트 방향(theta) 기반 회전 좌표계 계산

부호 규약:
  - y 상향 양수 (단면 도심 기준)
  - theta: X축(수평)에서 반시계 방향으로 측정한 모멘트 방향 [rad]
  - 회전 변환: y' = -x·sin(θ) + y·cos(θ)
              x' =  x·cos(θ) + y·sin(θ)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np

from .shapes import Polygon


# ══════════════════════════════════════════════════════════════════════
# 기하 특성 결과 데이터 클래스
# ══════════════════════════════════════════════════════════════════════
@dataclass
class GeoProps:
    """단면 기하 특성 결과"""
    # ── 기본 특성 (도심 기준) ───────────────────────────────────────
    A: float          # 단면적 [mm²]
    cx: float         # 도심 x [mm] (입력 좌표계)
    cy: float         # 도심 y [mm] (입력 좌표계)

    Ixx: float        # 관성모멘트 Ixx (도심 x축, y² 적분) [mm⁴]
    Iyy: float        # 관성모멘트 Iyy (도심 y축, x² 적분) [mm⁴]
    Ixy: float        # 상호 관성모멘트 (도심 기준) [mm⁴]

    # ── 주 관성모멘트 ─────────────────────────────────────────────
    I1: float         # 최대 주관성모멘트 [mm⁴]
    I2: float         # 최소 주관성모멘트 [mm⁴]
    theta_p: float    # 주축 방향각 [rad] (X축 기준)

    # ── 회전 좌표계 특성 (모멘트 방향 theta 적용) ─────────────────
    theta: float = 0.0        # 모멘트 방향 [rad]
    Iy_prime: float = 0.0     # 회전 후 y' 방향 관성모멘트 I_y'y' [mm⁴]
    y_prime_top: float = 0.0  # 회전 후 최대 y' 좌표 (압축 측 극단 파이버) [mm]
    y_prime_bot: float = 0.0  # 회전 후 최소 y' 좌표 (인장 측 극단 파이버) [mm]

    @property
    def rx(self) -> float:
        """X축 회전반경 [mm]"""
        return math.sqrt(self.Ixx / self.A) if self.A > 0 else 0.0

    @property
    def ry(self) -> float:
        """Y축 회전반경 [mm]"""
        return math.sqrt(self.Iyy / self.A) if self.A > 0 else 0.0

    @property
    def r_prime(self) -> float:
        """회전 후 y' 방향 회전반경 [mm]"""
        return math.sqrt(self.Iy_prime / self.A) if self.A > 0 else 0.0

    def to_dict(self) -> dict:
        return {
            "단면적 A [mm²]":           f"{self.A:,.1f}",
            "도심 cx [mm]":              f"{self.cx:.3f}",
            "도심 cy [mm]":              f"{self.cy:.3f}",
            "Ixx [mm⁴]":                f"{self.Ixx:.4e}",
            "Iyy [mm⁴]":                f"{self.Iyy:.4e}",
            "Ixy [mm⁴]":                f"{self.Ixy:.4e}",
            "주관성모멘트 I₁ [mm⁴]":    f"{self.I1:.4e}",
            "주관성모멘트 I₂ [mm⁴]":    f"{self.I2:.4e}",
            "주축 방향각 θp [°]":        f"{math.degrees(self.theta_p):.2f}",
            "회전반경 rx [mm]":          f"{self.rx:.2f}",
            "회전반경 ry [mm]":          f"{self.ry:.2f}",
            f"I_y'y' @ θ={math.degrees(self.theta):.1f}° [mm⁴]": f"{self.Iy_prime:.4e}",
            "y'_max (압축 측) [mm]":     f"{self.y_prime_top:.2f}",
            "y'_min (인장 측) [mm]":     f"{self.y_prime_bot:.2f}",
        }


# ══════════════════════════════════════════════════════════════════════
# 스캔라인 보조 함수
# ══════════════════════════════════════════════════════════════════════
def _x_at_y(verts: np.ndarray, y: float) -> List[float]:
    """
    다각형 엣지들과 수평선 y=y의 교점 x 좌표 목록 반환
    (스캔라인 알고리즘)
    """
    xs = []
    n = len(verts)
    for i in range(n):
        j = (i + 1) % n
        x1, y1 = verts[i]
        x2, y2 = verts[j]
        if (y1 <= y < y2) or (y2 <= y < y1):
            t = (y - y1) / (y2 - y1)
            xs.append(x1 + t * (x2 - x1))
    return sorted(xs)


def _width_mx_from_segs(segs: List[Tuple[float, float]]) -> Tuple[float, float]:
    """Total chord width and first moment ∫ x·dx over chords (for x-centroid)."""
    w = 0.0
    mx = 0.0
    for x1, x2 in segs:
        if x2 - x1 < 1e-18:
            continue
        dw = x2 - x1
        w += dw
        mx += 0.5 * (x1 + x2) * dw
    return w, mx


def _subtract_segs(
    outer_segs: List[Tuple[float, float]],
    hole_segs:  List[Tuple[float, float]],
) -> List[Tuple[float, float]]:
    """
    outer_segs에서 hole_segs를 제거한 나머지 선분 목록 반환
    """
    result = list(outer_segs)
    for (c, d) in hole_segs:
        new_result = []
        for (a, b) in result:
            if d <= a or c >= b:          # 겹침 없음
                new_result.append((a, b))
            elif c <= a and d >= b:       # 완전히 덮임 → 제거
                pass
            elif c <= a:                  # 왼쪽 일부 겹침
                new_result.append((d, b))
            elif d >= b:                  # 오른쪽 일부 겹침
                new_result.append((a, c))
            else:                         # 중간에 구멍
                new_result.append((a, c))
                new_result.append((d, b))
        result = new_result
    return result


# ══════════════════════════════════════════════════════════════════════
# 핵심 클래스: 임의 다각형 단면
# ══════════════════════════════════════════════════════════════════════
class PolygonSection:
    """
    임의 다각형 단면 (Outer Boundary + Inner Holes)

    Usage:
        outer = [(0,0),(800,0),(800,1200),(0,1200)]
        hole  = [(200,200),(600,200),(600,1000),(200,1000)]
        sec = PolygonSection(outer, holes=[hole])
        props = sec.geometric_properties(theta=0.0)
        fibers = sec.mesh_slices(ny=120)
    """

    def __init__(
        self,
        outer: np.ndarray,
        holes: Optional[List[np.ndarray]] = None,
    ):
        """
        Args:
            outer : 외곽 꼭짓점 [(x1,y1), ...] — 임의 방향(CW/CCW 모두 OK)
            holes : 중공 꼭짓점 목록 [[(x1,y1),...], ...]
        """
        self.outer = Polygon(np.asarray(outer, dtype=float))
        self.holes = [Polygon(np.asarray(h, dtype=float)) for h in (holes or [])]

    # ──────────────────────────────────────────────────────────────────
    # Meshing
    # ──────────────────────────────────────────────────────────────────
    def _segments_at_y(self, y: float) -> List[Tuple[float, float]]:
        """Outer minus holes as x-intervals on horizontal line y."""
        outer_xs = _x_at_y(self.outer.vertices, y)
        if len(outer_xs) < 2:
            return []
        outer_segs = [
            (outer_xs[i], outer_xs[i + 1])
            for i in range(0, len(outer_xs) - 1, 2)
        ]
        for hole in self.holes:
            hole_xs = _x_at_y(hole.vertices, y)
            if len(hole_xs) >= 2:
                hole_segs = [
                    (hole_xs[i], hole_xs[i + 1])
                    for i in range(0, len(hole_xs) - 1, 2)
                ]
                outer_segs = _subtract_segs(outer_segs, hole_segs)
        return outer_segs

    def mesh_slice_rows(self, ny: int = 120) -> List[dict]:
        """
        Horizontal slice mesh with strip dimensions (for export / review).

        Returns:
            List of dicts: slice_no, y_bottom_mm, y_top_mm, h_mm, w_bottom_mm,
            w_top_mm, x_centroid_mm, y_centroid_mm, area_mm2
        """
        xmin, ymin, xmax, ymax = self.outer.bounding_box()
        h_tot = ymax - ymin
        if h_tot < 1e-15 or ny < 1:
            return []
        dy = h_tot / ny
        y_levels: set = {ymin + j * dy for j in range(ny + 1)}
        for poly in [self.outer] + self.holes:
            for vx, vy in poly.vertices:
                vyf = float(vy)
                if ymin < vyf < ymax:
                    y_levels.add(vyf)
        ys = sorted(y_levels)
        rows: List[dict] = []
        slice_no = 0
        for ya, yb in zip(ys[:-1], ys[1:]):
            h = yb - ya
            if h < 1e-15:
                continue
            delta = min(h * 1.0e-3, 1.0e-6)
            y_lo = ya + delta
            y_hi = yb - delta
            if y_hi <= y_lo:
                y_lo = ya + h / 3.0
                y_hi = ya + 2.0 * h / 3.0
            segs_lo = self._segments_at_y(y_lo)
            segs_hi = self._segments_at_y(y_hi)
            w0, mx0 = _width_mx_from_segs(segs_lo)
            w1, mx1 = _width_mx_from_segs(segs_hi)
            if w0 < 1e-18 and w1 < 1e-18:
                continue
            A = 0.5 * (w0 + w1) * h
            if A < 1e-18:
                continue
            denom = w0 + w1
            if denom > 1e-18:
                y_c = ya + h * (w0 + 2.0 * w1) / (3.0 * denom)
            else:
                y_c = 0.5 * (ya + yb)
            if w0 > 1e-18 and w1 > 1e-18:
                xc0 = mx0 / w0
                xc1 = mx1 / w1
                x_c = (xc0 * (2.0 * w1 + w0) + xc1 * (w0 + 2.0 * w1)) / (3.0 * denom)
            elif w0 > 1e-18:
                x_c = mx0 / w0
            else:
                x_c = mx1 / w1
            slice_no += 1
            rows.append({
                "slice_no": slice_no,
                "y_bottom_mm": ya,
                "y_top_mm": yb,
                "h_mm": h,
                "w_bottom_mm": w0,
                "w_top_mm": w1,
                "x_centroid_mm": x_c,
                "y_centroid_mm": y_c,
                "area_mm2": A,
            })
        return rows

    def mesh_slices(self, ny: int = 120) -> List[Tuple[float, float, float]]:
        """
        Horizontal slices: trapezoidal strip areas; vertex y refines boundaries.

        Returns:
            List[(x_centroid, y_centroid, area)] in input coordinates.
        """
        return [
            (r["x_centroid_mm"], r["y_centroid_mm"], r["area_mm2"])
            for r in self.mesh_slice_rows(ny)
        ]

    def mesh_grid(self, nx: int = 30, ny: int = 120) -> List[Tuple[float, float, float]]:
        """
        격자(Grid) 메싱

        중공 안에 있는 셀은 자동 제외됩니다.
        슬라이스 방식보다 느리지만, 복잡한 형상에 유리합니다.

        Returns:
            List[(x_centroid, y_centroid, area)]
        """
        return self.outer.discretize(nx=nx, ny=ny, holes=self.holes)

    # ──────────────────────────────────────────────────────────────────
    # 기하 특성 계산 (슬라이스 기반, Iyy 자기모멘트 보정 포함)
    # ──────────────────────────────────────────────────────────────────
    def geometric_properties(
        self,
        theta: float = 0.0,
        fibers: Optional[List[Tuple[float, float, float]]] = None,
        ny: int = 120,
    ) -> GeoProps:
        """
        단면 기하 특성 계산 (회전 포함)

        Args:
            theta  : 모멘트 방향 각도 [rad] (X축 기준, 반시계 양수)
                     이 방향으로 단면을 회전시켜 압축·인장 극단 파이버를 결정합니다.
            fibers : 외부에서 주입할 파이버 목록 (None이면 내부에서 슬라이스 메싱)
                     ※ 외부 주입 시 Iyy 자기모멘트 항이 포함되지 않습니다.
                       (각 파이버가 점 질량으로 취급)
            ny     : 슬라이스 수 (fibers=None 일 때 사용)

        Returns:
            GeoProps 객체

        Notes:
            슬라이스 메싱의 경우:
              - Ixx (y² 적분): 슬라이스 폭이 넓어도 y 도심으로 정확.
              - Iyy (x² 적분): 각 슬라이스의 자기모멘트  w³·dy/12  가 필요.
                → 슬라이스 폭 w 정보를 내부에서 직접 보유하여 보정합니다.
        """
        if fibers is not None:
            # ── 외부 파이버 사용 (점 질량 근사, Iyy 근사치) ──────
            return self._geo_from_point_fibers(fibers, theta)

        # ── 슬라이스 직접 계산 (Iyy 자기모멘트 보정 포함) ────────
        return self._geo_from_slices(theta=theta, ny=ny)

    def _geo_from_slices(self, theta: float = 0.0, ny: int = 120) -> GeoProps:
        """Trapezoid mesh (mesh_slices) + GeoProps via point-fiber integration."""
        fibers = self.mesh_slices(ny=ny)
        A = sum(a for _, _, a in fibers)
        if A < 1e-9:
            raise ValueError("단면적이 0입니다. 좌표를 확인하세요.")
        return compute_geo_props(fibers, theta=theta)

    def _geo_from_point_fibers(
        self,
        fibers: List[Tuple[float, float, float]],
        theta: float,
    ) -> GeoProps:
        """점 파이버 목록에서 기하 특성 계산 (Iyy 자기모멘트 무시)."""
        A  = sum(a for _, _, a in fibers)
        cx = sum(x * a for x, _, a in fibers) / A
        cy = sum(y * a for _, y, a in fibers) / A
        Ixx = sum(a * (y - cy) ** 2 for _, y, a in fibers)
        Iyy = sum(a * (x - cx) ** 2 for x, _, a in fibers)
        Ixy = sum(a * (x - cx) * (y - cy) for x, y, a in fibers)
        return self._finalize_geo(A, cx, cy, Ixx, Iyy, Ixy, theta, fibers)

    @staticmethod
    def _finalize_geo(
        A: float, cx: float, cy: float,
        Ixx: float, Iyy: float, Ixy: float,
        theta: float,
        fibers: List[Tuple[float, float, float]],
    ) -> GeoProps:
        """주관성모멘트·회전 특성을 계산하여 GeoProps를 반환합니다."""
        # ── 주관성모멘트 (Mohr's circle) ─────────────────────────
        avg     = 0.5 * (Ixx + Iyy)
        diff    = 0.5 * (Ixx - Iyy)
        R       = math.sqrt(diff ** 2 + Ixy ** 2)
        I1      = avg + R
        I2      = avg - R
        theta_p = 0.5 * math.atan2(-2.0 * Ixy, Ixx - Iyy)

        # ── 회전 좌표계 특성 ─────────────────────────────────────
        # 회전 변환: y'_i = -(x_i-cx)·sin(θ) + (y_i-cy)·cos(θ)
        cos_t = math.cos(theta)
        sin_t = math.sin(theta)

        y_primes = [
            -(x - cx) * sin_t + (y - cy) * cos_t
            for x, y, _ in fibers
        ]
        y_prime_top = max(y_primes)
        y_prime_bot = min(y_primes)

        # Iy'y' = Iyy·sin²θ + Ixx·cos²θ - Ixy·sin(2θ)
        # (모멘트 변환 공식 - Ixx, Iyy가 정확해야 정확)
        Iy_prime = (
            Iyy * sin_t ** 2
            + Ixx * cos_t ** 2
            - Ixy * math.sin(2.0 * theta)
        )

        return GeoProps(
            A=A, cx=cx, cy=cy,
            Ixx=Ixx, Iyy=Iyy, Ixy=Ixy,
            I1=I1, I2=I2, theta_p=theta_p,
            theta=theta,
            Iy_prime=Iy_prime,
            y_prime_top=y_prime_top,
            y_prime_bot=y_prime_bot,
        )

    # ──────────────────────────────────────────────────────────────────
    # 편의 메서드
    # ──────────────────────────────────────────────────────────────────
    def centroid(self, ny: int = 80) -> Tuple[float, float]:
        """단면 도심 (cx, cy) — 입력 좌표계 기준"""
        props = self.geometric_properties(ny=ny)
        return props.cx, props.cy

    def area(self, ny: int = 80) -> float:
        """단면적 [mm²]"""
        return sum(a for _, _, a in self.mesh_slices(ny=ny))

    def bounding_box(self) -> Tuple[float, float, float, float]:
        """외곽 경계 상자 (xmin, ymin, xmax, ymax)"""
        return self.outer.bounding_box()

    def __repr__(self) -> str:
        n_holes = len(self.holes)
        bb = self.bounding_box()
        return (
            f"PolygonSection("
            f"outer={len(self.outer.vertices)}pts, "
            f"holes={n_holes}, "
            f"bbox=[{bb[0]:.0f},{bb[1]:.0f}]~[{bb[2]:.0f},{bb[3]:.0f}])"
        )


# ══════════════════════════════════════════════════════════════════════
# 단면 기하 특성 직접 계산 (FiberSection 용 범용 함수)
# ══════════════════════════════════════════════════════════════════════
def compute_geo_props(
    fibers_xy_area: List[Tuple[float, float, float]],
    theta: float = 0.0,
) -> GeoProps:
    """
    파이버 목록 [(x, y, area), ...] 에서 기하 특성을 계산합니다.

    FiberSection의 철근/강연선 파이버도 포함시킬 수 있습니다.
    각 파이버는 점 질량으로 취급합니다(Iyy 자기모멘트 무시).
    격자(Grid) 방식처럼 파이버 폭이 충분히 좁을 때 오차가 작습니다.

    Args:
        fibers_xy_area: 파이버 (x, y, area) 목록 — 임의 좌표계
        theta         : 모멘트 방향 [rad]

    Returns:
        GeoProps
    """
    A  = sum(a for _, _, a in fibers_xy_area)
    cx = sum(x * a for x, _, a in fibers_xy_area) / A
    cy = sum(y * a for _, y, a in fibers_xy_area) / A
    Ixx = sum(a * (y - cy) ** 2 for _, y, a in fibers_xy_area)
    Iyy = sum(a * (x - cx) ** 2 for x, _, a in fibers_xy_area)
    Ixy = sum(a * (x - cx) * (y - cy) for x, y, a in fibers_xy_area)
    return PolygonSection._finalize_geo(A, cx, cy, Ixx, Iyy, Ixy, theta, fibers_xy_area)
