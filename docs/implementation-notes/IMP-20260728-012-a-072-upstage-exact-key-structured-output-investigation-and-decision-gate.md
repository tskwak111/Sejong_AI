# IMP-20260728-012 — A-072 Upstage exact-key structured-output investigation and decision gate

- Date/Time (KST): 2026-07-28T21:12:48+09:00
- Task ID: A-072-CLASSIFIER-EXACT-KEY-CORRECTION
- Type: diagnosis-decision-gate
- Status: Decision-only — Q-LLM-014 pending
- Author/Agent: 사용자 방향 승인 / Codex 조사
- Branch: main
- Base commit: 629f1bb
- Related plan/ADR/RFP: D-111, A-072, ADR-0027,
  `docs/test-reports/CHAT-HYBRID-RAG-001-UPSTAGE-ACTUAL.md`

## 1. 사용자 요청과 완료 기준

### 요청

사용자가 A-071의 `KEY_SET_REJECTED` 9/9 진단 후 A-072 exact-key 교정을 계속 진행하도록
지시했다.

### Acceptance Criteria

- 실제 provider를 다시 호출하지 않고 root cause와 현재 공식 지원 범위를 대조
- validator 완화·provider body 보관·새 dependency 없이 2~3개 교정 접근 비교
- architecture/prompt/provider-wire 변경에 필요한 인간 결정 하나를 명확히 제시
- 결정 전 제품 코드 변경 0
## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 사용자가 진행을 승인하고 Codex가 repository와 Upstage 공식 문서를 대조했다. |
| When — 언제 | 2026-07-28 KST |
| Where — 어디서 | local/private `main`, classifier prompt/transport/contracts/tests와 공식 Upstage docs |
| What — 무엇을 | exact five-key failure의 request-side 원인과 structured-output 선택지 조사 |
| Why — 왜 | 추측성 prompt 수정이나 실제 호출 반복 없이 strict decision을 안정화하기 위해 |
| How — 어떻게 | A-071 aggregate evidence→request payload→공식 `json_schema` 요구 역추적 |
| How much — 어느 정도 | 코드/provider/API/DB/data 변경 0, 실제 호출 0, 인간 결정 1개 |

## 3. 시작 전 상태

- 관련 파일: `classifier_prompt.py`, `upstage_classifier.py`, `classifier_contracts.py`,
  `test_upstage_classifier.py`, D-111 actual report
- 기존 동작: request는 `response_format={"type":"json_object"}`이고 prompt shorthand만으로
  five-key shape를 요구한다. D-111 actual은 9건 모두 JSON object까지 통과한 뒤
  `KEY_SET_REJECTED`에서 종료했다.
- 발견한 충돌/부채: 공식 Upstage 문서는 exact structured output에 `json_schema`,
  `strict:true`, 모든 필드 `required`, `additionalProperties:false`를 안내한다. 현재 request에는
  schema가 없다. 공식 지원 타입 목록은 string/number/boolean/integer/object/array를 명시하지만
  `null`/union은 명시하지 않는다.
- Git 상태: 시작 clean `main` HEAD `629f1bb`; `origin/main`은 `8ecde44`로 로컬보다 뒤다.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| Q-LLM-014 | A/Blocker | nullable wire를 공식 지원 string-only schema로 바꿀지 | 추천 A, 답 없으면 A | prompt set, internal adapter/tests, future actual |

## 5. 설계 결정과 대안

### 선택

아직 미확정. 추천안은 공식 `json_schema`를 사용하되 다섯 key를 모두 required string으로 만들고
nullable 의미는 고정 sentinel `NONE`으로 전달한 뒤 서버가 기존 `None` 계약으로 정규화하는
방식이다.

### 이유

Upstage가 문서화한 타입만 사용하면서 exact keys를 schema로 강제할 수 있고, public
`ClassifierDecision`과 시민 API는 바뀌지 않는다.

### 고려했지만 선택하지 않은 대안

- nullable union `["string","null"]`: wire는 깔끔하지만 Upstage 공식 지원 목록에 null/union이
  명시되지 않아 다시 4xx가 날 위험이 있다.
- prompt-only full example: 코드 변경은 작지만 D-107 prompt-only 교정 뒤에도 key set이 9/9
  실패해 구조 보장이 없다.
- tool calling: exact arguments는 가능하지만 parser·token·finish/choice 경계 변경이 크고
  five-key object 하나에는 과도하다.
## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| 구현 코드 | 없음 | design human gate 전 |
| 이 구현 노트/INDEX | 조사 근거와 Q-LLM-014 기록 | 재현·인수인계 |

### 데이터 흐름/상태 변화

없음. provider call·DB write·prompt/runtime 변경 0.

### 오류·빈 상태·롤백

현재 local runtime은 계속 fail-closed fallback을 사용한다. 이번 문서-only 조사 롤백은 note
commit revert이며 DB/data rollback은 없다.
## 7. 버전 전후

### 생성 시 매니페스트
- product_spec: 2.6.0
- repo_guidance: 1.7.10
- application: 0.12.2-response-stage-diagnostics
- web: 0.8.0-guided-chat
- api: 4.0.0-draft
- shared_contracts: 1.0.0
- database_schema: 0.5.0-local
- official_data: 0.1.0-initial.2
- mock_data: 0.0.0-not-populated
- prompt_set: 0.4.1-json-mode-instruction
- test_suite: 2.1.5-response-stage-diagnostics
- documentation: 2.29.8

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Application | 0.12.2-response-stage-diagnostics | unchanged | 결정 전 |
| Web | 0.8.0-guided-chat | unchanged | 영향 없음 |
| API | 4.0.0-draft | unchanged | public contract 불변 |
| DB schema | 0.5.0-local | unchanged | migration 없음 |
| Official data | 0.1.0-initial.2 | unchanged | protected data |
| Mock data | 0.0.0-not-populated | unchanged | 생성 없음 |
| Prompt set | 0.4.1-json-mode-instruction | unchanged | 결정 전 |
| Test suite | 2.1.5-response-stage-diagnostics | unchanged | 구현 전 |
| Docs | 2.29.8 | unchanged | note-only, version axis 유지 |

## 8. 명령과 테스트 증거

| 명령/검증 | 결과 | 시간/개수 | 증거 경로 |
|---|---|---|---|
| Git/status/recent history | clean baseline 확인 | HEAD `629f1bb` | command output |
| prompt/transport/contracts/tests 조사 | current `json_object`, formal schema 0 확인 | relevant files | repository |
| Upstage 공식 문서 조회 | `json_schema` strict requirements 확인 | provider call 0 | `https://console.upstage.ai/docs/capabilities/generate/structured-outputs` |

### 미실행 검증과 이유

제품 코드가 바뀌지 않아 pytest/Ruff/Mypy는 실행하지 않았다. actual provider call은 A-072
written spec·plan·별도 승인 전 금지한다.
## 9. 보안·개인정보·접근성·성능 영향

- Privacy: 질문·provider body·key·DSN 접근/출력/보관 0
- Security: strict validator와 fail-closed fallback 유지
- Accessibility: Web 변경 없음
- Performance/cost: provider call 0, 비용 0

## 10. 데이터와 출처 영향

- 공식 데이터: 변경 0
- mock/AI 생성: 변경 0
- schema/lineage: D-111 aggregate evidence만 read-only 근거로 사용
- verified date: 2026-07-28 KST

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- Q-LLM-014에서 internal provider wire의 nullable 표현을 결정해야 한다.
- 추천 A는 public API/DB/data가 아니라 prompt set과 internal classifier adapter만 바꾼다.
- 새 exact-one actual은 written spec·TDD source commit 뒤 별도 human gate다.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- schema constant 위치, helper 함수명, fixture 구성은 승인된 wire 계약 안에서 AI가 정한다.

## 13. 인수인계·재현·롤백

### 재현

current request payload에서 `response_format`을 확인하고 D-111 report의 stage counts를 공식
structured-output 문서와 대조한다. provider command는 실행하지 않는다.

### 롤백

note/INDEX commit을 revert한다. runtime/DB/data rollback은 없다.

### 다음 개발자 시작점

Q-LLM-014 답을 D-112로 기록하고 A-072 설계 섹션을 작성한다. design 승인 전 code를 쓰지 않는다.
## 14. 남은 위험·미해결 질문·다음 단계

- Upstage가 nullable/union schema를 실제로 지원하는지는 현재 공식 문서에서 명확히 확인되지 않았다.
- A안은 이 미지의 영역을 string-only sentinel로 제거한다.

## 15. 자체 리뷰

- [x] 요청 충족
- [x] 테스트/검증 — code test not applicable, provider call 0
- [x] source-of-truth/계약/버전 동기화 — 행동 변경 0
- [x] 개인정보 원문 노출 없음
- [x] 구현 노트 INDEX 갱신
