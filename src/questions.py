"""
RDAP 퀵버전 — 문항 렌더링 함수

본 모듈은 각 블록(SC, DM, CR, CF, DQ, MC, FB)의 UI를 그린다.
페이지 라우팅(어느 시점에 어느 블록을 호출할지)은 app.py가 담당하며,
본 모듈의 각 함수는 해당 페이지에 진입한 시점에 한 번씩 호출된다.

각 렌더 함수의 책임:
1. 진입 시점에 RT 시작 시점을 기록 (utils.capture_rt_start)
2. 위젯을 그리고 응답값을 받음
3. "다음" 버튼 클릭 시 RT 종료 시점 기록, 응답 저장, 페이지 전환
"""

from __future__ import annotations

import streamlit as st

import config
from src import utils


# =============================================================================
# 진행률 헤더
# =============================================================================
# 총 단계: 동의(1) + 인구통계 4 + CR 12 + CF + DQ + MC + FB = 21
# 인구통계 시작 단계: 2
_TOTAL_STEPS = 21


def progress_header(current: int, title: str) -> None:
    """페이지 상단에 진행률과 단계 제목을 표시한다."""
    pct = int(current / _TOTAL_STEPS * 100) if _TOTAL_STEPS else 0
    st.progress(pct / 100, text=f"단계 {current} / {_TOTAL_STEPS}")
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

    st.markdown(f"#### {config.SC_01_QUESTION}")
    sc01 = st.radio(
        config.SC_01_QUESTION,
        config.SC_01_OPTIONS,
        index=None,
        key="sc01_widget",
        label_visibility="collapsed",
    )

    st.markdown(f"#### {config.SC_02_QUESTION}")
    sc02 = st.radio(
        config.SC_02_QUESTION,
        config.SC_02_OPTIONS,
        index=None,
        key="sc02_widget",
        label_visibility="collapsed",
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
        utils.go_to(config.DM_PAGE_KEYS[0])


# =============================================================================
# DM — 인구통계 (4문항, 4페이지 분리)
# =============================================================================

def _render_dm_page(idx: int) -> None:
    """인구통계 4문항 중 idx번째 페이지를 렌더링한다."""
    q = config.DM_QUESTIONS[idx]
    rt_key = f"dm_{q['key']}"
    utils.capture_rt_start(rt_key)

    # 진행률 단계 2~5 (DM 4 페이지)
    progress_header(2 + idx, "기본 정보")
    st.caption("응답은 통계 분석 목적으로만 사용됩니다.")

    st.markdown(f"#### {q['label']}")
    selected = st.radio(
        q["label"],
        q["options"],
        index=None,
        key=f"dm_{q['key']}_widget",
        label_visibility="collapsed",
    )

    if st.button("다음", type="primary", use_container_width=True, key=f"next_dm_{idx}"):
        if selected is None:
            st.warning("항목을 선택해 주세요.")
            return
        st.session_state["responses"][q["key"]] = selected
        utils.capture_rt_end(rt_key)

        # 다음 DM 페이지가 있으면 그쪽으로, 마지막이면 바로 첫 CR 페이지로 이동
        if idx + 1 < len(config.DM_QUESTIONS):
            utils.go_to(config.DM_PAGE_KEYS[idx + 1])
        else:
            utils.go_to(CR_PAGE_ORDER[0])


def render_dm_age() -> None:
    _render_dm_page(0)


def render_dm_gender() -> None:
    _render_dm_page(1)


def render_dm_region() -> None:
    _render_dm_page(2)


def render_dm_religion() -> None:
    _render_dm_page(3)


# =============================================================================
# CR — 비교 응답 (4 시나리오 × 3 종교 = 12 페이지)
# =============================================================================
#
# 페이지 키 규약:
#   cr_Q{n}_{pos}   pos = 0, 1, 2 (시나리오 내 제시 순서)
#
# 실제 어느 종교가 어느 pos에 표시될지는 응답자별로 다르다
# (utils.assign_religion_orders가 결정).
# =============================================================================

# 페이지 순서: Q1의 pos 0, 1, 2 → Q2의 pos 0, 1, 2 → ...
CR_PAGE_ORDER = [
    f"cr_{sc['id']}_{pos}"
    for sc in config.SCENARIOS
    for pos in range(len(config.COMPARISON_RELIGIONS))
]


def _render_cr_item(qid: str, pos: int) -> None:
    """CR 한 문항(시나리오 qid의 pos번째 종교)을 렌더링한다."""
    option_order = st.session_state["option_order"]
    religion_orders = st.session_state["religion_orders"]
    religion_code = religion_orders[qid][pos]

    sc = next(s for s in config.SCENARIOS if s["id"] == qid)
    rt_key = f"q{qid[1:]}_{religion_code.lower()}"  # 예: q1_pt, q1_is, q1_nr
    utils.capture_rt_start(rt_key)

    # 현재 단계 산출 (진행률 표시용)
    # 단계 2~5: DM 4. 단계 6 ~ 17: CR 12. 그 뒤 CF/DQ/MC/FB.
    sc_idx = next(i for i, s in enumerate(config.SCENARIOS) if s["id"] == qid)
    n_rel = len(config.COMPARISON_RELIGIONS)
    cr_step_no = 6 + sc_idx * n_rel + pos  # 6 ~ 17
    progress_header(cr_step_no, f"시나리오 {qid[-1]} — {sc['title']}")

    stem = sc["stems"][religion_code]
    st.markdown(f"#### {stem}")

    display_options = utils.get_display_options(sc["options"], option_order)
    selected = st.radio(
        "가장 가까운 답을 골라 주세요.",
        display_options,
        index=None,
        key=f"cr_{qid}_{pos}_widget",
        label_visibility="collapsed",
    )

    if st.button(
        "다음",
        type="primary",
        use_container_width=True,
        key=f"next_cr_{qid}_{pos}",
    ):
        if selected is None:
            st.warning("답을 선택해 주세요.")
            return

        selected_idx = display_options.index(selected)
        normalized = utils.normalize_response(selected_idx, option_order)
        # 응답 저장 키: "Q1_PT", "Q1_IS", ...
        st.session_state["responses"][f"{qid}_{religion_code}"] = normalized
        utils.capture_rt_end(rt_key)

        # 다음 페이지로
        current_idx = CR_PAGE_ORDER.index(f"cr_{qid}_{pos}")
        if current_idx + 1 < len(CR_PAGE_ORDER):
            utils.go_to(CR_PAGE_ORDER[current_idx + 1])
        else:
            # CR 블록 종료 → CF 페이지
            utils.go_to("cf")


def render_cr_page(page_key: str) -> None:
    """app.py에서 호출할 단일 진입점.

    page_key 예: "cr_Q3_1" (시나리오 Q3의 2번째 종교)
    """
    parts = page_key.split("_")
    # parts = ["cr", "Q3", "1"]
    qid = parts[1]
    pos = int(parts[2])
    _render_cr_item(qid, pos)


# =============================================================================
# CF — 반사실 확인 (1문항, Q3 직후) — 백그라운드 수집
# =============================================================================

def render_cf() -> None:
    utils.capture_rt_start("cf")
    progress_header(18, "잠시 멈추고 돌아보기")

    st.markdown(config.CF_INTRO)
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
        st.session_state["responses"]["cf_q3_response"] = cf_idx
        utils.capture_rt_end("cf")
        utils.go_to("dq")


# =============================================================================
# DQ — 직접 질문 닻 (1문항) — 백그라운드 수집
# =============================================================================

def render_dq() -> None:
    utils.capture_rt_start("dq")
    progress_header(19, "직접 질문")

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
    progress_header(20, "응답 점검")

    st.markdown(f"#### {config.MC_01_QUESTION}")
    mc01 = st.radio(
        config.MC_01_QUESTION,
        config.MC_01_OPTIONS,
        index=None,
        key="mc01_widget",
        label_visibility="collapsed",
    )

    st.markdown(f"#### {config.MC_02_QUESTION}")
    mc02 = st.radio(
        config.MC_02_QUESTION,
        config.MC_02_OPTIONS,
        index=None,
        key="mc02_widget",
        label_visibility="collapsed",
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
    progress_header(21, "솔직함 점검")

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
