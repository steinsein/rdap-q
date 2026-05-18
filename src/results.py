"""
RDAP 퀵버전 V4 — 결과 페이지 컴포지션

본 모듈은 V4 §10의 8단계 결과 페이지를 그린다. 점수 산출은 scoring.py,
시각화는 visualizations.py가 담당하며, 본 모듈은 그것들을 조합해
응답자에게 보여줄 화면을 구성한다.

8단계 흐름:
1. 헤더 + 요약 카드 4개
2. CR 응답 비교 히트맵
3. 자동성 지표 (RT 비교)
4. 영역별 차등 레이더
5. DQ vs CR 산점도
6. 반사실 vs 실제 격차 대조
7. 종합 프로파일 + 성찰 질문
8. [다음으로] 버튼 → MT 페이지
"""

from __future__ import annotations

import streamlit as st

import config
from src import scoring, sheets, utils, visualizations


# =============================================================================
# 점수 수집 — 세션 상태 → scoring 입력
# =============================================================================

def _gather_inputs() -> dict:
    """세션 상태에서 점수 산출에 필요한 입력을 모은다."""
    resp = st.session_state["responses"]
    version = st.session_state["version"]
    cb = st.session_state["cb_condition"]

    cr_scores = {
        f"{qid}{ab}": int(resp.get(f"{qid}{ab}_response", 0))
        for qid in ("Q1", "Q2", "Q3", "Q4", "Q5")
        for ab in ("A", "B")
    }

    rt_data = {
        f"{qid.lower()}{ab.lower()}_ms": utils.get_rt(f"{qid.lower()}{ab.lower()}") or 0
        for qid in ("Q1", "Q2", "Q3", "Q4", "Q5")
        for ab in ("A", "B")
    }

    return {
        "cr_scores": cr_scores,
        "dq_response": int(resp.get("dq_01_response", 2)),
        "cf_response": int(resp.get("cf_q5_response", 4)),
        "rt_data": rt_data,
        "scenarios": config.SCENARIOS[version],
        "cb_condition": cb,
    }


# =============================================================================
# 1단계 — 요약 카드 4개
# =============================================================================

def _stage_kpi_cards(scores: dict) -> None:
    st.markdown("### 응답 요약")
    cols = st.columns(4)
    rt_asym = scores["rt_asymmetry"]["asymmetry"]
    rt_sec = f"{rt_asym / 1000:.1f}초" if rt_asym is not None else "—"

    with cols[0]:
        st.metric(
            "종교 간 차등",
            f"{scores['deviation_total']} / 15",
            help="비교 쌍 5개의 절대 차이 합. 높을수록 두 종교에 다르게 응답하셨다는 신호.",
        )
    with cols[1]:
        st.metric(
            "전반적 신중도",
            f"{scores['overall_caution']} / 30",
            help="10개 문항 점수 합. 종교 평균에 가까운 응답 강도.",
        )
    with cols[2]:
        st.metric(
            "자기 보고–응답 일치",
            f"{scores['dq_cr_alignment']:+d}",
            help="−: 자기 보고는 개방, 실제는 차등 (Devine 패턴) / +: 반대",
        )
    with cols[3]:
        st.metric(
            "응답 시간 비대칭",
            rt_sec,
            help="두 비교 종교 간 평균 응답 시간 차이.",
        )


# =============================================================================
# 2단계 — CR 히트맵
# =============================================================================

def _stage_heatmap(scores: dict, inputs: dict) -> None:
    st.markdown("---")
    st.markdown("### 문항별 응답 비교")
    fig = visualizations.cr_heatmap(inputs["cr_scores"], inputs["scenarios"])
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.caption(
        "각 행이 하나의 시나리오입니다. 두 종교에 대한 응답 점수(0~3)를 셀에 표시했습니다."
    )


# =============================================================================
# 3단계 — RT 비교
# =============================================================================

def _stage_rt(scores: dict, inputs: dict) -> None:
    st.markdown("---")
    st.markdown("### 자동성 지표 — 응답 시간 비교")
    rt = scores["rt_asymmetry"]
    fig = visualizations.rt_comparison_bars(rt["mean_r1"], rt["mean_r2"], inputs["scenarios"])
    if fig is None:
        st.info("응답 시간 데이터가 충분하지 않아 비교 표시를 생략합니다.")
        return
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.caption(config.RT_MESSAGE[scores["rt_message_level"]])
    st.caption(
        "※ 응답 시간은 1회 측정이라 노이즈가 큽니다. 종교 간 상대 차이만 참고하세요."
    )


# =============================================================================
# 4단계 — 영역별 레이더
# =============================================================================

def _stage_radar(scores: dict) -> None:
    st.markdown("---")
    st.markdown("### 영역별 차등")
    fig = visualizations.domain_radar(scores["domain_deviations"])
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    dom = scores["dominant_domain"]
    label = {"public": "공적 영역", "work": "직장 영역", "private": "사적 영역"}[dom]
    st.caption(f"이번 응답에서는 **{label}**의 차등이 가장 두드러졌습니다.")


# =============================================================================
# 5단계 — DQ vs CR 산점도
# =============================================================================

def _stage_scatter(scores: dict, inputs: dict) -> None:
    st.markdown("---")
    st.markdown("### 자기 보고 vs 실제 응답")
    fig = visualizations.dq_cr_scatter(inputs["dq_response"], scores["deviation_total"])
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.caption(
        "왼쪽 위(자기 보고: 개방 / 실제: 차등)는 Devine(1989)이 기술한 자동–통제 분리 영역입니다."
    )


# =============================================================================
# 6단계 — 반사실 vs 실제
# =============================================================================

