# Verification guide

## Manual (UI)

1. Run **P-M 상관도 계산** with known inputs.
2. Open tab **🔬 검증**.
3. Enter reference values (hand calc, textbook, other software).
4. Click update — green/orange badges show pass/fail vs `VERIFY_REF_ERR_PCT`.

## Automated (pytest)

### Layout

```
tests/
  conftest.py
  test_golden_pm.py
  golden/
    rect_400x600_kds30.yaml
```

### YAML schema

```yaml
id: rect_400x600_kds30
description: "400×600 rect, KDS 30 MPa, default rebar"
inputs:
  code_name: "KDS 24 14 21:2025"
  fck: 30
  fy: 400
  # ... all AnalysisInputs fields
expected:
  N_max_v:
    abs_tol: 50        # kN
  N_bal:
    rel_pct: 2.0
  skip: true           # remove when expected values confirmed
```

### Workflow for new cases

1. Run app with case inputs → note key outputs in verification tab.
2. Add YAML under `tests/golden/`.
3. Set `skip: false` when values are confirmed.
4. `pytest tests/test_golden_pm.py -v`

### CI suggestion

```bash
pytest tests/ -v --tb=short
```

Skip cases with `expected.skip: true` until manually verified.
