# -*- coding: utf-8 -*-
path = "app.py"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

start, end = 1756, 1833
fig_start, fig_end = 1761, 1801
ref_start, ref_end = 1804, 1832

fig_lines = lines[fig_start:fig_end]
ref_lines = lines[ref_start:ref_end]


def add_compact(s):
    s = s.rstrip("\n")
    if "compact=True" in s or "_refs_2 = {}" in s:
        return s + "\n"
    if s.strip().startswith("_ref_row(") and s.rstrip().endswith(")"):
        return s[:-1] + ", compact=True)\n"
    return s + "\n"


ref_new = [add_compact(l) for l in ref_lines]

_em = chr(0x1F4D6)
_hdr2 = (
    f'                    f"**{_em} \ucc38\uc870\uac12 (\uae30\ud638 \uff5c \uc785\ub825 \uff5c '
    f'\uc624\ucc28\uc728, \xb1{{VERIFY_REF_ERR_PCT:.0f}}%)**")\n'
)

header = [
    "            with _cr:\n",
    "                _yt_d = float(_y_prime_top_ref)\n",
    "                _yb_d = float(_yp_tens_ui)\n",
    "                st.markdown(\n",
    _hdr2,
    "                _cct, _ccr = st.columns([1.42, 0.88])\n",
    "                with _cct:\n",
]
ref_indented = ["    " + ln for ln in ref_new]

fig_adj = []
for ln in fig_lines:
    if "figsize=(2.45, 1.12)" in ln:
        ln = ln.replace("figsize=(2.45, 1.12)", "figsize=(1.225, 0.56)")
    if ln.strip() == "st.pyplot(_fig_d)":
        ln = ln.replace("st.pyplot(_fig_d)", "st.pyplot(_fig_d, use_container_width=True)")
    fig_adj.append("    " + ln)

new_block = header + ref_indented + ["                with _ccr:\n"] + fig_adj + ["\n"]

if "with _cr:" not in lines[start]:
    raise SystemExit("anchor mismatch")
lines[start:end] = new_block
with open(path, "w", encoding="utf-8") as f:
    f.writelines(lines)
print("ok")
