# -*- coding: utf-8 -*-
from pathlib import Path

p = Path("app.py")
t = p.read_text(encoding="utf-8")
old_cb = (
    '                        f"  cb=εcu/(εcu+εyd)×d={_cb_est:.1f}�)\\n"\n'
    '                        f"  cb_��진={c_bal_mm:.1f}mm\\n"\n'
)
new_cb = (
    '                        f"  cb('
    '\uc774\ub860 \uc801\uc6a9)={_cb_est:.1f}mm  \u03b5_bot(\uadf9\ub2e8)={eps_bal_bot:.6f}\\n"\n'
)
if old_cb not in t:
    raise SystemExit("old_cb missing")
t = t.replace(old_cb, new_cb, 1)
old_csb = (
    '                        f"���근 {_ncs_b}개: Csb={_Csb:.1f}kN\\n"\n'
    '                        f"  인장��근 {_nt_b}개: Tb={_Tb:.1f}kN\\n"\n'
)
new_csb = (
    '                        f"���근 {_ncs_b}개: Csb={_Csb:.1f}kN\\n"\n'
    '                        f"    ������근 \u03b5: min={_eps_csb_min*1000:.4f}\u2030 max={_eps_csb_max*1000:.4f}\u2030\\n"\n'
    '                        f"    \u203b Csb: strip_concrete_overlapping_steel\ub85c \ucca0\uadfc \uc704\uce58 \ucf58\ud06c\ub9ac\ud2b8 \ud30c\uc774\ubc84 \uc81c\uac70(\uc774\uc911\uba74\uc801 \uc5c6\uc74c)\\n"\n'
    '                        f"  \uc778\uc7a5\ucca0\uadfc\xb7\uac15\uc5f0\uc120 {_nt_b}\uac1c: Tb={_Tb:.1f}kN\\n"\n'
    '                        f"  [Tb \uac1c\ubcc4 \ud30c\uc774\ubc84]\\n{_tb_detail_txt}\\n"\n'
)
if old_csb not in t:
    raise SystemExit("old_csb missing")
t = t.replace(old_csb, new_csb, 1)
old_tb_fallback = '            if _tb_detail_lines else "      (인장근/��연선 없음)")'
new_tb_fallback = (
    '            if _tb_detail_lines else "      ('
    '\uc778\uc7a5 \ucca0\uadfc\xb7\uac15\uc5f0\uc120 \uc5c6\uc74c)")'
)
if old_tb_fallback in t:
    t = t.replace(old_tb_fallback, new_tb_fallback, 1)
else:
    t = t.replace(
        '            if _tb_detail_lines else "      (인�근/��연선 없음)")',
        new_tb_fallback,
        1,
    )
old_ref = (
    "            # 레이블(��게) | 입력(��게) | 오차���지 | 검토메시지\n"
    "            _la, _lb, _lc, _ld = st.columns([0.35, 0.5, 0.62, 2.05])\n"
)
new_ref = (
    "            # 레이블(��게)�게) |�지 | 검토메시지\n"
    "            if compact:\n"
    "                _la, _lb, _lc, _ld = st.columns([0.33, 0.46, 0.72, 1.74])\n"
    "            else:\n"
    "                _la, _lb, _lc, _ld = st.columns([0.35, 0.5, 0.62, 2.05])\n"
)
if old_ref not in t:
    raise SystemExit("old_ref missing")
t = t.replace(old_ref, new_ref, 1)
p.write_text(t, encoding="utf-8")
print("done")
