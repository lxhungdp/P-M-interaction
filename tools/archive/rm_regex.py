# -*- coding: utf-8 -*-
from pathlib import Path

p = Path("app.py")
t = p.read_text(encoding="utf-8")
a = t.find('                    f"\\n"\n                    f"※')
if a < 0:
    raise SystemExit("start not found")
b = t.find("                )\n            with _cr:", a)
if b < 0:
    raise SystemExit("end not found")
# include st.caption before with _cr
c = t.rfind("st.caption(", a, b)
if c < 0:
    chunk = t[a:b]
    p.write_text(t[:a] + t[b:], encoding="utf-8")
else:
    d = t.find("                )\n", c) + len("                )\n")
    p.write_text(t[:a] + t[d:], encoding="utf-8")
print("removed")
