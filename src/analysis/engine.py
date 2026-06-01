"""
파이버 단면 해석 엔진 (Fiber Section Analysis Engine)  v2

핵심 알고리즘:
  1. 평면유지 가정(Bernoulli): ε(y') = ε₀ + κ·y'
  2. 회전 변환: y'_i = -x_i·sin(θ) + y_i·cos(θ)
     → 모멘트 방향 θ로 회전한 좌표계에서 중립축 결정
  3. 각 파이버 응력: σ = material.stress(ε_fiber + ε_initial)
  4. N = Σ σᵢ·Aᵢ,   M = Σ σᵢ·Aᵢ·y'ᵢ

부호 규약:
  - y(원래), y'(회전): 도심 기준 상향 양수
  - 변형률: 압축 = +, 인장 = -
  - N: 압축 = +  [kN]
  - M: y' 방향 압축 유발 모멘트 = +  [kN·m]
  - theta [rad]: X축에서 반시계 방향 (0° = 수평 모멘트, 90° = 수직 모멘트)
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np

from ..section.fiber_section import Fiber, FiberSection

PM_DIAGRAM_ETU = 0.015


# ══════════════════════════════════════════════════════════════════════
# 결과 데이터 클래스
# ══════════════════════════════════════════════════════════════════════
@dataclass
class SectionResponse:
    """단일 변형률 상태에 대한 단면 응답"""
    N_kN: float
    M_kNm: float
    eps_top: float
    eps_bot: float
    neutral_axis: float   # 압축 측 극단에서 중립축까지 거리 [mm]
    theta: float = 0.0    # 모멘트 방향 [rad]


@dataclass
class PMPoint:
    """P-M 상관도 상의 한 점"""
    N_kN: float
    M_kNm: float
    label: str = ""


# ══════════════════════════════════════════════════════════════════════
# 핵심 적분 함수 (회전 포함)
# ══════════════════════════════════════════════════════════════════════
def _integrate(
    fibers: List[Fiber],
    eps_top: float,
    eps_bot: float,
    y_top_r: float,
    y_bot_r: float,
    cos_t: float = 1.0,
    sin_t: float = 0.0,
) -> Tuple[float, float]:
    """
    회전된 좌표계에서 N, M을 수치 적분합니다.

    변형률 보간 (회전 y' 기준):
        κ   = (eps_top - eps_bot) / (y_top_r - y_bot_r)
        ε₀  = eps_top - κ · y_top_r
        ε(fiber) = ε₀ + κ · y'_fiber
        y'_i = -x_i·sin(θ) + y_i·cos(θ)

    Args:
        y_top_r, y_bot_r : 회전 좌표계에서의 극단 y' 값
        cos_t, sin_t     : cos(theta), sin(theta)

    Returns:
        (N [N], M [N·mm])  — M은 회전 축에 대한 모멘트 (스칼라)
    """
    dy_r = y_top_r - y_bot_r
    if abs(dy_r) < 1e-12:
        kappa = 0.0
        eps0  = eps_top
    else:
        kappa = (eps_top - eps_bot) / dy_r
        eps0  = eps_top - kappa * y_top_r

    N = 0.0
    M = 0.0
    for f in fibers:
        y_r      = -f.x * sin_t + f.y * cos_t   # 회전된 y' 좌표
        eps_geom = eps0 + kappa * y_r
        sigma    = f.material.stress(eps_geom)    # Strand: 내부에서 eps_pe 합산
        contrib  = sigma * f.area
        N += contrib
        M += contrib * y_r                         # 회전 축 기준 모멘트

    return N, M   # N[N], M[N·mm]

# --- Axial force by material (same strain path as _integrate) ---

def axial_force_split_materials_kn(
    section: FiberSection,
    eps_top: float,
    eps_bot: float,
    theta: float = 0.0,
    phi: float = 1.0,
) -> Tuple[float, float, float]:
    """Same strain interpolation as _integrate; split axial [kN] concrete vs steel."""
    from ..materials.concrete import Concrete

    fibers = section.fibers
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)
    y_primes = [-f.x * sin_t + f.y * cos_t for f in fibers]
    y_top_r = max(y_primes)
    y_bot_r = min(y_primes)
    dy_r = y_top_r - y_bot_r
    if abs(dy_r) < 1e-12:
        kappa = 0.0
        eps0 = eps_top
    else:
        kappa = (eps_top - eps_bot) / dy_r
        eps0 = eps_top - kappa * y_top_r
    n_conc = 0.0
    n_steel = 0.0
    for f in fibers:
        y_r = -f.x * sin_t + f.y * cos_t
        eps_geom = eps0 + kappa * y_r
        sigma = f.material.stress(eps_geom)
        contrib = sigma * f.area
        if isinstance(f.material, Concrete):
            n_conc += contrib
        else:
            n_steel += contrib
    return (
        phi * n_conc / 1_000,
        phi * n_steel / 1_000,
        phi * (n_conc + n_steel) / 1_000,
    )

# ══════════════════════════════════════════════════════════════════════
# P-M 상관도 계산 (회전 포함)
# ══════════════════════════════════════════════════════════════════════

def compute_pm_diagram(
    section: FiberSection,
    ecu: float = 3.5e-3,
    n_pts: int = 200,
    theta: float = 0.0,
    phi: float = 1.0,
) -> List[PMPoint]:
    """
    P-M 상관도를 파이버 해석으로 계산합니다.

    알고리즘:
      1. 모멘트 방향 theta로 회전한 좌표계에서 극단 y' 결정
      2. 압축 측(y'_top) 변형률 = εcu 고정
      3. 인장 측(y'_bot) 변형률을 +εcu(순압축) → -εtu(순인장) 스윕
      4. 각 점에서 N, M 계산 → PMPoint 목록

    Args:
        section : FiberSection 객체
        ecu     : 극한 압축변형률
        n_pts   : 스윕 포인트 수
        theta   : 모멘트 방향 [rad]  (0=X축, π/2=Y축)
                  단면이 이 방향으로 회전한 것처럼 계산됩니다.
        phi     : 강도감소계수 (ACI 방식. KDS는 1.0)

    Returns:
        List[PMPoint] — 닫힌 P-M 곡선 (양·음 모멘트 포함)
    """
    fibers = section.fibers
    cos_t  = math.cos(theta)
    sin_t  = math.sin(theta)

    # ── 회전 좌표계에서 극단 y' ──────────────────────────────────
    y_primes = [-f.x * sin_t + f.y * cos_t for f in fibers]
    y_top_r  = max(y_primes)
    y_bot_r  = min(y_primes)
    etu      = PM_DIAGRAM_ETU

    points: List[PMPoint] = []

    # ── 1. 순압축 (전단면 균일 εcu) ──────────────────────────────
    N0, M0 = _integrate(fibers, ecu, ecu, y_top_r, y_bot_r, cos_t, sin_t)
    points.append(PMPoint(
        N_kN  = phi * N0 / 1_000,
        M_kNm = phi * abs(M0) / 1_000_000,
        label = "순압축 N_max",
    ))

    # ── 2. 압축 측 εcu 고정, 인장 측 스윕 ───────────────────────
    for eb in np.linspace(ecu, -etu, n_pts):
        N, M = _integrate(fibers, ecu, eb, y_top_r, y_bot_r, cos_t, sin_t)
        points.append(PMPoint(
            N_kN  = phi * N  / 1_000,
            M_kNm = phi * M  / 1_000_000,
        ))

    # ── 3. 순인장 (전단면 균일 −εtu) ────────────────────────────
    N1, M1 = _integrate(fibers, -etu, -etu, y_top_r, y_bot_r, cos_t, sin_t)
    points.append(PMPoint(
        N_kN  = phi * N1 / 1_000,
        M_kNm = phi * abs(M1) / 1_000_000,
        label = "순인장 N_min",
    ))

    # ── 4. 음의 모멘트 방향 (대칭) ──────────────────────────────
    mirrored = [PMPoint(N_kN=p.N_kN, M_kNm=-p.M_kNm) for p in points]

    return points + mirrored[::-1]


def diagram_max_positive_moment_strain(
    section: FiberSection,
    ecu: float,
    n_pts: int,
    theta: float,
    phi: float = 1.0,
) -> Tuple[float, float, float]:
    """Same discrete strain set as compute_pm_diagram; max M with M_kNm >= -1e-3 (Pb, Mb)."""
    fibers = section.fibers
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)
    y_primes = [-f.x * sin_t + f.y * cos_t for f in fibers]
    y_top_r = max(y_primes)
    y_bot_r = min(y_primes)
    etu = PM_DIAGRAM_ETU
    best_eb = ecu
    best_n = 0.0
    best_m = -1e300

    def consider(eb: float, nk: float, mk: float) -> None:
        nonlocal best_eb, best_n, best_m
        if mk >= -1e-3 and mk > best_m:
            best_m = mk
            best_eb = eb
            best_n = nk

    N0, M0 = _integrate(fibers, ecu, ecu, y_top_r, y_bot_r, cos_t, sin_t)
    consider(ecu, phi * N0 / 1_000, phi * abs(M0) / 1_000_000)

    for eb in np.linspace(ecu, -etu, n_pts):
        N, M = _integrate(fibers, ecu, eb, y_top_r, y_bot_r, cos_t, sin_t)
        consider(eb, phi * N / 1_000, phi * M / 1_000_000)

    N1, M1 = _integrate(fibers, -etu, -etu, y_top_r, y_bot_r, cos_t, sin_t)
    consider(-etu, phi * N1 / 1_000, phi * abs(M1) / 1_000_000)

    return best_eb, best_n, best_m


def diagram_closest_strain_to_nm(
    section: FiberSection,
    ecu: float,
    n_pts: int,
    theta: float,
    phi: float,
    N_tgt_kN: float,
    M_tgt_kNm: float,
) -> Tuple[float, float, float]:
    """Same discrete set as compute_pm_diagram; closest point to target N, M."""
    fibers = section.fibers
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)
    y_primes = [-f.x * sin_t + f.y * cos_t for f in fibers]
    y_top_r = max(y_primes)
    y_bot_r = min(y_primes)
    etu = PM_DIAGRAM_ETU
    best_eb = ecu
    best_n = 0.0
    best_m = 0.0
    best_err = 1e300

    def consider(eb: float, nk: float, mk: float) -> None:
        nonlocal best_eb, best_n, best_m, best_err
        err = (nk - N_tgt_kN) ** 2 + (mk - M_tgt_kNm) ** 2
        if err < best_err:
            best_err = err
            best_eb = eb
            best_n = nk
            best_m = mk

    # ── 1단계: 거친 스윕 ─────────────────────────────────────────
    N0, M0 = _integrate(fibers, ecu, ecu, y_top_r, y_bot_r, cos_t, sin_t)
    consider(ecu, phi * N0 / 1_000, phi * abs(M0) / 1_000_000)

    eb_sweep = np.linspace(ecu, -etu, n_pts)
    for eb in eb_sweep:
        N, M = _integrate(fibers, ecu, eb, y_top_r, y_bot_r, cos_t, sin_t)
        consider(eb, phi * N / 1_000, phi * M / 1_000_000)

    N1, M1 = _integrate(fibers, -etu, -etu, y_top_r, y_bot_r, cos_t, sin_t)
    consider(-etu, phi * N1 / 1_000, phi * abs(M1) / 1_000_000)

    # ── 2단계: 정밀 스윕 (1단계 최적 주변 ±2 구간 세분화) ────────
    step = (ecu + etu) / (n_pts - 1)
    eb_fine_min = max(best_eb - 2 * step, -etu)
    eb_fine_max = min(best_eb + 2 * step,  ecu)
    for eb in np.linspace(eb_fine_max, eb_fine_min, n_pts * 10):
        N, M = _integrate(fibers, ecu, eb, y_top_r, y_bot_r, cos_t, sin_t)
        consider(eb, phi * N / 1_000, phi * M / 1_000_000)

    return best_eb, best_n, best_m





# ══════════════════════════════════════════════════════════════════════
# 단일 변형률 상태 해석
# ══════════════════════════════════════════════════════════════════════
def analyze_strain_state(
    section: FiberSection,
    eps_top: float,
    eps_bot: float,
    theta: float = 0.0,
) -> SectionResponse:
    """특정 변형률 상태에서 N, M 계산 (회전 포함)"""
    fibers  = section.fibers
    cos_t   = math.cos(theta)
    sin_t   = math.sin(theta)

    y_primes = [-f.x * sin_t + f.y * cos_t for f in fibers]
    y_top_r  = max(y_primes)
    y_bot_r  = min(y_primes)

    N, M = _integrate(fibers, eps_top, eps_bot, y_top_r, y_bot_r, cos_t, sin_t)

    # 중립축 깊이 (압축 측에서)
    dy = y_top_r - y_bot_r
    if abs(eps_top - eps_bot) > 1e-12 and abs(dy) > 1e-9:
        kappa   = (eps_top - eps_bot) / dy
        eps0    = eps_top - kappa * y_top_r
        y_na    = -eps0 / kappa          # ε(y_na) = 0 인 y'
        na_depth = y_top_r - y_na
    else:
        na_depth = float("nan")

    return SectionResponse(
        N_kN         = N / 1_000,
        M_kNm        = M / 1_000_000,
        eps_top      = eps_top,
        eps_bot      = eps_bot,
        neutral_axis = na_depth,
        theta        = theta,
    )


# ══════════════════════════════════════════════════════════════════════
# 역산: 주어진 N에서 M 탐색 (이분법)
# ══════════════════════════════════════════════════════════════════════
def find_moment_at_axial(
    section: FiberSection,
    N_target_kN: float,
    ecu: float = 3.5e-3,
    theta: float = 0.0,
    tol: float = 0.1,
    max_iter: int = 100,
) -> Optional[float]:
    """주어진 축력 N에서 P-M 상관도 상의 M을 이분법으로 탐색 [kN·m]"""
    fibers  = section.fibers
    cos_t   = math.cos(theta)
    sin_t   = math.sin(theta)
    y_primes= [-f.x * sin_t + f.y * cos_t for f in fibers]
    y_top_r = max(y_primes)
    y_bot_r = min(y_primes)
    N_tgt   = N_target_kN * 1_000
    etu     = PM_DIAGRAM_ETU
    lo, hi  = -etu, ecu

    for _ in range(max_iter):
        mid = (lo + hi) / 2
        N_mid, _ = _integrate(fibers, ecu, mid, y_top_r, y_bot_r, cos_t, sin_t)
        if abs(N_mid - N_tgt) < tol * 1_000:
            _, M = _integrate(fibers, ecu, mid, y_top_r, y_bot_r, cos_t, sin_t)
            return M / 1_000_000
        if N_mid > N_tgt:
            hi = mid
        else:
            lo = mid
    return None
