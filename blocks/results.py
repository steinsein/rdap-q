# -*- coding: utf-8 -*-
"""결과 페이지 (명세서 §11).

V7.3 — 응답을 항목별로 되비추던 화면을 '종합' 화면으로 바꾼다.
  · 1단계(시각화 이전): 메타 해석 질문을 '필수'로 받는다(앵커링 최소화).
  · 2단계: 두 장의 합성 이미지로 태도를 요약한다.
      ① 종교 다양성 태도 지도  — 5개 문항을 개방성 × 차등성 두 축으로 합성해 위치 표시
      ② 수용의 사다리          — 관계 친밀도에 따른 종교별 수용 곡선(Bogardus 사회적 거리)
    이어서 합성 수식에서 뽑은 '핵심 인사이트'를 짧게 제시한다.
  원자료 되비추기(감정 온도 막대·히트맵·단어 카드)는 인사이트가 없어 제거했다.
'점수·등급·편향' 등 금지 표현(§11.2)은 사용하지 않는다(종합치는 '위치/성향'으로 표기).
"""
import time

import pandas as pd
import streamlit as st

import config
import scoring
import sheets
import state

# 차트 축 라벨용 짧은 관계명
_RELATION_SHORT = {
    "같은 동네 이웃": "이웃",
    "직장 동료": "직장 동료",
    "자녀(또는 본인)의 결혼 상대": "결혼 상대",
}

# 태도 지도 분할선 (성향 판정과 동일 기준)
_O_SPLIT = 50   # 개방성: 중립 기준선
_D_SPLIT = 30   # 차등성: '갈림' 기준선


# ─────────────────────────────────────────────────────────────────────────────
# 이미지 ① 종교 다양성 태도 지도 (개방성 × 차등성)
# ─────────────────────────────────────────────────────────────────────────────
def _viz_attitude_map(pos):
    bg = pd.DataFrame([
        {"x0": 0,        "x1": _D_SPLIT, "y0": _O_SPLIT, "y1": 100, "c": "#e8f5e9"},
        {"x0": _D_SPLIT, "x1": 100,      "y0": _O_SPLIT, "y1": 100, "c": "#fff8e1"},
        {"x0": 0,        "x1": _D_SPLIT, "y0": 0,        "y1": _O_SPLIT, "c": "#e3f2fd"},
        {"x0": _D_SPLIT, "x1": 100,      "y0": 0,        "y1": _O_SPLIT, "c": "#fce4ec"},
    ])
    quads = pd.DataFrame([
        {"x": _D_SPLIT / 2,         "y": 75, "label": "고르게 열린 시선"},
        {"x": (_D_SPLIT + 100) / 2, "y": 75, "label": "선택적으로 열린 시선"},
        {"x": _D_SPLIT / 2,         "y": 25, "label": "고르게 거리를 둔 시선"},
        {"x": (_D_SPLIT + 100) / 2, "y": 25, "label": "선별적으로 경계하는 시선"},
    ])
    pt = pd.DataFrame([{"x": pos["differentiation"], "y": pos["openness"]}])

    try:
        import altair as alt
        x_enc = alt.X("x0:Q", scale=alt.Scale(domain=[0, 100]),
                      axis=alt.Axis(title="고르게 본다  ←   차등성   →  다르게 본다",
                                    values=[], grid=False))
        y_enc = alt.Y("y0:Q", scale=alt.Scale(domain=[0, 100]),
                      axis=alt.Axis(title="거리를 둔다  ←   개방성   →  열려 있다",
                                    values=[], grid=False))
        rect = alt.Chart(bg).mark_rect(opacity=0.65).encode(
            x=x_enc, x2="x1:Q", y=y_enc, y2="y1:Q",
            color=alt.Color("c:N", scale=None))
        labels = alt.Chart(quads).mark_text(
            fontSize=12, fontWeight="bold", color="#7a7a7a").encode(
            x="x:Q", y="y:Q", text="label:N")
        point = alt.Chart(pt).mark_point(
            size=420, filled=True, color="#d32f2f",
            stroke="white", strokeWidth=2).encode(x="x:Q", y="y:Q")
        plabel = alt.Chart(pt).mark_text(
            text="현재 위치", dy=-20, fontWeight="bold",
            color="#d32f2f", fontSize=13).encode(x="x:Q", y="y:Q")
        chart = (rect + labels + point + plabel).properties(height=380)
        st.altair_chart(chart, use_container_width=True)
    except Exception:
        st.write(f"개방성: {pos['o_band']} · 차등성: {pos['d_band']}")

    st.caption("세로=다섯 종교 전반에 얼마나 열려 있는가 · 가로=종교에 따라 얼마나 "
               "다르게 대하는가. 위치는 좋고 나쁨이 아니라, 지금 본인의 시선이 "
               "어디쯤 놓여 있는지를 보여줍니다.")


