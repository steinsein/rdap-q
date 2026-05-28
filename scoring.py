# -*- coding: utf-8 -*-
"""
scoring.py — 결과 계산 로직

본 도구는 측정 도구가 아니므로 '편향 점수'·'등급' 등은 산출하지 않는다(명세서 §14).
여기서 계산하는 값은 오직 응답자에게 보여줄 자기 인식 자료(감정 온도 범위,
예측-실제 격차, 최고/최저 반응 종교, 그리고 본인 응답의 구조적 '특성')에 한정된다.

V7.1 추가 — '특성 분석' 계층:
  앞 설문 응답을 단순히 되비추는 데 그치지 않고, 응답자 본인의 응답 안에 담긴
  구조적 패턴을 계산하여 자기 성찰 자료로 제시한다. 모든 산출물은 평가가 아닌
  '기술(description) + 성찰 질문' 형태이며, 점수·등급·정상 범위 표현을 쓰지 않는다.
  근거 틀: 사회적 거리 척도(Bogardus, 1933)의 친밀성 위계, 태도의 3요소 모델
  (정서 vs 행동), 사회정체성 이론의 내집단/외집단 차등.
"""
import config


# ─────────────────────────────────────────────────────────────────────────────
# 기본 지표 (기존)
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
# 특성 분석 (V7.1) — 평가가 아닌 '기술 + 성찰' 카드 목록 생성
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


def _affect_behavior_gap(ft: dict, sd_rel: dict):
    """
    특성 3 — 느낌(정서)과 거리감(행동)의 일치.
    종교별 감정 온도(0~100)와 일상 가까움 평균(1~4)을 0~1로 표준화해 비교한다.
    태도의 3요소 모델에서 정서적 차원과 행동적 차원의 결을 견주어 보는 자료.
    """
    if not ft or not sd_rel:
        return None
    rows = []
    for rel in config.RELIGIONS:
        if rel in ft and rel in sd_rel:
            warm = ft[rel] / 100.0            # 0~1 (정서: 따뜻함)
            close = (sd_rel[rel] - 1) / 3.0   # 0~1 (행동: 가까움)
            rows.append((rel, warm - close))
    if not rows:
        return None

    warm_far = max(rows, key=lambda x: x[1])      # 따뜻하게 느끼나 거리는 둠(양수)
    close_cool = min(rows, key=lambda x: x[1])    # 온도는 낮으나 가까이 둠(음수)

    if warm_far[1] >= 0.25:
        finding = (f"**{warm_far[0]}**에 대해서는 감정적으로는 비교적 따뜻하게 느끼면서도, "
                   f"일상에서 가까이 두는 데에는 한 발 더 신중한 모습이 보였습니다.")
        note = "'좋게 느끼는 것'과 '내 삶 가까이 두는 것' 사이의 간격은 누구에게나 있을 수 있습니다."
    elif close_cool[1] <= -0.25:
        finding = (f"**{close_cool[0]}**에 대해서는 감정 온도는 높지 않았지만, "
                   f"가까운 관계에는 오히려 비교적 열려 있는 모습이었습니다.")
        note = "느낌과 실제 거리감이 늘 같은 방향으로 움직이지는 않습니다."
    else:
        finding = "감정으로 느끼는 따뜻함과 가까이 두려는 마음이 대체로 같은 방향이었습니다."
        note = "느낌과 행동의 결이 서로 일관된 편입니다."
    return {"title": "느낌과 거리감이 같은 방향인가", "finding": finding, "note": note}


def _valence_texture(wc: dict):
    """특성 4 — 첫인상 단어의 정서가(valence) 결."""
    counts = {"positive": 0, "neutral": 0, "negative": 0}
    nonpos = []
    for rel in config.RELIGIONS:
        word = wc.get(rel)
        val = config.WORD_VALENCE.get(word)
        if val in counts:
            counts[val] += 1
            if val != "positive":
                nonpos.append((rel, word))
    finding = (f"첫인상 단어는 긍정 **{counts['positive']}**개 · 중립 "
               f"**{counts['neutral']}**개 · 거리감 **{counts['negative']}**개로 고르셨습니다.")
    if nonpos:
        tail = ", ".join(f"{r}({w})" for r, w in nonpos)
        finding += f" 그중 {tail}에서는 거리감 있는 단어가 먼저 떠올랐습니다."
        note = ("직관적으로 가장 먼저 떠오른 단어는, 평소 어떤 인상이 마음에 자리 잡고 "
                "있는지를 보여주는 단서일 수 있습니다.")
    else:
        note = "다섯 종교 모두에서 긍정·중립 계열의 단어를 고르셨습니다."
    return {"title": "가장 먼저 떠오른 단어의 결", "finding": finding, "note": note}


