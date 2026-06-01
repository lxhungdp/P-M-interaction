# -*- coding: utf-8 -*-
path = "app.py"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

lines[1666] = (
    '            st.markdown(f"���도 검증 (Pn,max, 참조 ±{VERIFY_REF_ERR_PCT:.0f}%")\n'
)
lines[1677] = (
    '                    f"Ag(이��·외��기하)={Ag_theory_cached:,.0f} mm²\\n"\n'
)
lines[1678] = (
    '                    f"Ag(메시)=Σ파이버면적={_Ag_mesh_tot:,.0f} mm² (=geo.A; '
    'ny�로 |상대오차|≤0.001%)\\n"\n'
)
lines[1679] = (
    '                    f"  As(��근)={_As:,.0f} mm² �연선)='
    '{_As_steel_tot:,.0f} mm²\\n"\n'
)
lines[1680] = (
    '                    f"[����크리트 Ag(이��)−ΣAs={_Ac_theory:,.0f} mm²\\n"\n'
)

for i, ln in enumerate(lines):
    if ln.strip() == 'st.markdown("**�� 참조값  (기호 │ 입력 │ 오차��)**")' and "_refs_1" in lines[i + 1]:
        lines[i] = (
            '                st.markdown(f"**�� 참조값 (기호 │ 입력 │ 오차��, '
            '±{VERIFY_REF_ERR_PCT:.0f}%)**")\n'
        )
        break

for i, ln in enumerate(lines):
    if 'st.markdown(f"##### ② {_lc1_name} 기준  (Pn, Mn + ��형상태 비교)")' in ln:
        lines[i] = (
            '            st.markdown(f"##### ② {_lc1_name} 기준 (Pn, Mn + ��형상태, '
            '��조 ±{VERIFY_REF_ERR_PCT:.0f}%)")\n'
        )
        break

for i, ln in enumerate(lines):
    if "warn_ctx=" in ln and "Ag(" in ln and "메시" in ln:
        if "이��" in ln:
            continue
        lines[i] = (
            '                         float(_Ag_mesh_tot), '
            'warn_ctx="Ag(이��·외��기하) vs Ag(메시)=Σ파이버")\n'
        )
        break

# _big
for i, ln in enumerate(lines):
    if "abs(_verr(v[0],v[1])) >= 5}" in ln:
        lines[i] = (
            "                    and abs(_verr(v[0],v[1])) >= VERIFY_REF_ERR_PCT}\n"
        )
        # broken - the line is part of comprehension        break

with open(path, "w", encoding="utf-8") as f:
    f.writelines(lines)
print("lines patched")
