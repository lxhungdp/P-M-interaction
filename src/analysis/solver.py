"""
P-M 상관도 전용 Solver  (Strain-Compatibility Based)
══════════════════════════════════════════════════════════════════════

핵심 알고리즘
─────────────
1. Strain Compatibility (평면유지 가정, Bernoulli)
     ε(y') = ε₀ + κ · y'
     y'_i  = −x_i·sin(θ) + y_i·cos(θ)   ← 모멘트 방향 θ 로 회전

2. Neutral-Axis Sweep
     압축 극단 변형률 εcu 고정
     중립축 깊이 c: ∞(순압축) → 0(순인장) 로그 스케일 스윕
     eps_bot = εcu × (1 − h_eff / c)    — c 로부터 직접 결정

3. Force Equilibrium (파이버 적분)
     N = Σ σᵢ·Aᵢ
     M = Σ σᵢ·Aᵢ·y'ᵢ          (회전 축 기준 모멘트)
     강연선: ε_eff = ε_geom + ε_pe   (Locked-in 포함)

4. Output
     • PMSolverResult 목록 : P-M 점마다 c, κ, εtop/bot, 파이버 상태
     • PositionStrainSummary 목록 : 위치별 전체 스윕의 max/min 변형률

부호 규약
──────────
  y', y_i  : 도심 기준, 상향 양수
  ε        : 압축 = +,  인장 = −
  N        : 압축 = +  [kN]
  M        : y' 방향 압축 유발 = +  [kN·m]
  c        : 압축 극단 y'_top 에서 중립축까지의 거리 [mm]  (항상 ≥ 0)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np

from ..section.fiber_section import Fiber, FiberSection
from .engine import PM_DIAGRAM_ETU
from ..materials.concrete import Concrete
from ..materials.rebar    import Rebar
from ..materials.strand   import Strand


# ══════════════════════════════════════════════════════════════════════
# 결과 데이터 클래스
# ══════════════════════════════════════════════════════════════════════
@dataclass
class FiberState:
    """단일 파이버의 변형률·응력·힘 상태 (P-M 곡선의 한 점에서)"""
    fiber_id:     int
    mat_type:     str     # "concrete" | "rebar" | "strand"
    mat_label:    str
    x_mm:         float   # 원래 x 좌표 (도심 기준)
    y_mm:         float   # 원래 y 좌표 (도심 기준)
    y_prime_mm:   float   # 회전 좌표계 y' = −x·sin(θ) + y·cos(θ)
    area_mm2:     float
    strain_geom:  float   # 기하 변형률 ε₀ + κ·y'
    strain_eff:   float   # 유효 변형률 (강연선: + ε_pe)
    stress_mpa:   float   # 응력 σ [MPa]
    force_kn:     float   # 기여 축력 σ·A [kN]


@dataclass
class PMSolverResult:
    """P-M 상관도의 한 점 (전체 파이버 상태 포함)"""
    idx:           int
    # ── 단면 결과 ──────────────────────────────────────────────────
    N_kN:          float   # 축력 (압축 +) [kN]
    M_kNm:         float   # 모멘트 (+M: y' 측 압축) [kN·m]
    N_phi_kN:      float   # φ 적용 후 축력
    M_phi_kNm:     float   # φ 적용 후 모멘트

    # ── 중립축 / 곡률 ──────────────────────────────────────────────
    c_mm:          float   # 중립축 깊이 [mm]  (∞ → 순압축)
    kappa:         float   # 곡률 κ [1/mm]
    eps_top:       float   # 압축 극단 변형률 (= +εcu)
    eps_bot:       float   # 인장 극단 변형률
    state:         str     # "순압축" | "전단면압축" | "압축지배" | "균형" | "인장지배" | "순인장"

    # ── 재료별 최대/최소 변형률 ────────────────────────────────────
    eps_conc_max:       float   # 콘크리트 최대 압축변형률 (가장 큰 +ε)
    eps_conc_min:       float   # 콘크리트 최소 변형률 (인장 측)
    eps_rebar_max:      float   # 철근 최대 압축변형률
    eps_rebar_min:      float   # 철근 최소 변형률 (가장 큰 인장)
    eps_strand_eff_max: float   # 강연선 유효 최대 (ε_geom + ε_pe)
    eps_strand_eff_min: float   # 강연선 유효 최소

    # ── 상세 파이버 상태 ───────────────────────────────────────────
    fiber_states: List[FiberState] = field(default_factory=list)


@dataclass
class PositionStrainSummary:
    """특정 파이버 위치에서 전체 P-M 범위에 걸친 변형률 통계"""
    fiber_id:   int
    mat_type:   str
    mat_label:  str
    y_prime_mm: float    # 회전 좌표계 y' 위치

    strain_max: float    # 전체 스윕 중 최대 변형률 (압축 측)
    strain_min: float    # 전체 스윕 중 최소 변형률 (인장 측)
    N_at_max:   float    # 최대 변형률 발생 시 N [kN]
    M_at_max:   float    # 최대 변형률 발생 시 M [kN·m]
    N_at_min:   float    # 최소 변형률 발생 시 N [kN]
    M_at_min:   float    # 최소 변형률 발생 시 M [kN·m]


@dataclass
class PMSolverOutput:
    """Solver 전체 출력"""
    pm_results:       List[PMSolverResult]
    position_summary: List[PositionStrainSummary]
    theta_rad:        float
    phi:              float
    ecu:              float
    etu:              float
    h_eff_mm:         float   # 회전 후 유효 단면 높이


# ══════════════════════════════════════════════════════════════════════
# 내부 보조 함수
# ══════════════════════════════════════════════════════════════════════
def _mat_type(material) -> str:
    if isinstance(material, Concrete): return "concrete"
    if isinstance(material, Rebar):    return "rebar"
    if isinstance(material, Strand):   return "strand"
    return "unknown"


def _classify_state(
    c_mm: float,
    h_eff: float,
    eps_bot: float,
    eps_sy: float,
    ecu: float,
) -> str:
    """
    중립축 깊이와 인장 극단 변형률로 단면 상태 분류
    eps_sy : 철근 항복 변형률 (양수, 예: 0.002)
    """
    if c_mm >= 1e6:
        return "순압축"
    if eps_bot >= 0.0:
        return "전단면압축"
    eps_bot_abs = abs(eps_bot)
    eps_sy_abs  = abs(eps_sy)
    if eps_bot_abs < eps_sy_abs * 0.98:
        return "압축지배"
    if abs(eps_bot_abs - eps_sy_abs) / eps_sy_abs < 0.03:
        return "균형"
    if eps_bot_abs < 0.005:
        return "인장지배"
    return "순인장"


def _integrate_full(
    fibers:   List[Fiber],
    eps_top:  float,
    eps_bot:  float,
    y_top_r:  float,
    y_bot_r:  float,
    cos_t:    float,
    sin_t:    float,
) -> Tuple[float, float, List[Tuple[float, float, float]]]:
    """
    파이버 적분 — N, M 산출 + 파이버별 (변형률, 응력) 반환

    Returns:
        N [N], M [N·mm],
        fiber_data: List[(strain_geom, strain_eff, stress_mpa)]
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
    fiber_data: List[Tuple[float, float, float]] = []

    for f in fibers:
        y_r        = -f.x * sin_t + f.y * cos_t
        eps_geom   = eps0 + kappa * y_r
        sigma      = f.material.stress(eps_geom)   # Strand: 내부에서 ε_pe 합산
        contrib    = sigma * f.area
        N         += contrib
        M         += contrib * y_r

        # 강연선의 경우 유효 변형률 = geom + eps_pe
        if isinstance(f.material, Strand):
            eps_eff = eps_geom + f.material.eps_pe
        else:
            eps_eff = eps_geom

        fiber_data.append((eps_geom, eps_eff, sigma))

    return N, M, fiber_data


