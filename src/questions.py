"""
RDAP 퀵버전 V4 — 문항 렌더링 함수

본 모듈은 각 블록(SC, DM, CR, CF, DQ, MC, FB, MT)의 UI를 그린다.
페이지 라우팅(어느 시점에 어느 블록을 호출할지)은 app.py가 담당하며,
본 모듈의 각 함수는 해당 페이지에 진입한 시점에 한 번씩 호출된다.

각 렌더 함수의 책임:
1. 진입 시점에 RT 시작 시점을 기록 (utils.capture_rt_start)
2. 위젯을 그리고 응답값을 받음
3. "다음" 버튼 클릭 시 RT 종료 시점 기록, 응답 저장, 페이지 전환
"""

from __future__ import annotations

from typing import Any

import streamlit as st

import config
from src import utils


# =============================================================================
# 공통 유틸 — 진행률 바, 헤더
# =============================================================================

def progress_header(current: int, total: int, title: str) -> None:
    """페이지 상단에 진행률과 단계 제목을 표시한다."""
    pct = int(current / total * 100) if total else 0
    st.progress(pct / 100, text=f"단계 {current} / {total}")
    st.markdown(f"### {title}")


# =============================================================================
# SC — 동의 및 선별 (2문항, 한 페이지)
# =============================================================================

def render_consent_and_screen() -> None:
    """SC-01 (참여 동의) + SC-02 (연령 확인)을 한 화면에 표시."""
    utils.capture_rt_start("consent_page")

    st.title(config.TOOL_NAME)
    st.markdown(f"##### {config.CONSENT_TITLE}")
    st.info(config.CONSENT_TEXT)

    sc01 = st.radio(
        config.SC_01_QUESTION,
        config.SC_01_OPTIONS,
        index=None,
        key="sc01_widget",
    )

    sc02 = st.radio(
        config.SC_02_QUESTION,
        config.SC_02_OPTIONS,
        index=None,
        key="sc02_widget",
    )

    if st.button("다음", type="primary", use_container_width=True):
        if sc01 is None or sc02 is None:
            st.warning("두 항목 모두 응답해 주세요.")
            return
        if sc01 == config.SC_01_OPTIONS[1]:  # 참여하지 않음
            st.session_state["responses"]["sc01"] = 2
            utils.go_to("declined")
            return
        if sc02 == config.SC_02_OPTIONS[1]:  # 18세 미만
            st.session_state["responses"]["sc02"] = 2
            utils.go_to("underage")
            return
        st.session_state["responses"]["sc01"] = 1
        st.session_state["responses"]["sc02"] = 1
        utils.capture_rt_end("consent_page")
        utils.go_to("demographics")


# =============================================================================
# DM — 인구통계 (4문항)
# =============================================================================

def render_demographics() -> None:
    utils.capture_rt_start("dm_page")
    progress_header(1, 9, "기본 정보")
    st.caption("응답은 통계 분석 목적으로만 사용됩니다.")

    answers: dict[str, str] = {}
    for q in config.DM_QUESTIONS:
        answers[q["key"]] = st.radio(
            q["label"],
            q["options"],
            index=None,
            key=f"dm_{q['key']}_widget",
            horizontal=False,
        )

    if st.button("다음", type="primary", use_container_width=True):
        if any(v is None for v in answers.values()):
            st.warning("모든 항목에 응답해 주세요.")
            return
        for k, v in answers.items():
            st.session_state["responses"][k] = v
        utils.capture_rt_end("dm_page")
        utils.go_to("cr_intro")


# =============================================================================
# CR 도입 페이지
# =============================================================================

def render_cr_intro() -> None:
    st.markdown("### 비교 응답 블록 안내")
    st.markdown(
        """
        지금부터 5가지 상황에서 **같은 상황을 두 가지 종교로** 제시하는 짝지어진
        질문이 이어집니다.

        - 정답이 없습니다. 평소 느끼시는 가장 가까운 반응을 골라 주세요.
        - "바람직해 보이는 답"보다 **솔직한 첫 반응**이 더 유용한 데이터가 됩니다.
        - 각 시나리오는 두 화면에 걸쳐 표시됩니다.
        """
    )
    if st.button("시작하기", type="primary", use_container_width=True):
        utils.go_to("cr_Q1A")


