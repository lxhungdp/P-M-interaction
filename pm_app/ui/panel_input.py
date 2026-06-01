"""Left input panel (Streamlit widgets)."""

from __future__ import annotations

import math

import pandas as pd
import streamlit as st

from src.codes import CODES
from pm_app.models import AnalysisInputs
from pm_app.section_builder import compute_rebar_positions


def render_input_panel(expanded: bool) -> tuple[AnalysisInputs, bool]:
    """Render input widgets; return (inputs, run_clicked)."""
    _ = expanded  # panel only rendered when expanded
    # ══ ① 설계기준 & 재료 ══════════════════════════════════════
    with st.expander("🏛  설계기준 · 재료 강도", expanded=True):
        # 설계기준 선택 (전체 폭, 라벨 표시)
        code_name = st.selectbox("설계기준 선택", list(CODES.keys()), key="sel_code")
        _code_tmp = CODES[code_name]()
        # fck / fck응력곡선 / fy — 한 줄
        m1, m2, m3 = st.columns(3)
        fck        = m1.number_input("fck [MPa]", 18, 90, 30, 2, key="inp_fck")
        curve_conc = m2.selectbox("fck 응력곡선",
                                  ["parabolic_rectangular","bilinear","linear"],
                                  key="inp_curve")
        fy         = m3.number_input("fy [MPa]",  300, 600, 400, 50, key="inp_fy")
        # KDS 계수 설명 — fck/fy 아래
        _fcd_tmp = _code_tmp.fcd(fck)
        _ecu_tmp = _code_tmp.epsilon_cu(fck)
        _Ec_tmp  = _code_tmp.elastic_modulus_concrete(fck)
        _fyd_tmp = _code_tmp.fyd(fy)
        _mf      = _code_tmp.material_factors("ULS")
        _gc = _mf.gamma_c; _gs = _mf.gamma_s; _acc = _mf.alpha_cc
        st.caption(
            f"fcd = αcc·fck·Φc = {_acc}×{fck}×{_gc} = **{_fcd_tmp:.2f}** MPa  │  "
            f"εcu = **{_ecu_tmp*1e3:.2f}‰**  │  Ec = **{_Ec_tmp:.0f}** MPa"
        )
        st.caption(
            f"fyd = fy·Φs = {fy}×{_gs} = **{_fyd_tmp:.1f}** MPa  │  "
            f"Es = **200,000** MPa"
        )

    # ══ ② 단면 형상 ════════════════════════════════════════════
    # 제목 행: [📐 단면 형상] [콤보박스] [👁]  ← 같은 행에 모두 배치
    with st.container(border=True):
        poly_outer = None; poly_holes = []; poly_rebar_positions = []

        _h1, _h2, _h3 = st.columns([1.4, 3.2, 0.75])
        _h1.markdown("**📐 단면 형상**")
        sec_type = _h2.selectbox(
            "형상 선택", ["직사각형","원형","임의 다각형"],
            label_visibility="collapsed", key="sec_type_sel")
        if _h3.button("👁", key="prev_btn", help="단면 미리보기"):
            st.session_state.show_preview = True

        # ── 치수 (피복은 철근 배치 테이블로 이동) ──────────────
        diameter = None
        if sec_type == "직사각형":
            d1, d2 = st.columns(2)
            b = d1.number_input("b [mm]", 100, 5000, 400, 50, key="inp_b")
            h = d2.number_input("h [mm]", 100, 5000, 600, 50, key="inp_h")
        elif sec_type == "원형":
            d1, d2 = st.columns(2)
            diameter = d1.number_input("D [mm]", 200, 5000, 600, 50, key="inp_D")
            b = h = diameter
            cover = d2.number_input("피복 c [mm]", 20, 200, 40, 5, key="inp_cov_circ")
            bar_dia = 25  # circle uses single bar_dia
        else:
            cover = st.number_input("피복 c [mm]", 20, 200, 40, 5, key="inp_cov_poly")
            b, h = 400., 600.

        # 임의 다각형 전용 입력
        if sec_type == "임의 다각형":
            pf1,pf2 = st.columns([3,1])
            uploaded_outer = pf1.file_uploader(
                "외곽 CSV", type=["csv","txt"],
                label_visibility="collapsed", key="up_outer")
            pf2.download_button("📎외곽예제",
                "x,y\n0,0\n400,0\n400,600\n0,600\n",
                "outer.csv","text/csv", use_container_width=True)
            def_outer = pd.DataFrame({"x[mm]":[0.,400.,400.,0.],"y[mm]":[0.,0.,600.,600.]})
            if uploaded_outer:
                try:
                    _df=pd.read_csv(uploaded_outer,header=0)
                    _df.columns=["x[mm]","y[mm]"]; def_outer=_df
                except Exception: st.error("CSV 파싱 오류")
            df_outer = st.data_editor(def_outer, num_rows="dynamic",
                use_container_width=True, key="df_outer", height=120)
            try:
                poly_outer=df_outer[["x[mm]","y[mm]"]].dropna().values.tolist()
                xs=[p[0] for p in poly_outer]; ys=[p[1] for p in poly_outer]
                b=max(xs)-min(xs); h=max(ys)-min(ys)
            except Exception: poly_outer=[[0,0],[400,0],[400,600],[0,600]]

            if st.checkbox("중공 포함", key="cb_hole"):
                hf1,hf2=st.columns([3,1])
                uploaded_hole=hf1.file_uploader("중공 CSV", type=["csv","txt"],
                    label_visibility="collapsed", key="up_hole")
                hf2.download_button("📎중공예제",
                    "x,y\n100,100\n300,100\n300,500\n100,500\n",
                    "hole.csv","text/csv", use_container_width=True)
                def_hole=pd.DataFrame({"x[mm]":[100.,300.,300.,100.],"y[mm]":[100.,100.,500.,500.]})
                if uploaded_hole:
                    try:
                        _dh=pd.read_csv(uploaded_hole,header=0); _dh.columns=["x[mm]","y[mm]"]; def_hole=_dh
                    except Exception: pass
                df_hole=st.data_editor(def_hole, num_rows="dynamic",
                    use_container_width=True, key="df_hole", height=110)
                try:
                    hp=df_hole[["x[mm]","y[mm]"]].dropna().values.tolist()
                    if len(hp)>=3: poly_holes=[hp]
                except Exception: poly_holes=[]

            rb_f1,rb_f2=st.columns([3,1])
            uploaded_rb=rb_f1.file_uploader("철근 CSV", type=["csv","txt"],
                label_visibility="collapsed", key="up_rb")
            rb_f2.download_button("📎철근예제",
                "x,y\n50,50\n200,50\n350,50\n50,550\n200,550\n350,550\n",
                "rebar.csv","text/csv", use_container_width=True)
            def_rb=pd.DataFrame({"x[mm]":[50.,200.,350.,50.,200.,350.],"y[mm]":[50.,50.,50.,550.,550.,550.]})
            if uploaded_rb:
                try:
                    _dr=pd.read_csv(uploaded_rb,header=0); _dr.columns=["x[mm]","y[mm]"]; def_rb=_dr
                except Exception: pass
            df_rb=st.data_editor(def_rb, num_rows="dynamic",
                use_container_width=True, key="df_rb", height=120)
            try: poly_rebar_positions=df_rb[["x[mm]","y[mm]"]].dropna().values.tolist()
            except Exception: poly_rebar_positions=[]

    # ══ ③ 철근 배치 (테이블: 위치/갯수/직경/피복) ═══════════════
    with st.expander("🔩  철근 배치", expanded=True):
        if sec_type != "임의 다각형":
            _rebar_default = pd.DataFrame({
                "위치":     ["상단",  "하단",  "좌측면", "우측면"],
                "갯수":     [4,        4,        0,        0      ],
                "D [mm]":   [32,       32,       25,       25     ],
                "피복 [mm]":[70,       70,       40,       40     ],
            })
            df_rebar = st.data_editor(
                _rebar_default,
                column_config={
                    "위치":     st.column_config.TextColumn(
                                    "위치", disabled=True, width="small"),
                    "갯수":     st.column_config.NumberColumn(
                                    "갯수", min_value=0, max_value=30, step=1, width="small"),
                    "D [mm]":   st.column_config.NumberColumn(
                                    "D [mm]", min_value=6, max_value=51, step=1, width="small"),
                    "피복 [mm]":st.column_config.NumberColumn(
                                    "피복 [mm]", min_value=10, max_value=200, step=5, width="small"),
                },
                hide_index=True, use_container_width=True, key="df_rebar",
            )
            r = df_rebar
            n_top   = int(r.iloc[0]["갯수"]);  dia_top   = int(r.iloc[0]["D [mm]"]);  cov_top   = int(r.iloc[0]["피복 [mm]"])
            n_bot   = int(r.iloc[1]["갯수"]);  dia_bot   = int(r.iloc[1]["D [mm]"]);  cov_bot   = int(r.iloc[1]["피복 [mm]"])
            n_left  = int(r.iloc[2]["갯수"]);  dia_left  = int(r.iloc[2]["D [mm]"]);  cov_left  = int(r.iloc[2]["피복 [mm]"])
            n_right = int(r.iloc[3]["갯수"]);  dia_right = int(r.iloc[3]["D [mm]"]);  cov_right = int(r.iloc[3]["피복 [mm]"])
            cover   = cov_top      # 일반 피복 참조값 (강연선 등)
            bar_dia = dia_top      # 참조 직경
            if sec_type == "직사각형":
                rb_list = compute_rebar_positions(
                    b, h,
                    n_top,  dia_top,  cov_top,
                    n_bot,  dia_bot,  cov_bot,
                    n_left, dia_left, cov_left,
                    n_right,dia_right,cov_right,
                )
            st.caption(
                f"총 {n_top+n_bot+n_left+n_right}개  │  "
                f"좌·우면 철근은 상·하단 모서리와 겹치지 않게 배치"
            )
        else:
            n_top = n_bot = n_left = n_right = 0
            bar_dia = st.number_input("철근 직경 D [mm]", 10, 51, 25, 1)
            rb_list = []

    # ══ ④ 강연선 (접힘) ══════════════════════════════════════════
    use_strand = False; strand_pos = []; strand_dia_val = 15.2
    fpk_val = fp01k_val = Ep_val = fpe_val = eps_pe_val = 0
    with st.expander("🔗  강연선 (PSC)", expanded=False):
        use_strand = st.checkbox("강연선 포함", False, key="cb_strand")
        if use_strand:
            ss1,ss2=st.columns(2)
            fpk_val=ss1.number_input("fpk",1000,2100,1860,10)
            fp01k_val=ss2.number_input("fp0.1k",800,2000,1580,10)
            ss3,ss4=st.columns(2)
            Ep_val=ss3.number_input("Ep",180000,210000,195000,1000)
            fpe_val=ss4.number_input("fpe[MPa]",0,1500,900,50)
            eps_pe_val=fpe_val/Ep_val
            ss5,ss6=st.columns(2)
            strand_dia_val=ss5.number_input("직경[mm]",9.5,22.,15.2,0.1)
            n_strand=ss6.number_input("개수",1,30,4,1)
            y_strand=st.number_input("y[mm](도심기준)",value=int(-h//2+cover+50),step=10)
            xsp=(b-2*(cover+strand_dia_val))/max(n_strand-1,1)
            xst0=-(b/2-cover-strand_dia_val)
            strand_pos=[(xst0+i*xsp,float(y_strand)) for i in range(n_strand)]

    # ══ ⑤ 하중 케이스 ══════════════════════════════════════════
    with st.container(border=True):
        _lh1, _lh2 = st.columns([4.2, 0.8])
        _lh1.markdown("**📋 하중 케이스**")
        n_lc = _lh2.number_input(
            "갯수", min_value=1, max_value=30, value=3, step=1,
            key="n_lc", label_visibility="collapsed",
            help="하중 케이스 초기 행 수 (입력 후 Enter)"
        )
        # n_lc 변경 시 기본 행 수 재구성
        _prev_n = st.session_state.get("_prev_n_lc", 3)
        if n_lc != _prev_n:
            st.session_state["_prev_n_lc"] = n_lc
            st.session_state.pop("df_loads", None)  # 키 초기화
        st.session_state["_prev_n_lc"] = n_lc
        _default_lc = pd.DataFrame({
            "극단":      [False] * n_lc,
            "케이스":    [f"LC{i+1}" for i in range(n_lc)],
            "Pu [kN]":   [3000. - i*300 for i in range(n_lc)],
            "Mx [kN·m]": [450.  - i*50  for i in range(n_lc)],
            "My [kN·m]": [0.] * n_lc,
        })
        df_loads = st.data_editor(
            _default_lc,
            column_config={
                "극단": st.column_config.CheckboxColumn(
                    "극단", help="극단한계상태/사고 하중", default=False, width="small"),
                "케이스": st.column_config.TextColumn("케이스", width="small"),
                "Pu [kN]":   st.column_config.NumberColumn("Pu [kN]",   width="small"),
                "Mx [kN·m]": st.column_config.NumberColumn("Mx [kN·m]", width="small"),
                "My [kN·m]": st.column_config.NumberColumn("My [kN·m]", width="small"),
            },
            num_rows="dynamic", use_container_width=True, key="df_loads",
        )
        try:
            vl=df_loads.dropna(subset=["Pu [kN]","Mx [kN·m]","My [kN·m]"])
            avg_Mx=float(vl["Mx [kN·m]"].abs().mean()) if not vl.empty else 1.0
            avg_My=float(vl["My [kN·m]"].abs().mean()) if not vl.empty else 0.0
            theta_rad=math.atan2(avg_My, avg_Mx)
            theta_deg_auto=math.degrees(theta_rad)
        except Exception:
            avg_Mx=1.0; avg_My=0.0; theta_rad=0.0; theta_deg_auto=0.0
        st.caption(f"θ = **{theta_deg_auto:.1f}°** (자동)  │  Ctrl+S = P-M 계산")
        sym_check = st.checkbox("2축 대칭 — 양/음 M 동시 표기")

    # ══ ⑥ 해석 설정 (접힘) ══════════════════════════════════════
    with st.expander("⚙️  해석 설정", expanded=False):
        an1,an2=st.columns(2)
        n_pts   =an1.number_input("포인트 수",50,500,200,50)
        ny_fiber=an2.number_input("파이버 분할",50,900,120,10)

    run = st.button("🚀  P-M 상관도 계산  (Ctrl+S)",
                    use_container_width=True, type="primary")
    if run:
        st.session_state.show_preview = False  # 계산 시 미리보기 자동 닫기

    return AnalysisInputs(
        code_name=code_name, fck=fck, fy=fy, curve_conc=curve_conc,
        sec_type=sec_type, b=b, h=h, cover=cover, bar_dia=bar_dia,
        rb_list=rb_list, n_top=n_top, n_bot=n_bot, n_left=n_left, n_right=n_right,
        poly_outer=poly_outer, poly_holes=poly_holes,
        poly_rebar_positions=poly_rebar_positions,
        use_strand=use_strand, strand_params=None,
        strand_dia_val=strand_dia_val, strand_pos=strand_pos,
        fpk_val=fpk_val, fp01k_val=fp01k_val, Ep_val=Ep_val,
        fpe_val=fpe_val, eps_pe_val=eps_pe_val,
        df_loads=df_loads, avg_Mx=avg_Mx, avg_My=avg_My,
        theta_rad=theta_rad, theta_deg_auto=theta_deg_auto,
        sym_check=sym_check, n_pts=n_pts, ny_fiber=ny_fiber,
    ), run
