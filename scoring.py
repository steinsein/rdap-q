# -*- coding: utf-8 -*-
"""
scoring.py — 결과 계산 로직

본 도구는 측정 도구가 아니므로 '편향 점수'·'등급' 등은 산출하지 않는다(명세서 §14).
산출하는 값은 응답자에게 보여줄 자기 인식 자료에 한정되며, 모든 종합치는 '점수/등급'이
아니라 자기 성찰용 '위치/성향'으로 제시한다.

V7.3 — 응답을 항목별로 되비추는 대신, 여러 문항을 하나로 합성해 태도를 요약한다.
  핵심 수식: 종교별 '종합 수용도' A_r 를 태도의 3요소 모델로 계산한다.
      A_r = (0.4·정서 + 0.4·행동 + 0.2·인지) / (가용 가중치 합)
        · 정서(affect)   = 감정 온도 FT_r / 100              ∈ [0,1]
        · 행동(behavior) = 일상 가까움 평균(1~4) → (m−1)/3    ∈ [0,1]
        · 인지(cognition)= 첫인상 단어 valence(긍1·중0.5·부0) ∈ [0,1]
      (Stangor 등(1991)에 따라 정서·행동을 단일 단어 인지보다 높게 가중)
  이 A_r 로부터 두 축을 도출한다.
      · 개방성(openness)        = 100 · mean_r(A_r)         (50=중립 기준선)
      · 차등성(differentiation) = 100 · (max A_r − min A_r) (0=모두 동일)
  두 축 위의 위치가 곧 '종교 다양성 태도 지도'이다. 근거 틀: 사회적 거리 척도
  (Bogardus, 1933), 태도의 3요소 모델, 사회정체성 이론의 내집단/외집단 차등.
"""
import config


# ─────────────────────────────────────────────────────────────────────────────
# 기본 지표
# ─────────────────────────────────────────────────────────────────────────────
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
    """예측(SP-01) 대비 실제(FT 범위) 비교 → Case A/B/C (명세서 §7)."""
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
    """결과 페이지·저장에서 쓰는 핵심 지표."""
    ft = responses.get("ft", {})
    rng = feeling_range(ft)
    warmest, coldest = warmest_coldest(ft)
    sp_idx = responses.get("sp01")
    case = mirror_case(sp_idx, rng)
    return {"ft_range": rng, "warmest": warmest, "coldest": coldest, "case": case}


# ─────────────────────────────────────────────────────────────────────────────
# 일상 가까움(SD-01) 집계
# ─────────────────────────────────────────────────────────────────────────────
def _mean(vals):
    vals = [v for v in vals if v is not None]
    return sum(vals) / len(vals) if vals else None


def sd_means_by_religion(sd: dict) -> dict:
    """종교별 일상 가까움 평균(1~4). 3관계 평균."""
    out = {}
    for rel in config.RELIGIONS:
        m = _mean([sd.get((rel, r)) for r in config.SD_RELATIONS])
        if m is not None:
            out[rel] = m
    return out


# ─────────────────────────────────────────────────────────────────────────────
# 합성 수식 (V7.3)
# ─────────────────────────────────────────────────────────────────────────────
_VALENCE_SCORE = {"positive": 1.0, "neutral": 0.5, "negative": 0.0}


def religion_acceptance(responses: dict) -> dict:
    """
    종교별 종합 수용도 A_r ∈ [0,1].
    정서(감정 온도)·행동(일상 가까움)·인지(첫인상 단어)를 0~1로 환산해 가중 평균한다.
    일부 응답이 비어 있어도 가용한 요소만으로 가중 정규화한다.
    """
    ft = responses.get("ft", {})
    sd_rel = sd_means_by_religion(responses.get("sd", {}))
    wc = responses.get("wc", {})

    out = {}
    for r in config.RELIGIONS:
        num = 0.0
        wsum = 0.0
        if r in ft:
            num += 0.4 * (ft[r] / 100.0)          # 정서
            wsum += 0.4
        if r in sd_rel:
            num += 0.4 * ((sd_rel[r] - 1) / 3.0)  # 행동
            wsum += 0.4
        v = _VALENCE_SCORE.get(config.WORD_VALENCE.get(wc.get(r)))
        if v is not None:
            num += 0.2 * v                        # 인지
            wsum += 0.2
        if wsum > 0:
            out[r] = num / wsum
    return out