# =============================================================================
# CR — 비교 응답 (10페이지, 시나리오당 2개)
# =============================================================================

def _render_cr_item(qid: str, ab: str) -> None:
    """CR 한 문항(Q{1..5}{A|B})을 렌더링한다."""
    version = st.session_state["version"]
    cb = st.session_state["cb_condition"]
    option_order = utils.get_option_order(cb)
    scenarios = config.SCENARIOS[version]
    sc = next(s for s in scenarios if s["id"] == qid)

    rt_key = f"{qid.lower()}{ab.lower()}"
    utils.capture_rt_start(rt_key)

    # 진행률: Q1A=2/9, Q1B=2/9 … 단계로 보기 좋게 변환
    step_no = 2  # 비교 응답 블록은 단계 2
    total = 9
    progress_header(step_no, total, f"시나리오 {qid[-1]} — {sc['title']}")

    # 역균형화: 페어 순서에 따라 어느 시나리오 본문을 표시할지 결정
    pair_ordered = utils.get_pair_order(sc["pair"], cb)
    # cb_condition이 beta면 stem_b가 화면 A로, stem_a가 화면 B로 가야 한다
    if cb.startswith("beta"):
        stem = sc["stem_b"] if ab == "A" else sc["stem_a"]
    else:
        stem = sc["stem_a"] if ab == "A" else sc["stem_b"]

    st.markdown(f"#### {stem}")
    display_options = utils.get_display_options(sc["options"], option_order)
    selected = st.radio(
        "가장 가까운 답을 골라 주세요.",
        display_options,
        index=None,
        key=f"cr_{qid}{ab}_widget",
        label_visibility="collapsed",
    )

    col1, col2 = st.columns([1, 1])
    with col2:
        if st.button("다음", type="primary", use_container_width=True, key=f"next_{qid}{ab}"):
            if selected is None:
                st.warning("답을 선택해 주세요.")
                return
            selected_idx = display_options.index(selected)
            normalized = utils.normalize_response(selected_idx, option_order)
            st.session_state["responses"][f"{qid}{ab}_response"] = normalized
            utils.capture_rt_end(rt_key)

            # 다음 페이지로
            order = _CR_PAGE_ORDER
            current_idx = order.index(f"cr_{qid}{ab}")
            next_page = order[current_idx + 1] if current_idx + 1 < len(order) else "cf"
            utils.go_to(next_page)


# CR 페이지 순서: Q1A→Q1B→…→Q5B→CF
_CR_PAGE_ORDER = [f"cr_Q{i}{ab}" for i in (1, 2, 3, 4, 5) for ab in ("A", "B")]


def render_cr_page(page_key: str) -> None:
    """app.py에서 호출할 단일 진입점.

    page_key 예: "cr_Q3A"
    """
    _, qid_ab = page_key.split("_")
    qid, ab = qid_ab[:2], qid_ab[2]
    _render_cr_item(qid, ab)


# =============================================================================
# CF — 반사실 확인 (1문항)
# =============================================================================

def render_cf() -> None:
    utils.capture_rt_start("cf")
    progress_header(3, 9, "잠시 멈추고 돌아보기")

    version = st.session_state["version"]
    st.markdown(config.CF_INTRO[version])
    st.markdown(f"#### {config.CF_QUESTION}")

    selected = st.radio(
        "선택해 주세요.",
        config.CF_OPTIONS,
        index=None,
        key="cf_widget",
        label_visibility="collapsed",
    )

    if st.button("다음", type="primary", use_container_width=True):
        if selected is None:
            st.warning("답을 선택해 주세요.")
            return
        cf_idx = config.CF_OPTIONS.index(selected) + 1  # 1~4 코딩
        st.session_state["responses"]["cf_q5_response"] = cf_idx
        utils.capture_rt_end("cf")
        utils.go_to("dq")


