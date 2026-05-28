# -*- coding: utf-8 -*-
"""
sheets.py — 응답 익명 저장 (Google Sheets, gspread + 서비스 계정)

자격증명(st.secrets["gcp_service_account"])이 없으면 저장을 건너뛰고
앱은 그대로 동작한다(데모·로컬 테스트용). 컬럼은 build_record()의 키 순서로
평탄화(flat)되어 분석 친화적인 단일 행으로 저장된다(명세서 §12).
"""
from collections import OrderedDict
from datetime import datetime

import streamlit as st

import config
import scoring

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


# ─────────────────────────────────────────────────────────────────────────────
# 레코드 구성 (헤더 = 키, 행 = 값) — 명세서 §12 백엔드 데이터 구조
# ─────────────────────────────────────────────────────────────────────────────
def build_record(response_id: str, responses: dict, block_times: dict,
                  religion_order, relation_order, duration_total: float) -> OrderedDict:
    rec = OrderedDict()
    rec["response_id"] = response_id
    rec["timestamp"] = datetime.now().isoformat(timespec="seconds")
    rec["duration_total_sec"] = round(duration_total, 1)

    # 인구통계
    dm = responses.get("dm", {})
    rec["dm_age"] = dm.get("age", "")
    rec["dm_gender"] = dm.get("gender", "")
    rec["dm_religion"] = dm.get("religion", "")

    # 사전 짐작
    sp_idx = responses.get("sp01")
    rec["sp01_prediction"] = (
        config.SP01_OPTIONS[sp_idx]["label"] if sp_idx is not None else ""
    )

    # 첫인상 단어 (종교별)
    wc = responses.get("wc", {})
    for rel in config.RELIGIONS:
        key = config.RELIGION_KEYS[rel]
        word = wc.get(rel, "")
        rec[f"wc_{key}"] = word
        rec[f"wc_{key}_valence"] = config.WORD_VALENCE.get(word, "")

    # 감정 온도계 (종교별)
    ft = responses.get("ft", {})
    for rel in config.RELIGIONS:
        key = config.RELIGION_KEYS[rel]
        rec[f"ft_{key}"] = ft.get(rel, "")

    summary = scoring.result_summary(responses)
    rec["ft_range"] = summary["ft_range"]
    rec["ft_warmest"] = summary["warmest"] or ""
    rec["ft_coldest"] = summary["coldest"] or ""

    # 거울 직면 #1
    mr_idx = responses.get("mr01")
    rec["mr01_reaction"] = (
        config.MR01_REACTION_OPTIONS[mr_idx] if mr_idx is not None else ""
    )
    rec["mr01_case"] = summary["case"]

    # 일상 가까움 (5종교 × 3관계 = 15셀)
    sd = responses.get("sd", {})
    for rel in config.RELIGIONS:
        rkey = config.RELIGION_KEYS[rel]
        for relation in config.SD_RELATIONS:
            ckey = config.SD_RELATION_KEYS[relation]
            rec[f"sd_{rkey}_{ckey}"] = sd.get((rel, relation), "")

    # 시나리오 카드
    rec["sc01_choice"] = responses.get("sc01") or ""

    # 결과 페이지 메타 응답
    meta_idx = responses.get("result_meta")
    rec["result_meta"] = (
        config.RESULT_META_OPTIONS[meta_idx] if meta_idx is not None else ""
    )

    # 순서·시간 메타
    rec["religion_order"] = " > ".join(religion_order)
    rec["relation_order"] = " > ".join(relation_order)
    for step, sec in block_times.items():
        rec[f"time_{step}"] = sec

    return rec


# ─────────────────────────────────────────────────────────────────────────────
# 저장
# ─────────────────────────────────────────────────────────────────────────────
def _get_worksheet():
    """자격증명이 있으면 워크시트를 반환, 없으면 None."""
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError:
        return None

    if "gcp_service_account" not in st.secrets:
        return None

    creds = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]), scopes=SCOPES
    )
    client = gspread.authorize(creds)

    sheet_cfg = st.secrets.get("sheet", {})
    sheet_name = sheet_cfg.get("name", config.SHEET_NAME)
    ws_name = sheet_cfg.get("worksheet", config.WORKSHEET_NAME)

    spreadsheet = client.open(sheet_name)
    try:
        ws = spreadsheet.worksheet(ws_name)
    except Exception:
        ws = spreadsheet.add_worksheet(title=ws_name, rows=1000, cols=80)
    return ws


def save_response(record: OrderedDict) -> bool:
    """
    record를 한 행으로 추가. 성공 시 True.
    헤더가 비어 있으면 헤더 행을 먼저 기록한다.
    자격증명이 없거나 오류 시 False(앱은 계속 진행).
    """
    try:
        ws = _get_worksheet()
        if ws is None:
            return False

        existing = ws.row_values(1)
        header = list(record.keys())
        if not existing:
            ws.append_row(header, value_input_option="USER_ENTERED")
        elif existing != header:
            # 헤더가 다르면(블록 시간 컬럼 변동 등) 합집합으로 맞춤
            for col in header:
                if col not in existing:
                    existing.append(col)
            ws.update("A1", [existing])
            header = existing

        row = [record.get(col, "") for col in header]
        ws.append_row(row, value_input_option="USER_ENTERED")
        return True
    except Exception as e:  # noqa: BLE001 — 저장 실패가 응답 흐름을 막지 않도록
        st.session_state["_sheet_error"] = str(e)
        return False
