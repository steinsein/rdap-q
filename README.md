# RDAP 퀵버전 (rdap-q)

**종교 다양성, 나의 시선** — 자기 성찰을 위한 5분 자기 탐구 도구 (퀵버전).

> 본 도구는 측정 도구가 아닌 **교육적 자기 성찰 도구**입니다.

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

### 저장 컬럼

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

본문 블록(WC-01·FT-01·SD-01·SC-01)에만 적용하며, SD-01은 관계(열) 순서, WC-01은 단어 카드 위치도 무작위화합니다.

---

## 라이선스 및 인용

본 도구는 RDAP 프로젝트 내부 자료이며, 학술 출판 시 다음을 인용한다.

> RDAP 프로젝트. (2026). RDAP 퀵버전: 종교 다양성 태도 프로파일 [Streamlit 애플리케이션].
