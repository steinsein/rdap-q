# -*- coding: utf-8 -*-
"""
app.py — RDAP 퀵버전 V7 메인 엔트리

역할은 라우팅에 한정한다. 화면은 blocks/ 모듈, 상태는 state.py,
계산은 scoring.py, 저장은 sheets.py가 담당한다.

실행:  streamlit run app.py
"""
import streamlit as st

import config
import state
import blocks


def main():
    st.set_page_config(
        page_title=config.APP_TITLE,
        page_icon=config.APP_ICON,
        layout="centered",
        initial_sidebar_state="collapsed",
    )

    state.init_state()

    # 본문 진행바 (intro/results 제외 구간에서 표시)
    step = st.session_state.step
    if step not in ("intro", "results"):
        st.progress(state.progress_ratio())

    # step → render 함수 라우팅
    renderer = blocks.RENDERERS.get(step)
    if renderer is None:
        st.error(f"알 수 없는 단계: {step}")
        return
    renderer()


if __name__ == "__main__":
    main()
