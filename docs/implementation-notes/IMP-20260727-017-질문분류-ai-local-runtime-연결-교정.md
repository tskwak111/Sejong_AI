# IMP-20260727-017 — 질문분류 AI local runtime 연결 교정

- Date/Time (KST): 2026-07-27T12:22:51+09:00
- Task ID: CLASSIFIER-RUNTIME-WIRING-001
- Type: bugfix-runtime-integration
- Status: Done
- Author/Agent: 사용자 제품 결정자 / Codex
- Branch: `codex/CLASSIFIER-RUNTIME-WIRING-001`
- Base commit: `6e62aa4`
- Related: Q-CLASS-001=A, Q-CLASS-002=A, ADR-0025, CHAT-NATURAL-001

## 1. 사용자 요청과 완료 기준

### 요청

승인했지만 실제 local 시민 API에 조립되지 않았던 Upstage 질문분류 AI를 즉시 연결한다.

### Acceptance Criteria

- exact classifier profile에서 `/api/v1/chat`의 안전한 ambiguous 질문만 classifier를 1회 사용한다.
- startup, health, readiness와 deterministic safety routes는 provider 호출 0이다.
- classifier 장애는 질문 row를 만들지 않는 안전한 FOLLOWUP으로 닫힌다.
- combined profile은 classifier/generator가 같은 non-resettable 20/30/40 ledger를 공유한다.
- 두 provider client와 DB pool은 lifespan에서 독립적으로 닫힌다.
- API 전체 test/lint/type gate와 tracked secret/docs/diff gate가 통과한다.

## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | Q-CLASS를 승인한 사용자, TDD 구현·통합한 Codex |
| When — 언제 | 2026-07-27 KST, PR #18 병합 후 local 실행 확인 중 |
| Where — 어디서 | `apps/api` local composition, Upstage generator budget, ignored primary `.env` |
| What — 무엇을 | classifier runtime 주입, shared ledger, lifecycle, 회귀/actual smoke |
| Why — 왜 | adapter 60/60을 실제 시민 runtime 완료로 잘못 판정한 결함을 교정하기 위해 |
| How — 어떻게 | 최신 main 새 branch, RED→GREEN, API full gate, PII-free frozen fixture actual |
| How much — 어느 정도 | tracked 코드 2·테스트 2·문서/버전 8개, DB/API 계약/data/dependency 변경 0 |

## 3. 시작 전 상태

- `QuestionClassifier`, exact settings, closed parser와 `ChatService.question_classifier` port는 존재했다.
- direct adapter actual 60/60과 fake service 주입 테스트는 통과했다.
- `create_local_app()`은 grounded generator만 주입하고 classifier를 생성하지 않았다.
- grounded generator는 legacy `AttemptBudget`만 받아 combined cap 40을 공유하지 않았다.
- `apps/api/tests/test_local.py`에는 classifier composition acceptance가 없었다.
- 시작 commit은 최신 private `origin/main`의 PR #18 merge `6e62aa4`였다.

## 4. 결정·가정·미지의 영역

| ID | 상태 | 내용 | 처리 |
|---|---|---|---|
| Q-CLASS-001/002 | 기존 승인 | privacy-first hybrid와 exact 호출 한도 | 변경 없이 구현 |
| GAP-RUNTIME | 해결 | local factory classifier 주입 0 | TDD composition 추가 |
| GAP-LEDGER | 해결 | combined generator가 별도 budget 사용 | shared ledger 지원 |
| Public/remote | 비범위 유지 | real citizen/free-input/public provider | 실행·승인 확대 없음 |

새 공개 계약, DB migration, production dependency 또는 제품 결정은 필요하지 않았다.

## 5. 설계와 버린 대안

### 선택

- classifier settings가 exact일 때만 client, ledger, classifier를 lazy composition한다.
- combined exact profile이면 classifier에서 만든 `ProviderAttemptLedger`를 grounded runtime에도
  전달한다. grounded-only profile은 기존 `AttemptBudget`과 호환한다.
- lifespan은 grounded runtime, classifier runtime, pool을 각각 suppress 경계로 닫는다.

### 버린 대안

