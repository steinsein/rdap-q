"""
RDAP 퀵버전 — 결과 페이지 컴포지션

본 모듈은 결과 페이지의 3단계 표시를 그린다. 점수 산출은 scoring.py,
시각화는 visualizations.py가 담당하며, 본 모듈은 그것들을 조합해
응답자에게 보여줄 화면을 구성한다.

3단계 흐름:
1. RDAS 점수 카드 (게이지 + 라벨 + 한 줄 메시지)
2. 영역별 차등 막대 (4개 영역, 가장 큰 영역 강조 + 성찰 질문)
3. NR(신종교) 참고 정보 박스

결과 페이지 종료 후: 디브리핑 페이지로 이동 (MT 페이지 없음).
"""

from __future__ import annotations

import streamlit as st

import config
from src import scoring, sheets, utils, visualizations


# =============================================================================
# 입력 수집 — 세션 상태 → scoring 입력
# =============================================================================

def _gather_cr_scores() -> dict[str, int]:
    """세션의 CR 응답을 정규화 점수 딕셔너리로 변환한다.

    반환: {"Q1_PT": 0~3, "Q1_IS": 0~3, "Q1_NR": 0~3, ..., "Q4_NR": 0~3}
    """
    resp = st.session_state["responses"]
    return {
        f"{sc['id']}_{rel}": int(resp.get(f"{sc['id']}_{rel}", 0))
        for sc in config.SCENARIOS
        for rel in config.COMPARISON_RELIGIONS
    }


# =============================================================================
# 1단계 — RDAS 점수 카드
# =============================================================================

