# -*- coding: utf-8 -*-
"""
scoring.py — 결과 계산 로직

본 도구는 측정 도구가 아니므로 '편향 점수' 등은 산출하지 않는다(명세서 §14).
여기서 계산하는 값은 오직 응답자에게 보여줄 자기 인식 자료(감정 온도 범위,
예측-실제 격차, 최고/최저 반응 종교)에 한정된다.
"""
import config


def feeling_range(ft_values: dict) -> int:
    """감정 온도계 5종교 값의 (최댓값 − 최솟값)."""
    if not ft_values:
        return 0
    vals = list(ft_values.values())
    return int(max(vals) - min(vals))


def warmest_coldest(ft_values: dict):
    """가장 따뜻한/차가운 반응을 보인 종교명 반환 (동률이면 첫 항목)."""
    if not ft_values:
        return None, None
    warmest = max(ft_values, key=ft_values.get)
    coldest = min(ft_values, key=ft_values.get)
    return warmest, coldest


def mirror_case(sp01_idx: int, ft_range: int) -> str:
    """
    예측(SP-01) 대비 실제(FT 범위) 비교 → Case A/B/C (명세서 §7).
      A: 예측 ≈ 실제 (실제가 예측 구간 안)
      B: 예측 < 실제 (실제가 예측 구간보다 큼)
      C: 예측 > 실제 (실제가 예측 구간보다 작음)
    """
    if sp01_idx is None:
        return "A"
    opt = config.SP01_OPTIONS[sp01_idx]
    if ft_range > opt["high"]:
        return "B"
    if ft_range < opt["low"]:
        return "C"
    return "A"


def mirror_text(case: str, ft_range: int) -> str:
    """거울 직면 #1 자동 생성 문구."""
    if case == "A":
        return ("본인은 본인의 종교별 반응 차이를 꽤 정확하게 알고 있었네요. "
                "의식적인 자기 인식이 잘 작동하는 패턴입니다.")
    if case == "B":
        return (f"본인은 종교별 반응 차이가 그렇게 클 줄 몰랐다고 답하셨는데, "
                f"실제로는 **{ft_range}점** 차이가 있었네요. 한번 생각해볼 만한 지점입니다.")
    return (f"본인은 종교별 반응이 꽤 차이 날 거라고 예상하셨는데, "
            f"실제로는 **{ft_range}점** 정도였네요. 평소의 자기 이미지와 실제 응답이 "
            f"약간 달랐을 수도 있습니다.")


def prediction_accuracy_text(case: str) -> str:
    """결과 페이지용 '자기 예측 정확도' 한 문장."""
    return {
        "A": "예측과 실제가 잘 맞았습니다 — 본인의 반응 차이를 꽤 정확히 인식하고 있었어요.",
        "B": "실제 차이가 예측보다 컸습니다 — 평소 생각보다 반응 폭이 넓었어요.",
        "C": "실제 차이가 예측보다 작았습니다 — 예상만큼 차이가 크지는 않았어요.",
    }.get(case, "")


def result_summary(responses: dict) -> dict:
    """결과 페이지에서 쓰는 핵심 지표를 한 번에 계산."""
    ft = responses.get("ft", {})
    rng = feeling_range(ft)
    warmest, coldest = warmest_coldest(ft)
    sp_idx = responses.get("sp01")
    case = mirror_case(sp_idx, rng)
    return {
        "ft_range": rng,
        "warmest": warmest,
        "coldest": coldest,
        "case": case,
    }
