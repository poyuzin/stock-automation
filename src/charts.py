"""차트를 인라인 SVG 문자열로 만든다 (외부 JS 라이브러리 없음).

색은 dataviz 레퍼런스 팔레트를 그대로 쓴다. 색상값은 CSS 변수로 넘기고
여기서는 var(--...) 만 참조하므로 다크모드 전환이 한 곳에서 끝난다.
"""
from __future__ import annotations

import math

SERIES = [f"var(--series-{i})" for i in range(1, 9)]


def _points(values: list[float], w: float, h: float, pad: float = 2.0):
    vs = [v for v in values if v is not None and not math.isnan(v)]
    if len(vs) < 2:
        return []
    lo, hi = min(vs), max(vs)
    rng = (hi - lo) or 1.0
    step = (w - pad * 2) / (len(vs) - 1)
    return [
        (pad + i * step, pad + (h - pad * 2) * (1 - (v - lo) / rng))
        for i, v in enumerate(vs)
    ]


def sparkline(values: list[float], w: int = 132, h: int = 34) -> str:
    pts = _points(values, w, h)
    if not pts:
        return ""
    d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    area = d + f" L{pts[-1][0]:.1f},{h} L{pts[0][0]:.1f},{h} Z"
    ex, ey = pts[-1]
    return f"""<svg class="spark" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-hidden="true">
  <path d="{area}" fill="var(--spark-fill)"/>
  <path d="{d}" fill="none" stroke="var(--series-1)" stroke-width="2"
        stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="{ex:.1f}" cy="{ey:.1f}" r="3" fill="var(--series-1)"
          stroke="var(--surface-1)" stroke-width="2"/>
</svg>"""


def range_meter(low: float, high: float, value: float, w: int = 120, h: int = 8) -> str:
    """52주 저가~고가 구간에서 현재가 위치. 단일 비율이라 미터가 맞는 형태."""
    if high <= low:
        return ""
    frac = min(max((value - low) / (high - low), 0.0), 1.0)
    x = 2 + frac * (w - 4)
    return f"""<svg class="meter" viewBox="0 0 {w} {h}" width="{w}" height="{h}" role="img" aria-hidden="true">
  <rect x="0" y="{h/2-2:.1f}" width="{w}" height="4" rx="2" fill="var(--track)"/>
  <rect x="0" y="{h/2-2:.1f}" width="{x:.1f}" height="4" rx="2" fill="var(--seq-350)"/>
  <circle cx="{x:.1f}" cy="{h/2:.1f}" r="{h/2:.1f}" fill="var(--seq-450)"
          stroke="var(--surface-1)" stroke-width="2"/>
</svg>"""


def weight_bar(items: list[tuple[str, float]]) -> str:
    """포트폴리오 비중 - 가로 스택 막대.

    SVG 대신 flexbox 로 그린다. 텍스트가 늘어나지 않고 세그먼트 사이
    2px 갭도 gap 속성 하나로 끝난다.
    """
    total = sum(v for _, v in items) or 1.0
    cells = []
    for i, (name, v) in enumerate(items):
        pct = v / total * 100
        color = "var(--track-strong)" if name == "현금" else SERIES[i % 8]
        label = f"{name} {v:.0f}%" if pct >= 7 else ""
        cells.append(
            f'<div class="seg" style="flex:{pct:.4f} 1 0;background:{color}" '
            f'title="{name} {v:.1f}%">{label}</div>'
        )
    return f'<div class="wbar" role="img" aria-label="포트폴리오 비중">{"".join(cells)}</div>'


def equity_chart(
    dates: list[str],
    series: list[tuple[str, list[float]]],
    w: int = 720,
    h: int = 260,
) -> str:
    """자산곡선 - 2개 시리즈(전략 vs 단순보유). 단일 y축."""
    pad_l, pad_r, pad_t, pad_b = 52, 12, 14, 26
    plot_w, plot_h = w - pad_l - pad_r, h - pad_t - pad_b

    flat = [v for _, vals in series for v in vals]
    lo, hi = min(flat), max(flat)
    rng = (hi - lo) or 1.0
    lo, hi = max(lo - rng * 0.06, 0.0), hi + rng * 0.06  # 자산은 음수가 될 수 없다
    rng = hi - lo

    def xy(i: int, v: float, n: int):
        return (
            pad_l + (plot_w * i / max(n - 1, 1)),
            pad_t + plot_h * (1 - (v - lo) / rng),
        )

    grid, ticks = [], []
    for k in range(5):
        v = lo + rng * k / 4
        y = pad_t + plot_h * (1 - k / 4)
        grid.append(
            f'<line x1="{pad_l}" y1="{y:.1f}" x2="{w-pad_r}" y2="{y:.1f}" stroke="var(--grid)" stroke-width="1"/>'
        )
        ticks.append(
            f'<text x="{pad_l-8}" y="{y+4:.1f}" text-anchor="end" class="axis">${v:,.0f}</text>'
        )

    paths, marks = [], []
    end_ys = []
    for si, (name, vals) in enumerate(series):
        pts = [xy(i, v, len(vals)) for i, v in enumerate(vals)]
        d = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        color = SERIES[si]
        paths.append(
            f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2" '
            f'stroke-linejoin="round" stroke-linecap="round"><title>{name}</title></path>'
        )
        ex, ey = pts[-1]
        # 끝점이 겹치면 라벨을 위/아래로 갈라 놓는다
        dy = -10 if not any(abs(ey - y) < 16 for y in end_ys) else 18
        end_ys.append(ey)
        marks.append(
            f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="4" fill="{color}" '
            f'stroke="var(--surface-1)" stroke-width="2"/>'
            f'<text x="{ex-8:.1f}" y="{ey+dy:.1f}" text-anchor="end" class="series-label">{name}</text>'
        )

    xlabels = []
    for i in (0, len(dates) // 2, len(dates) - 1):
        x, _ = xy(i, lo, len(dates))
        anchor = "start" if i == 0 else ("end" if i == len(dates) - 1 else "middle")
        xlabels.append(
            f'<text x="{x:.1f}" y="{h-6}" text-anchor="{anchor}" class="axis">{dates[i][:7]}</text>'
        )

    hover = (
        f'<g class="cross" style="display:none">'
        f'<line y1="{pad_t}" y2="{pad_t+plot_h:.1f}" stroke="var(--baseline)" stroke-width="1"/>'
        f'</g>'
        f'<rect class="hit" x="{pad_l}" y="{pad_t}" width="{plot_w:.1f}" height="{plot_h:.1f}" fill="transparent"/>'
    )
    payload = _json_min(
        {
            "x0": pad_l,
            "w": plot_w,
            "dates": dates,
            "series": [{"name": n, "values": [round(v, 2) for v in vs]} for n, vs in series],
        }
    )
    return f"""<div class="chart-box">
<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="자산곡선" data-chart='{payload}'>
  {''.join(grid)}
  <line x1="{pad_l}" y1="{pad_t+plot_h:.1f}" x2="{w-pad_r}" y2="{pad_t+plot_h:.1f}" stroke="var(--baseline)" stroke-width="1"/>
  {''.join(ticks)}{''.join(xlabels)}
  {''.join(paths)}{''.join(marks)}
  {hover}
</svg>
<div class="tip" hidden></div>
</div>"""


def _json_min(obj) -> str:
    import json

    return json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("'", "&#39;")
