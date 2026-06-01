# -*- coding: utf-8 -*-
from pathlib import Path

p = Path("app.py")
lines = p.read_text(encoding="utf-8").splitlines(keepends=True)
i_star = next(i for i, ln in enumerate(lines) if "※ ΣAc" in ln)
cs_idx = i_star - 2
if "fyd×As=" not in lines[cs_idx]:
    raise SystemExit("unexpected layout")
# remove f"� block, language line duplicate?, caption — from i_star-1 to closing ) of caption
j = i_star - 1
while j < len(lines) and "with _cr:" not in lines[j]:
    j += 1
if j >= len(lines):
    raise SystemExit("with _cr not found")
# lines[j] is '            with _cr:'
# delete [i_star-1 : j]  — removes f"\n" through st.caption )
del lines[i_star - 1 : j]
# add comma to Cs line (was ...\\n"  -> ...\\n",
cs = lines[cs_idx]
cs = cs.rstrip()
if cs.endswith('"'):
    cs = cs[:-1] + '",\n'
else:
    raise SystemExit("bad cs line", cs)
lines[cs_idx] = cs
lines.insert(cs_idx + 1, '                    language="")\n')
p.write_text("".join(lines), encoding="utf-8")
print("ok")
