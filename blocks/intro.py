# -*- coding: utf-8 -*-
"""블록 0 — 안내·동의 (명세서 §2)"""
import streamlit as st

import config
import state


def render():
    st.title(f"{config.APP_ICON} {config.APP_TITLE}")
    st.caption(f"— {config.APP_SUBTITLE}")

    st.markdown(
        """
이것은 채점되는 시험이 아닙니다.
종교 다양성에 대한 본인의 평소 시선을 약 **5분** 동안 다양한 방식으로 들여다보는
자기 탐구 경험입니다.

- 정답은 없습니다. 직관적으로, 빠르게 답해주세요.
- 점수·등급은 산출되지 않습니다.
- 응답은 익명으로 처리되며, 결과는 본인만 볼 수 있습니다.
- 솔직할수록 자기 발견의 깊이가 깊어집니다.
        """
    )

    st.divider()
    if st.button("시작하기", type="primary", use_container_width=True):
        state.goto("demographics")
