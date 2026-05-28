# -*- coding: utf-8 -*-
"""블록 2 — 사전 짐작 SP-01 (명세서 §4)"""
import streamlit as st

import config
import state


def render():
    st.subheader("먼저, 한 가지만 짐작해보실래요?")

    st.markdown(
        "만약 본인이 **다음의 종교**에 대한 감정 온도를 0~100점 척도로 매긴다면, "
        "종교별 점수 사이에 얼마나 차이가 있을 것 같으세요?"
        "_예: 어떤 종교에는 80점, 다른 종교에는 40점을 매긴다면 두 점수 사이에는 "
        "40점 차이가 있는 셈입니다._"
    )

    labels = [opt["label"] for opt in config.SP01_OPTIONS]
    choice = st.radio("예상 차이", labels, index=None,
                      label_visibility="collapsed", key="sp01")

    st.divider()
    selected = choice is not None
    if st.button("다음", type="primary", disabled=not selected,
                 use_container_width=True):
        state.responses()["sp01"] = labels.index(choice)
        state.goto("word_card")
