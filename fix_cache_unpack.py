# -*- coding: utf-8 -*-
path = "app.py"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()
needle = '    ecu_val=_cache["ecu_val"]; Ec_val=_cache["Ec_val"]\n'
insert = needle + (
    "    ny_fiber_used = int(_cache.get(\"ny_fiber_used\", 120))\n"
    "    ny_fiber_req = _cache.get(\"ny_fiber_req\")\n"
    "    mesh_warn_msg = _cache.get(\"mesh_warn\")\n"
    "    Ag_theory_cached = float(_cache.get(\"Ag_theory\", _ag_theory_mm2(\n"
    "        sec_type, b, h, poly_outer, poly_holes)))\n"
    "\n"
    "    if mesh_warn_msg:\n"
    "        st.warning(mesh_warn_msg)\n"
    "    if ny_fiber_req is not None and int(ny_fiber_req) != ny_fiber_used:\n"
    "        st.caption(\n"
    "            f\"Fiber ny: requested {int(ny_fiber_req)} -> analysis {ny_fiber_used} \"\n"
    "            f\"(auto-tuned for Ag & cb rel.err. <= 0.001%).\")\n"
    "\n"
)
text = "".join(lines)
if needle not in text:
    raise SystemExit("needle missing")
text = text.replace(needle, insert, 1)
with open(path, "w", encoding="utf-8") as f:
    f.write(text)
print("ok")
