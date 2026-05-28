# RDAP 퀵버전 (rdap-q)

**종교 다양성, 나의 시선** — 자기 성찰을 위한 5분 자기 탐구 도구 (퀵버전 V7, Reflect Edition).

> 본 도구는 측정 도구가 아닌 **교육적 자기 성찰 도구**입니다. 점수·등급·편향 지표를 산출하지 않습니다(명세서 §14).

---

## 리포지토리 구조

```
rdap-q/
├── app.py                  # 메인 엔트리(라우팅 전담)
├── config.py               # 모든 문항·종교 라벨·선택지·상수 (단일 소스)
├── state.py                # 세션 상태·역균형화·시간 측정·페이지 이동
├── scoring.py              # 감정 온도 범위·거울 직면 Case 계산
├── sheets.py               # Google Sheets 저장 (gspread + 서비스 계정)
├── blocks/                 # 블록(화면)별 모듈
│   ├── __init__.py         #   step → render 레지스트리
│   ├── intro.py            #   블록 0  안내·동의
│   ├── demographics.py     #   블록 1  인구통계 DM
│   ├── prediction.py       #   블록 2  사전 짐작 SP-01
│   ├── word_card.py        #   블록 3  첫인상 단어 카드 WC-01
│   ├── thermometer.py      #   블록 4  감정 온도계 FT-01
│   ├── mirror.py           #   블록 5  거울 직면 #1 MR-01
│   ├── social_distance.py  #   블록 6  일상 가까움 매트릭스 SD-01
│   ├── scenario.py         #   블록 7  시나리오 카드 SC-01
│   └── results.py          #   결과 페이지 (V6 MR-02 통합)
├── requirements.txt
├── .gitignore
└── .streamlit/
    ├── config.toml
    └── secrets.toml.example
```

**유지보수 원칙**: 문항 텍스트·선택지는 모두 `config.py` 한 곳에서 관리합니다. 종교 라벨(`"신종교 및 기타"`)을 단일 상수로 두어 화면 간 불일치를 구조적으로 차단합니다(명세서 §13-7).

---

## 빠른 시작 (로컬)

```bash
pip install -r requirements.txt
streamlit run app.py
```

자격증명 없이도 동작합니다. 이 경우 응답은 저장되지 않고 화면 흐름만 동작합니다(데모용).

---

## GitHub → Streamlit Community Cloud 배포

1. 이 폴더(`rdap-q/`)를 GitHub 리포지토리 루트로 올립니다.
2. [share.streamlit.io](https://share.streamlit.io) → **New app** → 리포지토리·브랜치 선택, **Main file path** 를 `app.py` 로 지정.
3. **Settings → Secrets** 에 `.streamlit/secrets.toml.example` 내용을 채워 붙여넣습니다.
4. 이후 GitHub에 push하면 자동 재배포됩니다.

> `secrets.toml` 은 `.gitignore` 로 커밋이 차단됩니다. 키는 반드시 Cloud의 Secrets에만 넣으세요.

---

## Google Sheets 연동

1. Google Cloud에서 **서비스 계정** 생성 → JSON 키 발급, **Sheets API · Drive API** 사용 설정.
2. 대상 스프레드시트를 서비스 계정 이메일(`client_email`)에 **편집자**로 공유.
3. 스프레드시트 이름을 `secrets.toml` 의 `[sheet].name`(기본 `RDAP_quickv_responses`)과 일치시킴.

저장은 **결과 페이지에서 '응답 저장하고 마치기'** 를 누를 때 1행으로 추가됩니다. 메타 해석 응답까지 포함됩니다.

### 저장 컬럼(평탄화 스키마, 명세서 §12)

| 그룹 | 컬럼 | 내용 |
|---|---|---|
| 식별 | `response_id`, `timestamp`, `duration_total_sec` | UUID·저장시각·총 소요(초) |
| 인구통계 | `dm_age`, `dm_gender`, `dm_religion` | DM-01·02·03 |
| 사전 짐작 | `sp01_prediction` | SP-01 |
| 첫인상 단어 | `wc_{종교}`, `wc_{종교}_valence` | 종교별 단어·valence |
| 감정 온도 | `ft_{종교}`, `ft_range`, `ft_warmest`, `ft_coldest` | 5종교 값·범위·최고/최저 |
| 거울 직면 | `mr01_reaction`, `mr01_case` | 반응·Case(A/B/C) |
| 일상 가까움 | `sd_{종교}_{관계}` (15개) | 5×3 매트릭스(1~4) |
| 시나리오 | `sc01_choice` | SC-01 선택 |
| 결과 메타 | `result_meta` | 결과 페이지 메타 해석 |
| 순서·시간 | `religion_order`, `relation_order`, `time_{블록}` | 역균형화 순서·블록별 시간 |

> 종교 컬럼 키: `buddhism / protestant / catholic / islam / newreligion` · 관계 키: `neighbor / coworker / marriage`.

---

## 역균형화(위치 효과 통제)

`config.COUNTERBALANCE_MODE` 로 전환합니다.

- `"random"` (기본): 응답자별 종교 순서 무작위 셔플
- `"reverse"`: 응답자별 정순/역순 무작위 배정(counterbalancing)

본문 블록(WC-01·FT-01·SD-01·SC-01)에만 적용하며, SD-01은 관계(열) 순서, WC-01은 단어 카드 위치도 무작위화합니다. **DM-03(본인 종교)은 자기보고 항목이므로 제외**합니다(명세서 §3 설계 메모).

---

## 구현 주의 사항

- **단어 카드(WC-01)** 는 명세서 §13-3의 4×3 버튼 그리드로 구현했습니다(선택 카드는 강조 표시).
- **감정 온도계 조정 횟수**: Streamlit `st.slider` 는 이동 횟수를 직접 제공하지 않아, 최종 값만 저장합니다(명세서 §6 '움직임 패턴'은 미구현 — 추후 커스텀 컴포넌트 필요).
- **결과 페이지 금지 표현**(편향·점수·등급·정상 범위 등, §11.2)은 코드 문구에서 일괄 배제했습니다.

---

## 명세 출처

본 구현은 프로젝트 내부 문서 「RDAP 퀵버전 V7 문항 명세서(Reflect Edition)」(2026-05-27)를 기준으로 합니다.
