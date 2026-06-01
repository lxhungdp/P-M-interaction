# -*- coding: utf-8 -*-
from pathlib import Path

p = Path("app.py")
lines = p.read_text(encoding="utf-8").splitlines(keepends=True)
out = []
i = 0
while i < len(lines):
    line = lines[i]
    if line.startswith('                    f"※ ΣAc'):
        # skip until after st.caption closing )
        while i < len(lines) and not (
            lines[i].strip() == ")" and i > 0 and "st.caption" in lines[i - 2]
        ):
            i += 1
        if i < len(lines) and lines[i].strip() == ")":
            i += 1
        # also skip blank after caption if any
        continue
    if "st.caption(" in line and i + 2 < len(lines) and "Ag−ΣAs: gross" in lines[i + 1]:
        i += 4 # caption line, string line, ), blank?
        while i < len(lines) and lines[i].strip() in (")", ""):
            i += 1
        continue
    out.append(line)
    i += 1

p.write_text("".join(out), encoding="utf-8")
print("lines", len(lines), "->", len(out))
