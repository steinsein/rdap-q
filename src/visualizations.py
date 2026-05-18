"""
RDAP 퀵버전 — 시각화 (Plotly Figure 생성)

본 모듈은 결과 페이지에 필요한 Plotly Figure 객체만 생성한다. Streamlit
세션이나 위젯을 직접 조작하지 않는다. 모든 차트는 중성 톤·고대비 텍스트
정책을 따른다.

차트 목록:
- rdas_gauge:       1단계 RDAS 점수 카드 (반원 게이지)
- domain_bars:      2단계 영역별 PT-IS 차등 막대

NR 참고 정보는 단순 텍스트 박스로 표시되므로 별도 Figure가 필요하지 않다
(results.py에서 st.info로 처리).
"""

from __future__ import annotations

import plotly.graph_objects as go

import config

# 공통 레이아웃 옵션 — 모바일 호환
_COMMON_LAYOUT = {
    "paper_bgcolor": "white",
    "plot_bgcolor": "white",
    "font": {
        "family": "Pretendard, -apple-system, system-ui, sans-serif",
        "size": 13,
        "color": "#111827",
    },
    "margin": {"l": 40, "r": 20, "t": 50, "b": 40},
}


# =============================================================================
# 1단계 — RDAS 게이지
# =============================================================================

def rdas_gauge(score: int, color: str, label_name: str) -> go.Figure:
    """RDAS 점수(0~100)를 반원 게이지로 표현한다.

    중앙에 큰 숫자, 게이지 위 호에 5단계 구간을 옅게 표시.
    """
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=score,
            number={"font": {"size": 56, "color": color}, "suffix": ""},
            gauge={
                "axis": {
                    "range": [0, 100],
                    "tickwidth": 1,
                    "tickcolor": config.COLOR_NEUTRAL,
                    "tickvals": [0, 20, 40, 60, 80, 100],
                    "ticktext": ["0", "20", "40", "60", "80", "100"],
                    "tickfont": {"size": 11, "color": config.COLOR_NEUTRAL},
                },
                "bar": {"color": color, "thickness": 0.25},
                "bgcolor": "white",
                "borderwidth": 1,
                "bordercolor": config.COLOR_LIGHT,
                "steps": [
                    {"range": [0, 20], "color": "#FEF2F2"},
                    {"range": [20, 40], "color": "#FFF7ED"},
                    {"range": [40, 60], "color": "#FEFCE8"},
                    {"range": [60, 80], "color": "#F0FDF4"},
                    {"range": [80, 100], "color": "#EFF6FF"},
                ],
                "threshold": {
                    "line": {"color": color, "width": 3},
                    "thickness": 0.75,
                    "value": score,
                },
            },
            domain={"x": [0, 1], "y": [0, 1]},
        )
    )
    fig.update_layout(
        height=260,
        margin={"l": 30, "r": 30, "t": 20, "b": 10},
        paper_bgcolor="white",
        font={
            "family": "Pretendard, -apple-system, system-ui, sans-serif",
            "color": "#111827",
        },
    )
    return fig


# =============================================================================
# 2단계 — 영역별 PT-IS 차등 막대
# =============================================================================

def domain_bars(
    domain_dev: dict[str, int],
    dominant_domain: str,
) -> go.Figure:
    """공적·직장·사적·미디어 영역의 PT-IS 차등을 가로 막대로 표시한다.

    가장 차등이 큰 영역은 진한 색으로 강조하고, 나머지는 옅은 색으로.
    """
    labels = [config.DOMAIN_LABELS[d] for d in config.DOMAIN_ORDER]
    values = [domain_dev.get(d, 0) for d in config.DOMAIN_ORDER]
    colors = [
        config.COLOR_PRIMARY if d == dominant_domain else config.COLOR_LIGHT
        for d in config.DOMAIN_ORDER
    ]
    text_colors = [
        "white" if d == dominant_domain else config.COLOR_NEUTRAL
        for d in config.DOMAIN_ORDER
    ]

    fig = go.Figure(
        data=go.Bar(
            y=labels,
            x=values,
            orientation="h",
            marker={"color": colors},
            text=[f"{v}점" for v in values],
            textposition="inside",
            textfont={"color": text_colors, "size": 13},
            hovertemplate="%{y}: %{x}점<extra></extra>",
            cliponaxis=False,
        )
    )
    fig.update_layout(
        height=260,
        title={
            "text": "영역별 차등 (PT−IS, 점수 ↑ = 두 종교를 다르게 평가)",
            "font": {"size": 14},
            "x": 0.0,
            "xanchor": "left",
        },
        xaxis={
            "range": [0, 3.4],
            "tickvals": [0, 1, 2, 3],
            "ticktext": ["0", "1", "2", "3"],
            "gridcolor": config.COLOR_LIGHT,
            "zerolinecolor": config.COLOR_LIGHT,
            "title": "차등 점수",
        },
        yaxis={
            "tickfont": {"size": 12},
            "autorange": "reversed",  # 공적이 위에서부터
        },
        showlegend=False,
        **_COMMON_LAYOUT,
    )
    return fig
