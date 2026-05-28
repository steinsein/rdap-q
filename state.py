# -*- coding: utf-8 -*-
"""
state.py — 세션 상태 관리, 역균형화, 시간 측정, 페이지 이동

st.session_state에 응답·순서·시간을 보관한다. 모든 블록은 여기 정의된
헬퍼(get_responses / goto / religion_order 등)를 통해 상태에 접근한다.
"""
import time
import uuid
import random

import streamlit as st

import config

# 진행 순서 (intro/results 포함)
STEP_ORDER = [
    "intro",
    "demographics",
    "prediction",
    "word_card",
    "thermometer",
    "mirror",
    "social_distance",
    "scenario",
    "results",
]

# 진행바 표시 대상(본문 응답 지점). intro/results 제외.
BODY_STEPS = STEP_ORDER[1:-1]


def _build_religion_order():
    """응답자별 종교 제시 순서 생성 (config.COUNTERBALANCE_MODE)."""
    base = config.RELIGIONS.copy()
    if config.COUNTERBALANCE_MODE == "reverse":
        # 정순/역순 중 무작위 배정 (counterbalancing)
        return base if random.random() < 0.5 else list(reversed(base))
    # 기본값: 무작위 셔플
    random.shuffle(base)
    return base


def init_state():
    """최초 진입 시 1회 초기화."""
    if st.session_state.get("initialized"):
        return

    st.session_state.initialized = True
    st.session_state.step = "intro"
    st.session_state.response_id = str(uuid.uuid4())
    st.session_state.start_ts = time.time()
    st.session_state.block_enter_ts = time.time()

    # 응답 저장소
    st.session_state.responses = {
        "dm": {},          # age / gender / religion
        "sp01": None,      # 사전 짐작 선택지 index (0~3)
        "wc": {},          # 종교 -> 단어
        "ft": {},          # 종교 -> 0~100
        "mr01": None,      # 거울 직면 반응 index
        "sd": {},          # (종교, 관계) -> 1~4
        "sc01": None,      # 시나리오 선택 (라벨)
        "result_meta": None,
    }
    st.session_state.block_times = {}     # step -> 초
    st.session_state.saved = False

    # ── 역균형화: 응답자별 순서 (본문 블록 전반에 일관 적용) ──
    st.session_state.religion_order = _build_religion_order()

    relations = config.SD_RELATIONS.copy()
    random.shuffle(relations)
    st.session_state.relation_order = relations

    word_order = config.WORD_CARDS.copy()
    random.shuffle(word_order)
    st.session_state.word_order = word_order


# ── 접근 헬퍼 ────────────────────────────────────────────────────────────────
def responses():
    return st.session_state.responses


def religion_order():
    return st.session_state.religion_order


def relation_order():
    return st.session_state.relation_order


def word_order():
    return st.session_state.word_order


def goto(next_step):
    """현재 블록의 소요 시간을 기록하고 다음 블록으로 이동."""
    now = time.time()
    current = st.session_state.step
    st.session_state.block_times[current] = round(now - st.session_state.block_enter_ts, 1)
    st.session_state.block_enter_ts = now
    st.session_state.step = next_step
    st.rerun()


def progress_ratio():
    """본문 진행률(0.0~1.0). intro=0, results=1."""
    step = st.session_state.step
    if step == "intro":
        return 0.0
    if step == "results":
        return 1.0
    idx = BODY_STEPS.index(step)
    return (idx + 1) / (len(BODY_STEPS) + 1)
