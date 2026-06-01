# -*- coding: utf-8 -*-
from pathlib import Path

lines = Path("app.py").read_text(encoding="utf-8").splitlines()
for i in range(1758, 1775):
    print(i + 1, lines[i][:100])
