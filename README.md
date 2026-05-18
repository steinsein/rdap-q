# RDAP 퀵버전 — Streamlit 배포 저장소

**RDAP (Religious Diversity Attitude Profile)** 의 퀵버전 구현 저장소다. 종교 다양성에 대한 태도를 자기 성찰적으로 시각화하는 **교육적 도구**이며, 표준화된 심리 검사가 아니다.

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
    ├── utils.py              # RT 캡처, 버전 배정, 역균형화, 세션 초기화
    ├── questions.py          # 모든 블록의 UI 렌더링 함수
    ├── scoring.py            # 점수 산출 로직 (부수효과 없음)
    ├── visualizations.py     # Plotly Figure 생성기
    ├── results.py            # 결과 페이지 8단계 컴포지션
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
   - 서비스 계정 생성 후 JSON 키 다운로드.
4. 응답을 저장할 Google Sheets를 새로 만들고, 위 서비스 계정 이메일을 **"편집자"** 권한으로 공유.
5. 시트 탭은 코드가 자동 생성한다 (`responses`, `mt_responses`). 미리 만들 필요는 없으나, 수동으로 만들 때는 탭 이름을 정확히 일치시켜야 한다.

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

본 도구는 다음 24문항으로 구성된다.

| 블록 | 유형 | 문항 수 | 비고 |
|---|---|:---:|---|
| 동의·선별 (SC) | 라디오 | 2 | RT 측정 안내 포함 |
| 인구통계 (DM) | 라디오 | 4 | 연령·성별·지역·종교 |
| **비교 응답 (CR)** | 라디오 | 10 | 5 시나리오 × 2 종교. **RT 측정** |
| 반사실 확인 (CF) | 라디오 | 1 | Q5 직후. **신규** |
| 직접 질문 닻 (DQ) | 라디오 | 1 | 동료 선택 시 종교 고려도 |
| 비교 의도 점검 (MC) | 라디오 | 2 | |
| 피드백 (FB) | 라디오 + 텍스트 | 2 | 솔직성 + 자유 의견 |
| **결과 페이지** | 시각화 | — | 8단계 차트·메시지 |
| 거울 테스트 (MT) | 라디오 + 텍스트 | 2 | 결과 후 자기 직면. **신규** |
| 디브리핑 | — | — | |

예상 소요 시간: **5~6분**.

---

## 5. 유형 운영 정책

- **유형 A (메인)** 를 기본으로 단독 배포한다.
- 유형 B (백업 1), 유형 C (백업 2) 는 코드에 포함되어 있으며, `secrets.toml`의 `[version_weights]` 가중치로 점진 투입할 수 있다.
- 세 유형은 동일한 측정 구조(10 CR + 1 CF + …)를 갖고 시나리오 내용만 다르다.

| 유형 | 중심 축 | Q5 시나리오 |
|---|---|---|
| A | 직접·정서·능동 | 가족의 종교 간 결혼 |
| B | 행동 부담·구조적 요청 | 친구의 종교적 변화 |
| C | 매개·인지·수동 | 이웃의 종교 행동 |

---

## 6. 데이터 스키마

응답은 Google Sheets의 두 탭에 저장된다.

### 6.1. `responses` 탭 (메인)

총 약 46개 컬럼. 자세한 헤더 정의는 `src/sheets.py::MAIN_HEADERS` 참조. 주요 컬럼군:
- 메타 (`timestamp`, `session_id`, `version`, `cb_condition`)
- 인구통계 (4)
- CR 정규화 응답 점수 (10)
- CR RT (10)
- CF / DQ / MC / FB
- RT 품질 플래그 (`rt_anomaly_flags`)
- 산출 점수 (`overall_caution`, `deviation_total`, `dom_*`, `dq_cr_alignment`, `rt_asymmetry`, `cf_actual_match`, `profile_type`, `dominant_domain`)
- 소요 시간

### 6.2. `mt_responses` 탭 (분리 저장)

거울 테스트 응답은 별도 탭에 저장된다. `session_id`로 메인 탭과 조인 가능하나, **분석은 도구 개선 목적으로만** 사용한다.

---

## 7. 점수 산출 규칙

`src/scoring.py`에 함수가 모두 포함되어 있다. 핵심 산출만 요약:

- **종교 간 차등 (`deviation_total`)** = ∑ \|Q*nA* − Q*nB*\|, 범위 0~15
- **전반적 신중도 (`overall_caution`)** = 10문항 점수 합, 범위 0~30
- **영역별 차등** = 공적/직장/사적 영역별 차등 합
- **자기 보고–응답 일치 (`dq_cr_alignment`)** = DQ 수준(1~4) − CR 차등 quantile(1~4), 범위 −3~+3
- **응답 시간 비대칭 (`rt_asymmetry`)** = \|평균 RT(종교1) − 평균 RT(종교2)\| (ms)
- **CF–실제 일치도 (`cf_actual_match`)** = 7개 카테고리 (§10.7)
- **프로파일 유형 (`profile_type`)** = 5유형 (`consistent_open` / `consistent_caution` / `devine_signature` / `self_aware_diff` / `mixed`)

---

## 8. RT 측정의 한계

- 본 도구의 RT는 **서버 사이드 `time.perf_counter()`** 기반이다.
- 사용자가 페이지를 잠시 떠난 경우의 시간 부풀림은 보정 불가하다.
- **1회 측정으로는 단정할 수 없으며**, 결과 페이지의 모든 RT 메시지는 "이번 응답에서는~" 프레이밍을 유지한다.
- 품질 플래그(`rt_too_fast` / `rt_too_slow` / `rt_inconsistent`)는 사후 분석에서 응답 필터링에 사용한다 (응답자에게는 노출하지 않음).

---

## 9. 라이선스 및 인용

본 도구는 RDAP 프로젝트 내부 자료이며, 학술 출판 시 다음을 인용한다.

> RDAP 프로젝트. (2026). RDAP 퀵버전: 종교 다양성 태도 프로파일 [Streamlit 애플리케이션]. 

문의: 도구 개발팀.