# -*- coding: utf-8 -*-
"""블록 1 — 인구통계 DM (명세서 §3)"""
import streamlit as st

import config
import state


def render():
    st.subheader("기본 정보")
    st.caption("3문항 · 약 30초")

    age = st.radio("본인의 연령대는?", config.DM01_AGE_OPTIONS,
                   index=None, horizontal=True, key="dm_age")
    gender = st.radio("본인의 성별은?", config.DM02_GENDER_OPTIONS,
                      index=None, horizontal=True, key="dm_gender")
    # DM-03은 역균형화 제외(자기보고). 기본 6항목 순서 고정.
    religion = st.radio("본인의 종교는?", config.DM03_OPTIONS,
                        index=None, horizontal=True, key="dm_religion")

    st.divider()
    complete = all(v is not None for v in (age, gender, religion))
    if st.button("다음", type="primary", disabled=not complete,
                 use_container_width=True):
        dm = state.responses()["dm"]
        dm["age"] = age
        dm["gender"] = gender
        dm["religion"] = religion
        state.goto("prediction")
