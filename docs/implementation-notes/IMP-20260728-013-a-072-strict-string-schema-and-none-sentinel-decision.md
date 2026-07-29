# IMP-20260728-013 — A-072 strict string schema and NONE sentinel decision

- Date/Time (KST): 2026-07-28T21:19:12+09:00
- Task ID: Q-LLM-014
- Type: decision-design
- Status: Decision-only
- Author/Agent: 사용자 결정자 / Codex 기록·설계
- Branch: main
- Base commit: 97e4c80
- Related plan/ADR/RFP: ADR-0027, A-072, D-111/D-112, IMP-20260728-012

## 1. 사용자 요청과 완료 기준

### 요청

사용자가 `Q-LLM-014: A`로 A-072의 strict string schema와 `NONE` sentinel 방식을 선택했다.

### Acceptance Criteria

- 선택 A를 source-of-truth, 결정 로그, 모호성 등록부와 작업 상태에 일관되게 기록한다.
- public API/DB/data/dependency를 변경하지 않는다.
- 상세 설계 승인 전 제품 코드와 provider actual을 실행하지 않는다.
- 다음 설계 검토에서 provider wire, server normalization, fail-closed 경계를 명확히 제시한다.

## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 사용자가 A를 결정했고 Codex가 권위 문서와 설계 checkpoint를 기록했다. |
| When — 언제 | 2026-07-28 21:19 KST |
| Where — 어디서 | `main`의 source-of-truth·결정·모호성·task·version·구현 노트 문서 |
| What — 무엇을 | strict Upstage `json_schema`, required string 5필드, fixed `NONE` sentinel을 확정했다. |
| Why — 왜 | D-111 actual 9/9가 JSON object였지만 exact key set에서 거절됐고, 공식 structured output 방식으로 단일 변수를 교정해야 하기 때문이다. |
| How — 어떻게 | provider-only wire에서 exact key/type를 강제하고 서버에서 `NONE`을 기존 `None`으로 정규화한다. |
| How much — 어느 정도 | 문서·버전 메타만 변경, 제품 코드·provider call·DB/data/API/dependency 0, 비용 USD 0 |

## 3. 시작 전 상태

- 관련 파일: `classifier_prompt.py`, `upstage_classifier.py`, strict parser tests와 D-111 actual
  report를 조사한 IMP-20260728-012.
- 기존 동작: request는 `response_format.type=json_object`; prompt는 축약 label을 포함하고
  response parser는 exact canonical 5-key object를 요구한다.
- 발견한 충돌/부채: JSON object 보장은 exact key/schema 보장이 아니며 actual 9/9가
  `KEY_SET_REJECTED`였다. 조사한 공식 타입 목록은 nullable union을 명확히 보장하지 않았다.
- Git 상태: base `97e4c80`, 시작 시 tracked worktree clean.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| Q-LLM-014 / A-072 | B / High | nullable provider wire 표현과 exact-key 보장 방식 | A: required string 5필드 + fixed `NONE` sentinel | provider-only prompt/request/parser/test; public 계약 불변 |

## 5. 설계 결정과 대안

### 선택

- Upstage request의 `response_format`을 official strict `json_schema` 방식으로 설계한다.
- exact keys는 `route`, `intent`, `topic_id`, `coverage_id`, `pending_slot`이다.
- 다섯 값은 모두 string이고 nullable 의미는 정확히 대문자 `NONE`만 사용한다.
- 서버는 sentinel을 내부 `None`으로 바꾼 뒤 기존 closed enum/catalog validator를 적용한다.

### 이유

- exact key와 추가 필드 금지를 provider 단계에서 강제할 수 있다.
- 공식 문서가 명시한 string/object/required/additionalProperties/strict 범위 안에 머문다.
- public/internal domain 모델의 nullable 의미를 바꾸지 않고 wire 호환 계층에서만 처리한다.

### 고려했지만 선택하지 않은 대안

- B, nullable union `["string", "null"]`: 더 자연스럽지만 조사한 공식 지원 타입 목록에서
  null/union 지원이 명확하지 않아 새 4xx 위험이 있다.
- C, prompt-only exact example: 변경량은 작지만 schema enforcement가 없고 이전 prompt-only
  actual이 exact key set에서 9/9 실패했다.

## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| 권위·결정 문서 | D-112와 A-072 Decision A 기록 | 선택의 단일 기준 유지 |
| task/version/changelog | design review 상태와 docs 2.29.9 기록 | 구현 전 checkpoint 추적 |
| 제품 코드·계약·DB·data | 변경 없음 | 설계 승인 gate 준수 |

### 데이터 흐름/상태 변화

