"""Verification tab (Streamlit UI)."""

from __future__ import annotations

import math

import numpy as np
import streamlit as st

from src.analysis.engine import axial_force_split_materials_kn, diagram_closest_strain_to_nm
from src.analysis.solver import pm_result_at_strains
from src.codes import CODES
from src.materials.concrete import Concrete
from src.materials.rebar import Rebar
from src.materials.strand import Strand

from pm_app.config import VERIFY_REF_ERR_PCT
from pm_app.pm_checks import ray_intersect_pm_curve
from pm_app.section_builder import ag_theory_mm2, h_eff_and_cb_theory
from pm_app.ui.context import VerifyContext


def render_tab_verify(ctx: VerifyContext) -> None:
    code_name = ctx.code_name
    section = ctx.section
    geo = ctx.geo
    b, h = ctx.b, ctx.h
    sec_type = ctx.sec_type
    theta_rad = ctx.theta_rad
    fck, fy = ctx.fck, ctx.fy
    fcd_val, fyd_val, ecu_val = ctx.fcd_val, ctx.fyd_val, ctx.ecu_val
    N_max_v, N_bal, M_bal = ctx.N_max_v, ctx.N_bal, ctx.M_bal
    eps_bal_top, eps_bal_bot = ctx.eps_bal_top, ctx.eps_bal_bot
    load_cases = ctx.load_cases
    lc1_Pn_cap, lc1_Mn_cap, lc1_eps_bot = ctx.lc1_Pn_cap, ctx.lc1_Mn_cap, ctx.lc1_eps_bot
    N_des, M_des = ctx.N_des, ctx.M_des
    n_pts = ctx.n_pts
    n_top, n_bot, n_left, n_right = ctx.n_top, ctx.n_bot, ctx.n_left, ctx.n_right
    Ag_theory_cached = ctx.Ag_theory_cached
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
            _Mn_ray, _Pn_ray = ray_intersect_pm_curve(_Mu_lc1, _Pu_lc1, _M_arr, _N_arr)
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
