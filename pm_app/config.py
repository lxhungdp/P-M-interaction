"""Application constants and page configuration."""

PAGE_CONFIG = {
    "page_title": "단면 P-M상관도 검토",
    "page_icon": "🏗️",
    "layout": "wide",
    "initial_sidebar_state": "collapsed",
}

VERIFY_REF_ERR_PCT = 3.0
MESH_AG_TOL = 1e-5
MESH_CB_TOL = 1e-5
MESH_NY_CAP = 900
MESH_MAX_ITER = 48

SESSION_DEFAULTS = {
    "show_preview": False,
    "inp_expand": True,
    "inp_width": 3,
}

APP_FOOTER = (
    "단면 P-M상관도 검토 v6.1  │  Fiber Section Analysis  │  "
    "KDS 24 14 21:2025 / ACI 318-19 / Eurocode 2"
)
