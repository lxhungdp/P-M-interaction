# -*- coding: utf-8 -*-
path = "app.py"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, ln in enumerate(lines):
    if "_vh.markdown" in ln and "Verification" in ln:
        lines[i] = (
            '        _vh.markdown(f"### \uac80\uc99d (\ucc38\uc870 \uc624\ucc28 '
            '\xb1{VERIFY_REF_ERR_PCT:.0f}%)")\n'
        )
    if "pm-verify-msg" in ln and "padding-top:8px;color:#C62828;" in ln:
        lines[i] = ln.replace(
            "padding-top:8px;color:#C62828;",
            "padding-top:{_pt};color:#C62828;line-height:1.15;",
        )
    if "pm-verify-msg" in ln and "padding-top:8px;color:#2E7D32;" in ln:
        lines[i] = ln.replace(
            "padding-top:8px;color:#2E7D32;",
            "padding-top:{_pt};color:#2E7D32;line-height:1.15;",
        )
with open(path, "w", encoding="utf-8") as f:
    f.writelines(lines)
print("ok")
