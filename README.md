# 01-PM — Concrete Column P-M Interaction Diagram

Fiber-section web tool for reviewing **P-M interaction diagrams** of reinforced concrete columns.

## Features

- Rectangular, circular, and arbitrary polygon sections
- KDS 2025 (primary), ACI 318-19, Eurocode 2
- Fiber mesh with auto-tuned `ny` (Ag/cb convergence)
- P-M diagram, strain visualization, geometry summary, verification tab
- Load cases with automatic θ from Mx/My

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
streamlit run app.py
```

Open `http://localhost:8501`. Use **P-M 상관도 계산** or **Ctrl+S**.

## Tests

```bash
pytest tests/ -v
```

Golden cases live in `tests/golden/*.yaml`. Fill `expected` values after manual confirmation in the verification tab.

## Project structure

```
app.py              Entry point (Streamlit)
pm_app/             App layer (UI + pipeline)
src/                Analysis engine
tests/golden/       Regression YAML cases
docs/               Architecture & conventions
AGENTS.md           Guide for AI assistants
```

## For developers / AI

Read **AGENTS.md** and **docs/** before changing formulas or UI.
Do not create root-level `patch_*.py` scripts — edit modules directly.

## License

Internal / project use — see repository owner.
