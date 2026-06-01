# -*- coding: utf-8 -*-
path = "app.py"
with open(path, "r", encoding="utf-8") as f:
    t = f.read()
a = '_blue("\u2705 \uc8fc\uc694 \ud56d\ubaa9 \uc624\ucc28 5% \ubbf8\ub9cc")'
b = '_blue(f"\u2705 \uc8fc\uc694 \ud56d\ubaa9 \uc624\ucc28 {VERIFY_REF_ERR_PCT:.0f}% \ubbf8\ub9cc")'
c = '_blue(f"\u274c {len(_big)}\uac1c \ud56d\ubaa9 \uc624\ucc28 \u2265{VERIFY_REF_ERR_PCT:.0f}%")'
# second line has len(_big) - need different approach
t = t.replace(
    '_blue("\u2705 \uc8fc\uc694 \ud56d\ubaa9 \uc624\ucc28 5% \ubbf8\ub9cc")',
    '_blue(f"\u2705 \uc8fc\uc694 \ud56d\ubaa9 \uc624\ucc28 {VERIFY_REF_ERR_PCT:.0f}% \ubbf8\ub9cc")',
    1,
)
t = t.replace(
    '_blue(f"\u274c {len(_big)}\uac1c \ud56d\ubaa9 \uc624\ucc28 \u22655%")',
    '_blue(f"\u274c {len(_big)}\uac1c \ud56d\ubaa9 \uc624\ucc28 \u2265{VERIFY_REF_ERR_PCT:.0f}%")',
    1,
)
with open(path, "w", encoding="utf-8") as f:
    f.write(t)
print("ok")
