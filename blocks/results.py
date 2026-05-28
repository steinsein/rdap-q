# -*- coding: utf-8 -*-
"""결과 페이지 (명세서 §11) — V6 MR-02(종합 직면)를 인트로로 통합.

V7.2 구성:
  · 1단계(시각화 이전): 메타 해석 질문('이 차이는 어떻게 형성된 것 같으세요?')을
    '필수'로 받는다. 응답해야 '결과 보기' 버튼이 활성화된다(앵커링 최소화).
  · 2단계: ① 내가 응답한 내용(원자료 시각화) → ② 종교 다양성 태도의 특성(계산된
    분석을 '차트'로 제시). 원자료 되비추기는 더 이상 마지막에 두지 않고, 계산된
    특성 시각화를 결과의 마무리로 삼는다.
'점수·등급·편향' 등 금지 표현(§11.2)은 사용하지 않는다.
"""
import time

import pandas as pd
import streamlit as st

import config
import scoring
import sheets
import state

# 차트 축 라벨용 짧은 관계명 (config.SD_RELATIONS의 표시 축약)
_RELATION_SHORT = {
    "같은 동네 이웃": "이웃",
    "직장 동료": "직장 동료",
    "자녀(또는 본인)의 결혼 상대": "결혼 상대",
}


# ─────────────────────────────────────────────────────────────────────────────
# 원자료 시각화 (내가 응답한 내용)
# ─────────────────────────────────────────────────────────────────────────────
def _feeling_map(ft: dict):
    """감정 온도 지도 — 가로 막대그래프(altair)."""
    if not ft:
        return
    df = pd.DataFrame(
        {"종교": config.RELIGIONS,
         "감정 온도": [ft.get(r, config.FT_DEFAULT) for r in config.RELIGIONS]}
    )
    try:
        import altair as alt
        chart = (
            alt.Chart(df)
            .mark_bar(cornerRadius=4)
            .encode(
                x=alt.X("감정 온도:Q", scale=alt.Scale(domain=[0, 100])),
                y=alt.Y("종교:N", sort=config.RELIGIONS, title=None),
                color=alt.Color("감정 온도:Q",
                                scale=alt.Scale(scheme="redyellowblue"),
                                legend=None),
                tooltip=["종교", "감정 온도"],
            )
            .properties(height=220)
        )
        st.altair_chart(chart, use_container_width=True)
    except Exception:
        st.bar_chart(df.set_index("종교"))


def _closeness_heatmap(sd: dict):
    """일상 가까움 히트맵 — 편안함 수준에 비례한 색상."""
    data = {}
    for relation in config.SD_RELATIONS:
        data[relation] = [sd.get((r, relation)) for r in config.RELIGIONS]
    df = pd.DataFrame(data, index=config.RELIGIONS)
    try:
        styled = df.style.background_gradient(cmap="RdYlGn", vmin=1, vmax=4) \
                         .format(precision=0)
        st.dataframe(styled, use_container_width=True)
    except Exception:
        st.dataframe(df, use_container_width=True)
    st.caption("4 = 매우 편안 · 1 = 부담스러움")


