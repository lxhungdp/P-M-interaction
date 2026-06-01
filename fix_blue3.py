# -*- coding: utf-8 -*-
path = "app.py"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()
for i, ln in enumerate(lines):
    if '_blue("' in ln and "주요" in ln and "5%" in ln and "미만" in ln:
        lines[i] = (
            '                _blue(f"\u2705 \uc8fc\uc694 \ud56d\ubaa9 \uc624\ucc28 '
            "{VERIFY_REF_ERR_PCT:.0f}% \ubbf8\ub9cc\")\n"
        )
    if "_blue(f" in ln and "len(_big)" in ln and "항목 오차" in ln and "5%" in ln:
        lines[i] = (
            '                _blue(f"\u274c {len(_big)}\uac1c \ud56d\ubaa9 \uc624\ucc28 '
            "\u2265{VERIFY_REF_ERR_PCT:.0f}%\")\n"
        )
with open(path, "w", encoding="utf-8") as f:
    f.writelines(lines)
print("ok")
