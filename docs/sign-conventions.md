# Sign conventions

These conventions are **load-bearing** for KDS checks and verification. Do not flip signs without updating golden tests and the verification tab.

## Axial force N

- **Compression is positive (+)**
- Tension is negative (−)

## Moment M

- Resultant moment direction **θ = atan2(My, Mx)** from load cases
- **y′ axis** (compression side) is perpendicular to neutral axis in the P-M plane
- Diagram uses **M = √(Mx² + My²)** projected onto the interaction plane

## Strain

- **Compression strain is positive (+)**
- Tension strain is negative (−)
- Plane sections remain plane: ε(y′) = ε₀ + κ·y′

## KDS material strength (ULS)

```
fcd = αcc × fck × Φc     # Φc = γc (e.g. 0.65) — multiply, not divide
fyd = fy × Φs
```

Do **not** use Eurocode-style `fck/γc` for KDS unless explicitly implementing EC2 path in `src/codes/`.

## Coordinates (section preview)

- **X →** horizontal (Mx ↔ bending about X)
- **Y ↑** vertical (My ↔ bending about Y)
- **y′** compression direction (dashed green arrow when M ≠ 0)

## Verification tab

Reference inputs are compared to engine output with relative error threshold `VERIFY_REF_ERR_PCT` (default 3%).

When adding formulas, match the **same sign** as `src/analysis/engine.py` and `src/analysis/solver.py`.
