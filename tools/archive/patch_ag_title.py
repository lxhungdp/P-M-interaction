# -*- coding: utf-8 -*-
path = "app.py"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, ln in enumerate(lines):
    if 'st.markdown("##### ①' in ln and "Pn,max" in ln:
        lines[i] = (
            '            st.markdown(f"#####① \ucd95\uc555\ucd95\uac15\ub3c4 \uac80\uc99d '
            '(Pn,max, \ucc38\uc870 \xb1{VERIFY_REF_ERR_PCT:.0f}%)")\n'
        )
        break

old = (
    '                    f"Ag(\uae30\ud558)={_Ag_geo:,.0f} mm\xb2  As(\ucca0\uadfc)='
    '{_As:,.0f} mm\xb2  \u03a3As(\ucca0\uadfc\xb7\uac15\uc5f0\uc120)='
    '{_As_steel_tot:,.0f} mm\xb2\\n"\n'
)
# read actual line from file for Ag
for i, ln in enumerate(lines):
    if "Ag(\uae30\ud558)=" in ln or "Ag(기하)=" in ln:
        lines[i] = (
            '                    f"Ag(\uc774\ub860\xb7\uc678\uacf1\uae30\ud558)='
            '{Ag_theory_cached:,.0f} mm\xb2\\n"\n'
        )
        lines[i + 1] = (
            '                    f"Ag(\uba54\uc2dc)=\u03a3\ud30c\uc774\ubc84\uba74\uc801='
            '{_Ag_mesh_tot:,.0f} mm\xb2 (=geo.A; ny \uc790\ub3d9\uc870\uc808\ub85c '
            '|\uc0c1\ub300\uc624\ucc28|\u22640.001%)\\n"\n'
        )
        lines[i + 2] = (
            '                    f"  As(\ucca0\uadfc)={_As:,.0f} mm\xb2  '
            '\u03a3As(\ucca0\uadfc\xb7\uac15\uc5f0\uc120)='
            '{_As_steel_tot:,.0f} mm\xb2\\n"\n'
        )
        lines[i + 3] = (
            '                    f"[\ucc38\uace0] \uc774\ub860\uc0c1 \uc21c\ucf58\ud06c\ub9ac\ud2b8 '
            'Ag(\uc774\ub860)\u2212\u03a3As={_Ac_theory:,.0f} mm\xb2\\n"\n'
        )
        break

for i, ln in enumerate(lines):
    if '_refs_1 = {}' in ln and i > 0 and "��조값" in lines[i - 1]:
        lines[i - 1] = (
            '                st.markdown(f"**\\U0001f4d6 \ucc38\uc870\uac12 '
            '(\uae30\ud638 \uff5c \uc785\ub825 \uff5c \uc624\ucc28\uc728, '
            '\xb1{VERIFY_REF_ERR_PCT:.0f}%)**")\n'
        )
        break

for i, ln in enumerate(lines):
    if 'st.markdown(f"##### ② {_lc1_name} 기준  (Pn, Mn�형상태 비교)")' in ln:
        lines[i] = (
            '            st.markdown(f"##### ② {_lc1_name} \uae30\uc900 '
            '(Pn, Mn + \uade0\ud615\uc0c1\ud0dc, \ucc38\uc870 '
            '\xb1{VERIFY_REF_ERR_PCT:.0f}%)")\n'
        )
        break

with open(path, "w", encoding="utf-8") as f:
    f.writelines(lines)
print("ok")
