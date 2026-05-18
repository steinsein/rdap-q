"""
RDAP 퀵버전 — 점수 산출 로직

본 모듈은 응답 데이터로부터 결과 페이지 표시에 필요한 모든 점수를 산출한다.
핵심 산출 지표는 RDAS(Religious Diversity Acceptance Score)로,
PT vs IS 차등을 0~100점으로 환산한 단일 지표다.

함수는 부수효과를 갖지 않으며(Streamlit 세션 접근 없음), 입력을 받아 값을
반환한다. 테스트 용이성을 위한 설계다.

NR(신종교) 응답은 RDAS 산출에서 제외하며, 참고 정보로만 표시한다
(개선 방향 권고서 §2.4 참조).
"""

from __future__ import annotations

import statistics
from typing import Any

import config


# =============================================================================
# 기본 점수 산출
# =============================================================================

def pair_deviation(
    cr_scores: dict[str, int],
    qid: str,
    pair: tuple[str, str],
) -> int:
    """특정 시나리오에서 두 종교 간 차등 |X − Y| 산출.

    cr_scores: {"Q1_PT": 0~3, "Q1_IS": 0~3, "Q1_NR": 0~3, ...}
    """
    a = cr_scores.get(f"{qid}_{pair[0]}", 0)
    b = cr_scores.get(f"{qid}_{pair[1]}", 0)
    return abs(a - b)


def compute_pair_deviations(
    cr_scores: dict[str, int],
    pair: tuple[str, str],
) -> dict[str, int]:
    """모든 시나리오에 대해 두 종교 간 차등 합산. 시나리오별 차등 딕셔너리 반환."""
    return {
        sc["id"]: pair_deviation(cr_scores, sc["id"], pair)
        for sc in config.SCENARIOS
    }


def compute_domain_deviations(
    cr_scores: dict[str, int],
    pair: tuple[str, str] = config.RDAS_PAIR,
) -> dict[str, int]:
    """영역별 차등 합. 본 도구는 영역당 1 시나리오이므로 곧 시나리오 차등과 같다."""
    pair_dev = compute_pair_deviations(cr_scores, pair)
    totals = {dom: 0 for dom in config.DOMAIN_ORDER}
    for qid, dev in pair_dev.items():
        totals[config.QID_TO_DOMAIN[qid]] += dev
    return totals


# =============================================================================
# RDAS 산출
# =============================================================================

def compute_rdas(cr_scores: dict[str, int]) -> dict[str, Any]:
    """RDAS(0~100) 및 라벨을 산출한다.

    공식:
        pt_is_deviation = ∑ |Q*_PT − Q*_IS| (4 시나리오 합산, 범위 0~12)
        RDAS = round(100 × (1 − pt_is_deviation / 12))

    반환:
        {
            "score": 0~100 정수,
            "pt_is_deviation": 0~12 정수,
            "label_key": "consistent" | "partial_diff" | ...,
            "label_name": 한글 라벨,
            "label_message": 한 줄 해석 메시지,
            "color": HEX 색상 코드,
        }
    """
    pt_is_dev_pairs = compute_pair_deviations(cr_scores, config.RDAS_PAIR)
    pt_is_total = sum(pt_is_dev_pairs.values())
    max_dev = config.RDAS_MAX_DEVIATION

    rdas = round(100 * (1 - pt_is_total / max_dev))
    rdas = max(0, min(100, rdas))  # 안전 클램프

    label_key = _assign_rdas_label(rdas)
    label = config.RDAS_LABELS[label_key]
    color = config.RDAS_COLOR[label_key]

    return {
        "score": rdas,
        "pt_is_deviation": pt_is_total,
        "label_key": label_key,
        "label_name": label["name"],
        "label_message": label["message"],
        "color": color,
    }


def _assign_rdas_label(rdas: int) -> str:
    """RDAS 점수를 5단계 라벨 키로 매핑한다."""
    for key, spec in config.RDAS_LABELS.items():
        if spec["min"] <= rdas <= spec["max"]:
            return key
    # 정의되지 않은 점수 (이론상 도달 불가) — 안전 fallback
    return "domain_diff"


# =============================================================================
# NR 참고 정보 산출
# =============================================================================

def compute_nr_reference(cr_scores: dict[str, int]) -> dict[str, int]:
    """NR과 다른 두 종교 간 차등을 산출한다 (참고 정보용).

    반환:
        {
            "pt_nr_deviation": ∑ |Q*_PT − Q*_NR|,
            "is_nr_deviation": ∑ |Q*_IS − Q*_NR|,
            "nr_mean_score":   NR 응답의 4 시나리오 평균 점수 (0~3),
        }
    """
    pt_nr_pairs = compute_pair_deviations(cr_scores, ("PT", "NR"))
    is_nr_pairs = compute_pair_deviations(cr_scores, ("IS", "NR"))
    nr_scores = [cr_scores.get(f"{sc['id']}_NR", 0) for sc in config.SCENARIOS]

    return {
        "pt_nr_deviation": sum(pt_nr_pairs.values()),
        "is_nr_deviation": sum(is_nr_pairs.values()),
        "nr_mean_score": (
            round(statistics.mean(nr_scores), 2) if nr_scores else 0
        ),
    }


# =============================================================================
# 영역별 dominant 산출
# =============================================================================

def get_dominant_domain(domain_deviations: dict[str, int]) -> str:
    """가장 차등이 큰 영역의 키를 반환한다.

    동률일 경우 config.DOMAIN_ORDER 기준 앞 순위를 선택.
    """
    best_dev = max(domain_deviations.values()) if domain_deviations else 0
    for dom in config.DOMAIN_ORDER:
        if domain_deviations.get(dom, 0) == best_dev:
            return dom
    return config.DOMAIN_ORDER[0]


# =============================================================================
# 통합 산출 — 한 번에 모든 점수 계산
# =============================================================================

def compute_all_scores(cr_scores: dict[str, int]) -> dict[str, Any]:
    """결과 페이지·시트 저장에 필요한 모든 점수를 산출해 단일 딕셔너리로 반환.

    cr_scores: {"Q1_PT": 0~3, "Q1_IS": 0~3, "Q1_NR": 0~3, ..., "Q4_NR": 0~3}
    """
    rdas = compute_rdas(cr_scores)
    domain_dev = compute_domain_deviations(cr_scores, config.RDAS_PAIR)
    nr_ref = compute_nr_reference(cr_scores)
    dominant = get_dominant_domain(domain_dev)

    return {
        "rdas_score": rdas["score"],
        "rdas_label_key": rdas["label_key"],
        "rdas_label_name": rdas["label_name"],
        "rdas_label_message": rdas["label_message"],
        "rdas_color": rdas["color"],
        "pt_is_deviation": rdas["pt_is_deviation"],
        "domain_deviations": domain_dev,
        "dominant_domain": dominant,
        "nr_reference": nr_ref,
    }
