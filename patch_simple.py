# -*- coding: utf-8 -*-
path = "app.py"
with open(path, "r", encoding="utf-8") as f:
    t = f.read()

t = t.replace(
    'st.markdown("���도 검증  (Pn,max)")',
    'st.markdown(f"##### �도 검증 (Pn,max, 참조 ±{VERIFY_REF_ERR_PCT:.0f}%)")',
    1,
)

old_ag = (
    '                    f"Ag(기하)={_Ag_geo:,.0f} mm²  As(��근)={_As:,.0f} mm²  ΣAs(��근·��연선)={_As_steel_tot:,.0f} mm²\\n"\n'
    '                    f"[����크리트 Ag−ΣAs={_Ac_theory:,.0f} mm²\\n"'
)
new_ag = (
    '                    f"Ag(이��·외��기하)={Ag_theory_cached:,.0f} mm²\\n"\n'
    '                    f"Ag(메시)=Σ파이버면적={_Ag_mesh_tot:,.0f} mm² (=geo.A; ny 자동조��로 |상대오차|≤0.001%)\\n"\n'
    '                    f"�근)={_As:,.0f} mm²  ΣAs(��근·��연선)={_As_steel_tot:,.0f} mm²\\n"\n'
    '                    f"[��고] 이���크리트�)−ΣAs={_Ac_theory:,.0f} mm²\\n"'
)
if old_ag not in t:
    raise SystemExit("old_ag block missing")
t = t.replace(old_ag, new_ag, 1)

t = t.replace(
    'st.markdown("**�� 참조값  (기호 │ 입력�)**")\n                _refs_1 = {}',
    'st.markdown(f"**�� 참조값 (기호 │ 입력 │ 오차��, ±{VERIFY_REF_ERR_PCT:.0f}%)**")\n                _refs_1 = {}',
    1,
)

t = t.replace(
    'st.markdown(f"##### ② {_lc1_name} 기준  (Pn, Mn + ��형상태 비교)")',
    'st.markdown(f"##### ② {_lc1_name} 기준 (Pn, Mn + ��형상태, 참조 ±{VERIFY_REF_ERR_PCT:.0f}%)")',
    1,
)

t = t.replace(
    'warn_ctx="Ag(이��) vs Ag(메시)=Σ파이버"',
    'warn_ctx="Ag(이��) vs Ag(메시)=Σ파이버"',
    1,
)

old_big = (
    '            _big = {k: _verr(v[0],v[1]) for k,v in _all_refs.items()\n'
    '                    if _verr(v[0],v[1]) is not None and abs(_verr(v[0],v[1])) >= 5}\n'
    '            if not _big:\n'
    '                _blue("�� 주요 ��목 오차 5% 미만")\n'
    '            else:\n'
    '                _blue(f"�� {len(_big)}개 ��목 오차 ≥5%")'
)
new_big = (
    '            _big = {k: _verr(v[0],v[1]) for k,v in _all_refs.items()\n'
    '                    if _verr(v[0],v[1]) is not None\n'
    '                    and abs(_verr(v[0],v[1])) >= VERIFY_REF_ERR_PCT}\n'
    '            if not _big:\n'
    '                _blue(f"�� 주요 ��목 오차 {VERIFY_REF_ERR_PCT:.0f}% 미만")\n'
    '            else:\n'
    '                _blue(f"�� {len(_big)}개 ��목 오차 ≥{VERIFY_REF_ERR_PCT:.0f}%")'
)
if old_big not in t:
    raise SystemExit("old_big missing")
t = t.replace(old_big, new_big, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(t)
print("ok")
