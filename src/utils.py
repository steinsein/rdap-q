"""
RDAP 퀵버전 — 보조 함수 모음

본 모듈은 다음 기능을 제공한다:
- RT(반응 시간) 캡처 헬퍼 (시작/종료, 페이지 재실행 보호)
- 역균형화 조건 배정 (선택지 forward/reverse + 시나리오별 3종교 순서)
- RT 품질 플래그 산출
- 응답값 정규화 (선택지 인덱스 → 점수 0~3)
- 세션 초기화 / 페이지 전환
"""

from __future__ import annotations

import random
import statistics
import time
import uuid
from typing import Iterable

import streamlit as st

import config


# =============================================================================
# RT 캡처
# =============================================================================

def capture_rt_start(key: str) -> None:
    """페이지 진입 시점을 기록한다.

    Streamlit은 위젯 상호작용 시 스크립트를 재실행한다. 이때 동일 키로
    이 함수가 다시 호출되어도 시작 시점을 갱신하지 않도록 가드를 둔다.
    이렇게 해야 RT가 부풀려지지 않는다.
    """
    if "rt_starts" not in st.session_state:
        st.session_state["rt_starts"] = {}
    if key not in st.session_state["rt_starts"]:
        st.session_state["rt_starts"][key] = time.perf_counter()


def capture_rt_end(key: str) -> int | None:
    """응답 제출 시점을 기록하고 경과 시간(ms)을 반환한다.

    동일 키로 다시 호출되어도 최초 종료 시점의 값을 유지한다.
    """
    if "rt_results" not in st.session_state:
        st.session_state["rt_results"] = {}
    if key in st.session_state["rt_results"]:
        return st.session_state["rt_results"][key]

    start = st.session_state.get("rt_starts", {}).get(key)
    if start is None:
        return None

    elapsed_ms = int((time.perf_counter() - start) * 1000)
    st.session_state["rt_results"][key] = elapsed_ms
    return elapsed_ms


def get_rt(key: str) -> int | None:
    """저장된 RT 값을 반환한다 (없으면 None)."""
    return st.session_state.get("rt_results", {}).get(key)


def check_rt_anomaly(cr_keys: Iterable[str]) -> list[str]:
    """CR RT를 점검해 품질 플래그 목록을 반환한다.

    플래그:
    - rt_too_fast: 1개 이상이 RT_TOO_FAST_MS 미만
    - rt_too_slow: 1개 이상이 RT_TOO_SLOW_MS 초과
    - rt_inconsistent: 전체 RT의 변동계수 < RT_INCONSISTENT_CV
    """
    rts = [get_rt(k) for k in cr_keys]
    rts = [r for r in rts if r is not None]

    flags: list[str] = []
    if not rts:
        return flags

    if any(r < config.RT_TOO_FAST_MS for r in rts):
        flags.append("rt_too_fast")
    if any(r > config.RT_TOO_SLOW_MS for r in rts):
        flags.append("rt_too_slow")

    if len(rts) >= 3:
        mean = statistics.mean(rts)
        if mean > 0:
            cv = statistics.pstdev(rts) / mean
            if cv < config.RT_INCONSISTENT_CV:
                flags.append("rt_inconsistent")

    return flags


# =============================================================================
# 역균형화 — 선택지 순서 + 시나리오별 3종교 제시 순서
# =============================================================================

def assign_option_order() -> str:
    """선택지 순서를 무작위 배정한다 (forward / reverse)."""
    return random.choice(["forward", "reverse"])


def assign_religion_orders(scenarios: list[dict]) -> dict[str, list[str]]:
    """시나리오마다 3종교의 화면 제시 순서를 무작위 셔플한다.

    반환: {"Q1": ["IS", "NR", "PT"], "Q2": ["PT", "IS", "NR"], ...}

    동일 응답자가 모든 시나리오에서 같은 순서로 보면 순서 효과가 시나리오에
    누적되므로, 시나리오마다 독립적으로 셔플한다.
    """
    orders: dict[str, list[str]] = {}
    for sc in scenarios:
        rels = list(config.COMPARISON_RELIGIONS)
        random.shuffle(rels)
        orders[sc["id"]] = rels
    return orders


def build_cb_condition(option_order: str, religion_orders: dict[str, list[str]]) -> str:
    """역균형화 조건을 단일 문자열로 직렬화한다 (시트 저장용).

    예: "forward|Q1:IS-NR-PT|Q2:PT-IS-NR|..."
    """
    parts = [option_order]
    for qid, rels in religion_orders.items():
        parts.append(f"{qid}:{'-'.join(rels)}")
    return "|".join(parts)


# =============================================================================
# 응답값 정규화
# =============================================================================

def normalize_response(selected_idx: int, option_order: str) -> int:
    """선택지 인덱스(0~3)를 정규화 점수(0~3, 폐쇄=고점)로 변환한다.

    forward 조건: ①(0) → 0점, ②(1) → 1점, ③(2) → 2점, ④(3) → 3점
    reverse 조건: 선택지가 역순으로 표시되므로 인덱스를 뒤집어 점수 산출
    """
    if option_order == "reverse":
        return 3 - selected_idx
    return selected_idx


def get_display_options(options: list[str], option_order: str) -> list[str]:
    """역균형화 조건에 따라 화면에 표시할 선택지 순서를 반환한다."""
    if option_order == "reverse":
        return list(reversed(options))
    return list(options)


# =============================================================================
# 세션 초기화
# =============================================================================

def init_session() -> None:
    """세션 상태의 초기 키들을 보장한다.

    재호출 시에는 기존 값을 보존한다 (Streamlit 재실행 안전).
    """
    if "session_id" not in st.session_state:
        st.session_state["session_id"] = str(uuid.uuid4())
    if "option_order" not in st.session_state:
        st.session_state["option_order"] = assign_option_order()
    if "religion_orders" not in st.session_state:
        st.session_state["religion_orders"] = assign_religion_orders(config.SCENARIOS)
    if "cb_condition" not in st.session_state:
        st.session_state["cb_condition"] = build_cb_condition(
            st.session_state["option_order"],
            st.session_state["religion_orders"],
        )
    if "page" not in st.session_state:
        st.session_state["page"] = "consent"
    if "responses" not in st.session_state:
        st.session_state["responses"] = {}
    if "started_at" not in st.session_state:
        st.session_state["started_at"] = time.perf_counter()
    if "rt_starts" not in st.session_state:
        st.session_state["rt_starts"] = {}
    if "rt_results" not in st.session_state:
        st.session_state["rt_results"] = {}


def go_to(page: str) -> None:
    """페이지를 전환한다."""
    st.session_state["page"] = page
    st.rerun()


def total_elapsed_seconds() -> int:
    """설문 시작부터 현재까지 경과 시간(초)을 반환한다."""
    started = st.session_state.get("started_at")
    if started is None:
        return 0
    return int(time.perf_counter() - started)
