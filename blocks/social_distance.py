# -*- coding: utf-8 -*-
"""블록 6 — 일상 가까움 매트릭스 SD-01 (명세서 §8)

5(종교) × 3(관계) 매트릭스. 각 셀은 이모지 4점 척도(😊🙂😐😟).
행(종교)·열(관계) 모두 응답자별 역균형화 순서 적용.
"""
import streamlit as st

import config
import state


def _emoji_options():
    return [f"{s['emoji']} {s['label']}" for s in config.SD_SCALE]


def render():
    st.subheader("일상 가까움")
    st.markdown(
        "다음 종교의 신자가 본인 인생의 여러 자리에 들어왔을 때, "
        "얼마나 편안할 것 같으세요? 각 칸에서 하나를 선택해주세요."
    )
    st.caption("😊 매우 편안 · 🙂 괜찮음 · 😐 약간 거리감 · 😟 부담스러움")

    sd = state.responses()["sd"]
    relations = state.relation_order()
    options = _emoji_options()
    emoji_value = {f"{s['emoji']} {s['label']}": s["value"] for s in config.SD_SCALE}

    for religion in state.religion_order():
        st.markdown(f"##### {religion}")
        cols = st.columns(len(relations))
        for col, relation in zip(cols, relations):
            with col:
                cur = sd.get((religion, relation))
                idx = None
                if cur is not None:
                    # 저장된 값(1~4)을 라벨 인덱스로 환산
                    for i, opt in enumerate(options):
                        if emoji_value[opt] == cur:
                            idx = i
                            break
                choice = st.radio(
                    relation,
                    options,
                    index=idx,
                    key=f"sd_{religion}_{relation}",
                )
                if choice is not None:
                    sd[(religion, relation)] = emoji_value[choice]
        st.write("")

    st.divider()
    total_cells = len(config.RELIGIONS) * len(config.SD_RELATIONS)
    complete = len(sd) == total_cells
    if not complete:
        st.caption(f"응답 완료: {len(sd)} / {total_cells} 칸")
    if st.button("다음", type="primary", disabled=not complete,
                 use_container_width=True):
        state.goto("scenario")
