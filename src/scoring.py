"""
RDAP 퀵버전 V4 — 점수 산출 로직

본 모듈은 응답 데이터로부터 결과 페이지 표시에 필요한 모든 점수를
산출한다. V4 §10.7의 CF–실제 격차 카테고리 분기, V4 §10.4의 RT 비대칭성
메시지 카테고리도 본 모듈에서 산출한다.

함수는 부수효과를 갖지 않으며 (Streamlit 세션 접근 없음), 입력을 받아
값을 반환한다. 테스트 용이성을 위한 설계다.
"""

from __future__ import annotations

import statistics
from typing import Any

import config


# =============================================================================
# 기본 점수 산출
# =============================================================================

def compute_overall_caution(cr_scores: dict[str, int]) -> int:
    """전반적 신중도 = 10문항(Q1A~Q5B) 점수 합 (0~30).

    cr_scores: {"Q1A": 0~3, "Q1B": 0~3, ..., "Q5A": 0~3, "Q5B": 0~3}
    """
    return sum(cr_scores.values())


def compute_pair_deviations(cr_scores: dict[str, int]) -> dict[str, int]:
    """쌍별 차등 |A − B| 산출. {"Q1": 0~3, ..., "Q5": 0~3}."""
    return {
        qid: abs(cr_scores.get(f"{qid}A", 0) - cr_scores.get(f"{qid}B", 0))
        for qid in ("Q1", "Q2", "Q3", "Q4", "Q5")
    }


def compute_deviation_total(cr_scores: dict[str, int]) -> int:
    """5쌍 차등의 합 (0~15)."""
    return sum(compute_pair_deviations(cr_scores).values())


def compute_domain_deviations(cr_scores: dict[str, int]) -> dict[str, int]:
    """영역별 차등 합. {"public": 0~6, "work": 0~6, "private": 0~3}."""
    pair_dev = compute_pair_deviations(cr_scores)
    totals = {"public": 0, "work": 0, "private": 0}
    for qid, dev in pair_dev.items():
        totals[config.QID_TO_DOMAIN[qid]] += dev
    return totals


def compute_dq_cr_alignment(dq_response: int, deviation_total: int) -> int:
    """자기 보고(DQ) vs 응답 패턴(CR) 일치도 (-3 ~ +3).

    DQ는 1~4 선택. DQ 점수가 낮을수록 "개방적 자기 보고", 높을수록 "신중한
    자기 보고". CR deviation_total이 낮을수록 "일관 응답", 높을수록 "차등 응답".

    음수: 자기 보고는 개방, 실제는 차등 (Devine 패턴)
    양수: 자기 보고는 신중, 실제는 일관 (자기 인식 격차)
    0   : 일치
    """
    # DQ를 4단계 → 1~4. 1=가장 개방, 4=가장 신중.
    # CR deviation 0~15를 4단계 quantile로 환산: 0~3=1, 4~7=2, 8~10=3, 11+=4.
    if deviation_total <= 3:
        cr_level = 1
    elif deviation_total <= 7:
        cr_level = 2
    elif deviation_total <= 10:
        cr_level = 3
    else:
        cr_level = 4

    # 일치도 = DQ 수준 − CR 수준
    # (DQ는 신중↑일수록 4, CR도 차등↑일수록 4. 둘이 같으면 0.)
    return dq_response - cr_level


# =============================================================================
# RT 비대칭성 산출 (V4 §4.5.3)
# =============================================================================

def compute_rt_asymmetry(
    rt_data: dict[str, int],
    scenarios: list[dict[str, Any]],
    cb_condition: str,
) -> dict[str, float | None]:
    """종교 1과 종교 2의 평균 RT, 차이값을 산출한다.

    rt_data: {"q1a_ms": 1234, ..., "q5b_ms": 5678}
    scenarios: 본 응답자에게 표시된 시나리오 목록 (config.SCENARIOS[version])

    역균형화 조건에 따라 어느 쪽이 "원본 페어의 첫 종교"인지가 달라지므로,
    cb_condition을 함께 받는다. alpha면 A→B 순서로 제시, beta면 B→A 순서.
    여기서 "religion1"은 시나리오 정의상 페어의 첫 종교(stem_a의 종교).
    """
    flip = cb_condition.startswith("beta")
    r1_rts: list[int] = []
    r2_rts: list[int] = []

    for sc in scenarios:
        qid = sc["id"].lower()
        rt_first = rt_data.get(f"{qid}a_ms")  # 화면 첫 번째 표시
        rt_second = rt_data.get(f"{qid}b_ms")  # 화면 두 번째 표시

        if rt_first is None or rt_second is None:
            continue

        # 화면 표시 순서 ↔ 원본 페어 순서 매핑
        if flip:
            religion1_rt, religion2_rt = rt_second, rt_first
        else:
            religion1_rt, religion2_rt = rt_first, rt_second

        # 비정상 RT는 제외
        if config.RT_TOO_FAST_MS <= religion1_rt <= config.RT_TOO_SLOW_MS:
            r1_rts.append(religion1_rt)
        if config.RT_TOO_FAST_MS <= religion2_rt <= config.RT_TOO_SLOW_MS:
            r2_rts.append(religion2_rt)

    mean1 = statistics.mean(r1_rts) if r1_rts else None
    mean2 = statistics.mean(r2_rts) if r2_rts else None
    asym: float | None = None
    if mean1 is not None and mean2 is not None:
        asym = abs(mean1 - mean2)

    return {"mean_r1": mean1, "mean_r2": mean2, "asymmetry": asym}


