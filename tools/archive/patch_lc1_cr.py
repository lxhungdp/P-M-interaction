# -*- coding: utf-8 -*-
path = "app.py"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

start = 1756
end = 1833
new_block = r'''            with _cr:
                _yt_d = float(_y_prime_top_ref)
                _yb_d = float(_yp_tens_ui)
                st.markdown(
                    f"**�� 참조값 (기호 �� 입력 �� 오차��, ±{VERIFY_REF_ERR_PCT:.0f}%)**")
                _cct, _ccr = st.columns([1.42, 0.88])
                with _cct:
                    _refs_2 = {}
                    _ref_row("εcu",       "s_v_ecu",  "w_v_ecu",  round(ecu_val, 6), _refs_2, ecu_val,
                             warn_ctx="εcu 표 3.1-2 보간값 확인", compact=True)
                    _ref_row("εyd",       "s_v_ey",   "w_v_ey",   round(_eyd,   6),  _refs_2, _eyd,
                             warn_ctx="fyd�s 확인", compact=True)
                    _ref_row("d [mm]",    "s_v_d",    "w_v_d",    round(_h_eff, 1),  _refs_2, _h_eff,
                            �복(표면→��근중��) 및 단면치수 확인", compact=True)
                    _ref_row("cb [mm]",   "s_v_cb",   "w_v_cb",   round(_cb_est, 1), _refs_2, _cb_est,
                             warn_ctx="εcu/(εcu+εyd)×d 공식 확인", compact=True)
                    _ref_row("Ccb [kN]",  "s_v_ccb",  "w_v_ccb",  round(_Ccb, 1),    _refs_2, _Ccb,
                            ��크리트 ��력��선/εcu 확인", compact=True)
                    _ref_row("Csb [kN]",  "s_v_csb",  "w_v_csb",  round(_Csb, 1),    _refs_2, _Csb,
                            �근 위치/��력 확인", compact=True)
                    _ref_row("Tb [kN]",   "s_v_tb",   "w_v_tb",   round(_Tb,  1),    _refs_2, _Tb,
                             warn_ctx�근 위치/εyd 확인", compact=True)
                    _ref_row("Pb [kN]",   "s_v_pb",   "w_v_pb",   round(_Pb_eng, 1), _refs_2, _Pb_eng,
                             warn_ctx="Ccb+Csb-Tb ��력 확인", compact=True)
                    _ref_row("Mb [kN·m]", "s_v_mb",   "w_v_mb",   round(_Mb_eng, 1), _refs_2, _Mb_eng,
                             warn_ctx="���트 확인", compact=True)
                    _ref_row("Ccd [kN]",  "s_v_ccd",  "w_v_ccd",  round(_Ccd, 1),    _refs_2, _Ccd,
                             warn_ctx="LC1 ������력 확인", compact=True)
                    _ref_row("Csd [kN]",  "s_v_csd",  "w_v_csd",  round(_Csd, 1),    _refs_2, _Csd,
                             warn_ctx�근력 확인", compact=True)
                    _ref_row("Td [kN]",   "s_v_td",   "w_v_td",   round(_Td,  1),    _refs_2, _Td,
                             warn_ctx="LC1 인장��근력 확인", compact=True)
                    _ref_row("Pn [kN]",   "s_v_pn1",  "w_v_pn1",  round(_Pn_lc1, 1), _refs_2, _Pn_lc1,
                             warn_ctx="Ccd+Csd-Td� 확인", compact=True)
                    _ref_row("Mn [kN·m]", "s_v_mn1",  "w_v_mn1",  round(_Mn_lc1, 1), _refs_2, _Mn_lc1,
                             warn_ctx=f"fcd={fcd_val:.2f}MPa 또는 ��력분포 확인", compact=True)
                with _ccr:
                    _fig_d, (_ax_sd, _ax_dd) = plt.subplots(
                        1, 2, figsize=(1.225, 0.56), dpi=100,
                        gridspec_kw=dict(width_ratios=[1.45, 0.62], wspace=0.14))
                    draw_section_with_na(
                        _ax_sd, section, theta_rad, float(_cb_est),
                        _y_prime_top_ref, _y_prime_bot_ref,
                        sec_type, b, h, poly_outer, poly_holes,
                        strand_dia_val,
                        eps_top=None, eps_bot=None, fs=0.38)
                    _ax_sd.axhline(
                        _yt_d, color="#1565C0", lw=1.1, ls="--", zorder=12, alpha=0.95)
                    _ax_sd.axhline(
                        _yb_d, color="#C62828", lw=1.1, ls="--", zorder=12, alpha=0.95)
                    _ax_sd.set_title("단면·y'", fontsize=8, pad=2)
                    _pad_d = max(abs(_yt_d - _yb_d) * 0.12, 12.0)
                    _ax_dd.plot([0, 0], [_yb_d, _yt_d], color="#333", lw=1.8,
                                solid_capstyle="round")
                    _ax_dd.scatter([0], [_yt_d], color="#1565C0", s=18, zorder=3)
                    _ax_dd.scatter([0], [_yb_d], color="#C62828", s=18, zorder=3)
                    _ax_dd.set_xlim(-0.55, 0.55)
                    _ax_dd.set_ylim(_yb_d - _pad_d, _yt_d + _pad_d)
                    _ax_dd.axis("off")
                    _ax_dd.annotate(
                        f"y'_top={_yt_d:.0f}",
                        xy=(0, _yt_d), xytext=(5, 0), textcoords="offset points",
                        va="center", fontsize=7, color="#1565C0")
                    _ax_dd.annotate(
                        f"y'_tens={_yb_d:.0f}",
                        xy=(0, _yb_d), xytext=(5, 0), textcoords="offset points",
                        va="center", fontsize=7, color="#C62828")
                    _mid_d = 0.5 * (_yt_d + _yb_d)
                    _ax_dd.annotate(
                        "", xy=(0.18, _yt_d), xytext=(0.18, _yb_d),
                        arrowprops=dict(arrowstyle="<->", color="#2E7D32", lw=1.0))
                    _ax_dd.text(
                        0.24, _mid_d, f"d={_h_eff:.1f}",
                        va="center", fontsize=7, color="#2E7D32")
                    _ax_dd.set_title("d (y' ��)", fontsize=8, pad=2)
                    plt.tight_layout(pad=0.12)
                    st.pyplot(_fig_d, use_container_width=True)
                    plt.close(_fig_d)

'''.splitlines(keepends=True)

if lines[start].strip() != "with _cr:":
    raise SystemExit(f"unexpected line at {start}: {lines[start]!r}")

lines[start:end] = new_block
with open(path, "w", encoding="utf-8") as f:
    f.writelines(lines)
print("lc1 layout ok")