def _c_to_eps_bot(c_mm: float, y_top_r: float, y_bot_r: float, ecu: float) -> float:
    """
    중립축 깊이 c → 인장 극단 변형률 eps_bot

    중립축 y_na = y_top_r − c
    eps_bot = ecu × (y_bot_r − y_na) / c
            = ecu × (y_bot_r − y_top_r + c) / c
            = ecu × (1 − h_eff / c)
    """
    h_eff = y_top_r - y_bot_r
    if c_mm >= 1e6:
        return ecu          # 순압축
    return ecu * (1.0 - h_eff / c_mm)


def _eps_bot_to_c(eps_bot: float, y_top_r: float, y_bot_r: float, ecu: float) -> float:
    """eps_bot → 중립축 깊이 c [mm]"""
    h_eff = y_top_r - y_bot_r
    delta = ecu - eps_bot
    if abs(delta) < 1e-15:
        return 1e9    # 사실상 순압축
    return ecu * h_eff / delta



def eps_bot_from_compression_depth(
    c_mm: float,
    y_top_r: float,
    y_bot_r: float,
    ecu: float,
    clip_tension: Optional[float] = None,
) -> float:
    """Compression depth c from y_top to NA -> strain at extreme y_bot."""
    eb = _c_to_eps_bot(c_mm, y_top_r, y_bot_r, ecu)
    if clip_tension is not None:
        eb = max(eb, -float(clip_tension))
    return float(min(eb, ecu * (1.0 - 1e-12)))


