"""P-M curve safety checks and geometric helpers."""

from __future__ import annotations

import numpy as np


def m_cap(N_u, N_half, M_half):
    try:
        order = np.argsort(N_half)
        return abs(float(np.interp(N_u, N_half[order], M_half[order])))
    except Exception:
        return 0.0


def is_safe(N_u, M_u, N_half, M_half):
    if N_u > max(N_half) + 1e-3 or N_u < min(N_half) - 1e-3:
        return False
    return abs(M_u) <= m_cap(N_u, N_half, M_half)


def utilization(N_u, M_u, N_half, M_half):
    mc = m_cap(N_u, N_half, M_half)
    return abs(M_u) / mc if mc > 1e-6 else float("inf")


def p0_point(N_half, M_half):
    for i in range(len(N_half) - 1):
        n0, n1 = N_half[i], N_half[i + 1]
        if n0 * n1 <= 0 and abs(n0 - n1) > 1e-9:
            t = -n0 / (n1 - n0)
            return M_half[i] + t * (M_half[i + 1] - M_half[i]), 0.0
    idx = int(np.argmin(np.abs(N_half)))
    return M_half[idx], N_half[idx]


def ray_intersect_pm_curve(M_lc, N_lc, M_arr, N_arr):
    """Intersection of ray from origin along (M_lc, N_lc) with P-M curve."""
    if abs(M_lc) < 1e-6:
        return 0.0, float(np.max(N_arr))
    results = []
    for i in range(len(M_arr) - 1):
        M0, N0 = float(M_arr[i]), float(N_arr[i])
        dM = float(M_arr[i + 1]) - M0
        dN = float(N_arr[i + 1]) - N0
        det = -dM * N_lc + M_lc * dN
        if abs(det) < 1e-15:
            continue
        s = (M0 * N_lc - M_lc * N0) / det
        t = (-dM * N0 + M0 * dN) / det
        if -1e-9 <= s <= 1.0 + 1e-9 and t > 0.01:
            results.append((t, M0 + s * dM, N0 + s * dN))
    if not results:
        return None, None
    results.sort(key=lambda r: abs(r[0] - 1.0))
    return results[0][1], results[0][2]


def half_pm_curve(pm_list):
    """Positive-moment half of PM diagram as (N_array, M_array)."""
    pts = sorted([(p.N_kN, p.M_kNm) for p in pm_list if p.M_kNm >= -1e-3], key=lambda x: -x[0])
    return np.array([x[0] for x in pts]), np.array([x[1] for x in pts])