이번 요청에서는 runtime 상태 변화가 없다. 승인 후 목표 흐름은
`safe masked question → bounded catalog → strict 5-key wire → NONE normalization → existing
closed validator → decision/fail-closed`다.

### 오류·빈 상태·롤백

알 수 없는 sentinel, 누락/추가 key, 비문자열 값, enum/catalog 불일치는 모두 기존처럼
decision `None`과 fail-closed 시민 fallback으로 종료하도록 다음 설계에서 고정한다.

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
| Application | 0.12.2-response-stage-diagnostics | unchanged | 제품 코드 변경 0 |
| Web | 0.8.0-guided-chat | unchanged | Web 변경 0 |
| API | 4.0.0-draft | unchanged | 공개 계약 변경 0 |
| DB schema | 0.5.0-local | unchanged | migration/DB 실행 0 |
| Official data | 0.1.0-initial.2 | unchanged | 공식 데이터 변경 0 |
| Mock data | 0.0.0-not-populated | unchanged | mock 변경 0 |
| Prompt set | 0.4.1-json-mode-instruction | unchanged | 설계 승인 전 prompt 변경 0 |
| Test suite | 2.1.5-response-stage-diagnostics | unchanged | 구현 전 test 변경 0 |
| Docs | 2.29.8 | 2.29.9 | Q-LLM-014 결정 checkpoint |

## 8. 명령과 테스트 증거

| 명령/검증 | 결과 | 시간/개수 | 증거 경로 |
|---|---|---|---|
| `python -B scripts/check_repository_docs.py` | PASS — `repository documentation check passed` | 1회 | stdout |
| `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check_secret_patterns.ps1 -RepositoryRoot .` | PASS — finding 0 | 1회 | exit 0 |
| `git diff --check` | PASS — whitespace error 0 | 1회 | exit 0 |

### 미실행 검증과 이유

- 제품 테스트·실제 Upstage 호출: 결정 기록 단계이며 상세 설계 승인 전이라 실행하지 않았다.
- DB/Web/API actual: 변경이 없으므로 실행하지 않았다.

## 9. 보안·개인정보·접근성·성능 영향

- Privacy: 질문 원문·provider body를 읽거나 기록하지 않았고 external call 0이다.
- Security: key·DSN·status detail을 출력하지 않았으며 기존 fail-closed 경계는 불변이다.
- Accessibility: UI 변경 없음.
- Performance/cost: runtime 변경 없음, provider 비용 USD 0.

## 10. 데이터와 출처 영향

- 공식 데이터: `0.1.0-initial.2` bytes 변경 0.
- mock/AI 생성: 변경 0.
- schema/lineage: DB schema와 catalog lineage 변경 0.
- verified date: 2026-07-28.

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- Q-LLM-014=A는 provider-only wire 결정이며 시민에게 보이는 public 응답 계약을 바꾸지 않는다.
- 제품 구현과 새 actual은 아직 승인되지 않았다. 우선 상세 설계 1부 확인이 필요하다.
- corrective actual은 구현·offline 검증·clean source commit 뒤 별도 승인을 받아야 한다.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- 다음 단계의 helper/module 경계와 exact test case 배치는 같은 계약 안에서 AI가 제안할 수 있다.
- schema에 provider enum을 중복 기입하지 않고 server validator를 권위로 유지하는 세부는
  설계 검토에서 설명한다.

## 13. 인수인계·재현·롤백

### 재현

1. D-111의 `KEY_SET_REJECTED` 9/9 증거를 확인한다.
2. IMP-20260728-012의 official docs 대조와 A/B/C 비교를 확인한다.
3. D-112와 A-072의 Decision A 상태, manifest docs 2.29.9를 확인한다.

### 롤백

이 요청은 문서-only다. D-112를 삭제해 역사를 재작성하지 말고 후속 결정 행으로 대체한다.
실수로 배포되지 않은 메타 변경을 되돌려야 한다면 이 커밋의 문서 diff만 revert한다.

### 다음 개발자 시작점

A-072 설계 1부 승인 후 written specification을 작성하고 자체 리뷰한 다음 사용자 명세 승인을
받는다. 그 뒤 RED/GREEN plan을 작성하며 제품 코드나 provider call을 먼저 실행하지 않는다.

## 14. 남은 위험·미해결 질문·다음 단계

- 상세 parser/prompt/test 설계 1부 승인.
- written specification 및 plan 승인.
- TDD offline 구현 뒤 corrective actual 별도 인간 승인.

## 15. 자체 리뷰

- [x] 요청 충족
- [x] 테스트/검증
- [x] source-of-truth/계약/버전 동기화
- [x] 개인정보 원문 노출 없음
- [x] 구현 노트 INDEX 갱신
