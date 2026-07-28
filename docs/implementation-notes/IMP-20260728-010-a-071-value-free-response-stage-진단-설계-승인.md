# IMP-20260728-010 — A-071 value-free response-stage 진단 설계 승인

- Date/Time (KST): 2026-07-28T20:08:29+09:00
- Task ID: A-071-RESPONSE-STAGE-DIAGNOSTICS-DESIGN
- Type: design-decision-gate
- Status: Decision-only — written specification review pending
- Author/Agent: 사용자 결정자 / Codex 설계·문서화
- Branch: main
- Base commit: 00a7b00
- Related plan/ADR/RFP: D-107/D-108, A-071, ADR-0027, CHAT-HYBRID-RAG-001

## 1. 사용자 요청과 완료 기준

### 요청

사용자의 `ㅇㅋ 구현해`를 A-071 추천 A 설계 승인으로 반영하고, production classifier parser의
enum-only optional observer와 aggregate-only actual evidence 경계를 written specification으로
고정한다.

### Acceptance Criteria

- 질문·provider body·status detail·exception·key·DSN을 observer/report에 넣지 않는다.
- production parser와 actual diagnostic의 검증 경로를 하나로 유지한다.
- public parser와 시민 fail-closed 동작, API/DB/data/dependency를 바꾸지 않는다.
- TDD·exact-one actual·비용·재실행 금지 조건을 명세한다.
- 구현 전 written specification 확인 gate를 남긴다.
## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 사용자가 추천 A를 승인하고 Codex가 설계·권위 문서를 작성했다. |
| When — 언제 | 2026-07-28 19:58~20:12 KST |
| Where — 어디서 | private local `main`, classifier/runner 설계와 `docs/` |
| What — 무엇을 | 13개 fixed terminal stage, typed observer, aggregate report, exact-one actual gate |
| Why — 왜 | D-107의 9/9 2xx가 strict decision 전에 거부된 정확한 단계를 원문 없이 찾기 위해 |
| How — 어떻게 | production parser observer A를 B runner 재파싱/C content logging과 비교해 선택 |
| How much — 어느 정도 | documentation-only; provider call·제품 코드·DB/data 변경 0 |

## 3. 시작 전 상태

- 관련 파일: `classifier_contracts.py`, `upstage_classifier.py`,
  `run_hybrid_rag_actual.py`, D-107 actual report, A-071.
- 기존 동작: 9/9 HTTP 2xx와 usage는 수신했지만 모든 parser failure가 `None`으로 합쳐졌다.
- 발견한 충돌/부채: runner가 body를 별도 재파싱하면 production validator와 drift한다.
- Git 상태: base `00a7b00`, local `main`은 `origin/main`보다 3 commit 앞선 clean tree였다.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| A-071 | B/High | strict response rejection stage | production typed observer A | internal parser/runner |
| D-108 | 인간 결정 | A 설계와 bounded actual 방향 | 승인, written spec review pending | TDD/actual gate |

## 5. 설계 결정과 대안

### 선택

production parser가 HTTP response마다 fixed enum terminal stage 하나만 optional observer에
전달한다. runner는 enum별 aggregate count만 기록한다.

### 이유

실제 runtime과 진단 경로가 동일하고 observer 타입이 content 전달을 원천 차단한다.

### 고려했지만 선택하지 않은 대안

- runner-only 재파싱: validator drift 때문에 기각.
- 오류/content logging: 개인정보·provider content 비보관 경계 때문에 기각.
## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| response-stage written spec | 구성요소·enum·flow·TDD·actual·rollback | 구현 권위 |
| D-108/A-071/SOT/version/CHANGELOG | 설계 승인과 미구현 경계 | 단일 권위 유지 |
| 제품 코드·runner | 변경 0 | written spec 확인 전 금지 |

### 데이터 흐름/상태 변화