def _stage_rdas(scores: dict) -> None:
    st.markdown(
        f"<div style='text-align:center; margin-top: 0.5rem;'>"
        f"<span style='font-size: 14px; color: {config.COLOR_NEUTRAL};'>"
        f"당신의 종교 다양성 수용도</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

    fig = visualizations.rdas_gauge(
        scores["rdas_score"], scores["rdas_color"], scores["rdas_label_name"],
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    st.markdown(
        f"<div style='text-align:center; margin-top: -0.5rem;'>"
        f"<span style='font-size: 20px; font-weight: 600; color: {scores['rdas_color']};'>"
        f"{scores['rdas_label_name']}</span><br>"
        f"<span style='font-size: 14px; color: #374151;'>"
        f"{scores['rdas_label_message']}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )


# =============================================================================
# 2단계 — 영역별 차등 막대 + 성찰 질문
# =============================================================================

def _stage_domains(scores: dict) -> None:
    st.markdown("---")
    fig = visualizations.domain_bars(
        scores["domain_deviations"], scores["dominant_domain"],
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    dom = scores["dominant_domain"]
    dom_value = scores["domain_deviations"][dom]
    # 차등이 0이면 성찰 질문 대신 다른 메시지
    if dom_value == 0:
        st.info(
            "네 영역 모두에서 개신교와 이슬람에 같은 기준으로 답하셨어요. "
            "일관성이 두드러진 응답입니다."
        )
    else:
        st.info(config.DOMAIN_REFLECTION[dom])


# =============================================================================
# 3단계 — NR(신종교) 참고 정보 박스
# =============================================================================

def _stage_nr_reference(scores: dict) -> None:
    st.markdown("---")
    st.markdown("##### 참고 — 신종교와의 차등")

    nr = scores["nr_reference"]
    pt_nr = nr["pt_nr_deviation"]
    is_nr = nr["is_nr_deviation"]

    st.markdown(
        f"""
        <div style='
            padding: 14px 18px;
            border-left: 3px solid {config.COLOR_ACCENT};
            background: #FAF5FF;
            border-radius: 4px;
            font-size: 14px;
            color: #374151;
            line-height: 1.7;
        '>
        본 점수(RDAS)는 <b>개신교와 이슬람의 비교</b>를 기준으로 산출됩니다.<br>
        신종교는 한국 사회에서 일정한 사회적 합의가
        형성된 영역으로 보아 점수 산출에서는 제외하였습니다.<br><br>
        다만 비교 자료로 함께 보여드립니다:<br>
        · 개신교 vs 신종교 차등: <b>{pt_nr}점</b> / 12점 만점<br>
        · 이슬람 vs 신종교 차등: <b>{is_nr}점</b> / 12점 만점
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.caption(
        "차등이 크다는 것은 신종교에 대해 다른 두 종교와 매우 다른 기준을 적용했다는 "
        "신호로 읽을 수 있어요."
    )


# =============================================================================
# 진입 함수 — app.py에서 호출
# =============================================================================

def render_results() -> None:
    """결과 페이지 3단계를 순차 렌더링한다.

    렌더링 직전에 점수를 산출하고, 시트에 동시 저장한다.
    """
    cr_scores = _gather_cr_scores()
    scores = scoring.compute_all_scores(cr_scores)
    st.session_state["computed_scores"] = scores

    # 1회만 저장 (재실행 시 중복 방지)
    if not st.session_state.get("saved_main", False):
        payload = _build_save_payload(cr_scores, scores)
        st.session_state["saved_main"] = sheets.append_response(payload)

    st.title("응답 결과")
    st.caption(
        "본 결과는 한 시점의 응답을 반영한 것이며, 응답자를 분류하거나 평가하지 않습니다."
    )

    _stage_rdas(scores)
    _stage_domains(scores)
    _stage_nr_reference(scores)

    st.markdown("---")
    if st.button(
        "마치기",
        type="primary",
        use_container_width=True,
    ):
        utils.go_to("debriefing")


# =============================================================================
# 시트 저장 페이로드 구성
# =============================================================================

def _build_save_payload(cr_scores: dict[str, int], scores: dict) -> dict:
    """sheets.append_response에 전달할 행 딕셔너리를 구성한다."""
    resp = st.session_state["responses"]

    # CR RT 키: q1_pt, q1_is, ...
    cr_rt_keys = [
        f"q{sc['id'][1:]}_{rel.lower()}"
        for sc in config.SCENARIOS
        for rel in config.COMPARISON_RELIGIONS
    ]
    anomaly_flags = utils.check_rt_anomaly(cr_rt_keys)

    payload = {
        "session_id": st.session_state["session_id"],
        "cb_condition": st.session_state["cb_condition"],
        # 인구통계
        "age_group": resp.get("age_group", ""),
        "gender": resp.get("gender", ""),
        "region": resp.get("region", ""),
        "religion": resp.get("religion", ""),
        # CR 정규화 점수
        **{
            f"q{sc['id'][1:]}_{rel.lower()}": cr_scores[f"{sc['id']}_{rel}"]
            for sc in config.SCENARIOS
            for rel in config.COMPARISON_RELIGIONS
        },
        # CR RT
        **{f"rt_{k}_ms": utils.get_rt(k) or 0 for k in cr_rt_keys},
        # CF (백그라운드)
        "cf_q3_response": resp.get("cf_q3_response", ""),
        "rt_cf_ms": utils.get_rt("cf") or 0,
        # DQ (백그라운드)
        "dq_01_response": resp.get("dq_01_response", ""),
        "rt_dq_ms": utils.get_rt("dq") or 0,
        # MC
        "mc_01_response": resp.get("mc_01_response", ""),
        "mc_02_response": resp.get("mc_02_response", ""),
        # FB
        "fb_01_response": resp.get("fb_01_response", ""),
        "fb_02_text": resp.get("fb_02_text", ""),
        # 품질 플래그
        "rt_anomaly_flags": ",".join(anomaly_flags),
        # 산출 점수
        "rdas_score": scores["rdas_score"],
        "rdas_label": scores["rdas_label_key"],
        "pt_is_deviation": scores["pt_is_deviation"],
        "pt_nr_deviation": scores["nr_reference"]["pt_nr_deviation"],
        "is_nr_deviation": scores["nr_reference"]["is_nr_deviation"],
        "nr_mean_score": scores["nr_reference"]["nr_mean_score"],
        "dom_public": scores["domain_deviations"]["public"],
        "dom_work": scores["domain_deviations"]["work"],
        "dom_private": scores["domain_deviations"]["private"],
        "dom_media": scores["domain_deviations"]["media"],
        "dominant_domain": scores["dominant_domain"],
        # 소요 시간
        "total_duration_sec": utils.total_elapsed_seconds(),
    }
    return payload
