# -*- coding: utf-8 -*-
"""Insert _ag_theory_mm2 and _h_eff_and_cb_theory before the section preview block."""
path = "app.py"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

insert_at = None
for i, line in enumerate(lines):
    if line.startswith("def draw_section_preview"):
        j = i - 1
        while j >= 0 and lines[j].strip() == "":
            j -= 1
        while j >= 0 and lines[j].lstrip().startswith("#"):
            j -= 1
        insert_at = j + 1
        break

if insert_at is None:
    raise SystemExit("draw_section_preview not found")

blob = (
    "def _ag_theory_mm2(sec_type, b, h, poly_outer, poly_holes) -> float:\n"
    '    """Nominal gross area [mm^2] from geometry (for mesh convergence)."""\n'
    '    if sec_type == "\uc9c1\uc0ac\uac01\ud615":\n'
    "        return float(b * h)\n"
    '    if sec_type == "\uc6d0\ud615":\n'
    "        r = float(b) / 2.0\n"
    "        return math.pi * r * r\n"
    '    if sec_type == "\uc784\uc758 \ub2e4\uac01\ud615" and poly_outer is not None and len(poly_outer) >= 3:\n'
    "        holes = poly_holes or []\n"
    "        ps = PolygonSection(\n"
    "            np.asarray(poly_outer, dtype=float),\n"
    "            [np.asarray(h, dtype=float) for h in holes],\n"
    "        )\n"
    "        a = float(ps.outer.area())\n"
    "        for ho in ps.holes:\n"
    "            a -= float(ho.area())\n"
    "        return max(a, 0.0)\n"
    "    return float(b * h)\n"
    "\n\n"
    "def _h_eff_and_cb_theory(\n"
    "    section: FiberSection,\n"
    "    theta_rad: float,\n"
    "    ecu_val: float,\n"
    "    fyd_val: float,\n"
    "    sec_type: str,\n"
    "    b: float,\n"
    "    h: float,\n"
    ") -> tuple[float, float]:\n"
    '    """Effective d and theoretical balanced cb [mm] (verification tab logic)."""\n'
    "    _eyd = fyd_val / 200000.0\n"
    '    if sec_type == "\uc9c1\uc0ac\uac01\ud615" and abs(theta_rad) < 1e-9:\n'
    "        _y_prime_top_ref = float(h) / 2.0\n"
    "        _y_prime_bot_ref = -float(h) / 2.0\n"
    "    else:\n"
    "        _y_prime_top_ref, _y_prime_bot_ref = section.rotated_y_extremes(theta_rad)\n"
    "    _rb_yp_list = []\n"
    "    for _f in section.fibers:\n"
    "        if isinstance(_f.material, Rebar):\n"
    "            _yp = -_f.x * math.sin(theta_rad) + _f.y * math.cos(theta_rad)\n"
    "            _rb_yp_list.append((_yp, _f.area))\n"
    "    if _rb_yp_list:\n"
    "        _rb_yp_sorted = sorted(_rb_yp_list, key=lambda x: x[0])\n"
    "        _min_yp_rb = _rb_yp_sorted[0][0]\n"
    "        _dia_ref = 2 * math.sqrt(max(a for _, a in _rb_yp_list) / math.pi)\n"
    "        _tol_d = max(_dia_ref * 1.5, 30.0)\n"
    "        _tens_rb = [(yp, a) for yp, a in _rb_yp_list if yp <= _min_yp_rb + _tol_d]\n"
    "        _At_tot = sum(a for _, a in _tens_rb)\n"
    "        _yp_tens = sum(yp * a for yp, a in _tens_rb) / _At_tot if _At_tot > 0 else _min_yp_rb\n"
    "        _h_eff = _y_prime_top_ref - _yp_tens\n"
    "    else:\n"
    "        _h_eff = _y_prime_top_ref - _y_prime_bot_ref\n"
    "    _cb_est = ecu_val / (ecu_val + _eyd) * _h_eff\n"
    "    return _h_eff, _cb_est\n"
    "\n\n"
)

new_lines = lines[:insert_at] + [blob] + lines[insert_at:]
with open(path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)
print("ok")