이번 checkpoint에는 runtime 데이터 흐름 변화가 없다. 목표 흐름은 provider response process
memory에서 fixed enum만 분기해 aggregate counter로 전달하는 것이다.

### 오류·빈 상태·롤백

written spec이 승인되지 않으면 수정 후 다시 검토한다. 문서 rollback은 이 checkpoint commit을
revert하며 DB/data rollback은 없다.
## 7. 버전 전후

### 생성 시 매니페스트
- product_spec: 2.6.0
- repo_guidance: 1.7.10
- application: 0.12.1-bounded-hybrid-rag
- web: 0.8.0-guided-chat
- api: 4.0.0-draft
- shared_contracts: 1.0.0
- database_schema: 0.5.0-local
- official_data: 0.1.0-initial.2
- mock_data: 0.0.0-not-populated
- prompt_set: 0.4.1-json-mode-instruction
- test_suite: 2.1.4-json-mode-regression
- documentation: 2.29.4

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Application | 0.12.1 | 0.12.1 | 제품 코드 미변경 |
| Web | 0.8.0 | 0.8.0 | 미변경 |
| API | 4.0.0-draft | 동일 | 공개 계약 미변경 |
| DB schema | 0.5.0-local | 동일 | 미변경 |
| Official data | 0.1.0-initial.2 | 동일 | immutable |
| Mock data | 0.0.0-not-populated | 동일 | 미변경 |
| Prompt set | 0.4.1-json-mode-instruction | 동일 | 미변경 |
| Test suite | 2.1.4-json-mode-regression | 동일 | 구현 전 |
| Docs | 2.29.4 | 2.29.5 | written specification checkpoint |

## 8. 명령과 테스트 증거

| 명령/검증 | 결과 | 시간/개수 | 증거 경로 |
|---|---|---|---|
| Git/관련 parser·runner·A-071 조사 | 완료 | read-only | local stdout |
| spec placeholder/consistency/scope scan | 최종 검증 예정 | 1 spec | written spec |
| repository docs/secret/diff | 최종 검증 예정 | documentation gate | local stdout |

### 미실행 검증과 이유

TDD, API tests, actual provider call은 written specification 확인 전이므로 실행하지 않았다.
## 9. 보안·개인정보·접근성·성능 영향

- Privacy: 질문·response value 없이 enum/count만 허용하는 설계다.
- Security: key/DSN/status/exception 전달 금지, public generic failure 유지.
- Accessibility: UI 변경 0.
- Performance/cost: 현재 0 call/USD0. future exact-one은 retry 0/USD0.20 cap.

## 10. 데이터와 출처 영향

- 공식 데이터: `.2` 변경 0.
- mock/AI 생성: fixture 변경 0.
- schema/lineage: DB/API 계약 변경 0, documentation lineage만 증가.
- verified date: 2026-07-28 KST.

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- 추천 A 설계는 승인됐지만 written specification 확인 전 구현과 provider call은 0이다.
- future actual은 fixed 20/expected 9 outbound/정확히 1회이며 실패해도 재시도하지 않는다.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- enum 이름·observer protocol·counter ordering은 공개 API가 아닌 내부 구현 세부다.

## 13. 인수인계·재현·롤백

### 재현

base `00a7b00`에서 written spec과 D-108/A-071/version diff를 읽고 docs checker를 실행한다.

### 롤백

이 documentation checkpoint commit을 revert한다. DB/data/provider rollback은 없다.

### 다음 개발자 시작점

written spec 확인 뒤 `superpowers:writing-plans`로 exact RED/GREEN 계획을 작성한다.
## 14. 남은 위험·미해결 질문·다음 단계

- written specification 사용자 확인.
- 구현계획 승인 전 production code와 actual provider call 0.

## 15. 자체 리뷰

- [x] 요청 충족
- [x] 테스트/검증
- [x] source-of-truth/계약/버전 동기화
- [x] 개인정보 원문 노출 없음
- [x] 구현 노트 INDEX 갱신
