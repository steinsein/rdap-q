"""
RDAP 퀵버전 — Google Sheets 저장 모듈

본 모듈은 응답 데이터를 Google Sheets로 안전하게 저장한다. 시트가
연결되어 있지 않거나 secrets가 누락된 경우에도 앱이 죽지 않도록,
실패 시 로컬 JSON 백업을 남기고 사용자 흐름은 그대로 진행한다.

본 도구는 단일 탭(`responses`)으로 운영되며, MT(거울 테스트) 관련
탭은 운영하지 않는다.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import os
import pathlib
from typing import Any

import streamlit as st

import config

logger = logging.getLogger(__name__)


# =============================================================================
# 클라이언트 초기화 (lazy import, 캐시)
# =============================================================================

@st.cache_resource(show_spinner=False)
def init_client():
    """gspread 클라이언트를 초기화한다 (없으면 None).

    secrets.toml에 [gcp_service_account] 섹션이 있어야 한다.
    참고: https://docs.streamlit.io/develop/tutorials/databases/private-gsheet
    """
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError:
        logger.warning("gspread / google-auth가 설치되지 않음. 로컬 백업 모드로 동작.")
        return None

    if "gcp_service_account" not in st.secrets:
        logger.warning("secrets.toml에 [gcp_service_account] 섹션 없음. 로컬 백업 모드.")
        return None

    try:
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_info(
            dict(st.secrets["gcp_service_account"]), scopes=scopes,
        )
        return gspread.authorize(creds)
    except Exception as exc:  # noqa: BLE001
        logger.exception("gspread 인증 실패: %s", exc)
        return None


def _open_sheet():
    """대상 스프레드시트를 연다 (없으면 None)."""
    client = init_client()
    if client is None:
        return None
    sheet_url = st.secrets.get("sheet_url") or st.secrets.get("SHEET_URL")
    sheet_key = st.secrets.get("sheet_key") or st.secrets.get("SHEET_KEY")
    try:
        if sheet_url:
            return client.open_by_url(sheet_url)
        if sheet_key:
            return client.open_by_key(sheet_key)
        logger.warning("sheet_url/sheet_key 모두 누락. 로컬 백업 모드.")
        return None
    except Exception as exc:  # noqa: BLE001
        logger.exception("시트 열기 실패: %s", exc)
        return None


def _ensure_tab(sheet, tab_name: str, headers: list[str]):
    """탭이 없으면 생성하고 헤더를 기록한다. 있으면 그대로 반환."""
    try:
        ws = sheet.worksheet(tab_name)
    except Exception:  # noqa: BLE001
        ws = sheet.add_worksheet(title=tab_name, rows=2000, cols=len(headers) + 5)
        ws.append_row(headers, value_input_option="USER_ENTERED")
        return ws

    # 헤더 점검 — 첫 행이 비어 있으면 헤더를 채워 둔다
    try:
        first_row = ws.row_values(1)
        if not first_row:
            ws.append_row(headers, value_input_option="USER_ENTERED")
    except Exception:  # noqa: BLE001
        pass
    return ws


# =============================================================================
# 스키마
# =============================================================================

# CR 응답 컬럼 동적 생성: q1_pt, q1_is, q1_nr, q2_pt, ..., q4_nr
_CR_RESPONSE_COLS = [
    f"q{sc_idx + 1}_{rel.lower()}"
    for sc_idx in range(len(config.SCENARIOS))
    for rel in config.COMPARISON_RELIGIONS
]
_CR_RT_COLS = [f"rt_{col}_ms" for col in _CR_RESPONSE_COLS]


MAIN_HEADERS = [
    # 메타
    "timestamp", "session_id", "cb_condition",
    # 인구통계
    "age_group", "gender", "region", "religion",
    # CR 정규화 응답 (0~3)
    *_CR_RESPONSE_COLS,
    # CR RT (ms)
    *_CR_RT_COLS,
    # DQ (백그라운드 수집)
    "dq_01_response", "rt_dq_ms",
    # MC
    "mc_01_response", "mc_02_response",
    # FB
    "fb_01_response", "fb_02_text",
    # 품질 플래그
    "rt_anomaly_flags",
    # 산출 점수
    "rdas_score", "rdas_label", "pt_is_deviation",
    "pt_nr_deviation", "is_nr_deviation", "nr_mean_score",
    "dom_public", "dom_work", "dom_private", "dom_media",
    "dominant_domain",
    # 소요 시간
    "total_duration_sec",
]


# =============================================================================
# 저장 함수
# =============================================================================

def _local_backup(tab_name: str, row: dict[str, Any]) -> None:
    """시트 저장 실패 시 호출. /tmp에 JSONL로 누적."""
    backup_dir = pathlib.Path(os.environ.get("RDAP_BACKUP_DIR", "/tmp/rdap_backup"))
    backup_dir.mkdir(parents=True, exist_ok=True)
    fpath = backup_dir / f"{tab_name}.jsonl"
    try:
        with fpath.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
        logger.info("로컬 백업 저장 완료: %s", fpath)
    except Exception as exc:  # noqa: BLE001
        logger.exception("로컬 백업 저장 실패: %s", exc)


def append_response(payload: dict[str, Any]) -> bool:
    """응답 1건을 `responses` 탭에 추가한다.

    payload는 MAIN_HEADERS의 키 일부 또는 전부를 포함해야 한다. 누락 키는
    빈 문자열로 채운다. 시트 접근 실패 시 로컬 백업 후 False 반환.
    """
    payload = dict(payload)
    payload.setdefault(
        "timestamp", dt.datetime.utcnow().isoformat(timespec="seconds") + "Z",
    )

    sheet = _open_sheet()
    if sheet is None:
        _local_backup(config.SHEET_TAB_MAIN, payload)
        return False

    try:
        ws = _ensure_tab(sheet, config.SHEET_TAB_MAIN, MAIN_HEADERS)
        row = [payload.get(h, "") for h in MAIN_HEADERS]
        ws.append_row(row, value_input_option="USER_ENTERED")
        return True
    except Exception as exc:  # noqa: BLE001
        logger.exception("시트 저장 실패, 로컬 백업으로 대체: %s", exc)
        _local_backup(config.SHEET_TAB_MAIN, payload)
        return False