# ─────────────────────────────────────────────────────────────────────────────
# 이미지 ② 수용의 사다리 (관계 친밀도 × 종교별 편안함)
# ─────────────────────────────────────────────────────────────────────────────
def _viz_ladder(resp):
    sd = resp.get("sd", {})
    rows = []
    for r in config.RELIGIONS:
        for rel in config.SD_RELATIONS:
            v = sd.get((r, rel))
            if v is not None:
                rows.append({"종교": r,
                             "관계": _RELATION_SHORT.get(rel, rel),
                             "편안함": v})
    if not rows:
        st.caption("일상 가까움 응답이 부족해 표시할 수 없습니다.")
        return
    df = pd.DataFrame(rows)
    order = [_RELATION_SHORT.get(x, x) for x in config.SD_RELATIONS]
    try:
        import altair as alt
        chart = (
            alt.Chart(df)
            .mark_line(point=alt.OverlayMarkDef(size=70, filled=True),
                       strokeWidth=2.5)
            .encode(
                x=alt.X("관계:N", sort=order, title="관계가 가까워질수록 →"),
                y=alt.Y("편안함:Q", scale=alt.Scale(domain=[1, 4]),
                        title="편안함 (1=부담 · 4=매우 편안)"),
                color=alt.Color("종교:N", sort=config.RELIGIONS,
                                legend=alt.Legend(orient="top", title=None)),
                tooltip=["종교", "관계", "편안함"],
            )
            .properties(height=320)
        )
        st.altair_chart(chart, use_container_width=True)
    except Exception:
        st.dataframe(df, use_container_width=True)
    st.caption("선이 오른쪽으로 갈수록 아래로 꺾이면, 그 종교를 멀리서는 받아들여도 "
               "가까운 사이로는 주저한다는 뜻입니다. 위에 평평한 선일수록 친밀도와 "
               "무관하게 받아들이는 종교입니다.")


# ─────────────────────────────────────────────────────────────────────────────
# 핵심 인사이트 (합성 수식에서 추출)
# ─────────────────────────────────────────────────────────────────────────────
def _render_insights(resp, pos):
    hi, lo = scoring.acceptance_extremes(resp)
    gap_r = scoring.feeling_distance_gap(resp)
    close_r = scoring.closing_religion(resp)
    v = scoring.valence_counts(resp)

    lines = []
    if hi and lo and hi != lo:
        lines.append(f"전반적으로 **{hi}**를 가장 가깝게, **{lo}**를 가장 멀게 "
                     f"받아들이고 있어요.")
    elif hi:
        lines.append(f"다섯 종교를 비교적 비슷한 거리에서 받아들이고 있어요.")

    if gap_r:
        lines.append(f"**{gap_r}**에 대해서는 따뜻하게 느끼면서도 가까이 두는 데에는 "
                     f"한 발 더 신중했어요 — 느낌과 거리감이 어긋나는 지점입니다.")
    if close_r:
        lines.append(f"관계가 가까워질수록 **{close_r}**에 대한 마음이 가장 많이 "
                     f"닫혔어요(이웃 → 결혼 상대).")
    if v["nonpos"]:
        tail = ", ".join(r for r, _ in v["nonpos"])
        lines.append(f"첫인상에서 거리감 있는 단어가 먼저 떠오른 종교: **{tail}**.")

    for ln in lines:
        st.markdown(f"- {ln}")


