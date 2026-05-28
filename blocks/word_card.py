# -*- coding: utf-8 -*-
"""블록 3 — 첫인상 단어 카드 WC-01 (명세서 §5)

종교는 응답자별 역균형화 순서로, 단어 카드 12개는 응답자별 무작위 위치로 제시.
선택된 카드는 강조(primary) 표시. 5종교 모두 선택해야 다음 진행.
"""
import streamlit as st

import config
import state


def render():
    st.subheader("첫인상 단어 카드")
    st.markdown(
        "다음 종교를 떠올렸을 때, **가장 먼저 떠오르는 단어 하나**를 고르세요. "
        "깊이 생각하지 말고 직관적으로, 빠르게."
    )

    wc = state.responses()["wc"]
    cards = state.word_order()

    for religion in state.religion_order():
        st.markdown(f"##### {religion}")
        selected = wc.get(religion)
        # 4열 × 3행 그리드
        for row_start in range(0, len(cards), 4):
            cols = st.columns(4)
            for col, card in zip(cols, cards[row_start:row_start + 4]):
                word = card["word"]
                is_sel = (selected == word)
                if col.button(
                    word,
                    key=f"wc_{religion}_{word}",
                    type="primary" if is_sel else "secondary",
                    use_container_width=True,
                ):
                    wc[religion] = word
                    st.rerun()
        st.write("")

    st.divider()
    complete = len(wc) == len(config.RELIGIONS)
    if not complete:
        st.caption(f"선택 완료: {len(wc)} / {len(config.RELIGIONS)}")
    if st.button("다음", type="primary", disabled=not complete,
                 use_container_width=True):
        state.goto("thermometer")