def assign_rt_message_level(rt_asymmetry: float | None) -> str:
    """RT 비대칭성 값을 메시지 카테고리로 변환한다 (V4 §10.4)."""
    if rt_asymmetry is None:
        return "small"
    if rt_asymmetry < config.RT_ASYM_SMALL:
        return "small"
    if rt_asymmetry < config.RT_ASYM_LARGE:
        return "medium"
    return "large"


# =============================================================================
# CF–실제 일치도 (V4 §4.5.4)
# =============================================================================

def compute_cf_actual_match(cf_response: int, q5_deviation: int) -> str:
    """CF 응답과 실제 Q5 격차의 일치도 카테고리를 산출한다.

    cf_response: 1~4 (1=똑같이, 2=한 단계, 3=두 단계 이상, 4=모르겠다)
    q5_deviation: |Q5A − Q5B| (0~3)
    """
    if cf_response == 4:
        return "meta_uncertain"

    if cf_response == 1:
        return "match_consistent" if q5_deviation <= 1 else "mismatch_underestimate"

    if cf_response == 2:
        return "mismatch_overestimate" if q5_deviation <= 1 else "match_one_step"

    if cf_response == 3:
        return "match_strong" if q5_deviation >= 2 else "mismatch_overestimate"

    return "meta_uncertain"


# =============================================================================
# 프로파일 라벨 배정 (V3 §4.2 낙인 회피 + V4 §10.8 통합 메시지)
# =============================================================================

def assign_profile(
    deviation_total: int,
    dq_cr_alignment: int,
    domain_deviations: dict[str, int],
) -> str:
    """5유형 프로파일 라벨 중 하나의 키를 반환한다.

    분기 기준 (대략):
    - deviation_total ≤ 3 그리고 |alignment| ≤ 1: consistent_open
    - deviation_total ≥ 8 그리고 alignment ≥ 2: consistent_caution
    - deviation_total ≥ 6 그리고 alignment ≤ -2: devine_signature
    - deviation_total ≤ 5 그리고 alignment ≥ 2: self_aware_diff
    - 그 외: mixed
    """
    if deviation_total <= 3 and abs(dq_cr_alignment) <= 1:
        return "consistent_open"
    if deviation_total >= 8 and dq_cr_alignment >= 2:
        return "consistent_caution"
    if deviation_total >= 6 and dq_cr_alignment <= -2:
        return "devine_signature"
    if deviation_total <= 5 and dq_cr_alignment >= 2:
        return "self_aware_diff"
    return "mixed"


def get_dominant_domain(domain_deviations: dict[str, int]) -> str:
    """가장 차등이 큰 영역의 키를 반환한다. 최대값 동률이면 사전 순."""
    return max(domain_deviations.items(), key=lambda kv: (kv[1], -ord(kv[0][0])))[0]


# =============================================================================
# 통합 산출 — 한 번에 모든 점수 계산
# =============================================================================

def compute_all_scores(
    cr_scores: dict[str, int],
    dq_response: int,
    cf_response: int,
    rt_data: dict[str, int],
    scenarios: list[dict[str, Any]],
    cb_condition: str,
) -> dict[str, Any]:
    """결과 페이지 표시에 필요한 모든 점수를 산출해 단일 딕셔너리로 반환.

    이 함수가 본 모듈의 진입점이다. sheets.append_response()도 본 결과를
    저장 행에 펼쳐 기록한다.
    """
    overall_caution = compute_overall_caution(cr_scores)
    pair_dev = compute_pair_deviations(cr_scores)
    deviation_total = sum(pair_dev.values())
    domain_dev = compute_domain_deviations(cr_scores)
    dq_align = compute_dq_cr_alignment(dq_response, deviation_total)

    rt_asym = compute_rt_asymmetry(rt_data, scenarios, cb_condition)
    rt_level = assign_rt_message_level(rt_asym["asymmetry"])

    cf_match = compute_cf_actual_match(cf_response, pair_dev["Q5"])
    profile = assign_profile(deviation_total, dq_align, domain_dev)
    dominant = get_dominant_domain(domain_dev)

    return {
        "overall_caution": overall_caution,
        "deviation_total": deviation_total,
        "pair_deviations": pair_dev,
        "domain_deviations": domain_dev,
        "dq_cr_alignment": dq_align,
        "rt_asymmetry": rt_asym,
        "rt_message_level": rt_level,
        "cf_actual_match": cf_match,
        "profile_type": profile,
        "dominant_domain": dominant,
    }
