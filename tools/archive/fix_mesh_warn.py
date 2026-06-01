# -*- coding: utf-8 -*-
path = "app.py"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()
start = None
for i, ln in enumerate(lines):
    if ln.strip() == "if _ny_cur >= _ny_cap:":
        start = i
        break
if start is None:
    raise SystemExit("start not found")
end = start
while end < len(lines) and not lines[end].strip().startswith(
    "geo        = section.geometric_properties"
):
    end += 1
chunk = [
    "                if _ny_cur >= _ny_cap:\n",
    "                    mesh_warn = (\n",
    '                        f"ny={_ny_cap} max: Ag/cb rel.err. still above 0.001% "\n',
    '                        f"(Ag {ag_err_r*100:.5f}%, cb {cb_err_r*100:.5f}%)."\n',
    "                    )\n",
    "                    break\n",
    "                _ny_try = _ny_cur + max(8, _ny_cur // 10)\n",
    "            else:\n",
    "                mesh_warn = (\n",
    '                    "Mesh auto-tune iteration limit; increase ny in solver settings."\n',
    "                )\n",
    "\n",
]
lines = lines[:start] + chunk + lines[end:]
with open(path, "w", encoding="utf-8") as f:
    f.writelines(lines)
print("ok")