def characteristics(responses: dict) -> list:
    """
    응답 전체를 계산해 '종교 다양성 태도의 특성' 카드 목록을 만든다.
    각 카드: {"title", "finding"(계산된 사실), "note"(성찰 메모)}.
    점수·등급·편향 표현을 쓰지 않으며, 모든 서술은 본인 응답에 한정된다.
    """
    ft = responses.get("ft", {})
    sd = responses.get("sd", {})
    wc = responses.get("wc", {})

    items = []

    # ── 특성 1: 시선의 분화 (내집단/외집단 차등의 정도) ──
    rng = feeling_range(ft)
    sd_rel = sd_means_by_religion(sd)
    sd_gap = (max(sd_rel.values()) - min(sd_rel.values())) if sd_rel else 0.0
    items.append({
        "title": "다섯 종교를 얼마나 다르게 대하는가",
        "finding": (
            f"감정 온도에서 가장 따뜻한 종교와 가장 차가운 종교 사이에는 "
            f"**{rng}점**의 차이가 있었고, 일상에서의 가까움(4점 만점)에서는 "
            f"종교 간 평균 **{sd_gap:.1f}점**의 차이가 있었습니다. "
            f"본인의 시선은 다섯 종교에 대해 **{_diff_level(rng)}**으로 나타납니다."
        ),
        "note": ("차이가 있다는 것 자체는 자연스러운 일입니다. 중요한 건 그 차이가 "
                 "'어디에서', '왜' 생기는지를 들여다보는 것입니다."),
    })

    # ── 특성 2: 관계가 가까워질수록 (Bogardus 친밀성 위계) ──
    by_rel = sd_by_relation(sd)
    if len(by_rel) == len(config.SD_RELATIONS):
        far = config.SD_RELATIONS[0]      # 같은 동네 이웃 (낮은 친밀)
        near = config.SD_RELATIONS[-1]    # 결혼 상대 (높은 친밀)
        far_spread = by_rel[far]["spread"]
        near_spread = by_rel[near]["spread"]
        far_mean = by_rel[far]["mean"]
        near_mean = by_rel[near]["mean"]

        if near_spread - far_spread >= 1:
            trend = ("관계가 **가까워질수록** 종교에 따라 마음의 문이 더 크게 "
                     "달라지는 패턴이 보입니다.")
        elif far_spread - near_spread >= 1:
            trend = ("거리가 있는 관계에서 오히려 종교 간 차이가 더 컸고, 가까운 "
                     "관계에서는 차이가 줄었습니다.")
        else:
            trend = ("관계의 친밀도와 비교적 무관하게, 종교 간 차이가 일관되게 "
                     "유지되었습니다.")

        items.append({
            "title": "관계가 가까워질수록 달라지는가",
            "finding": (
                f"가장 거리가 있는 관계(이웃)에서는 종교 간 차이가 **{far_spread}점**, "
                f"가장 가까운 관계(결혼 상대)에서는 **{near_spread}점**이었습니다. "
                f"평균 편안함도 이웃 {far_mean:.1f}점 → 결혼 상대 {near_mean:.1f}점으로 "
                f"나타났습니다. {trend}"
            ),
            "note": ("머리로 받아들이는 것과 내 삶의 가장 가까운 자리에 두는 것은 "
                     "서로 다른 차원일 수 있습니다."),
        })

    # ── 특성 3: 느낌(정서)과 거리감(행동)의 일치 ──
    gap_item = _affect_behavior_gap(ft, sd_rel)
    if gap_item:
        items.append(gap_item)

    # ── 특성 4: 첫인상 단어의 결 ──
    items.append(_valence_texture(wc))

    return items
