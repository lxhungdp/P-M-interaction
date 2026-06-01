# -*- coding: utf-8 -*-
from pathlib import Path

p = Path("app.py")
lines = p.read_text(encoding="utf-8").splitlines(keepends=True)
new = [
    '                        f" � 적용)={_cb_est:.1f}mm  ε_bot(��단)={eps_bal_bot:.6f}\n"',
    '                        f"\n"',
    '                        f"[��형점 파이버 상세]\n"',
    '                        f�크리트 {_nc_b}개: Ccb={_Ccb:.1f}kN\n"',
    '                        f"  ������근 {_ncs_b}개: Csb={_Csb:.1f}kN\n"',
    '                        f"    ������근 ε: min={_eps_csb_min*1000:.4f}‰ max={_eps_csb_max*1000:.4f}‰\n"',
    '                        f"    �� Csb: strip_concrete_overlapping_steel로 ����크리트 파이버 제거(이중면적 없음)\n"',
    '                        f"  인장��근·��연선 {_nt_b}개: Tb={_Tb:.1f}kN\n"',
    '                        f"  [Tb 개별 파이버]\n{_tb_detail_txt}\n"',
]
i0 = next(i for i, ln in enumerate(lines) if "cb=εcu/(εcu+εyd)×d=" in ln)
i1 = next(
    i for i, ln in enumerate(lines)
    if i > i0 and "{_nt_b}개: Tb=" in ln
)
lines[i0 : i1 + 1] = new
p.write_text("".join(lines), encoding="utf-8")
print("spliced", i0, i1)