def _word_collection(wc: dict):
    """첫인상 단어 모음 — valence 색상 카드."""
    cols = st.columns(len(config.RELIGIONS))
    for col, religion in zip(cols, config.RELIGIONS):
        word = wc.get(religion, "—")
        valence = config.WORD_VALENCE.get(word, "neutral")
        color = config.VALENCE_COLOR.get(valence, "#616161")
        with col:
            st.markdown(
                f"<div style='text-align:center;padding:10px;border-radius:10px;"
                f"border:1px solid #e0e0e0;'>"
                f"<div style='font-size:0.8rem;color:#888'>{religion}</div>"
                f"<div style='font-size:1.05rem;font-weight:600;color:{color}'>{word}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )


# ─────────────────────────────────────────────────────────────────────────────
# 특성 분석 시각화 (계산된 결과)
# ─────────────────────────────────────────────────────────────────────────────
def _viz_differentiation(resp):
    """① 시선의 분화 — 두 지표(metric) + 분화 정도 막대."""
    d = scoring.differentiation(resp)
    c1, c2 = st.columns(2)
    c1.metric("감정 온도 차이", f"{d['ft_range']}점",
              help="가장 따뜻한 종교와 가장 차가운 종교의 감정 온도 차이 (0~100)")
    c2.metric("일상 가까움 차이", f"{d['sd_gap']}점 / 4",
              help="종교 간 평균 가까움 차이 (0~3)")
    st.progress(min(d["ft_range"], 100) / 100)
    st.caption(f"다섯 종교를 대하는 본인의 시선: **{d['level']}**  "
               f"(왼쪽=고른 시선 · 오른쪽=강하게 갈림)")


def _viz_intimacy(resp):
    """② 관계가 가까워질수록 — 친밀도별 '종교 간 차이' 꺾은선(핵심 차트)."""
    g = scoring.intimacy_gradient(resp)
    rows = g["rows"]
    if len(rows) < len(config.SD_RELATIONS):
        st.caption("일상 가까움 응답이 부족해 표시할 수 없습니다.")
        return
    order = [_RELATION_SHORT.get(r["relation"], r["relation"]) for r in rows]
    df = pd.DataFrame({
        "관계": order,
        "종교 간 차이": [r["spread"] for r in rows],
        "평균 편안함": [r["mean"] for r in rows],
    })
    try:
        import altair as alt
        base = alt.Chart(df).encode(
            x=alt.X("관계:N", sort=order, title="관계가 가까워질수록 →")
        )
        line = base.mark_line(point=alt.OverlayMarkDef(size=110, filled=True),
                              strokeWidth=3, color="#c0392b").encode(
            y=alt.Y("종교 간 차이:Q", scale=alt.Scale(domain=[0, 3]),
                    title="종교 간 차이 (0~3)"),
            tooltip=["관계", "종교 간 차이", "평균 편안함"],
        )
        st.altair_chart(line.properties(height=210), use_container_width=True)
    except Exception:
        st.line_chart(df.set_index("관계")["종교 간 차이"])
    if g["trend"]:
        st.caption(f"📈 {g['trend']}")


def _viz_affect_behavior(resp):
    """③ 느낌 vs 거리감 — 종교별 두 막대(정서/행동) 그룹 비교."""
    rows = scoring.affect_behavior(resp)
    if not rows:
        return
    long = []
    for r in rows:
        long.append({"종교": r["religion"], "구분": "느낌(따뜻함)", "값": r["warmth"]})
        long.append({"종교": r["religion"], "구분": "거리(가까움)", "값": r["closeness"]})
    df = pd.DataFrame(long)
    try:
        import altair as alt
        chart = (
            alt.Chart(df)
            .mark_bar()
            .encode(
                y=alt.Y("종교:N", sort=config.RELIGIONS, title=None),
                x=alt.X("값:Q", scale=alt.Scale(domain=[0, 100]), title="0~100"),
                yOffset="구분:N",
                color=alt.Color("구분:N",
                                scale=alt.Scale(domain=["느낌(따뜻함)", "거리(가까움)"],
                                                range=["#e67e22", "#2980b9"]),
                                legend=alt.Legend(orient="top", title=None)),
                tooltip=["종교", "구분", "값"],
            )
            .properties(height=270)
        )
        st.altair_chart(chart, use_container_width=True)
    except Exception:
        st.dataframe(df, use_container_width=True)
    st.caption("주황(느낌)보다 파랑(거리)이 짧을수록, 따뜻하게 느끼면서도 "
               "가까이 두는 데에는 더 신중하다는 뜻입니다.")


def _viz_valence(resp):
    """④ 첫인상 단어의 결 — 긍정/중립/거리감 누적 막대."""
    v = scoring.valence_counts(resp)
    counts = v["counts"]
    df = pd.DataFrame({
        "정서": ["긍정", "중립", "거리감"],
        "개수": [counts["positive"], counts["neutral"], counts["negative"]],
        "순서": [0, 1, 2],
        "축": ["첫인상"] * 3,
    })
    try:
        import altair as alt
        chart = (
            alt.Chart(df)
            .mark_bar()
            .encode(
                x=alt.X("개수:Q", title="단어 수",
                        scale=alt.Scale(domain=[0, len(config.RELIGIONS)])),
                y=alt.Y("축:N", title=None),
                color=alt.Color("정서:N",
                                scale=alt.Scale(
                                    domain=["긍정", "중립", "거리감"],
                                    range=[config.VALENCE_COLOR["positive"],
                                           config.VALENCE_COLOR["neutral"],
                                           config.VALENCE_COLOR["negative"]]),
                                legend=alt.Legend(orient="top", title=None)),
                order=alt.Order("순서:Q"),
                tooltip=["정서", "개수"],
            )
            .properties(height=100)
        )
        st.altair_chart(chart, use_container_width=True)
    except Exception:
        st.bar_chart(df.set_index("정서")["개수"])
    if v["nonpos"]:
        tail = ", ".join(r for r, _ in v["nonpos"])
        st.caption(f"거리감 있는 단어가 먼저 떠오른 종교: **{tail}**")
    else:
        st.caption("다섯 종교 모두에서 긍정·중립 단어를 고르셨습니다.")


# ─────────────────────────────────────────────────────────────────────────────
# 섹션 묶음
# ─────────────────────────────────────────────────────────────────────────────
def _render_raw(ft, sd, wc):
    st.subheader("📊 내가 응답한 내용")
    st.markdown("**감정 온도 지도**")
    _feeling_map(ft)
    st.markdown("**일상 가까움 히트맵**")
    _closeness_heatmap(sd)
    st.markdown("**첫인상 단어 모음**")
    _word_collection(wc)


def _render_analysis(resp):
    st.subheader("🔍 본인의 종교 다양성 태도, 한눈에 보기")
    st.caption("아래는 본인 응답만으로 계산한 특성입니다. 점수나 등급이 아니라, "
               "스스로를 비춰보기 위한 자료입니다.")

    with st.container(border=True):
        st.markdown("**① 다섯 종교를 얼마나 다르게 대하는가**")
        _viz_differentiation(resp)

    with st.container(border=True):
        st.markdown("**② 관계가 가까워질수록 달라지는가**")
        _viz_intimacy(resp)

    with st.container(border=True):
        st.markdown("**③ 느낌과 거리감이 같은 방향인가**")
        _viz_affect_behavior(resp)

    with st.container(border=True):
        st.markdown("**④ 가장 먼저 떠오른 단어의 결**")
        _viz_valence(resp)

    summary = scoring.result_summary(resp)
    with st.container(border=True):
        st.markdown("**⑤ 내 예측은 실제와 얼마나 맞았나**")
        st.write(scoring.prediction_accuracy_text(summary["case"]))


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
# 2단계 — 원자료 시각화(먼저) + 특성 분석 시각화(마무리)
# ─────────────────────────────────────────────────────────────────────────────
def _render_results(resp):
    summary = scoring.result_summary(resp)
    ft = resp.get("ft", {})
    sd = resp.get("sd", {})
    wc = resp.get("wc", {})

    st.title("🗺️ 본인의 종교 다양성 지도")

    # 종합 직면 인트로 (V6 MR-02 통합)
    if summary["warmest"] and summary["coldest"]:
        st.markdown(
            f"본인의 오늘 응답을 종합해보면, 다섯 종교에 대한 본인의 반응 사이에 "
            f"**{summary['ft_range']}점**만큼의 차이가 보이네요.\n\n"
            f"- 가장 따뜻한 반응을 보이신 종교: **{summary['warmest']}**\n"
            f"- 가장 차가운 반응을 보이신 종교: **{summary['coldest']}**"
        )

    st.divider()

    # ① 원자료 시각화 — 더 이상 마지막에 두지 않는다
    _render_raw(ft, sd, wc)

    st.divider()

    # ② 특성 분석 시각화 — 결과의 마무리
    _render_analysis(resp)

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
    # 메타 해석을 시각화 '이전'에 '필수'로 받는다. 응답해야 결과가 펼쳐진다.
    if not st.session_state.get("meta_done"):
        _render_meta_gate(resp)
        return
    _render_results(resp)
