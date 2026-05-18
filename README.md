# RDAP 퀵버전 — Streamlit 배포 저장소

**RDAP (Religious Diversity Attitude Profile)** 의 퀵버전 구현 저장소다. 종교 다양성에 대한 태도를 자기 성찰적으로 시각화하는 **교육적 도구**이며, 표준화된 심리 검사가 아니다.

핵심 산출 지표는 **RDAS (Religious Diversity Acceptance Score)** 로, 개신교(PT) vs 이슬람(IS) 비교의 차등이 작을수록 높은 0~100점 단일 점수다. "사회적으로 논란이 된 종교 단체"(NR)는 참고 정보로만 표시하며 RDAS 산출에서는 제외된다.

---

## 1. 디렉터리 구조

```
rdap-q/
├── app.py                    # 메인 엔트리: 페이지 라우팅·세션 초기화만 담당
├── config.py                 # 모든 상수 (시나리오, 선택지, 임계값, 색상, 라벨)
├── requirements.txt
├── README.md
├── .gitignore
├── .streamlit/
│   ├── config.toml           # Streamlit 테마
│   └── secrets.toml.example  # secrets 템플릿 (실제 키는 secrets.toml로 별도 작성)
└── src/
    ├── __init__.py
    ├── utils.py              # RT 캡처, 역균형화, 세션 초기화
    ├── questions.py          # 모든 블록의 UI 렌더링 함수
    ├── scoring.py            # 점수 산출 로직 (부수효과 없음)
    ├── visualizations.py     # Plotly Figure 생성기
    ├── results.py            # 결과 페이지 3단계 컴포지션
    └── sheets.py             # Google Sheets I/O (실패 시 로컬 백업)
```

### 모듈 간 의존성

```
app.py
 ├── config
 ├── src/utils
 ├── src/questions ──► config, src/utils
 ├── src/results   ──► config, src/scoring, src/visualizations, src/sheets, src/utils
 └── src/sheets    ──► config

src/scoring        ──► config              (부수효과 없음, 테스트 용이)
src/visualizations ──► config              (Plotly Figure만 반환)
```

순환 의존성은 없다. `config.py`는 모든 모듈이 의존하는 종착점이다.

---

## 2. 빠른 시작 — 로컬 실행

### 2.1. 의존성 설치

```bash
git clone https://github.com/YOUR_USERNAME/rdap-q.git
cd rdap-q
conda activate rdap            # 또는 python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 2.2. 실행

```bash
streamlit run app.py
```

브라우저에서 `http://localhost:8501` 접속.

---

## 3. Streamlit Community Cloud 배포

### 3.1. 사전 준비 — Google Cloud 측

1. Google Cloud 콘솔에서 새 프로젝트 생성 (예: `ReligiousDiversityAttitudePro`).
2. **APIs & Services → Library**에서 다음 API 활성화:
   - Google Sheets API
   - Google Drive API
3. **APIs & Services → Credentials → Create Credentials → Service Account**:
   서비스 계정 생성 후 JSON 키 다운로드.
4. 응답을 저장할 Google Sheets를 새로 만들고, 위 서비스 계정 이메일을 **"편집자"** 권한으로 공유.
5. 시트 탭은 코드가 자동 생성한다 (`responses` 단일 탭). 미리 만들 때는 탭 이름을 정확히 일치시켜야 한다.

### 3.2. GitHub 업로드

```bash
git init
git add .
git commit -m "Initial commit: RDAP quick version"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/rdap-q.git
git push -u origin main
```

> `secrets.toml`은 `.gitignore`에 등록되어 자동 제외된다. 절대 커밋하지 말 것.

### 3.3. Streamlit Cloud 배포

