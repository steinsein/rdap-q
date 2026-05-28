# -*- coding: utf-8 -*-
"""결과 페이지 (명세서 §11) — V6 MR-02(종합 직면)를 인트로로 통합.

V7.1 변경 두 가지:
  ① 메타 해석 질문('이 차이는 어떻게 형성된 것 같으세요?')을 결과 시각화 '이전'으로
     이동. 결과 지도를 펼치기 전 단계에서 먼저 응답을 받고(앵커링 최소화), 버튼을
     눌러야 시각화·분석이 펼쳐진다.
  ② 앞 설문 응답을 단순히 되비추는 데 그치지 않고, scoring.characteristics()로 계산한
     '종교 다양성 태도의 특성'을 카드로 제시한 뒤, 그 근거가 되는 세부 데이터(감정 온도
     지도·가까움 히트맵·단어 모음)를 아래에 배치한다.
'점수·등급·편향' 등 금지 표현(§11.2)은 사용하지 않는다.
"""
import time

import pandas as pd
import streamlit as st

import config
import scoring
import sheets
import state


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


def _characteristics(resp: dict):
    """계산된 '종교 다양성 태도의 특성' 카드 목록."""
    for c in scoring.characteristics(resp):
        with st.container(border=True):
            st.markdown(f"**{c['title']}**")
            st.markdown(c["finding"])
            st.caption(c["note"])


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
# 1단계 — 결과 시각화 '이전' 메타 해석 질문
# ─────────────────────────────────────────────────────────────────────────────
def _render_meta_gate(resp):
    st.title("🗺️ 본인의 종교 다양성 지도")
    st.markdown(
        "조금 전 응답을 보면, 다섯 종교에 대한 본인의 반응에는 "
        "**서로 다른 결**이 있었습니다.\n\n"
        "자세한 결과 지도를 펼치기 전에, 한 가지만 먼저 짚고 가실게요."
    )

    st.markdown("**이 차이는 어떻게 형성된 것 같으세요?** (선택)")
    meta = st.radio("메타 해석", config.RESULT_META_OPTIONS, index=None,
                    label_visibility="collapsed", key="result_meta_radio")
    st.caption("결과를 보기 전 지금의 생각을 먼저 남겨두면, 곧 펼쳐질 분석과 "
               "비교해볼 수 있습니다.")

    st.divider()
    if st.button("내 결과 지도 펼쳐보기", type="primary",
                 use_container_width=True):
        if meta is not None:
            resp["result_meta"] = config.RESULT_META_OPTIONS.index(meta)
        st.session_state.meta_done = True
        st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# 2단계 — 특성 분석 + 결과 시각화
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

    # ── 특성 분석 (계산된 결과) ──
    st.subheader("🔍 본인의 종교 다양성 태도, 이렇게 나타났어요")
    st.caption("아래는 본인 응답만으로 계산한 특성입니다. 점수나 등급이 아니라, "
               "스스로를 비춰보기 위한 자료입니다.")
    _characteristics(resp)

    st.divider()

    # ── 세부 데이터 (위 특성의 근거) ──
    st.subheader("📊 응답 세부 데이터")

    st.markdown("**감정 온도 지도**")
    _feeling_map(ft)

    st.markdown("**일상 가까움 히트맵**")
    _closeness_heatmap(sd)

    st.markdown("**첫인상 단어 모음**")
    _word_collection(wc)

    # 자기 예측 정확도
    st.markdown("**자기 예측 정확도**")
    st.write(scoring.prediction_accuracy_text(summary["case"]))

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
    # 메타 해석을 시각화 '이전'에 받는다. 응답(또는 건너뛰기) 후에만 분석이 펼쳐진다.
    if not st.session_state.get("meta_done"):
        _render_meta_gate(resp)
        return
    _render_results(resp)
