# -*- coding: utf-8 -*-
from pathlib import Path
p = Path("app.py")
t = p.read_text(encoding="utf-8")
old = '''                    f"\\n"
                    f"※ ΣAc≠Ag−ΣAs: 파이버 분할(ny)↑이면 ���적오차는 줄지만 스트립(중��±r+여유)\\n"
                    f"  교과�전히 일치하지 않을 수 있음. Pmax는 실제 파이버 적분값.\\n"
                    f"※ Cc를 Ag−ΣAs로만 바���면 Nc+Ns≠Pmax가 되어 P-M 결과와 불일치.",
                    language="")
                st.caption(
                    "Ag−ΣAs: gross concrete area (hand check). ΣAc(mesh): summed concrete fiber areas used in analysis. Finer mesh (ny↑) reduces slice discretization error, but strip-at-steel removal still differs from Ag−ΣAs. Using only Cc=fcd×(Ag−ΣAs) would break Nc+Ns=Pmax vs the P–M curve."
                )
'''
new = '''                    language="")
'''
# fix: we need to keep closing of st.code - the old ends with language="") - the replacement should be
# remove f"\\n" before� as well - include line 1711 f"\\n"

old2 = '''                    f"\\n"
                    f"※ ΣAc≠Ag−ΣAs: 파이버 분할(ny)↑이면 ���적오차는 줄지만 스트립(중��±r+여유)\\n"
                    f"  교과서식과 ��전히 일치하지 않을 수 있음. Pmax는 실제 파이버 적분값.\\n"
                    f"※ Cc를 Ag−ΣAs로만 바���면 Nc+Ns≠Pmax가 되어 P-M 결과와 불일치.",
                    language="")
                st.caption(
                    "Ag−ΣAs: gross concrete area (hand check). ΣAc(mesh): summed concrete fiber areas used in analysis. Finer mesh (ny↑) reduces slice discretization error, but strip-at-steel removal still differs from Ag−ΣAs. Using only Cc=fcd×(Ag−ΣAs) would break Nc+Ns=Pmax vs the P–M curve."
                )
'''
if old2 not in t:
    raise SystemExit("not found")
p.write_text(t.replace(old2, "",1), encoding="utf-8")
print("ok")
