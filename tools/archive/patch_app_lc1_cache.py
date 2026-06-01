from pathlib import Path

p = Path("app.py")
lines = p.read_text(encoding="utf-8").splitlines(keepends=True)

ins = """        lc1_Pn_cap = lc1_Mn_cap = lc1_eps_bot = None
        if load_cases:
            _lc0 = load_cases[0]
            _Pu0 = float(_lc0.get("Pu [kN]", 0))
            _Mx0 = float(_lc0.get("Mx [kN·m]", 0))
            _My0 = float(_lc0.get("My [kN·m]", 0))
            _Mu0 = math.sqrt(_Mx0**2 + _My0**2)
            _N0 = np.asarray(N_des, float)
            _M0 = np.asarray(M_des, float)
            _Mr, _Pr = _ray_intersect_pm_curve(_Mu0, _Pu0, _M0, _N0)
            if _Mr is not None and abs(_Pu0) > 1e-6:
                lc1_Pn_cap = float(_Pr)
                lc1_Mn_cap = float(_Mr)
                lc1_eps_bot, _, _ = diagram_closest_strain_to_nm(
                    section, ecu_val, n_pts, theta_rad, 1.0, lc1_Pn_cap, lc1_Mn_cap)
            elif abs(_Pu0) > 1:
                _e_arr0 = np.where(_N0 > 10, _M0 / (_N0 + 1e-9), 1e12)
                _ix0 = int(np.argmin(np.abs(_e_arr0 - _Mu0 / (_Pu0 + 1e-9))))
                lc1_Pn_cap = float(_N0[_ix0])
                lc1_Mn_cap = float(_M0[_ix0])
                lc1_eps_bot, _, _ = diagram_closest_strain_to_nm(
                    section, ecu_val, n_pts, theta_rad, 1.0, lc1_Pn_cap, lc1_Mn_cap)
            else:
                lc1_Pn_cap = 0.0
                lc1_Mn_cap = float(_M0[int(np.argmax(_M0))])
                lc1_eps_bot, _, _ = diagram_closest_strain_to_nm(
                    section, ecu_val, n_pts, theta_rad, 1.0, lc1_Pn_cap, lc1_Mn_cap)

"""

idx = None
for i, ln in enumerate(lines):
    if ln.rstrip() == "            load_cases = []" and i > 0 and "except Exception" in lines[i - 1]:
        idx = i + 1
        break
if idx is None:
    raise SystemExit("insert point not found")

lines = lines[:idx] + [ins, "\n"] + lines[idx:]

text = "".join(lines)
old = "            n_pts=int(n_pts),\n            c_bal_mm=c_bal_mm,"
new = (
    "            n_pts=int(n_pts),\n"
    "            lc1_Pn_cap=lc1_Pn_cap, lc1_Mn_cap=lc1_Mn_cap, lc1_eps_bot=lc1_eps_bot,\n"
    "            c_bal_mm=c_bal_mm,"
)
if old not in text:
    raise SystemExit("dict pattern not found")
text = text.replace(old, new, 1)
p.write_text(text, encoding="utf-8")
print("lc1 cache ok")
