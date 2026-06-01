# -*- coding: utf-8 -*-
path = "app.py"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()
# LC1 _ref_row continuation lines (0-based ~1767-1792)
for i in range(1766, min(1793, len(lines))):
    ln = lines[i]
    if "warn_ctx=" in ln and ln.rstrip().endswith(")") and "compact=True" not in ln:
        lines[i] = ln.rstrip()[:-1] + ", compact=True)\n"
with open(path, "w", encoding="utf-8") as f:
    f.writelines(lines)
print("ok")
