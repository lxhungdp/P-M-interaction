"""
2D 단면 형상 정의

임의 다각형(Hole 포함), 직사각형, 원형 단면을 지원합니다.
Fiber 이산화(discretization)를 위한 그리드 분할 로직도 포함합니다.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np


# ══════════════════════════════════════════════════════════════════════
# 기본 다각형
# ══════════════════════════════════════════════════════════════════════
@dataclass
class Polygon:
    """
    2D 다각형 (임의 꼭짓점 배열)

    Attributes:
        vertices: 꼭짓점 좌표 배열 [(x1,y1), (x2,y2), ...], 반시계 방향 권장
    """
    vertices: np.ndarray  # shape (N, 2)

    def __post_init__(self):
        self.vertices = np.asarray(self.vertices, dtype=float)

    # ── 기하 속성 ────────────────────────────────────────────────────
    def area(self) -> float:
        """Shoelace (Gauss) 공식으로 넓이 계산"""
        x, y = self.vertices[:, 0], self.vertices[:, 1]
        return 0.5 * abs(
            np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1))
        )

    def centroid(self) -> Tuple[float, float]:
        """도심 좌표 (cx, cy)"""
        x, y = self.vertices[:, 0], self.vertices[:, 1]
        xn, yn = np.roll(x, -1), np.roll(y, -1)
        cross = x * yn - xn * y
        A = np.sum(cross) / 2.0
        cx = np.sum((x + xn) * cross) / (6.0 * A)
        cy = np.sum((y + yn) * cross) / (6.0 * A)
        return (cx, cy)

    def bounding_box(self) -> Tuple[float, float, float, float]:
        """(xmin, ymin, xmax, ymax)"""
        mn = self.vertices.min(axis=0)
        mx = self.vertices.max(axis=0)
        return mn[0], mn[1], mx[0], mx[1]

    def contains_point(self, px: float, py: float) -> bool:
        """Ray-casting 알고리즘으로 점 포함 여부 판별"""
        verts = self.vertices
        n = len(verts)
        inside = False
        j = n - 1
        for i in range(n):
            xi, yi = verts[i]
            xj, yj = verts[j]
            if ((yi > py) != (yj > py)) and (
                px < (xj - xi) * (py - yi) / (yj - yi) + xi
            ):
                inside = not inside
            j = i
        return inside

    # ── 이산화 ───────────────────────────────────────────────────────
    def discretize(
        self,
        nx: int = 20,
        ny: int = 100,
        holes: Optional[List["Polygon"]] = None,
    ) -> List[Tuple[float, float, float]]:
        """
        다각형을 격자 셀(fiber)로 분할합니다.

        Args:
            nx, ny: 수평·수직 셀 수
            holes : 내부 구멍 다각형 목록 (제외 영역)

        Returns:
            List of (x_centroid, y_centroid, area) for each fiber
        """
        xmin, ymin, xmax, ymax = self.bounding_box()
        dx = (xmax - xmin) / nx
        dy = (ymax - ymin) / ny
        cell_area = dx * dy
        fibers = []

        for j in range(ny):
            yc = ymin + (j + 0.5) * dy
            for i in range(nx):
                xc = xmin + (i + 0.5) * dx
                if not self.contains_point(xc, yc):
                    continue
                if holes and any(h.contains_point(xc, yc) for h in holes):
                    continue
                fibers.append((xc, yc, cell_area))

        return fibers


# ══════════════════════════════════════════════════════════════════════
# 편의 팩토리 함수
# ══════════════════════════════════════════════════════════════════════
def make_rectangle(b: float, h: float, cx: float = 0.0, cy: float = 0.0) -> Polygon:
    """
    직사각형 단면 생성 (도심 기준)

    Args:
        b, h: 폭, 높이 [mm]
        cx, cy: 도심 좌표 (기본 원점)
    """
    x0, y0 = cx - b / 2, cy - h / 2
    return Polygon(
        np.array([
            [x0,     y0    ],
            [x0 + b, y0    ],
            [x0 + b, y0 + h],
            [x0,     y0 + h],
        ])
    )


def make_circle(radius: float, cx: float = 0.0, cy: float = 0.0, n_seg: int = 64) -> Polygon:
    """원형 단면을 n_seg 각형으로 근사"""
    angles = np.linspace(0, 2 * math.pi, n_seg, endpoint=False)
    verts = np.column_stack([
        cx + radius * np.cos(angles),
        cy + radius * np.sin(angles),
    ])
    return Polygon(verts)


def make_T_section(
    bf: float, tf: float, bw: float, hw: float
) -> Polygon:
    """
    T형 단면 (도심 기준 아님, 하단 좌측 모서리 = 원점 기준)

    Args:
        bf: 플랜지 폭, tf: 플랜지 두께
        bw: 복부 폭, hw: 복부 높이
    """
    x_offset = (bf - bw) / 2
    verts = np.array([
        [0,          0       ],
        [bf,         0       ],
        [bf,         tf      ],
        [x_offset + bw, tf  ],
        [x_offset + bw, tf + hw],
        [x_offset,   tf + hw],
        [x_offset,   tf     ],
        [0,          tf     ],
    ])
    return Polygon(verts)


# ══════════════════════════════════════════════════════════════════════
# 철근/강연선 위치 계산 헬퍼
# ══════════════════════════════════════════════════════════════════════
def rebar_positions_rect(
    b: float,
    h: float,
    cover: float,
    n_top: int,
    n_bot: int,
    n_side_per_face: int = 0,
    bar_dia: float = 25.0,
) -> List[Tuple[float, float]]:
    """
    직사각형 단면의 철근 위치 목록 반환 (도심 원점 기준)

    y축 상향 양수, 압축 = 단면 상단(y = +h/2 방향)

    Returns:
        List of (x, y) 좌표 [mm]
    """
    positions = []
    # cover: surface to rebar centroid
    y_top = h / 2 - cover
    y_bot = -h / 2 + cover

    # 상단 철근
    if n_top > 0:
        xs = np.linspace(-b / 2 + cover, b / 2 - cover, n_top)
        for x in xs:
            positions.append((x, y_top))

    # 하단 철근
    if n_bot > 0:
        xs = np.linspace(-b / 2 + cover, b / 2 - cover, n_bot)
        for x in xs:
            positions.append((x, y_bot))

    # 측면 철근 (좌우 각 n개)
    if n_side_per_face > 0 and (n_top + n_bot) > 0:
        ys = np.linspace(y_bot, y_top, n_side_per_face + 2)[1:-1]
        x_left  = -b / 2 + cover
        x_right =  b / 2 - cover
        for y in ys:
            positions.append((x_left,  y))
            positions.append((x_right, y))

    return positions
