# -*- coding: utf-8 -*-
from pathlib import Path

p = Path("app.py")
lines = p.read_text(encoding="utf-8").splitlines(keepends=True)
# 1-based line numbers from read_file: replace 1762-1771
start, end = 1761, 1771  # 0-based inclusive start, exclusive end for slice
chunk_old = "".join(lines[start:end])
if "[��형 중립��]" not in chunk_old:
    raise SystemExit("wrong slice", chunk_old[:80])
new_block = """                        f"[���]\\n"
                        f"  εcu={ecu_val:.6f}({ecu_val*1e3:.3f}‰)\\n"
                        f"  εyd={_eyd:.6f}({_eyd*1e3:.4f}‰)\\n"
                        f"  cb(이�� 적용)={_cb_est:.1f}mm  ε_bot(��단)={eps_bal_bot:.6f}\\n"
                        f"\\n"
�형점 파이버 상세]\\n"
                        f"  ���크리트 {_nc_b}개: Ccb={_Ccb:.1f}kN\\n"
                       �근 {_ncs_b}개: Csb={_Csb:.1f}kN\\n"
                        f"    ������근 ε: min={_eps_csb_min*1000:.4f}‰ max={_eps_csb_max*1000:.4f}‰\\n"
                        f"    �� Csb: strip_concrete_overlapping_steel로 ��근 위치 ���크리트 파이버 제거(이중면적 없음)\\n"
                        f"  인장��근·��연선 {_nt_b}개: Tb={_Tb:.1f}kN\\n"
                        f"  [Tb 개별 파이버]\\n{_tb_detail_txt}\\n"
"""
lines[start:end] = [new_block]
p.write_text("".join(lines), encoding="utf-8")
print("lc1 code ok")
