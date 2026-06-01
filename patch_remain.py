# -*- coding: utf-8 -*-
path = "app.py"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# ① title (line 1667 in editor -> index 1666)
lines[1666] = (
    '            st.markdown(f"##### ① ��������도 검증 (Pn,max, 참조 ±{VERIFY_REF_ERR_PCT:.0f}%)")\n'
)
# Ag block in st.code (indices 1677-1679 for lines 1678-1680)
lines[1677] = (
    '                    f"Ag(이��·외��기하)={Ag_theory_cached:,.0f} mm²\\n"\n'
)
lines[1678] = (
    '                    f"Ag(메시)=Σ파이버면적={_Ag_mesh_tot:,.0f} mm² (=geo.A; '
    'ny�로 이�� 대비 |상대오차|≤0.001%)\\n"\n'
)
lines[1679] = (
    '                    f"  As(��근)={_As:,.0f} mm² �연선)='
    '{_As_steel_tot:,.0f} mm²\\n"\n'
)
lines[1680] = (
    '                    f"[��고] 이���크리트�)−ΣAs={_Ac_theory:,.0f} mm²\\n"\n'
)

# ① 참조값 header
for i, ln in enumerate(lines):
    if "**�� 참조값" in ln and "_refs_1" in lines[min(i + 1, len(lines) - 1)]:
        lines[i] = (
            '                st.markdown(f"**�� 참조값 (기호 │ 입력 │ 오차��, '
            '±{VERIFY_REF_ERR_PCT:.0f}%)**")\n'
        )
        break

#② LC1 title
for i, ln in enumerate(lines):
    if 'st.markdown(f"##### ② {_lc1_name} 기준' in ln:
        lines[i] = (
            '            st.markdown(f"##### ② {_lc1_name} 기준 (Pn, Mn + ��형상태, '
            '��조 ±{VERIFY_REF_ERR_PCT:.0f}%)")\n'
        )
        break

# Ag warn_ctxfor i, ln in enumerate(lines):
    if "warn_ctx=" in ln and "Ag(" in ln and "메시" in ln and "_refs_1" in "".join(
        lines[max(0, i - 3) : i]
    ):
        lines[i] = (
            '                         float(_Ag_mesh_tot), '
            'warn_ctx="�) vs Ag(메시)=Σ파이버")\n'
        )
        break

# _big block
for i, ln in enumerate(lines):
    if "if _verr(v[0],v[1]) is not None and abs(_verr(v[0],v[1])) >= 5" in ln:
        lines[i] = (
            "                    if _verr(v[0],v[1]) is not None\n"
            "                    and abs(_verr(v[0],v[1])) >= VERIFY_REF_ERR_PCT}\n"
        )
        # fix: the line was part of dict comprehension - need full two lines
        break

with open(path, "w", encoding="utf-8") as f:
    f.writelines(lines)
print("partial")
