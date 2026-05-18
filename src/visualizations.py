"""
RDAP 퀵버전 V4 — 시각화 (Plotly Figure 생성)

본 모듈은 결과 페이지에 필요한 Plotly Figure 객체만 생성한다. Streamlit
세션이나 위젯을 직접 조작하지 않는다. 모든 차트는 V4 §4.4.3의 색상 정책
(중성 톤, 명도 그라데이션, 색상 이모지 금지)을 따른다.

차트 목록 (V4 §5):
- kpi_value_cards: 1단계 요약 카드 (Plotly 외부에서 처리)
- cr_heatmap: 2단계 CR 응답 히트맵
- rt_comparison_bars: 3단계 자동성 지표
- domain_radar: 4단계 영역별 차등 레이더
- dq_cr_scatter: 5단계 DQ vs CR 산점도
- cf_vs_actual: 6단계 반사실 vs 실제 격차 대조
"""

from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

import config

# 공통 레이아웃 옵션 — 모바일 호환
_COMMON_LAYOUT = {
    "paper_bgcolor": "white",
    "plot_bgcolor": "white",
    "font": {"family": "Pretendard, -apple-system, system-ui, sans-serif", "size": 13, "color": "#111827"},
    "margin": {"l": 40, "r": 20, "t": 40, "b": 40},
}


# =============================================================================
# 2단계 — CR 응답 히트맵
# =============================================================================

def cr_heatmap(
    cr_scores: dict[str, int],
    scenarios: list[dict[str, Any]],
    rt_data: dict[str, int] | None = None,
) -> go.Figure:
    """5×2 히트맵. 행: Q1~Q5, 열: 시나리오의 종교 1·2.

    cr_scores: {"Q1A": 0~3, "Q1B": 0~3, ...} — 정규화 점수
    """
    z = []
    y_labels = []
    for sc in scenarios:
        qid = sc["id"]
        a = cr_scores.get(f"{qid}A", 0)
        b = cr_scores.get(f"{qid}B", 0)
        z.append([a, b])
        y_labels.append(f"{qid}: {sc['title']}")

    # 종교 라벨은 첫 시나리오의 페어 기준이 아니라 시나리오별로 다르므로,
    # 가로축 라벨은 일반적으로 "비교 1", "비교 2"로 두고 셀 텍스트로 종교 표시.
    text = [
        [
            f"{config.RELIGION_LABELS.get(sc['pair'][0], '')}<br>{z[i][0]}점",
            f"{config.RELIGION_LABELS.get(sc['pair'][1], '')}<br>{z[i][1]}점",
        ]
        for i, sc in enumerate(scenarios)
    ]

    fig = go.Figure(
        data=go.Heatmap(
            z=z,
            x=["비교 종교 1", "비교 종교 2"],
            y=y_labels,
            text=text,
            texttemplate="%{text}",
            textfont={"size": 11},
            colorscale=config.HEATMAP_COLORSCALE,
            zmin=0,
            zmax=3,
            showscale=False,
            hoverinfo="text",
        )
    )
    fig.update_layout(
        height=380,
        title={"text": "문항별 응답 비교", "font": {"size": 15}},
        yaxis={"autorange": "reversed", "tickfont": {"size": 11}},
        **_COMMON_LAYOUT,
    )
    return fig


# =============================================================================
# 3단계 — 자동성 지표 (RT 비교)
# =============================================================================