def eps_bot_for_tension_yield_at_depth(
    eps_top: float,
    y_top_r: float,
    y_bot_r: float,
    y_steel_r: float,
    eyd: float,
) -> float:
    """Linear strain: eps_top at y_top, -eyd at y_steel_r -> eps_bot at y_bot_r."""
    dy = y_bot_r - y_top_r
    if abs(dy) < 1e-12:
        return float(-eyd)
    t_s = (y_steel_r - y_top_r) / dy
    if abs(t_s) < 1e-15:
        return float(eps_top)
    return float(eps_top + (-eyd - eps_top) / t_s)


# ══════════════════════════════════════════════════════════════════════
# 메인 Solver
# ══════════════════════════════════════════════════════════════════════
def compute_pm_solver(
    section:  FiberSection,
    ecu:      float = 3.5e-3,
    etu:      float = PM_DIAGRAM_ETU,
    n_pts:    int   = 300,
    theta:    float = 0.0,
    phi:      float = 1.0,
    store_fiber_states: bool = True,
) -> PMSolverOutput:
    """
    P-M 상관도 Solver  —  Strain-Compatibility 기반

    Algorithm
    ─────────
    1. 회전 좌표계 y'_i 계산
    2. c를 로그 스케일로 스윕 : ∞(순압축) → 0(순인장)
    3. 각 c에서 eps_bot 결정 → _integrate_full 호출
    4. PMSolverResult 목록 생성 (파이버 변형률 포함)
    5. 위치별 최대/최소 변형률 요약 생성

    Args:
        section : FiberSection 객체
        ecu     : 콘크리트 극한 압축 변형률
        etu     : 극한 인장 변형률 (스윕 하한)
        n_pts   : 스윕 포인트 수
        theta   : 모멘트 방향 [rad]
        phi     : 강도감소계수
        store_fiber_states: 상세 파이버 상태 저장 여부 (메모리)

    Returns:
        PMSolverOutput
    """
    fibers  = section.fibers
    cos_t   = math.cos(theta)
    sin_t   = math.sin(theta)

    # ── 회전 y' 계산 ──────────────────────────────────────────────
    y_primes = [-f.x * sin_t + f.y * cos_t for f in fibers]
    y_top_r  = max(y_primes)
    y_bot_r  = min(y_primes)
    h_eff    = y_top_r - y_bot_r

    # ── 철근 항복변형률 (분류용) ──────────────────────────────────
    eps_sy = 0.002  # 기본값
    for f in fibers:
        if isinstance(f.material, Rebar):
            eps_sy = getattr(f.material, "eps_sy", f.material.fyd / f.material.Es)
            break

    # ── c 스윕 값 생성 (로그 스케일, 압축 → 인장) ──────────────
    # c_max: 사실상 순압축 (균일 εcu)
    # c_min: 극단 인장 (eps_bot ≈ -etu)
    c_min = max(ecu * h_eff / (ecu + etu), 1e-3)
    c_max = 1e9   # 사실상 무한대 (순압축)

    # 로그 스케일 c 값 + 특수 포인트 추가
    c_log = np.exp(
        np.linspace(math.log(c_min), math.log(min(c_max, 1000.0 * h_eff)), n_pts - 2)
    )
    c_log = np.sort(c_log)[::-1]  # 큰 것 → 작은 것 (압축 → 인장)

    # 특수 포인트: c = h_eff (중립축이 단면 하단), c = ∞ (순압축)
    c_values = np.concatenate([[c_max], c_log])

    # ── 각 c에서 적분 ──────────────────────────────────────────────
    pm_results: List[PMSolverResult] = []
    seen_eps_bots = set()   # 중복 방지

    for idx, c_mm in enumerate(c_values):
        eps_bot = _c_to_eps_bot(c_mm, y_top_r, y_bot_r, ecu)
        eps_bot = max(min(eps_bot, ecu), -etu)

        # 중복 eps_bot 건너뜀 (부동소수 반올림으로 동일한 점 방지)
        key = round(eps_bot, 8)
        if key in seen_eps_bots:
            continue
        seen_eps_bots.add(key)

        eps_top_used = ecu
        N, M, fiber_data = _integrate_full(
            fibers, eps_top_used, eps_bot, y_top_r, y_bot_r, cos_t, sin_t
        )

        # κ 계산
        dy_r  = y_top_r - y_bot_r
        kappa = (eps_top_used - eps_bot) / dy_r if abs(dy_r) > 1e-12 else 0.0

        # ── 재료별 변형률 ─────────────────────────────────────────
        eps_conc_list   = [fd[0] for fi, fd in zip(fibers, fiber_data)
                           if isinstance(fi.material, Concrete)]
        eps_rebar_list  = [fd[0] for fi, fd in zip(fibers, fiber_data)
                           if isinstance(fi.material, Rebar)]
        eps_strand_list = [fd[1] for fi, fd in zip(fibers, fiber_data)
                           if isinstance(fi.material, Strand)]

        conc_max  = max(eps_conc_list,   default=0.0)
        conc_min  = min(eps_conc_list,   default=0.0)
        rb_max    = max(eps_rebar_list,  default=0.0)
        rb_min    = min(eps_rebar_list,  default=0.0)
        st_max    = max(eps_strand_list, default=0.0)
        st_min    = min(eps_strand_list, default=0.0)

        # ── 상태 분류 ─────────────────────────────────────────────
        state = _classify_state(c_mm, h_eff, eps_bot, eps_sy, ecu)

        # ── FiberState 목록 ───────────────────────────────────────
        fstates: List[FiberState] = []
        if store_fiber_states:
            for fi_idx, (fi, (eg, ee, sg)) in enumerate(zip(fibers, fiber_data)):
                y_r = -fi.x * sin_t + fi.y * cos_t
                fstates.append(FiberState(
                    fiber_id    = fi_idx,
                    mat_type    = _mat_type(fi.material),
                    mat_label   = fi.material.label,
                    x_mm        = fi.x,
                    y_mm        = fi.y,
                    y_prime_mm  = y_r,
                    area_mm2    = fi.area,
                    strain_geom = eg,
                    strain_eff  = ee,
                    stress_mpa  = sg,
                    force_kn    = sg * fi.area / 1_000,
                ))

        # c_mm 정리 (출력용)
        c_display = c_mm if c_mm < 1e8 else float("inf")

        pm_results.append(PMSolverResult(
            idx           = len(pm_results),
            N_kN          = N / 1_000,
            M_kNm         = M / 1_000_000,
            N_phi_kN      = phi * N / 1_000,
            M_phi_kNm     = phi * M / 1_000_000,
            c_mm          = c_display,
            kappa         = kappa,
            eps_top       = eps_top_used,
            eps_bot       = eps_bot,
            state         = state,
            eps_conc_max  = conc_max,
            eps_conc_min  = conc_min,
            eps_rebar_max = rb_max,
            eps_rebar_min = rb_min,
            eps_strand_eff_max = st_max,
            eps_strand_eff_min = st_min,
            fiber_states  = fstates,
        ))

    # ── 음의 모멘트 대칭 포인트 (상관도 완성) ─────────────────────
    mirrored: List[PMSolverResult] = []
    for r in pm_results:
        mirrored.append(PMSolverResult(
            idx           = r.idx,
            N_kN          = r.N_kN,
            M_kNm         = -r.M_kNm,
            N_phi_kN      = r.N_phi_kN,
            M_phi_kNm     = -r.M_phi_kNm,
            c_mm          = r.c_mm,
            kappa         = r.kappa,
            eps_top       = r.eps_top,
            eps_bot       = r.eps_bot,
            state         = r.state,
            eps_conc_max  = r.eps_conc_max,
            eps_conc_min  = r.eps_conc_min,
            eps_rebar_max = r.eps_rebar_max,
            eps_rebar_min = r.eps_rebar_min,
            eps_strand_eff_max = r.eps_strand_eff_max,
            eps_strand_eff_min = r.eps_strand_eff_min,
            fiber_states  = [],   # 미러 포인트는 상세 생략
        ))

    all_results = pm_results + mirrored[::-1]

    # ── 위치별 변형률 요약 ─────────────────────────────────────────
    position_summary = _build_position_summary(
        fibers, y_top_r, y_bot_r, cos_t, sin_t,
        pm_results,   # 양의 모멘트 방향만 사용
    )

    return PMSolverOutput(
        pm_results       = all_results,
        position_summary = position_summary,
        theta_rad        = theta,
        phi              = phi,
        ecu              = ecu,
        etu              = etu,
        h_eff_mm         = h_eff,
    )


