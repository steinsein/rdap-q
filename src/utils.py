"""
RDAP 퀵버전 V4 — 보조 함수 모음

본 모듈은 다음 기능을 제공한다:
- RT(반응 시간) 캡처 헬퍼 (시작/종료, 페이지 재실행 보호)
- 응답자 버전 배정 (A/B/C, 가중치 적용)
- 역균형화 조건 배정 (α/β × forward/reverse = 4조건)
- RT 품질 플래그 산출
- 응답값 정규화 (선택지 1~4 → 점수 0~3, 역균형화 보정 포함)
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
# RT 캡처 (V4 §4.1)
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
    """10개 CR RT를 점검해 품질 플래그 목록을 반환한다 (V4 §4.1.5).

    플래그:
    - rt_too_fast: 1개 이상이 1500ms 미만
    - rt_too_slow: 1개 이상이 90000ms 초과
    - rt_inconsistent: 10개 RT의 변동계수 < 0.15
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
# 버전 배정 (V4 §0 — 메인 A 단독 배포가 원칙이나, 백업 B·C 운영 시를 위한 확장)
# =============================================================================

def assign_version(weights: dict[str, float] | None = None) -> str:
    """응답자에게 유형(A/B/C)을 배정한다.

    기본 가중치는 A 100% (메인 단독 배포 원칙). secrets에서 가중치를
    조정해 백업 유형을 점진적으로 투입할 수 있다.
    """
    if weights is None:
        weights = {"A": 1.0, "B": 0.0, "C": 0.0}

    versions = list(weights.keys())
    w = [weights[v] for v in versions]
    if sum(w) <= 0:
        return "A"
    return random.choices(versions, weights=w, k=1)[0]


def assign_counterbalance() -> str:
    """역균형화 조건을 배정한다 (4조건 균등 무작위).

    조건은 두 차원의 곱이다:
    - 페어 내 종교 순서: alpha (A→B) / beta (B→A)
    - 선택지 순서: forward (① 개방 → ④ 폐쇄) / reverse (④ 폐쇄 → ① 개방)
    """
    pair_order = random.choice(["alpha", "beta"])
    option_order = random.choice(["forward", "reverse"])
    return f"{pair_order}_{option_order}"


# =============================================================================
# 응답값 정규화
# =============================================================================

def normalize_response(selected_idx: int, option_order: str) -> int:
    """선택지 인덱스(0~3)를 정규화 점수(0~3, 폐쇄=고점)로 변환한다.

    forward 조건: ①(0) → 0점, ②(1) → 1점, ③(2) → 2점, ④(3) → 3점
    reverse 조건: 선택지 순서가 역전돼 표시되었으므로, 인덱스를 뒤집어 점수 산출
    """
    if option_order == "reverse":
        return 3 - selected_idx
    return selected_idx


def get_display_options(options: list[str], option_order: str) -> list[str]:
    """역균형화 조건에 따라 화면에 표시할 선택지 순서를 반환한다."""
    if option_order == "reverse":
        return list(reversed(options))
    return list(options)


def get_pair_order(pair: tuple[str, str], cb_condition: str) -> tuple[str, str]:
    """역균형화 조건에 따라 비교 쌍의 제시 순서를 반환한다.

    alpha: (A, B), beta: (B, A)
    """
    if cb_condition.startswith("beta"):
        return (pair[1], pair[0])
    return pair


def get_option_order(cb_condition: str) -> str:
    """역균형화 조건에서 option_order 부분을 추출한다."""
    return cb_condition.split("_")[1] if "_" in cb_condition else "forward"


# =============================================================================
# 세션 초기화
# =============================================================================

def init_session(version_weights: dict[str, float] | None = None) -> None:
    """세션 상태의 초기 키들을 보장한다.

    재호출 시에는 기존 값을 보존한다 (Streamlit 재실행 안전).
    """
    if "session_id" not in st.session_state:
        st.session_state["session_id"] = str(uuid.uuid4())
    if "version" not in st.session_state:
        st.session_state["version"] = assign_version(version_weights)
    if "cb_condition" not in st.session_state:
        st.session_state["cb_condition"] = assign_counterbalance()
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
