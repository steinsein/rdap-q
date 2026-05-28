# -*- coding: utf-8 -*-
"""블록 5 — 거울 직면 #1 MR-01 (명세서 §7)

SP-01(예측)과 FT-01(실제 범위)을 비교해 Case A/B/C 분기 문구를 즉시 제시하고,
응답자의 반응을 단일 선택으로 수집한다.
"""
import streamlit as st

import config
import scoring
import state


def render():
    st.subheader("잠깐 멈춰서, 본인의 응답을 한번 볼게요")

    resp = state.responses()
    sp_idx = resp.get("sp01")
    ft = resp.get("ft", {})
    rng = scoring.feeling_range(ft)
    case = scoring.mirror_case(sp_idx, rng)

    pred_label = config.SP01_OPTIONS[sp_idx]["label"] if sp_idx is not None else "—"

    col1, col2 = st.columns(2)
    col1.metric("예측한 종교 간 차이", pred_label.split("(")[0].strip())
    col2.metric("실제 종교 간 차이", f"{rng}점")

    st.info(scoring.mirror_text(case, rng))

    st.markdown("**이 결과를 보고 어떻게 느끼시나요?**")
    choice = st.radio("반응", config.MR01_REACTION_OPTIONS, index=None,
                      label_visibility="collapsed", key="mr01")

    st.divider()
    selected = choice is not None
    if st.button("다음", type="primary", disabled=not selected,
                 use_container_width=True):
        resp["mr01"] = config.MR01_REACTION_OPTIONS.index(choice)
        state.goto("social_distance")