1. [share.streamlit.io](https://share.streamlit.io) → **New app**.
2. 저장소: `YOUR_USERNAME/rdap-q`, 브랜치: `main`, 메인 파일: `app.py`.
3. **Advanced settings → Secrets** 화면에서 `.streamlit/secrets.toml.example`의 내용을 그대로 붙여 넣고 자신의 키로 채워 저장.
4. **Deploy** 클릭. 첫 빌드는 약 2~3분.

---

## 4. 설문 구조

본 도구는 다음 약 22문항으로 구성된다.

| 블록 | 유형 | 문항 수 | 비고 |
|---|---|:---:|---|
| 동의·선별 (SC) | 라디오 | 2 | 한 페이지 |
| 인구통계 (DM) | 라디오 | 4 | **4 페이지로 분리** (연령·성별·지역·종교) |
| **비교 응답 (CR)** | 라디오 | 12 | 4 시나리오 × 3 종교 (PT/IS/NR). **RT 측정** |
| 반사실 확인 (CF) | 라디오 | 1 | Q3 직후. 결과 페이지 미노출(분석용) |
| 직접 질문 닻 (DQ) | 라디오 | 1 | 결과 페이지 미노출(분석용) |
| 비교 의도 점검 (MC) | 라디오 | 2 | |
| 피드백 (FB) | 라디오 + 텍스트 | 2 | 솔직성 + 자유 의견 |
| **결과 페이지** | 시각화 | — | 3단계: RDAS 게이지 / 영역 막대 / NR 참고 |
| 디브리핑 | — | — | |

예상 소요 시간: **5~6분**.

---

## 5. 비교 종교 — PT, IS, NR 3종교 구조

|  | 코드 | 표시 라벨 | RDAS 반영 |
|---|:---:|---|:---:|
| 개신교 | PT | 개신교 | ✓ |
| 이슬람 | IS | 이슬람 | ✓ |
| 신종교 | NR | "사회적으로 논란이 된 종교 단체" | — (참고 정보) |

NR은 시나리오 표시 문구에서 일반 범주명("사회적으로 논란이 된 종교 단체")으로 노출되며, 특정 단체명을 응답자에게 제시하지 않는다.

### 시나리오 구성 (4 시나리오)

| Q | 영역 | 시나리오 |
|:---:|---|---|
| Q1 | 공적 | 동네 종교 시설 건립 |
| Q2 | 직장 | 새 팀원의 종교 정체성 공개 |
| Q3 | 사적 | 가족의 종교 간 결혼 |
| Q4 | 미디어 | 종교 지도자 비리 뉴스 |

---

## 6. RDAS — 점수 산출 공식

```
pt_is_deviation = ∑ |Q*_PT − Q*_IS|     (4 시나리오 합산, 범위 0~12)
RDAS            = round(100 × (1 − pt_is_deviation / 12))
```

응답 점수: ① 0점 → ④ 3점 (정방향). 각 문항의 두 종교 응답 차이가 작을수록 RDAS가 높다.

### 5단계 라벨

| RDAS | 라벨 | 응답자 메시지 |
|:---:|---|---|
| 80~100 | 일관 응답형 | 종교에 관계없이 비슷한 기준으로 답하셨어요. |
| 60~79 | 부분 차등형 | 일부 영역에서 종교에 따른 차이가 있었어요. |
| 40~59 | 영역 차등형 | 영역에 따라 종교에 다른 기준을 적용하셨어요. |
| 20~39 | 뚜렷한 차등형 | 종교 간에 뚜렷한 차이가 나타났어요. |
| 0~19 | 강한 차등형 | 응답에 종교에 따른 강한 차이가 있었어요. |

라벨 임계값은 본 검사 표본 분포에 따라 추후 조정될 수 있다.

---

## 7. 데이터 스키마

응답은 Google Sheets의 단일 탭 `responses`에 저장된다.

### 주요 컬럼군 (자세한 헤더는 `src/sheets.py::MAIN_HEADERS` 참조)

| 카테고리 | 컬럼명 (예) | 개수 |
|---|---|:---:|
| 메타 | `timestamp`, `session_id`, `cb_condition` | 3 |
| 인구통계 | `age_group`, `gender`, `region`, `religion` | 4 |
| CR 응답 (정규화 0~3) | `q1_pt`, `q1_is`, `q1_nr`, …, `q4_nr` | 12 |
| CR RT (ms) | `rt_q1_pt_ms`, …, `rt_q4_nr_ms` | 12 |
| CF | `cf_q3_response`, `rt_cf_ms` | 2 |
| DQ | `dq_01_response`, `rt_dq_ms` | 2 |
| MC | `mc_01_response`, `mc_02_response` | 2 |
| FB | `fb_01_response`, `fb_02_text` | 2 |
| 품질 플래그 | `rt_anomaly_flags` | 1 |
| 산출 점수 | `rdas_score`, `rdas_label`, `pt_is_deviation`, `pt_nr_deviation`, `is_nr_deviation`, `nr_mean_score`, `dom_public`, `dom_work`, `dom_private`, `dom_media`, `dominant_domain` | 11 |
| 소요 시간 | `total_duration_sec` | 1 |

---

## 8. 측정 차원의 처리 방침

| 차원 | 응답자 노출 | 데이터 수집 |
|---|:---:|:---:|
| **CR 응답** | ✓ (결과 페이지 핵심) | ✓ |
| **DQ 닻 문항** | — (백그라운드만) | ✓ |
| **CF 반사실 확인** | — (백그라운드만) | ✓ |
| **RT 응답 시간** | — (백그라운드만) | ✓ |
| **MC·FB** | — | ✓ |

DQ·CF·RT는 시트에 그대로 저장되어 사후 분석에서 응답 신뢰도 점검과 측정학적 검증에 활용된다. 응답자에게는 단순한 결과를, 연구자에게는 풍부한 데이터를 — 두 청중을 분리하는 설계다.

---

## 9. RT 측정의 한계

- 본 도구의 RT는 **서버 사이드 `time.perf_counter()`** 기반이다.
- 사용자가 페이지를 잠시 떠난 경우의 시간 부풀림은 보정 불가하다.
- 품질 플래그(`rt_too_fast` / `rt_too_slow` / `rt_inconsistent`)는 사후 분석에서 응답 필터링에 사용한다(응답자에게는 노출하지 않음).

---

## 10. 역균형화 설계

응답자별로 두 차원에서 무작위 배정된다.

1. **선택지 순서** (`option_order`): forward(①→④) 또는 reverse(④→①)
2. **시나리오별 종교 제시 순서** (`religion_orders`): 시나리오마다 PT/IS/NR 3종교의 화면 노출 순서를 독립적으로 셔플

두 차원의 조합이 시트의 `cb_condition` 컬럼에 단일 문자열로 직렬화되어 저장된다. 사후 분석에서 순서 효과 통제에 활용한다.

---

## 11. 라이선스 및 인용

본 도구는 RDAP 프로젝트 내부 자료이며, 학술 출판 시 다음을 인용한다.

> RDAP 프로젝트. (2026). RDAP 퀵버전: 종교 다양성 태도 프로파일 [Streamlit 애플리케이션].

문의: 도구 개발팀.