def pm_result_at_strains(
    section: FiberSection,
    eps_top: float,
    eps_bot: float,
    theta: float = 0.0,
    phi: float = 1.0,
    store_fiber_states: bool = True,
) -> PMSolverResult:
    """
    One strain pair (eps_top, eps_bot) with the same integration as compute_pm_solver.
    Use with eps_bot from diagram_max_positive_moment_strain / diagram_closest_strain_to_nm
    so fiber forces match the P-M curve from compute_pm_diagram.
    """
    fibers = section.fibers
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)
    y_primes = [-f.x * sin_t + f.y * cos_t for f in fibers]
    y_top_r = max(y_primes)
    y_bot_r = min(y_primes)
    h_eff = y_top_r - y_bot_r
    etu = PM_DIAGRAM_ETU

    eps_sy = 0.002
    for f in fibers:
        if isinstance(f.material, Rebar):
            eps_sy = getattr(f.material, "eps_sy", f.material.fyd / f.material.Es)
            break

    eps_top_used = eps_top
    eps_bot_use = max(min(eps_bot, eps_top_used), -etu)
    c_mm = _eps_bot_to_c(eps_bot_use, y_top_r, y_bot_r, eps_top_used)

    N, M, fiber_data = _integrate_full(
        fibers, eps_top_used, eps_bot_use, y_top_r, y_bot_r, cos_t, sin_t
    )

    dy_r = y_top_r - y_bot_r
    kappa = (eps_top_used - eps_bot_use) / dy_r if abs(dy_r) > 1e-12 else 0.0

    eps_conc_list = [
        fd[0] for fi, fd in zip(fibers, fiber_data) if isinstance(fi.material, Concrete)
    ]
    eps_rebar_list = [
        fd[0] for fi, fd in zip(fibers, fiber_data) if isinstance(fi.material, Rebar)
    ]
    eps_strand_list = [
        fd[1] for fi, fd in zip(fibers, fiber_data) if isinstance(fi.material, Strand)
    ]

    conc_max = max(eps_conc_list, default=0.0)
    conc_min = min(eps_conc_list, default=0.0)
    rb_max = max(eps_rebar_list, default=0.0)
    rb_min = min(eps_rebar_list, default=0.0)
    st_max = max(eps_strand_list, default=0.0)
    st_min = min(eps_strand_list, default=0.0)

    state = _classify_state(c_mm, h_eff, eps_bot_use, eps_sy, eps_top_used)

    fstates: List[FiberState] = []
    if store_fiber_states:
        for fi_idx, (fi, (eg, ee, sg)) in enumerate(zip(fibers, fiber_data)):
            y_r = -fi.x * sin_t + fi.y * cos_t
            fstates.append(FiberState(
                fiber_id=fi_idx,
                mat_type=_mat_type(fi.material),
                mat_label=fi.material.label,
                x_mm=fi.x,
                y_mm=fi.y,
                y_prime_mm=y_r,
                area_mm2=fi.area,
                strain_geom=eg,
                strain_eff=ee,
                stress_mpa=sg,
                force_kn=sg * fi.area / 1_000,
            ))

    c_display = c_mm if c_mm < 1e8 else float("inf")

    return PMSolverResult(
        idx=0,
        N_kN=N / 1_000,
        M_kNm=M / 1_000_000,
        N_phi_kN=phi * N / 1_000,
        M_phi_kNm=phi * M / 1_000_000,
        c_mm=c_display,
        kappa=kappa,
        eps_top=eps_top_used,
        eps_bot=eps_bot_use,
        state=state,
        eps_conc_max=conc_max,
        eps_conc_min=conc_min,
        eps_rebar_max=rb_max,
        eps_rebar_min=rb_min,
        eps_strand_eff_max=st_max,
        eps_strand_eff_min=st_min,
        fiber_states=fstates,
    )


