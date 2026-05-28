# -*- coding: utf-8 -*-
"""블록 7 — 시나리오 카드 SC-01 (명세서 §9)

①~⑤ 종교 체험 선택지는 역균형화 순서, ⑥·⑦(균등/관심 없음)은 뒤에 고정 배치.
"""
import streamlit as st

import config
import state


def render():
    st.subheader("시나리오 카드")
    st.markdown(
        "만약 다음 주말에 종교 문화 체험 행사에 **무료로 한 군데** 참여할 수 있다면, "
        "어디를 고르시겠어요?"
    )

    # ①~⑤ 역균형화 종교 선택지 + ⑥·⑦ 고정
    religion_opts = [config.SC01_EXPERIENCE[r] for r in state.religion_order()]
    options = religion_opts + config.SC01_FIXED_OPTIONS

    choice = st.radio("선택", options, index=None,
                      label_visibility="collapsed", key="sc01")

    st.divider()
    selected = choice is not None
    if st.button("결과 보기", type="primary", disabled=not selected,
                 use_container_width=True):
        state.responses()["sc01"] = choice
        state.goto("results")
