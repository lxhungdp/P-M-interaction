# -*- coding: utf-8 -*-
from pathlib import Path

p = Path("app.py")
lines = p.read_text(encoding="utf-8").splitlines(keepends=True)

for i, ln in enumerate(lines):
    if "cb=εcu/(εcu+εyd)×d=" in ln:
        lines[i] = (
            '                        f"  cb 적용)={_cb_est:.1f}mm '
            ' ε단)={eps_bal_bot:.6f}\n"'
        )
        if i + 1 < len(lines) and "cb_��진=" in lines[i + 1]:
            del lines[i + 1]
        break
else:
    raise SystemExit("cb line not found")

for i, ln in enumerate(lines):
    if���근 {_ncs_b}개: Csb=" in ln:
        lines.insert(
            i + 1,
            '                        f"���근 ε: min={_eps_csb_min*1000:.4f}‰ '
            'max={_eps_csb_max*1000:.4f}‰\n"',
        )
        lines.insert(
            i + 2,
            '                        f"    �� Csb: strip_concrete_overlapping_steel로 '
            '����크리트 파이버 제거(이중면적 없음)\n"',
        )
        break
else:
    raise SystemExit("Csb line not found")

for i, ln in enumerate(lines):
    if "인장��근 {_nt_b}개: Tb=" in ln:
        lines[i] = ln.replace("인장��근", "인장��근·��연선")
        lines.insert(
            i + 1,
            '                        f"  [Tb 개별 파이버]\n{_tb_detail_txt}\n"',
        )
        break
else:
    raise SystemExit("Tb line not found")

for i, ln in enumerate(lines):
    if "            _la, _lb, _lc, _ld = st.columns([0.35, 0.5, 0.62, 2.05])" in ln:
        indent = "            "
        lines[i] = indent + "if compact:\n"
        lines.insert(
            i + 1,
            indent + "    _la, _lb, _lc, _ld = st.columns([0.33, 0.46, 0.72, 1.74])\n",
        )
        lines.insert(
            i + 2,
            indent + "else:\n",
        )
        lines.insert(
            i + 3,
            indent + "    _la, _lb, _lc, _ld = st.columns([0.35, 0.5, 0.62, 2.05])\n",
        )
        break
else:
    raise SystemExit("ref columns not found")

for i, ln in enumerate(lines):
    if "if _tb_detail_lines else" in ln�음" in ln:
        lines[i] = (
            '        _tb_detail_txt = (\n'
            '            "\\n".join(_tb_detail_lines)\n'
            '            if _tb_detail_lines else '
            '"      (�연선 없음)")\n'
        )
        break

p.write_text("".join(lines), encoding="utf-8")
print("ok")