def rt_comparison_bars(
    mean_r1: float | None,
    mean_r2: float | None,
    scenarios: list[dict[str, Any]],
) -> go.Figure | None:
    """종교 1 vs 종교 2의 평균 RT 가로 막대 차트.

    페어의 종교가 시나리오마다 다르므로, 라벨은 일반화한다 ("비교 1", "비교 2").
    """
    if mean_r1 is None or mean_r2 is None:
        return None

    sec_r1 = round(mean_r1 / 1000, 1)
    sec_r2 = round(mean_r2 / 1000, 1)

    fig = go.Figure(
        data=go.Bar(
            y=["비교 종교 1", "비교 종교 2"],
            x=[sec_r1, sec_r2],
            orientation="h",
            text=[f"{sec_r1}초", f"{sec_r2}초"],
            textposition="outside",
            marker={"color": [config.COLOR_PRIMARY, config.COLOR_SECONDARY]},
            hoverinfo="x",
        )
    )
    fig.update_layout(
        height=240,
        title={"text": "응답 시간 비교 (시나리오 평균)", "font": {"size": 15}},
        xaxis={"title": "초", "gridcolor": config.COLOR_LIGHT},
        yaxis={"tickfont": {"size": 12}},
        **_COMMON_LAYOUT,
    )
    return fig


# =============================================================================
# 4단계 — 영역별 차등 레이더
# =============================================================================

def domain_radar(domain_dev: dict[str, int]) -> go.Figure:
    """공적/직장/사적 영역 차등 레이더."""
    # 각 축의 스케일을 0~1로 정규화 (영역별 최댓값으로 나눔)
    categories = ["공적 영역", "직장 영역", "사적 영역"]
    user_values = [
        domain_dev["public"] / config.DOMAIN_MAX["public"],
        domain_dev["work"] / config.DOMAIN_MAX["work"],
        domain_dev["private"] / config.DOMAIN_MAX["private"],
    ]
    sample_values = [
        config.SAMPLE_MEANS["dom_public"] / config.DOMAIN_MAX["public"],
        config.SAMPLE_MEANS["dom_work"] / config.DOMAIN_MAX["work"],
        config.SAMPLE_MEANS["dom_private"] / config.DOMAIN_MAX["private"],
    ]

    # 레이더는 첫 점과 끝 점을 연결하기 위해 닫아 둔다
    categories_closed = categories + [categories[0]]
    user_closed = user_values + [user_values[0]]
    sample_closed = sample_values + [sample_values[0]]

    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=sample_closed,
            theta=categories_closed,
            name=f"표본 평균 (N={config.SAMPLE_SIZE_N})",
            line={"color": config.COLOR_NEUTRAL, "dash": "dot", "width": 1.5},
            mode="lines",
        )
    )
    fig.add_trace(
        go.Scatterpolar(
            r=user_closed,
            theta=categories_closed,
            name="본인 응답",
            line={"color": config.COLOR_PRIMARY, "width": 2.5},
            fill="toself",
            fillcolor="rgba(30, 58, 138, 0.18)",
        )
    )
    fig.update_layout(
        height=380,
        title={"text": "영역별 종교 간 차등", "font": {"size": 15}},
        polar={
            "radialaxis": {
                "visible": True,
                "range": [0, 1],
                "tickvals": [0, 0.5, 1],
                "ticktext": ["", "", ""],
                "gridcolor": config.COLOR_LIGHT,
            },
            "angularaxis": {"tickfont": {"size": 12}},
            "bgcolor": "white",
        },
        showlegend=True,
        legend={"orientation": "h", "y": -0.1, "x": 0.5, "xanchor": "center"},
        **{k: v for k, v in _COMMON_LAYOUT.items() if k != "plot_bgcolor"},
    )
    return fig


# =============================================================================
# 5단계 — DQ vs CR 산점도
# =============================================================================

