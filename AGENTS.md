# AGENTS.md — AI assistant guide for 01-PM

## Project purpose

Web tool for **concrete column P-M interaction diagram** review using **fiber section analysis**.
Primary code: **KDS 24 14 21:2025**; also ACI 318-19 and Eurocode 2.

## Run

```bash
pip install -r requirements.txt
streamlit run app.py
pytest tests/ -v
```

## Layout (do not break)

```
app.py                 # Thin Streamlit entry (~60 lines)
pm_app/
  config.py            # Constants, page config
  models.py            # AnalysisInputs dataclass
  section_builder.py   # Mesh + rebar layout
  pm_checks.py         # Capacity / utilization helpers
  pipeline.py          # run_pm_analysis() — core orchestration
  viz/section_draw.py  # Matplotlib section plots
    ui/
    assets.py          # CSS/JS injection
    context.py           # OutputContext, VerifyContext
    panel_input.py       # Left input panel
    panel_output.py      # Right output shell + tab dispatch
    tabs/                # tab_pm, tab_section, tab_strain, tab_geometry, tab_detail, tab_verify
src/                   # Engine (analysis, geometry, materials, codes)
tests/golden/          # YAML regression cases
docs/                  # Architecture, sign conventions, verification
```

## Where to change what

| Task | Edit |
|------|------|
| New design code | `src/codes/` |
| Fiber / P-M engine | `src/analysis/`, `src/section/` |
| Mesh / rebar layout | `pm_app/section_builder.py` |
| Analysis flow | `pm_app/pipeline.py` |
| Streamlit widgets | `pm_app/ui/panel_input.py` |
| Result tabs 1–5 | `pm_app/ui/panel_output.py` |
| Verification tab | `pm_app/ui/tabs/tab_verify.py` |
| Page shell only | `app.py` |

## Hard rules

1. **Never add `patch_*.py` / `fix_*.py` at repo root.** Edit source modules directly.
2. **No debug `print()` in mesh loops** — use logging if needed.
3. **Keep `app.py` thin** — business logic belongs in `pm_app/` or `src/`.
4. **Preserve sign conventions** — see `docs/sign-conventions.md`.
5. **KDS material factors**: `fcd = αcc × fck × Φc` (multiply γc), not EC2-style divide.
6. **Golden tests before large refactors** — add/update `tests/golden/*.yaml`.
7. **UI text is Korean** — keep existing labels unless user asks to change.

## Sign conventions (critical)

- **N**: compression positive (+)
- **M**: per app coordinate system (θ from Mx/My)
- **Strain**: compression positive (+)
- **y′**: compression fiber direction (from θ)

## Verification workflow

1. Run analysis in app → **검증** tab.
2. Compare engine values vs manual reference inputs.
3. Error badge threshold: `VERIFY_REF_ERR_PCT` (3%) in `pm_app/config.py`.
4. Automate with `tests/golden/` + `pytest`.

## Adding a golden test

1. Copy `tests/golden/rect_400x600_kds30.yaml`.
2. Fill `inputs` from a confirmed manual run.
3. Fill `expected` with tolerances (`abs`, `rel_pct`).
4. Run `pytest tests/test_golden_pm.py -k <case_id> -v`.

## Cursor rules

See `.cursor/rules/` for file-scoped guidance:

- `pm-core.mdc` — architecture (always apply)
- `pm-formulas.mdc` — `src/analysis`, `src/codes`
- `pm-streamlit.mdc` — `pm_app/ui/`, `app.py`
- `no-patch-scripts.mdc` — ban root patch scripts

## Archive

Legacy monolith and one-off scripts: `tools/archive/` (not imported at runtime).