- `UPSTAGE_CLASSIFIER_MODE`만 바꾸고 코드 미수정: constructor가 읽지 않아 효력이 없다.
- 모든 safe 질문을 provider로 전송: deterministic safety fast path와 비용 경계를 위반한다.
- classifier와 generator에 별도 budget 유지: combined cap 40을 보장하지 못한다.
- 새 SDK/dependency 추가: 기존 `httpx` adapter로 충분하다.

## 6. 구현 상세

| 파일/영역 | 변경 |
|---|---|
| `apps/api/src/sejong_ai_api/local.py` | exact classifier runtime 생성·주입·close, shared ledger 전달 |
| `apps/api/src/sejong_ai_api/llm/upstage_chat.py` | legacy budget 또는 shared ledger의 generator lane 지원 |
| `apps/api/tests/test_local.py` | actual factory injection, zero-use, failure, shared identity/lifecycle 회귀 |
| `apps/api/tests/llm/test_upstage_chat.py` | combined cap과 supplied ledger 사용 회귀 |
| source-of-truth/ADR/runbook | 실제 runtime 상태와 combined 설정·rollback 동기화 |
| manifest/changelog/version docs | patch/test/docs 버전 승격 |

데이터 흐름은
`PII redaction → deterministic safety/fast path → ambiguous-only classifier → server route
validation → ACTIVE retrieval → optional grounded generation → server-owned source`다.

## 7. 버전 전후

| 축 | Before | After | 이유 |
|---|---|---|---|
| Application | 0.11.0-natural-dialogue | 0.11.1-classifier-runtime | local wiring patch |
| Web | 0.7.0-natural-dialogue | unchanged | Web 변경 없음 |
| API | 4.0.0-draft | unchanged | wire 계약 불변 |
| Shared contracts | 1.0.0 | unchanged | 생성 타입 불변 |
| DB schema | 0.5.0-local | unchanged | migration 없음 |
| Official data | 0.1.0-initial.2 | unchanged | seed/lineage 불변 |
| Mock data | 0.0.0-not-populated | unchanged | mock 없음 |
| Prompt set | 0.3.1-hybrid-classifier | unchanged | prompt 불변 |
| Test suite | 1.9.1-natural-dialogue | 1.9.2-classifier-runtime | composition 회귀 |
| Docs | 2.25.0 | 2.25.1 | runtime/runbook 교정 |

## 8. RED/GREEN과 검증 증거

| 명령/검증 | 실제 결과 |
|---|---|
| 최초 2개 regression | RED 2: fallback 없음, ledger type 거부 |
| classifier factory + generator ledger 최소 구현 | GREEN 2 |
| combined identity/runtime RED | RED 2: generator ledger 미전달, builder kw 미지원 |
| combined 최소 구현 | GREEN 2 |
| focused API/LLM/chat gate | 148 passed |
| 독립 review 1차 | Important 2, Minor 1 |
| review remediation RED→GREEN | RED 3 → GREEN 4, 재검토 Critical/Important 0 |
| 최종 API 전체 pytest | 2,149 passed, 8 local-DB-only skipped, subtests 5 passed |
| API Ruff | PASS |
| API Mypy 55 source files | PASS |
| combined ignored `.env` presence-only preflight | classifier/generator/combined READY=YES |
| 최종 local factory actual frozen `C-11` | HTTP 200, INSUFFICIENT_GROUNDING, outbound 1, pool closed |

첫 inline actual 시도는 PowerShell stdin 한글 손상 때문에 `PRIVACY_UNRESOLVED`로 provider 0
fail-closed됐고 증거에서 제외했다. UTF-8 frozen fixture `C-11` 재실행은 provider-only
ambiguous case가 `INSUFFICIENT_GROUNDING`으로 매핑됐다. 이는 classifier가 `SUPPORTED`를
제안하고 fake repository의 grounding이 실패한 expected local smoke다. review 교정 전후로
같은 `C-11` actual을 한 번씩 실행해 이 작업의 추가 provider attempt는 총 2다.

tracked final docs/secret/package/diff 명령 결과는 최종 commit 전에 새로 실행해 기록했다.
DB full gate와 Web gate는 DB/Web/contract 변경이 없어 재실행하지 않았다.