def dq_cr_scatter(dq_response: int, deviation_total: int) -> go.Figure:
    """DQ 응답 vs CR 총 차등의 4분면 산점도.

    X: DQ 응답 1~4 (개방→신중)
    Y: CR 총 차등 0~15 (일관→차등)

    4분면:
    - 좌상(낮은 DQ, 높은 CR): Devine 패턴
    - 우상(높은 DQ, 높은 CR): 자각적 차등
    - 좌하(낮은 DQ, 낮은 CR): 일관 개방
    - 우하(높은 DQ, 낮은 CR): 자기 인식 격차
    """
    fig = go.Figure()

    # 4분면 구분선
    fig.add_shape(type="line", x0=2.5, x1=2.5, y0=0, y1=15,
                  line={"color": config.COLOR_LIGHT, "width": 1, "dash": "dash"})
    fig.add_shape(type="line", x0=1, x1=4, y0=7.5, y1=7.5,
                  line={"color": config.COLOR_LIGHT, "width": 1, "dash": "dash"})

    # 4분면 라벨
    fig.add_annotation(x=1.5, y=13, text="자기 보고: 개방<br>실제: 차등",
                       showarrow=False, font={"size": 10, "color": config.COLOR_NEUTRAL})
    fig.add_annotation(x=3.5, y=13, text="자기 보고: 신중<br>실제: 차등",
                       showarrow=False, font={"size": 10, "color": config.COLOR_NEUTRAL})
    fig.add_annotation(x=1.5, y=2, text="자기 보고: 개방<br>실제: 일관",
                       showarrow=False, font={"size": 10, "color": config.COLOR_NEUTRAL})
    fig.add_annotation(x=3.5, y=2, text="자기 보고: 신중<br>실제: 일관",
                       showarrow=False, font={"size": 10, "color": config.COLOR_NEUTRAL})

    # 본인 마커
    fig.add_trace(
        go.Scatter(
            x=[dq_response],
            y=[deviation_total],
            mode="markers",
            marker={"size": 14, "color": config.COLOR_PRIMARY, "line": {"color": "white", "width": 2}},
            name="본인",
            hoverinfo="x+y",
        )
    )

    fig.update_layout(
        height=380,
        title={"text": "자기 보고 vs 실제 응답 패턴", "font": {"size": 15}},
        xaxis={
            "title": "자기 보고 (DQ)",
            "range": [0.5, 4.5],
            "tickvals": [1, 2, 3, 4],
            "ticktext": ["① 개방", "②", "③", "④ 신중"],
            "gridcolor": config.COLOR_LIGHT,
        },
        yaxis={
            "title": "실제 종교 간 차등 (CR 총합)",
            "range": [0, 15],
            "gridcolor": config.COLOR_LIGHT,
        },
        showlegend=False,
        **_COMMON_LAYOUT,
    )
    return fig


# =============================================================================
# 6단계 — 반사실 vs 실제 격차 대조
# =============================================================================

def cf_vs_actual(cf_response: int, q5_deviation: int) -> go.Figure:
    """CF 예상치 vs 실제 Q5 격차 짝 막대 차트.

    CF 응답을 예상 격차 점수로 환산:
      ① 똑같이 → 0
      ② 한 단계 → 1
      ③ 두 단계 이상 → 2.5
      ④ 모르겠다 → 표시 안 함 (회색 점선)
    """
    cf_estimate_map = {1: 0, 2: 1, 3: 2.5}

    fig = go.Figure()

    if cf_response == 4:
        # 좌측은 회색 점선 박스, 우측만 실제 격차
        fig.add_trace(
            go.Bar(
                x=["예상", "실제"],
                y=[0, q5_deviation],
                text=["?", f"{q5_deviation}점"],
                textposition="outside",
                marker={
                    "color": [config.COLOR_LIGHT, config.COLOR_PRIMARY],
                    "line": {"color": [config.COLOR_NEUTRAL, config.COLOR_PRIMARY], "width": 2},
                    "pattern": {"shape": ["x", ""]},
                },
                hoverinfo="x+y",
            )
        )
    else:
        estimate = cf_estimate_map.get(cf_response, 0)
        fig.add_trace(
            go.Bar(
                x=["예상", "실제"],
                y=[estimate, q5_deviation],
                text=[f"{estimate}점", f"{q5_deviation}점"],
                textposition="outside",
                marker={"color": [config.COLOR_SECONDARY, config.COLOR_PRIMARY]},
                hoverinfo="x+y",
            )
        )

    fig.update_layout(
        height=300,
        title={"text": "Q5 격차 — 예상 vs 실제", "font": {"size": 15}},
        yaxis={
            "title": "격차 점수",
            "range": [0, 3.5],
            "gridcolor": config.COLOR_LIGHT,
        },
        showlegend=False,
        **_COMMON_LAYOUT,
    )
    return fig