def _build_position_summary(
    fibers:   List[Fiber],
    y_top_r:  float,
    y_bot_r:  float,
    cos_t:    float,
    sin_t:    float,
    pm_list:  List[PMSolverResult],
) -> List[PositionStrainSummary]:
    """
    각 파이버 위치에서 전체 P-M 스윕에 걸친 변형률 min/max 추출

    콘크리트 파이버는 너무 많으므로 y' 레이어별 대표값 사용.
    철근·강연선은 개별 파이버 단위로 추적.
    """
    summary: List[PositionStrainSummary] = []

    # ── 철근 / 강연선: 개별 추적 ─────────────────────────────────
    for fi_idx, fi in enumerate(fibers):
        mtype = _mat_type(fi.material)
        if mtype not in ("rebar", "strand"):
            continue

        strain_history = [
            (r.fiber_states[fi_idx].strain_eff if r.fiber_states else None,
             r.N_kN, r.M_kNm)
            for r in pm_list
            if r.fiber_states
        ]
        if not strain_history:
            continue

        strains = [s for s, _, _ in strain_history]
        idx_max = int(np.argmax(strains))
        idx_min = int(np.argmin(strains))
        y_r = -fi.x * sin_t + fi.y * cos_t

        summary.append(PositionStrainSummary(
            fiber_id   = fi_idx,
            mat_type   = mtype,
            mat_label  = fi.material.label,
            y_prime_mm = y_r,
            strain_max = strains[idx_max],
            strain_min = strains[idx_min],
            N_at_max   = strain_history[idx_max][1],
            M_at_max   = strain_history[idx_max][2],
            N_at_min   = strain_history[idx_min][1],
            M_at_min   = strain_history[idx_min][2],
        ))

    # ── 콘크리트: y' 레이어별 대표값 (10개 레이어) ───────────────
    conc_fibers = [
        (fi_idx, fi, -fi.x * sin_t + fi.y * cos_t)
        for fi_idx, fi in enumerate(fibers)
        if isinstance(fi.material, Concrete)
    ]
    if conc_fibers and pm_list and pm_list[0].fiber_states:
        n_layers = 10
        yp_min = min(c[2] for c in conc_fibers)
        yp_max = max(c[2] for c in conc_fibers)
        layer_edges = np.linspace(yp_min - 1e-6, yp_max + 1e-6, n_layers + 1)

        for k in range(n_layers):
            y_lo, y_hi = layer_edges[k], layer_edges[k + 1]
            # 이 레이어에 속하는 콘크리트 파이버
            layer_ids = [
                fi_idx for fi_idx, fi, yp in conc_fibers
                if y_lo <= yp < y_hi
            ]
            if not layer_ids:
                continue

            # 레이어 대표 y' = 평균
            layer_yp = float(np.mean([yp for _, fi, yp in conc_fibers
                                      if layer_edges[k] <= yp < y_hi]))
            # 레이어 내 파이버들의 평균 변형률 (P-M 스윕 전체)
            strain_history: List[Tuple[float, float, float]] = []
            for r in pm_list:
                if not r.fiber_states:
                    continue
                layer_strains = [r.fiber_states[i].strain_geom for i in layer_ids]
                avg_strain = float(np.mean(layer_strains))
                strain_history.append((avg_strain, r.N_kN, r.M_kNm))

            if not strain_history:
                continue

            strains = [s for s, _, _ in strain_history]
            idx_max = int(np.argmax(strains))
            idx_min = int(np.argmin(strains))

            summary.append(PositionStrainSummary(
                fiber_id   = -k - 1,   # 음수 ID = 콘크리트 레이어
                mat_type   = "concrete",
                mat_label  = f"콘크리트 레이어 {k+1}",
                y_prime_mm = layer_yp,
                strain_max = strains[idx_max],
                strain_min = strains[idx_min],
                N_at_max   = strain_history[idx_max][1],
                M_at_max   = strain_history[idx_max][2],
                N_at_min   = strain_history[idx_min][1],
                M_at_min   = strain_history[idx_min][2],
            ))

    # y' 기준 정렬 (압축 측 → 인장 측)
    summary.sort(key=lambda s: -s.y_prime_mm)
    return summary