def _stage_cf(scores: dict, inputs: dict) -> None:
    st.markdown("---")
    st.markdown("### 예상 vs 실제 — Q5 격차")
    cf = inputs["cf_response"]
    q5_dev = scores["pair_deviations"]["Q5"]
    fig = visualizations.cf_vs_actual(cf, q5_dev)
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
    st.caption(config.CF_MATCH_LABELS[scores["cf_actual_match"]])


# =============================================================================
# 7단계 — 종합 프로파일 + 성찰 질문
# =============================================================================

def _stage_profile(scores: dict, inputs: dict) -> None:
    st.markdown("---")
    profile = config.PROFILE_LABELS[scores["profile_type"]]
    st.markdown(f"### {profile['name']}")
    st.markdown(profile["description"])

    # 영역별 성찰 질문
    dom = scores["dominant_domain"]
    domain_reflections = {
        "public": (
            "공적 영역(시설, 봉사, 미디어)에서 차이가 두드러졌어요. "
            "그 반응이 직접 경험에서 온 것인지, 미디어 이미지에서 온 것인지 생각해 보세요."
        ),
        "work": (
            "직장 영역에서 차이가 두드러졌어요. "
            "업무 능력 판단이나 동료 관계에 종교가 끼어드는 지점을 함께 살펴보세요."
        ),
        "private": (
            "사적 영역(가족·친구·이웃)에서 차이가 두드러졌어요. "
            "가까운 관계로 다가왔을 때 더 깊이 작동하는 패턴은 사회적 거리 효과로 알려져 있어요."
        ),
    }
    st.info(domain_reflections[dom])

    # RT 통합 메시지 (있다면)
    rt_level = scores["rt_message_level"]
    if rt_level in ("medium", "large"):
        st.caption(f"※ 응답 시간 패턴: {config.RT_MESSAGE[rt_level]}")


# =============================================================================
# 진입 함수 — app.py에서 호출
# =============================================================================

def render_results() -> None:
    """결과 페이지 8단계를 순차 렌더링한다.

    렌더링 직전에 점수를 산출하고, 시트에 동시 저장한다 (V4 §3.4).
    """
    inputs = _gather_inputs()
    scores = scoring.compute_all_scores(**inputs)
    st.session_state["computed_scores"] = scores

    # 1회만 저장 (재실행 시 중복 방지)
    if not st.session_state.get("saved_main", False):
        payload = _build_save_payload(inputs, scores)
        st.session_state["saved_main"] = sheets.append_response(payload)

    st.title("응답 결과")
    st.caption(
        "본 결과는 한 시점의 응답을 반영한 것이며, 응답자를 분류하거나 평가하지 않습니다."
    )

    _stage_kpi_cards(scores)
    _stage_heatmap(scores, inputs)
    _stage_rt(scores, inputs)
    _stage_radar(scores)
    _stage_scatter(scores, inputs)
    _stage_cf(scores, inputs)
    _stage_profile(scores, inputs)

    st.markdown("---")
    if st.button("다음으로 → 잠시 되돌아보기", type="primary", use_container_width=True):
        utils.go_to("mt")


# =============================================================================
# 시트 저장 페이로드 구성
# =============================================================================

def _build_save_payload(inputs: dict, scores: dict) -> dict:
    """sheets.append_response에 전달할 행 딕셔너리를 구성한다."""
    resp = st.session_state["responses"]
    cr_keys = [f"q{i}{ab}" for i in (1, 2, 3, 4, 5) for ab in ("a", "b")]
    anomaly_flags = utils.check_rt_anomaly(cr_keys)

    payload = {
        "session_id": st.session_state["session_id"],
        "version": st.session_state["version"],
        "cb_condition": st.session_state["cb_condition"],
        # 인구통계
        "age_group": resp.get("age_group", ""),
        "gender": resp.get("gender", ""),
        "region": resp.get("region", ""),
        "religion": resp.get("religion", ""),
        # CR 정규화 점수
        **{
            f"q{i}{ab}_response": inputs["cr_scores"][f"Q{i}{ab.upper()}"]
            for i in (1, 2, 3, 4, 5)
            for ab in ("a", "b")
        },
        # CR RT
        **{f"rt_{k}_ms": v for k, v in inputs["rt_data"].items()},
        # CF
        "cf_q5_response": inputs["cf_response"],
        "rt_cf_ms": utils.get_rt("cf") or 0,
        # DQ
        "dq_01_response": inputs["dq_response"],
        "rt_dq_ms": utils.get_rt("dq") or 0,
        # MC
        "mc_01_response": resp.get("mc_01_response", ""),
        "mc_02_response": resp.get("mc_02_response", ""),
        # FB
        "fb_01_response": resp.get("fb_01_response", ""),
        "fb_02_text": resp.get("fb_02_text", ""),
        # 품질 플래그
        "rt_anomaly_flags": ",".join(anomaly_flags),
        # 점수
        "overall_caution": scores["overall_caution"],
        "deviation_total": scores["deviation_total"],
        "dom_public": scores["domain_deviations"]["public"],
        "dom_work": scores["domain_deviations"]["work"],
        "dom_private": scores["domain_deviations"]["private"],
        "dq_cr_alignment": scores["dq_cr_alignment"],
        "rt_asymmetry": (
            int(scores["rt_asymmetry"]["asymmetry"])
            if scores["rt_asymmetry"]["asymmetry"] is not None
            else ""
        ),
        "cf_actual_match": scores["cf_actual_match"],
        "profile_type": scores["profile_type"],
        "dominant_domain": scores["dominant_domain"],
        "rt_message_level": scores["rt_message_level"],
        # 소요 시간
        "total_duration_sec": utils.total_elapsed_seconds(),
    }
    return payload