# =============================================================================
# DQ — 직접 질문 닻 (1문항)
# =============================================================================

def render_dq() -> None:
    utils.capture_rt_start("dq")
    progress_header(4, 9, "직접 질문")

    st.markdown(f"#### {config.DQ_QUESTION}")
    selected = st.radio(
        "선택해 주세요.",
        config.DQ_OPTIONS,
        index=None,
        key="dq_widget",
        label_visibility="collapsed",
    )

    if st.button("다음", type="primary", use_container_width=True):
        if selected is None:
            st.warning("답을 선택해 주세요.")
            return
        dq_idx = config.DQ_OPTIONS.index(selected) + 1  # 1~4
        st.session_state["responses"]["dq_01_response"] = dq_idx
        utils.capture_rt_end("dq")
        utils.go_to("mc")


# =============================================================================
# MC — 비교 의도 인지 점검 (2문항)
# =============================================================================

def render_mc() -> None:
    utils.capture_rt_start("mc")
    progress_header(5, 9, "응답 점검")

    mc01 = st.radio(
        config.MC_01_QUESTION,
        config.MC_01_OPTIONS,
        index=None,
        key="mc01_widget",
    )
    mc02 = st.radio(
        config.MC_02_QUESTION,
        config.MC_02_OPTIONS,
        index=None,
        key="mc02_widget",
    )

    if st.button("다음", type="primary", use_container_width=True):
        if mc01 is None or mc02 is None:
            st.warning("두 항목 모두 응답해 주세요.")
            return
        st.session_state["responses"]["mc_01_response"] = (
            config.MC_01_OPTIONS.index(mc01) + 1
        )
        st.session_state["responses"]["mc_02_response"] = (
            config.MC_02_OPTIONS.index(mc02) + 1
        )
        utils.capture_rt_end("mc")
        utils.go_to("fb")


# =============================================================================
# FB — 피드백 (2문항)
# =============================================================================

def render_fb() -> None:
    utils.capture_rt_start("fb")
    progress_header(6, 9, "솔직함 점검")

    fb01 = st.radio(
        config.FB_01_QUESTION,
        config.FB_01_OPTIONS,
        index=None,
        key="fb01_widget",
    )
    fb02 = st.text_area(
        config.FB_02_QUESTION,
        max_chars=300,
        key="fb02_widget",
    )

    if st.button("결과 보기", type="primary", use_container_width=True):
        if fb01 is None:
            st.warning("첫 번째 항목에 응답해 주세요.")
            return
        st.session_state["responses"]["fb_01_response"] = (
            config.FB_01_OPTIONS.index(fb01) + 1
        )
        st.session_state["responses"]["fb_02_text"] = fb02 or ""
        utils.capture_rt_end("fb")
        utils.go_to("results")


# =============================================================================
# MT — 거울 테스트 (2문항, 결과 페이지 후)
# =============================================================================

def render_mt() -> None:
    utils.capture_rt_start("mt")
    progress_header(8, 9, "되돌아보는 시간")

    st.markdown(config.MT_INTRO)
    st.markdown("---")

    mt01 = st.radio(
        config.MT_01_QUESTION,
        config.MT_01_OPTIONS,
        index=None,
        key="mt01_widget",
    )
    mt02 = st.text_area(
        config.MT_02_QUESTION,
        max_chars=300,
        key="mt02_widget",
    )

    col1, col2 = st.columns(2)
    with col1:
        skip = st.button("건너뛰기", use_container_width=True)
    with col2:
        submit = st.button("제출하고 마치기", type="primary", use_container_width=True)

    if skip or submit:
        if submit and mt01 is not None:
            st.session_state["responses"]["mt_01_response"] = (
                config.MT_01_OPTIONS.index(mt01) + 1
            )
        else:
            st.session_state["responses"]["mt_01_response"] = None
        st.session_state["responses"]["mt_02_text"] = (mt02 or "") if submit else ""
        utils.capture_rt_end("mt")
        utils.go_to("debriefing")
