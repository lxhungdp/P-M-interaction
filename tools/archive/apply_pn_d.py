# -*- coding: utf-8 -*-
from pathlib import Path


def main():
    p = Path("app.py")
    t = p.read_text(encoding="utf-8")

    ins = (
        "        _Nc_pmax, _Ns_pmax, _Nsum_pmax = axial_force_split_materials_kn(\n"
        "            section, ecu_val, ecu_val, theta_rad, phi=1.0)\n"
        "        _Ag_geo = float(geo.A)\n"
        "        _As_steel_tot = sum(\n"
        "            f.area for f in section.fibers\n"
        "            if isinstance(f.material, (Rebar, Strand)))\n"
        "        _Ac_mesh = sum(\n"
        "            f.area for f in section.fibers if isinstance(f.material, Concrete))\n"
        "        _Ac_theory = max(_Ag_geo - _As_steel_tot, 0.0)\n"
        "        _Cc_linear = fcd_val * _Ac_theory / 1000.0\n"
        "        _Cs_hand = fyd_val * _As / 1000.0\n"
    )
    key = "        _Pn_eng  = N_max_v"
    i = t.index(key)
    j = t.index("\n", i)
    t = t[: j + 1] + ins + t[j + 1 :]

    i0 = t.index("                _Ac_mesh = sum(")
    start = t.rfind("            with _ce:\n", 0, i0)
    end = t.index('                    language="")', i0) + len('                    language="")')
    new_pn = (
        "            with _ce:\n"
        '                st.markdown("**�� ��진 계산 과정**")\n'
        "                st.code(\n"
        '                    f"재료계수 (KDS 표 1.4-1)\\n"\n'
        '                    f"  Φc={_gc}, Φs={_gs}, αcc={_acc}\\n"\n'
        '                    f"fcd=αcc×�c={_acc}×{fck}×{_gc}={fcd_val:.3f} MPa\\n"\n'
        '                    f"fyd=fy×��s={fy}×{_gs}={fyd_val:.1f} MPa\\n"\n'
        '                    f"\\n"\n'
        '                    f"Ag(기하)={_Ag_geo:,.0f} mm²  As(��근)={_As:,.0f} mm²  "\n'
        '                    f"�연)={_As_steel_tot:,.0f} mm²\\n"\n'
        '                    f"��고) 이�� 순���크리트 Ag−ΣAs={_Ac_theory:,.0f} mm²\\n"\n'
        '�고) 파이버 ΣAc(메시)={_Ac_mesh:,.0f} mm² (��라이스·스트립 ��사)\\n"\n'
        '                    f"\\n"\n'
        '� εcu — P-M 설계��선 N_max와 동일 적분, φ=1.0]\\n"\n'
        '                    f" ��크리트 파이버)={_Nc_pmax:,.1f} kN\\n"\n'
        '                    f" �연선)={_Ns_pmax:,.1f} kN\\n"\n'
        '                    f"  Nc+Ns={_Nsum_pmax:,.1f} kN  (= P-M �� Pmax {_Pn_eng:.1f} kN)\\n"\n'
        '                    f"\\n"\n'
        '                    f"[��고] 선형근사 fcd×(Ag−ΣAs)={_Cc_linear:,.1f} kN "\n'
        '                    f"(σ-ε 비선형·메시 차이로 Nc와 다름)\\n"\n'
        '                    f"[��고]�근 fyd×As={fyd_val:.1f}×{_As:,.0f}={_Cs_hand:,.1f} kN "\n'
        '                    f"(��연선 ��도)\\n"\n'
        '                    f"\\n"\n'
        '                    f"※ ΣAc≠Ag−ΣAs: 파이버 분할(ny)↑이면 ��라이스 ��적오차는 줄지만, "\n'
        '                    f"스트립(중��±r+여유)은\\n"\n'
        '                    f"  교과서식과 ��전 일치하지 않을 수 있음. Pmax는 실제 파이버 적분값.\\n"\n'
        '                    f"※ Cc를 Ag−ΣAs로�면 Nc+Ns≠Pmax가 되어�과 불일치함.",\n'
        '                    language="")\n'
        "                st.caption(\n"
        '                    "Ag−ΣAs�계용 이��크리트 ��적이고, ΣAc(메시)는 해석에��인 "\n'
        '�크리트�입니다. **파이버 분할을 ��이면** 경계 계단·면적 "\n'
        '                    "적분 오차는 줄지만, **��근 주변 스트립 제거** 때문에 Ag−ΣAs와 ��전히 "\n'
        '                    "��아지지는 않습니다."\n'
        "                )\n"
    )
    t = t[:start] + new_pn + t[end:]

    d_key = "_fig_d, _ax_d = plt.subplots(figsize=(3.0, 2.0), dpi=100)"
    di = t.index(d_key)
    ds = t.rfind("            with _cr:\n", 0, di)
    de = t.index("                plt.close(_fig_d)", di) + len("                plt.close(_fig_d)")
    new_d = (
        "            with _cr:\n"
        '                st.markdown("**�� 참조값  (기호 │ 입력 │ 오차��)**")\n'
        "                _yt_d = float(geo.y_prime_top)\n"
        "                _yb_d = float(_yp_tens_ui)\n"
        "                _fig_d, (_ax_sd, _ax_dd) = plt.subplots(\n"
        "                    1, 2, figsize=(2.45, 1.12), dpi=100,\n"
        "                    gridspec_kw=dict(width_ratios=[1.45, 0.62], wspace=0.14))\n"
        "                draw_section_with_na(\n"
        "                    _ax_sd, section, theta_rad, float(_cb_est),\n"
        "                    geo.y_prime_top, geo.y_prime_bot,\n"
        "                    sec_type, b, h, poly_outer, poly_holes,\n"
        "                    strand_dia_val,\n"
        "                    eps_top=None, eps_bot=None, fs=0.38)\n"
        "                _ax_sd.axhline(\n"
        '                    _yt_d, color="#1565C0", lw=1.1, ls="--", zorder=12, alpha=0.95)\n'
        "                _ax_sd.axhline(\n"
        '                    _yb_d, color="#C62828", lw=1.1, ls="--", zorder=12, alpha=0.95)\n'
        '                _ax_sd.set_title("단면·y\'", fontsize=8, pad=2)\n'
        "                _pad_d = max(abs(_yt_d - _yb_d) * 0.12, 12.0)\n"
        '                _ax_dd.plot([0, 0], [_yb_d, _yt_d], color="#333", lw=1.8,\n'
        '                            solid_capstyle="round")\n'
        '                _ax_dd.scatter([0], [_yt_d], color="#1565C0", s=18, zorder=3)\n'
        '                _ax_dd.scatter([0], [_yb_d], color="#C62828", s=18, zorder=3)\n'
        "                _ax_dd.set_xlim(-0.55, 0.55)\n"
        "                _ax_dd.set_ylim(_yb_d - _pad_d, _yt_d + _pad_d)\n"
        '                _ax_dd.axis("off")\n'
        "                _ax_dd.annotate(\n"
        '                    f"y\'_top={_yt_d:.0f}",\n'
        '                    xy=(0, _yt_d), xytext=(5, 0), textcoords="offset points",\n'
        '                    va="center", fontsize=7, color="#1565C0")\n'
        "                _ax_dd.annotate(\n"
        '                    f"y\'_tens={_yb_d:.0f}",\n'
        '                    xy=(0, _yb_d), xytext=(5, 0), textcoords="offset points",\n'
        '                    va="center", fontsize=7, color="#C62828")\n'
        "                _mid_d = 0.5 * (_yt_d + _yb_d)\n"
        "                _ax_dd.annotate(\n"
        '                    "", xy=(0.18, _yt_d), xytext=(0.18, _yb_d),\n'
        '                    arrowprops=dict(arrowstyle="<->", color="#2E7D32", lw=1.0))\n'
        "                _ax_dd.text(\n"
        '                    0.24, _mid_d, f"d={_h_eff:.1f}",\n'
        '                    va="center", fontsize=7, color="#2E7D32")\n'
        '                _ax_dd.set_title("d (y\'��)", fontsize=8, pad=2)\n'
        "                plt.tight_layout(pad=0.12)\n"
        "                st.pyplot(_fig_d)\n"
        "                plt.close(_fig_d)\n"
    )
    t = t[:ds] + new_d + t[de:]

    p.write_text(t, encoding="utf-8")
    print("apply_pn_d: ok")


if __name__ == "__main__":
    main()