# ══════════════════════════════════════════════════════════════════════
# 편의 함수: DataFrame 변환
# ══════════════════════════════════════════════════════════════════════
def pm_results_to_dataframe(
    pm_output: PMSolverOutput,
    half_only: bool = True,
) -> "pd.DataFrame":
    """
    PMSolverOutput → pandas DataFrame

    Args:
        half_only: True이면 양의 모멘트 쪽 절반만 반환
    """
    import pandas as pd

    results = pm_output.pm_results
    if half_only:
        results = [r for r in results if r.M_kNm >= -1e-3]

    rows = []
    for r in results:
        c_str = f"{r.c_mm:.1f}" if r.c_mm < 1e8 else "∞"
        rows.append({
            "No":              r.idx,
            "c [mm]":          c_str,
            "κ [1/km]":        f"{r.kappa * 1e6:.3f}",
            "ε_top [‰]":       f"{r.eps_top * 1e3:.3f}",
            "ε_bot [‰]":       f"{r.eps_bot * 1e3:.3f}",
            "N [kN]":          round(r.N_kN, 1),
            "M [kN·m]":        round(r.M_kNm, 1),
            "φN [kN]":         round(r.N_phi_kN, 1),
            "φM [kN·m]":       round(r.M_phi_kNm, 1),
            "단면상태":         r.state,
            "ε_콘크리트_max[‰]": f"{r.eps_conc_max * 1e3:.3f}",
            "ε_콘크리트_min[‰]": f"{r.eps_conc_min * 1e3:.3f}",
            "ε_철근_max[‰]":    f"{r.eps_rebar_max * 1e3:.3f}" if r.eps_rebar_max != 0 else "—",
            "ε_철근_min[‰]":    f"{r.eps_rebar_min * 1e3:.3f}" if r.eps_rebar_min != 0 else "—",
            "ε_강연선_max[‰]":  f"{r.eps_strand_eff_max * 1e3:.3f}" if r.eps_strand_eff_max != 0 else "—",
            "ε_강연선_min[‰]":  f"{r.eps_strand_eff_min * 1e3:.3f}" if r.eps_strand_eff_min != 0 else "—",
        })
    return pd.DataFrame(rows)


def position_summary_to_dataframe(pos_summary: List[PositionStrainSummary]) -> "pd.DataFrame":
    """PositionStrainSummary 목록 → pandas DataFrame"""
    import pandas as pd

    rows = []
    for ps in pos_summary:
        rows.append({
            "재료":            ps.mat_type,
            "위치명":          ps.mat_label,
            "y' [mm]":         f"{ps.y_prime_mm:.1f}",
            "최대 변형률 [‰]":  f"{ps.strain_max * 1e3:.3f}",
            "최소 변형률 [‰]":  f"{ps.strain_min * 1e3:.3f}",
            "최대 발생 N [kN]": f"{ps.N_at_max:.1f}",
            "최대 발생 M [kN·m]": f"{ps.M_at_max:.1f}",
            "최소 발생 N [kN]": f"{ps.N_at_min:.1f}",
            "최소 발생 M [kN·m]": f"{ps.M_at_min:.1f}",
        })
    return pd.DataFrame(rows)
