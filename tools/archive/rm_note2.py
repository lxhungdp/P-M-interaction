# -*- coding: utf-8 -*-
from pathlib import Path

p = Path("app.py")
t = p.read_text(encoding="utf-8")
old = (
    '�고] 소계 ��근 fyd×As={fyd_val:.1f}×{_As:,.0f}={_Cs_hand:,.1f} kN (��연선 ��도)\\n"\n'
    '                    f"\\n"\n'
    '                    f"※ ΣAc≠Ag−ΣAs: 파이버 분할(ny)�라이스 ��적오차는 줄지만 스트립(중��±r+여유)\\n"\n'
    '                    f"  교과서식과 ��전히 일치하지 않을 수 있음. Pmax는 실제 파이버 적분값.\\n"\n'
    '                    f"※ Cc를 Ag−ΣAs로만 바���면 Nc+Ns≠Pmax가 되어 P-M 결과와 불일치.",\n'
    '                    language="")\n'
    '                st.caption(\n'
    '                    "Ag−ΣAs: gross concrete area (hand check). ΣAc(mesh): summed concrete fiber areas used in analysis. Finer mesh (ny↑) reduces slice discretization error, but strip-at-steel removal still differs from Ag−ΣAs. Using only Cc=fcd×(Ag−ΣAs) would break Nc+Ns=Pmax vs the P–M curve."\n'
    '                )\n'
)
new = (
    '�고] 소계 ��근 fyd×As={fyd_val:.1f}×{_As:,.0f}={_Cs_hand:,.1f} kN (��연선 ��도)\\n",\n'
    '                    language="")\n'
)
if old not in t:
    raise SystemExit("block not found")
p.write_text(t.replace(old, new, 1), encoding="utf-8")
print("ok")
