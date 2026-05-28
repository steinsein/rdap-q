# -*- coding: utf-8 -*-
"""
scoring.py — 결과 계산 로직

본 도구는 측정 도구가 아니므로 '편향 점수'·'등급' 등은 산출하지 않는다(명세서 §14).
여기서 계산하는 값은 오직 응답자에게 보여줄 자기 인식 자료(감정 온도 범위,
예측-실제 격차, 최고/최저 반응 종교, 그리고 본인 응답의 구조적 '특성')에 한정된다.

V7.2 — '특성 분석'을 문장 서술이 아니라 '시각화용 수치'로 산출한다.
  results.py가 이 수치를 차트로 렌더링한다. 근거 틀: 사회적 거리 척도
  (Bogardus, 1933)의 친밀성 위계, 태도의 3요소 모델(정서 vs 행동),
  사회정체성 이론의 내집단/외집단 차등.
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


# ─────────────────────────────────────────────────────────────────────────────
# 일상 가까움(SD-01) 집계 — 특성 분석의 기초 (1~4 척도)
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


def sd_by_relation(sd: dict) -> dict:
    """
    관계(친밀도)별 집계 반환.
      {관계: {"mean": 종교 평균, "spread": 종교 간 (최대-최소)}}
    SD_RELATIONS 순서는 친밀도 오름차순(이웃 → 동료 → 결혼 상대)을 가정한다.
    """
    out = {}
    for relation in config.SD_RELATIONS:
        vals = [sd.get((rel, relation)) for rel in config.RELIGIONS]
        vals = [v for v in vals if v is not None]
        if vals:
            out[relation] = {
                "mean": sum(vals) / len(vals),
                "spread": max(vals) - min(vals),
            }
    return out


# ─────────────────────────────────────────────────────────────────────────────
# 특성 분석 (V7.2) — 시각화용 수치 산출
#   모든 함수는 차트가 바로 쓸 수 있는 숫자/구조를 반환한다(문장 아님).
#   점수·등급·정상 범위 같은 평가 개념은 사용하지 않는다.
# ─────────────────────────────────────────────────────────────────────────────
def _diff_level(ft_range: int) -> str:
    """감정 온도 범위를 분화 정도 서술어로 환산(점수·등급 아님)."""
    if ft_range <= 10:
        return "고른 편"
    if ft_range <= 30:
        return "부분적으로 갈리는 편"
    if ft_range <= 50:
        return "뚜렷하게 갈리는 편"
    return "강하게 갈리는 편"


def differentiation(responses: dict) -> dict:
    """
    특성 ① 시선의 분화 — 내집단/외집단 차등의 정도.
      ft_range: 감정 온도 최댓-최솟 (0~100)
      sd_gap  : 종교 간 일상 가까움 평균 차이 (0~3)
      level   : 분화 정도 서술어
    """
    ft = responses.get("ft", {})
    sd = responses.get("sd", {})
    rng = feeling_range(ft)
    sd_rel = sd_means_by_religion(sd)
    sd_gap = (max(sd_rel.values()) - min(sd_rel.values())) if sd_rel else 0.0
    return {"ft_range": rng, "sd_gap": round(sd_gap, 1), "level": _diff_level(rng)}


def intimacy_gradient(responses: dict) -> dict:
    """
    특성 ② 관계가 가까워질수록 — Bogardus 친밀성 위계.
      rows : [{"relation", "spread"(0~3), "mean"(1~4)}] (친밀도 오름차순)
      trend: 추세 한 줄 설명 (커짐/줄어듦/일정)
    """
    sd = responses.get("sd", {})
    by_rel = sd_by_relation(sd)
    rows = []
    for relation in config.SD_RELATIONS:        # 친밀도 오름차순
        if relation in by_rel:
            rows.append({
                "relation": relation,
                "spread": by_rel[relation]["spread"],
                "mean": round(by_rel[relation]["mean"], 1),
            })

    trend = None
    if len(rows) == len(config.SD_RELATIONS):
        far = rows[0]["spread"]    # 이웃 (낮은 친밀)
        near = rows[-1]["spread"]  # 결혼 상대 (높은 친밀)
        if near - far >= 1:
            trend = "관계가 가까워질수록 종교 간 차이가 커집니다"
        elif far - near >= 1:
            trend = "거리가 있는 관계에서 오히려 종교 간 차이가 더 컸습니다"
        else:
            trend = "친밀도와 무관하게 종교 간 차이가 일정하게 유지됩니다"
    return {"rows": rows, "trend": trend}


def affect_behavior(responses: dict) -> list:
    """
    특성 ③ 느낌 vs 거리감 — 태도 3요소 모델(정서 vs 행동).
      [{"religion", "warmth"(0~100), "closeness"(0~100)}]
      warmth   : 감정 온도 그대로
      closeness: 일상 가까움 평균(1~4)을 0~100으로 환산
    """
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


def valence_counts(responses: dict) -> dict:
    """
    특성 ④ 첫인상 단어의 결.
      counts: {"positive", "neutral", "negative"}
      nonpos: [(종교, 단어)] — 긍정이 아닌 단어가 떠오른 종교
    """
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
