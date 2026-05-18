"""
RDAP 퀵버전 — Streamlit 메인 엔트리

본 파일은 페이지 라우팅과 세션 초기화만 담당한다. 실제 화면 렌더링은
`src/` 하위의 모듈이 수행한다.

페이지 흐름:
    consent
        → dm_age → dm_gender → dm_region → dm_religion
        → cr_Q1_0 → cr_Q1_1 → cr_Q1_2
        → cr_Q2_0 → cr_Q2_1 → cr_Q2_2
        → cr_Q3_0 → cr_Q3_1 → cr_Q3_2
        → cr_Q4_0 → cr_Q4_1 → cr_Q4_2
        → cf → dq → mc → fb
        → results → debriefing

종료 페이지:
    declined  : SC-01에서 동의하지 않음
    underage  : SC-02에서 18세 미만

배포 환경:
    Streamlit Community Cloud
    Python 3.12, Streamlit 1.32+
"""

from __future__ import annotations

import streamlit as st

import config
from src import questions, results, utils

# =============================================================================
# 페이지 설정
# =============================================================================

st.set_page_config(
    page_title="RDAP 종교 다양성 태도 프로파일 (퀵버전)",
    page_icon="🪞",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# 모바일 친화 CSS — 한글 자음 짤림 방지를 위해 상단 패딩과 line-height 확보
st.markdown(
    """
    <style>
        .block-container { padding-top: 2.4rem; padding-bottom: 2rem; }
        h1, h2, h3, h4 {
            font-family: 'Pretendard', -apple-system, system-ui, sans-serif;
            line-height: 1.6;
            margin-top: 1.2rem;
        }
        h1 { padding-top: 0.3rem; }
        div[data-testid="stRadio"] label { padding: 6px 0; }
        div[data-testid="stMetric"] {
            background: #F9FAFB;
            padding: 12px;
            border-radius: 8px;
        }
        div[data-testid="stMetricLabel"] { font-size: 12px; color: #6B7280; }
    </style>
    """,
    unsafe_allow_html=True,
)


# =============================================================================
# 세션 초기화
# =============================================================================

utils.init_session()


# =============================================================================
# 종료 페이지
# =============================================================================

def _page_declined() -> None:
    st.title("응답을 종료합니다")
    st.markdown(
        "참여해 주셔서 감사합니다. 본 도구는 동의하신 분에 한해 응답을 수집합니다."
    )


def _page_underage() -> None:
    st.title("응답을 종료합니다")
    st.markdown(
        "본 도구는 만 18세 이상을 대상으로 합니다. 관심 가져 주셔서 감사합니다."
    )


def _page_debriefing() -> None:
    """결과 페이지 이후 마지막 화면."""
    st.title("마무리")
    st.markdown(config.DEBRIEFING_MESSAGE)

    with st.expander("이 도구에 대해 알고 싶다면"):
        st.markdown(
            """
            **RDAP (Religious Diversity Attitude Profile)** 은 종교 다양성에 대한
            태도를 자기 성찰적으로 시각화하는 한국 맥락 교육 도구입니다.

            - 본 결과는 표준화된 심리 검사 결과가 아닙니다.
            - 응답은 익명으로 처리되며, 도구 개선과 학술 연구에 활용됩니다.
            - 결과는 한 시점의 응답이며, 응답자의 정체성을 규정하지 않습니다.

            궁금한 점이 있으시면 도구 개발팀에 문의해 주세요.
            """
        )


# =============================================================================
# 페이지 라우터
# =============================================================================

PAGE_HANDLERS = {
    "consent": questions.render_consent_and_screen,
    "declined": _page_declined,
    "underage": _page_underage,
    # 인구통계 4 페이지
    "dm_age": questions.render_dm_age,
    "dm_gender": questions.render_dm_gender,
    "dm_region": questions.render_dm_region,
    "dm_religion": questions.render_dm_religion,
    # 후속 블록
    "cf": questions.render_cf,
    "dq": questions.render_dq,
    "mc": questions.render_mc,
    "fb": questions.render_fb,
    # 결과·디브리핑
    "results": results.render_results,
    "debriefing": _page_debriefing,
}

# CR 페이지(12개)는 동적 등록
for _key in questions.CR_PAGE_ORDER:
    # 클로저 트랩 회피를 위해 default arg로 캡처
    PAGE_HANDLERS[_key] = (lambda k=_key: questions.render_cr_page(k))


def main() -> None:
    page = st.session_state.get("page", "consent")
    handler = PAGE_HANDLERS.get(page)
    if handler is None:
        st.error(f"알 수 없는 페이지: {page}")
        if st.button("처음으로 돌아가기"):
            st.session_state["page"] = "consent"
            st.rerun()
        return
    handler()


if __name__ == "__main__":
    main()
