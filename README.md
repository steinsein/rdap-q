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

---

## 2. 설문 구조

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

## 3. 점수 산출 규칙

`src/scoring.py`에 함수가 모두 포함되어 있다. 핵심 산출만 요약:

- **종교 간 차등 (`deviation_total`)** = ∑ \|Q*nA* − Q*nB*\|, 범위 0~15
- **전반적 신중도 (`overall_caution`)** = 10문항 점수 합, 범위 0~30
- **영역별 차등** = 공적/직장/사적 영역별 차등 합
- **자기 보고–응답 일치 (`dq_cr_alignment`)** = DQ 수준(1~4) − CR 차등 quantile(1~4), 범위 −3~+3
- **응답 시간 비대칭 (`rt_asymmetry`)** = \|평균 RT(종교1) − 평균 RT(종교2)\| (ms)
- **CF–실제 일치도 (`cf_actual_match`)** = 7개 카테고리 (§10.7)
- **프로파일 유형 (`profile_type`)** = 5유형 (`consistent_open` / `consistent_caution` / `devine_signature` / `self_aware_diff` / `mixed`)

---

## 4. RT 측정의 한계

- 본 도구의 RT는 **서버 사이드 `time.perf_counter()`** 기반이다.
- 사용자가 페이지를 잠시 떠난 경우의 시간 부풀림은 보정 불가하다.
- **1회 측정으로는 단정할 수 없으며**, 결과 페이지의 모든 RT 메시지는 "이번 응답에서는~" 프레이밍을 유지한다.
- 품질 플래그(`rt_too_fast` / `rt_too_slow` / `rt_inconsistent`)는 사후 분석에서 응답 필터링에 사용한다 (응답자에게는 노출하지 않음).

---

## 5. 라이선스 및 인용

본 도구는 RDAP 프로젝트 내부 자료이며, 학술 출판 시 다음을 인용한다.

> RDAP 프로젝트. (2026). RDAP 퀵버전: 종교 다양성 태도 프로파일 [Streamlit 애플리케이션]. 

문의: 도구 개발팀.
