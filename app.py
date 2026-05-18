"""
RDAP 퀵버전 V4 — Streamlit 메인 엔트리

본 파일은 페이지 라우팅과 세션 초기화만 담당한다. 실제 화면 렌더링은
`src/` 하위의 모듈이 수행한다.

페이지 흐름:
    consent → demographics → cr_intro
        → cr_Q1A → cr_Q1B → cr_Q2A → … → cr_Q5B
        → cf → dq → mc → fb
        → results → mt → debriefing

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
from src import questions, results, sheets, utils

# =============================================================================
# 페이지 설정
# =============================================================================

st.set_page_config(
    page_title="RDAP 종교 다양성 태도 프로파일 (퀵버전)",
    page_icon="🪞",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# 모바일 친화 CSS — Plotly 차트의 좌우 여백 조정, 라디오 간격, 한글 폰트
st.markdown(
    """
    <style>
        .block-container { padding-top: 1.2rem; padding-bottom: 2rem; }
        div[data-testid="stRadio"] label { padding: 6px 0; }
        div[data-testid="stMetric"] { background: #F9FAFB; padding: 12px; border-radius: 8px; }
        div[data-testid="stMetricLabel"] { font-size: 12px; color: #6B7280; }
        h1, h2, h3, h4 { font-family: 'Pretendard', -apple-system, system-ui, sans-serif; }
    </style>
    """,
    unsafe_allow_html=True,
)


# =============================================================================
# 세션 초기화 — 가중치는 secrets에서 조정 가능
# =============================================================================

def _version_weights() -> dict[str, float]:
    """secrets 또는 환경 변수에서 유형 가중치를 읽는다. 기본은 A 100%."""
    weights = st.secrets.get("version_weights") if hasattr(st, "secrets") else None
    if weights:
        # toml은 dict 유사 객체로 들어오므로 float 변환
        return {k: float(v) for k, v in weights.items()}
    return {"A": 1.0, "B": 0.0, "C": 0.0}


utils.init_session(_version_weights())


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
    """결과 페이지·MT 응답 후 마지막 화면."""
    # MT 응답 저장 (1회만)
    if not st.session_state.get("saved_mt", False):
        resp = st.session_state["responses"]
        scores = st.session_state.get("computed_scores", {})
        payload = {
            "session_id": st.session_state["session_id"],
            "version": st.session_state["version"],
            "mt_01_response": resp.get("mt_01_response", ""),
            "mt_02_text": resp.get("mt_02_text", ""),
            "result_profile_shown": scores.get("profile_type", ""),
            "result_deviation_shown": scores.get("deviation_total", ""),
        }
        st.session_state["saved_mt"] = sheets.append_mt_response(payload)

    st.title("마무리")
    st.markdown(config.MT_AFTER_MESSAGE)

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
    "demographics": questions.render_demographics,
    "cr_intro": questions.render_cr_intro,
    "cf": questions.render_cf,
    "dq": questions.render_dq,
    "mc": questions.render_mc,
    "fb": questions.render_fb,
    "results": results.render_results,
    "mt": questions.render_mt,
    "debriefing": _page_debriefing,
}

# CR 페이지는 동적 처리
for qid in ("Q1", "Q2", "Q3", "Q4", "Q5"):
    for ab in ("A", "B"):
        key = f"cr_{qid}{ab}"
        # 클로저 트랩 회피를 위해 default arg로 캡처
        PAGE_HANDLERS[key] = (lambda k=key: questions.render_cr_page(k))


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