def attitude_position(responses: dict):
    """
    종교 다양성 태도 지도의 좌표·성향.
      openness        : 100·평균 수용도 (50=중립 기준선)
      differentiation : 100·(최대−최소 수용도) (0=모두 동일)
      o_band / d_band : 밴드 서술어
      tendency        : 사분면 성향명 (개방성 50, 차등성 30 기준)
      acceptance      : 종교별 A_r (0~1)
    """
    A = religion_acceptance(responses)
    if not A:
        return None
    vals = list(A.values())
    openness = 100.0 * (sum(vals) / len(vals))
    differentiation = 100.0 * (max(vals) - min(vals))

    if openness >= 55:
        o_band = "열려 있는 편"
    elif openness <= 45:
        o_band = "거리를 두는 편"
    else:
        o_band = "중간"

    if differentiation >= 30:
        d_band = "뚜렷이 갈리는 편"
    elif differentiation <= 15:
        d_band = "고른 편"
    else:
        d_band = "중간"

    high_open = openness >= 50
    high_diff = differentiation >= 30
    if high_open and not high_diff:
        tendency = "고르게 열린 시선"
    elif high_open and high_diff:
        tendency = "선택적으로 열린 시선"
    elif (not high_open) and (not high_diff):
        tendency = "고르게 거리를 둔 시선"
    else:
        tendency = "선별적으로 경계하는 시선"

    return {
        "openness": round(openness),
        "differentiation": round(differentiation),
        "o_band": o_band,
        "d_band": d_band,
        "tendency": tendency,
        "acceptance": A,
    }


def acceptance_extremes(responses: dict):
    """종합 수용도가 가장 높은/낮은 종교 (동률이면 첫 항목)."""
    A = religion_acceptance(responses)
    if not A:
        return None, None
    return max(A, key=A.get), min(A, key=A.get)


def affect_behavior(responses: dict) -> list:
    """종교별 정서(따뜻함 0~100) vs 행동(가까움 0~100)."""
    ft = responses.get("ft", {})
    sd_rel = sd_means_by_religion(responses.get("sd", {}))
    rows = []
    for rel in config.RELIGIONS:
        if rel in ft and rel in sd_rel:
            rows.append({
                "religion": rel,
                "warmth": int(ft[rel]),
                "closeness": int(round((sd_rel[rel] - 1) / 3 * 100)),
            })
    return rows


def feeling_distance_gap(responses: dict):
    """따뜻하게 느끼지만 가까이엔 가장 신중한 종교(느낌−거리 격차 최대). 임계 미만이면 None."""
    rows = affect_behavior(responses)
    if not rows:
        return None
    best = max(rows, key=lambda r: r["warmth"] - r["closeness"])
    return best["religion"] if (best["warmth"] - best["closeness"]) >= 25 else None


def closing_religion(responses: dict):
    """이웃 → 결혼 상대로 갈 때 편안함이 가장 크게 떨어지는 종교(1점 이상). 없으면 None."""
    sd = responses.get("sd", {})
    far = config.SD_RELATIONS[0]
    near = config.SD_RELATIONS[-1]
    drops = []
    for r in config.RELIGIONS:
        a, b = sd.get((r, far)), sd.get((r, near))
        if a is not None and b is not None:
            drops.append((r, a - b))
    if not drops:
        return None
    r, d = max(drops, key=lambda x: x[1])
    return r if d >= 1 else None


def valence_counts(responses: dict) -> dict:
    """첫인상 단어의 정서가 분포. nonpos = 긍정이 아닌 단어가 떠오른 종교 목록."""
    wc = responses.get("wc", {})
    counts = {"positive": 0, "neutral": 0, "negative": 0}
    nonpos = []
    for rel in config.RELIGIONS:
        word = wc.get(rel)
        v = config.WORD_VALENCE.get(word)
        if v in counts:
            counts[v] += 1
            if v != "positive":
                nonpos.append((rel, word))
    return {"counts": counts, "nonpos": nonpos}
