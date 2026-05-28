# -*- coding: utf-8 -*-
"""블록 4 — 감정 온도계 FT-01 (명세서 §6)

5개 종교 가로 슬라이더(0~100, 기본 50). 종교 순서는 역균형화 적용.
"""
import streamlit as st

import config
import state


def render():
    st.subheader("감정 온도계")
    st.markdown(
        "다음 종교에 대한 본인의 전반적인 감정 온도를 슬라이더로 표시해주세요.\n\n"
        "**0 = 매우 차갑게  /  50 = 중립  /  100 = 매우 따뜻하게**"
    )

    ft = state.responses()["ft"]
    for religion in state.religion_order():
        val = st.slider(
            religion,
            min_value=config.FT_MIN,
            max_value=config.FT_MAX,
            value=ft.get(religion, config.FT_DEFAULT),
            key=f"ft_{religion}",
        )
        ft[religion] = val

    st.divider()
    if st.button("다음", type="primary", use_container_width=True):
        state.goto("mirror")