# ─────────────────────────────────────────────────────────────────────────────
# 저장
# ─────────────────────────────────────────────────────────────────────────────
def _save(resp):
    duration = time.time() - st.session_state.start_ts
    record = sheets.build_record(
        response_id=st.session_state.response_id,
        responses=resp,
        block_times=st.session_state.block_times,
        religion_order=state.religion_order(),
        relation_order=state.relation_order(),
        duration_total=duration,
    )
    ok = sheets.save_response(record)
    st.session_state.saved = True
    st.session_state.save_ok = ok


# ─────────────────────────────────────────────────────────────────────────────
# 1단계 — 결과 시각화 '이전' 메타 해석 질문 (필수)
# ─────────────────────────────────────────────────────────────────────────────
def _render_meta_gate(resp):
    st.title("🗺️ 본인의 종교 다양성 지도")
    st.markdown(
        "조금 전 응답을 보면, 다섯 종교에 대한 본인의 반응에는 "
        "**서로 다른 결**이 있었습니다.\n\n"
        "자세한 결과 지도를 펼치기 전에, 한 가지만 먼저 짚고 가실게요."
    )

    st.markdown("**이 차이는 어떻게 형성된 것 같으세요?**")
    meta = st.radio("메타 해석", config.RESULT_META_OPTIONS, index=None,
                    label_visibility="collapsed", key="result_meta_radio")

    st.divider()
    selected = meta is not None
    if not selected:
        st.caption("하나를 선택하면 결과를 볼 수 있습니다.")
    if st.button("결과 보기", type="primary", disabled=not selected,
                 use_container_width=True):
        resp["result_meta"] = config.RESULT_META_OPTIONS.index(meta)
        st.session_state.meta_done = True
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# 2단계 — 합성 결과
# ─────────────────────────────────────────────────────────────────────────────
def _render_results(resp):
    pos = scoring.attitude_position(resp)
    summary = scoring.result_summary(resp)

    st.title("🧭 본인의 종교 다양성 태도, 한눈에")
    st.caption("아래는 다섯 문항의 응답을 합성해 계산한 결과입니다. 점수나 등급이 "
               "아니라, 스스로를 비춰보기 위한 자료입니다.")

    # 한 줄 진단
    if pos:
        st.markdown(
            f"#### 지금 본인의 시선은 「**{pos['tendency']}**」에 가깝습니다."
        )
        st.markdown(
            f"다섯 종교 전반에 대한 태도는 **{pos['o_band']}**, 종교에 따라 "
            f"대하는 정도는 **{pos['d_band']}**입니다."
        )

    st.divider()

    # 이미지 ① 태도 지도
    with st.container(border=True):
        st.markdown("**🧭 종교 다양성 태도 지도**")
        if pos:
            _viz_attitude_map(pos)
        else:
            st.caption("응답이 부족해 지도를 그릴 수 없습니다.")

    # 이미지 ② 수용의 사다리
    with st.container(border=True):
        st.markdown("**🪜 수용의 사다리 — 관계가 가까워질수록**")
        _viz_ladder(resp)

    # 핵심 인사이트
    with st.container(border=True):
        st.markdown("**✨ 핵심 인사이트**")
        if pos:
            _render_insights(resp, pos)
        st.caption(f"자기 예측: {scoring.prediction_accuracy_text(summary['case'])}")

    # 활용 안내
    st.divider()
    st.markdown(
        "이 지도를 보고 새롭게 떠오르는 질문이 있다면, 그 질문에서 자기 탐구를 "
        "이어가 보세요. 본 결과는 점수나 등급이 아니라, 본인의 다양성에 대한 시선을 "
        "비춰보는 거울입니다."
    )

    # 저장
    st.divider()
    if not st.session_state.get("saved"):
        if st.button("응답 저장하고 마치기", type="primary",
                     use_container_width=True):
            _save(resp)
            st.rerun()
    else:
        if st.session_state.get("save_ok"):
            st.success("응답이 익명으로 저장되었습니다. 참여해 주셔서 감사합니다.")
        else:
            st.info("참여해 주셔서 감사합니다. (저장 서버가 연결되지 않아 응답은 "
                    "기록되지 않았습니다 — 데모/로컬 환경)")


def render():
    resp = state.responses()
    if not st.session_state.get("meta_done"):
        _render_meta_gate(resp)
        return
    _render_results(resp)
