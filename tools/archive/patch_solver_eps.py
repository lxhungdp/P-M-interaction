# -*- coding: utf-8 -*-
from pathlib import Path

ins = """

def eps_bot_from_compression_depth(
    c_mm: float,
    y_top_r: float,
    y_bot_r: float,
    ecu: float,
    clip_tension: Optional[float] = None,
) -> float:
    \"\"\"Compression depth c from y_top to NA -> strain at extreme y_bot.\"\"\"
    eb = _c_to_eps_bot(c_mm, y_top_r, y_bot_r, ecu)
    if clip_tension is not None:
        eb = max(eb, -float(clip_tension))
    return float(min(eb, ecu * (1.0 - 1e-12)))

"""

p = Path("src/analysis/solver.py")
t = p.read_text(encoding="utf-8")
marker = "    return ecu * h_eff / delta\n\n"
k = t.find(marker)
if k < 0:
    raise SystemExit("marker not found")
insert_pos = k + len(marker)
t2 = t[:insert_pos] + ins + t[insert_pos:]
p.write_text(t2, encoding="utf-8")
print("patched")