## 9. 보안·개인정보·접근성·성능·비용

- Privacy: redaction 이전 provider 호출은 없다. NON_CIVIC/PERSONAL/LEGAL은 provider/row 0으로
  local factory 수준에서 검증했다.
- Security: key·DSN·provider body·질문 원문을 출력하거나 commit하지 않았다. ignored `.env`에는
  non-secret exact caps/modes만 추가·변경했다.
- Source authority: classifier는 답변·출처·저장 여부를 결정하지 않는다.
- Accessibility: UI 변경 없음.
- Performance: classifier 3초/1 attempt/retry 0, generator 8초/1 attempt/retry 0,
  process caps 20/30/40을 유지한다.
- Cost: frozen `C-11` actual classifier 요청 2건이 추가됐다. citizen API는 usage/cost를
  노출하지 않아 정확한 추가 비용을 D-095 cumulative에 합산하지 않았다.

## 10. 공식 데이터와 mock

- official `.2`, ACTIVE 20 local snapshot, office/mapping과 데이터 lineage는 변경하지 않았다.
- actual smoke repository는 test fake이며 official DB/readiness 증거로 사용하지 않는다.
- provider 출력은 KB/source가 아니고 repository에 저장하지 않았다.

## 11. 인간이 반드시 알아야 하는 내용

- 이 branch가 merge되고 local에서 pull/restart되어야 실제 실행 중인 API에 반영된다.
- primary ignored `apps/api/.env`는 classifier와 grounded mode가 모두 true인 exact combined
  profile로 맞췄으며 Git에는 포함되지 않는다.
- 실제 local DB password 불일치가 남아 있으면 API 시작은 별도 provisioning이 필요하다.
- public/remote 시민 호출, public admin, remote DB/deploy는 여전히 승인·구성되지 않았다.

## 12. AI 내부 구현 세부

- `_ClassifierRuntime`이 client와 shared ledger lifetime을 소유한다.
- classifier client는 첫 eligible ambiguous 요청에서만 만들어지고 constructor 실패 시 즉시
  close 후 process lifetime 동안 disabled된다.
- `UpstageChatGenerator`는 기존 `AttemptBudget` 호환을 유지하면서
  `ProviderAttemptLedger.reserve_generator()`도 받는다.
- custom grounded test factory의 기존 one-argument signature는 grounded-only에서 유지하고,
  combined에서는 shared ledger를 받을 수 없으므로 실행하지 않고 generator를 fail-closed한다.

## 13. 재현·롤백·인수인계

### 재현

1. branch merge 후 최신 main을 pull한다.
2. `apps/api/.env.example`의 exact classifier/generator caps를 ignored `.env`에 둔다.
3. local DB login을 provision하고 API를 재시작한다.
4. `/ready=200` 뒤 안전한 ambiguous 합성 질문과 deterministic safety 질문을 확인한다.

### 롤백

- 코드: 이 commit을 revert한다.
- 즉시 provider 차단: ignored `.env`에서
  `UPSTAGE_CLASSIFIER_MODE=false`, `UPSTAGE_GROUNDED_CHAT_MODE=false`로 바꾸고 API를 재시작한다.
- DB/data 복구는 필요 없다.

### 다음 개발자 시작점

- actual real-DB demo에서 status만 기록하는 bounded rehearsal을 수행한다.
- citizen API per-lane aggregate usage/cost observability는 원문·payload 없는 별도 P1 후보다.

## 14. 남은 위험

- current 실제 DB credential 오류는 이 코드 수정과 독립적이다.
- actual C-11 smoke는 fake repository를 사용해 provider routing만 증명하며 real DB grounding을
  증명하지 않는다.
- public/remote와 real citizen/free-input provider 전송은 계속 금지다.

## 15. 자체 리뷰

- [x] 요청 동작과 승인된 ADR 일치
- [x] RED→GREEN 및 API full gate
- [x] 계약·DB·data/dependency 불변
- [x] privacy/provider-zero·shared cap·lifecycle 검증
- [x] source-of-truth/ADR/runbook/version 동기화
- [x] 비밀·DSN·provider body·원문 미기록
- [x] 구현 노트 INDEX 갱신
