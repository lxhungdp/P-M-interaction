# -*- coding: utf-8 -*-
from pathlib import Path
t = Path("app.py").read_text(encoding="utf-8")
needle = "\uc18c\uacc4 \ucca0\uadfc"
i = t.index(needle)
# back to start of f-string line
j = t.rfind("f\"", 0, i)
print(repr(t[j : j + 900]))
