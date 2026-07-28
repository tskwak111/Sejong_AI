# IMP-20260729-006 — A-074 DeepSeek classifier provider

- Date/Time (KST): 2026-07-29T05:21:53+09:00
- Task ID: A-074-DEEPSEEK-CLASSIFIER-PROVIDER
- Type: implementation-provider-offline
- Status: In Progress
- Author/Agent: 사용자 결정자 / Codex root / task-scoped implementer·reviewer agents
- Branch: codex/a-074-deepseek-classifier-provider
- Formal A-074 base commit: 50aab6e
- Task 1 reviewed checkpoint: 8d36e04
- Related plan/ADR/RFP: ADR-0028, D-122, A-074, SFR-002,
  `docs/superpowers/plans/2026-07-29-deepseek-classifier-provider.md`

## 1. 사용자 요청과 완료 기준

### 요청

먼저 A-073 final review fix wave를 root/Upstage actual 재실행 없이 닫고, 이어서
DeepSeek `deepseek-v4-flash`를 local/private 질문 분류 선택 공급자로 추가한다. Offline TDD,
새 A-074 통합 gate 정확히 1회, clean-source review와 DeepSeek actual 정확히 1회를 수행하고
commit·push·Draft PR까지 진행하되 자동 merge하지 않는다.

### Acceptance Criteria

- A-073 root `NOT VERIFIED/FAIL`, invocation/rerun 1/0 보존
- exact five-string/uppercase `NONE`과 server parser 권위 유지
- deterministic 11/DeepSeek outbound 9, privacy/policy outbound 0
- HTTP 2xx·parse·accepted·expected match 각 9
- 질문/body/invalid value/secret 보관 0, cost <= USD0.20
- 새 A-074 offline gate·actual invocation 각 1, rerun 0
- 새 dependency/API/DB/data/Web/public/remote 변경 0

## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 사용자 결정자, root 통합 담당, task별 구현·검토 agents |
| When — 언제 | 2026-07-29 KST, A-073 D-121 종료 직후 |
| Where — 어디서 | isolated local worktree, `apps/api`, `scripts`, active docs |
| What — 무엇을 | selectable DeepSeek classifier, provider별 비용·usage, one-shot evidence |
| Why — 왜 | Upstage를 보존하면서 질문 분류 공급자 비교와 자연어 분류 품질을 검증하기 위해 |
| How — 어떻게 | ADR-0028, exact selector, shared parser, Subagent-Driven TDD, aggregate-only actual |
| How much — 어느 정도 | fixed20 중 11 provider-free/9 outbound, actual cap USD0.20, retry/rerun 0 |

## 3. 시작 전 상태

- 관련 파일: classifier port/parser/prompt, Upstage adapter/settings, local composition,
  process ledger, existing fixed20 runner
- 기존 동작: Upstage classifier-only composition, deterministic fail-closed, exact five-string
- 발견한 충돌/부채: cost ledger가 Upstage estimator에 고정, active docs가 Upstage-only,
  old runner/report/root wrapper 재사용 불가
- Git 상태: branch `codex/a-074-deepseek-classifier-provider`, formal baseline `50aab6e`

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| Q-LLM-PROVIDER-001 | A | classifier 비교 공급자 | A / DeepSeek exact model | Architecture·security·cost |
| A-074 | A | provider/actual/retention 경계 | D-122로 Resolved | 전체 수직 흐름 |

## 5. 설계 결정과 대안

### 선택

Explicit `CLASSIFIER_PROVIDER=disabled|upstage|deepseek`, local app only DeepSeek composition,
shared exact parser와 provider별 cost estimator, 별도 A-074 runner/report/lease를 사용한다.

### 이유

공개 계약·DB·공식 데이터를 건드리지 않고 provider output을 신뢰하지 않으면서 Upstage
classifier와 final generator를 보존할 수 있다.

### 고려했지만 선택하지 않은 대안

- Upstage 삭제: 기존 검증 경로와 rollback을 잃어 기각
- provider 자동 cascade: 비용·감사·예측 가능성을 해쳐 기각
- DeepSeek output 직접 사용: source/grounding 권위를 깨므로 기각
- A-073 wrapper/report 재사용: one-shot 증거를 훼손하므로 금지

## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| `llm/limits.py`, `deepseek_usage.py` | provider별 estimator와 strict usage envelope | Upstage 단가 오계산과 cache 과소계상 방지 |
| `classifier_provider.py`, `deepseek_settings.py`, `.env.example` | explicit `disabled|upstage|deepseek` selector와 exact local settings | 비밀값·공급자 역할 분리 |
| `deepseek_classifier.py` | 3초·retry0·concurrency1·output128·temperature0/thinking-off transport | untrusted `json_object`를 exact parser/catalog로 재검증 |
| `local.py` | loopback local/private에서만 선택 classifier 조합 | public main과 final-answer provider 불변 |
| `run_deepseek_classifier_actual.py` | fixed20 readiness·permanent lease·aggregate-only actual evidence | secret/body/value 없는 exact-one 증거 |
| `run_a074_offline_gate.ps1` | clean SHA의 root offline gate exact-one wrapper | A-073 wrapper 재사용 없이 stdout/stderr 보존 |
| Task 5 controlled tests/runbook | lock ownership, timeout tree termination, report no-overwrite | concurrency·hard-failure false evidence 차단 |
| authority/version docs | offline 구현 상태와 세 version 축 승격 | actual 전 상태를 과장하지 않고 동기화 |

### 데이터 흐름/상태 변화

raw question → deterministic PII/policy/obvious route → redacted `SafeQuestion` → selected
classifier → exact server parser/catalog validation → existing grounding/fallback. DB schema와
official data state는 변하지 않는다. DeepSeek가 제안한 값은 시민 응답·출처가 아니며,
서버가 ACTIVE/OFFICIAL catalog의 동일 row와 결합할 때만 기존 흐름으로 전달한다.

### 오류·빈 상태·롤백

설정·timeout·HTTP·empty·JSON·wire·catalog·usage·cost 실패는 retry 없이 deterministic
fallback이다. DeepSeek→Upstage 자동 cascade는 없다. 즉시 rollback은 ignored local
environment에서 `CLASSIFIER_PROVIDER=disabled`로 되돌리는 것이며 DB migration이나 데이터
복구는 필요 없다.

## 7. 버전 전후

### 생성 시 매니페스트
- product_spec: 2.6.0
- repo_guidance: 1.7.10
- application: 0.12.4-classifier-wire-diagnostics
- web: 0.8.0-guided-chat
- api: 4.0.0-draft
- shared_contracts: 1.0.0
- database_schema: 0.5.0-local
- official_data: 0.1.0-initial.2
- mock_data: 0.0.0-not-populated
- prompt_set: 0.4.3-explicit-route-matrix
- test_suite: 2.1.7-classifier-wire-correction
- documentation: 2.30.8

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Application | 0.12.4-classifier-wire-diagnostics | 0.13.0-selectable-classifier-provider | selectable local classifier 구현 |
| Web | 0.8.0-guided-chat | 동일 | 시민 UI 변경 없음 |
| API | 4.0.0-draft | 동일 | 공개 계약 변경 없음 |
| Shared contracts | 1.0.0 | 동일 | 공개 schema 변경 없음 |
| DB schema | 0.5.0-local | 동일 | migration 없음 |
| Official data | 0.1.0-initial.2 | 동일 | immutable approved data 사용 |
| Mock data | 0.0.0-not-populated | 동일 | mock 추가 없음 |
| Prompt set | 0.4.3-explicit-route-matrix | 동일 | A-073 prompt byte 변경 없음 |
| Test suite | 2.1.7-classifier-wire-correction | 2.2.0-deepseek-classifier-provider | provider·one-shot TDD |
| Docs | 2.30.8 | 2.31.0-deepseek-classifier-provider | offline 구현·runbook 동기화 |

## 8. 명령과 테스트 증거

| 명령/검증 | 결과 | 시간/개수 | 증거 경로 |
|---|---|---|---|
| Task 1 provider cost/usage focused tests | PASS | reviewed checkpoint | `apps/api/tests/llm/test_deepseek_usage.py`, `test_limits.py` |
| Task 2 settings/selector focused tests | PASS | 35 tests | `apps/api/tests/llm/test_deepseek_settings.py` |
| Task 3 transport regression | PASS | 226 tests | `apps/api/tests/llm/test_deepseek_classifier.py` |
| Task 4 local composition regression | PASS | 595 tests + 5 subtests | `apps/api/tests/test_local.py`, `test_architecture.py` |
| Task 5 runner/wrapper combined regression | PASS | 348 tests + 5 subtests | `scripts/tests/test_run_*deepseek*`, `test_run_a074_offline_gate.py` |
| Ruff format/check, Mypy strict, PS parser | PASS | parser 1,347 tokens / 0 errors | tracked source/tests and runbook |
| Task 5 independent scoped review | PASS | Critical 0 / Important 0 | commit `54a767c` scoped review |
| Task 6 area integration | PASS | 1,012 tests + 5 subtests, 1 known warning | exact command below |
| Initial Ruff format check | FAIL→corrected | DeepSeek settings·test 2 files | mechanical formatting only |
| Focused post-format/settings test | PASS | 13 tests | `apps/api/tests/llm/test_deepseek_settings.py` |
| Ruff format/check | PASS | 125 files | exact command below |
| API Mypy strict | PASS | 122 source files | `apps/api/pyproject.toml` config |
| Task 5 runner Mypy strict | PASS | 3 source files | exact command below |
| Docs/secret/diff checks | PASS | links/secret patterns/diff | repository scripts below |

### Task 6 재현 명령

```powershell
.tools/uv/uv.exe run --offline --frozen --project apps/api pytest `
  apps/api/tests/llm apps/api/tests/chat apps/api/tests/test_local.py `
  apps/api/tests/test_chat_route.py apps/api/tests/test_architecture.py `
  scripts/tests/test_run_deepseek_classifier_actual.py `
  scripts/tests/test_run_a074_offline_gate.py -q -p no:cacheprovider

.tools/uv/uv.exe run --offline --frozen --project apps/api ruff format --check `
  apps/api/src apps/api/tests scripts/run_deepseek_classifier_actual.py `
  scripts/tests/test_run_deepseek_classifier_actual.py `
  scripts/tests/test_run_a074_offline_gate.py
.tools/uv/uv.exe run --offline --frozen --project apps/api ruff check `
  apps/api/src apps/api/tests scripts/run_deepseek_classifier_actual.py `
  scripts/tests/test_run_deepseek_classifier_actual.py `
  scripts/tests/test_run_a074_offline_gate.py

Push-Location apps/api
.venv/Scripts/python.exe -m mypy src tests
.venv/Scripts/python.exe -m mypy --strict `
  ../../scripts/run_deepseek_classifier_actual.py `
  ../../scripts/tests/test_run_deepseek_classifier_actual.py `
  ../../scripts/tests/test_run_a074_offline_gate.py
Pop-Location

python -B scripts/check_repository_docs.py
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File scripts/check_secret_patterns.ps1 -RepositoryRoot .
git diff --check
```

### 미실행 검증과 이유

- A-074 offline gate: source checkpoint commit 전이므로 invocation 0, rerun 0.
- DeepSeek actual: offline gate·same-SHA clean review 전이므로 invocation 0, rerun 0이고
  관측 token·비용 metric은 존재하지 않는다.
- A-073 root wrapper와 모든 Upstage actual: 사용자 금지에 따라 재실행하지 않았다.
- public/remote/실제 시민 free-input: 승인 범위 밖이다.

## 9. 보안·개인정보·접근성·성능 영향

- Privacy: provider에는 `SafeQuestion`의 마스킹 완료 텍스트만 전달한다. 질문 원문, masked
  question, request/response body, invalid field value, exception 상세를 DB·로그·report에
  영속하지 않는다. policy/privacy 고정 probe는 provider outbound 0으로 고정한다.
- Security: DeepSeek key와 Upstage key는 서로 다른 ignored local 설정이고, public main은
  provider-free다. exact URL/model/settings, no retry/cascade, strict server parser/catalog,
  permanent lease와 result no-overwrite를 적용한다.
- Accessibility: Web·시민 화면 계약 변경이 없어 직접 영향이 없다.
- Performance/cost: request 3초, concurrency 1, retry 0, output 128이다. actual은 all-miss+
  VAT 보수 계산으로 9회 최대 USD0.02306304이며 session cap USD0.20 아래다. 아직 실행하지
  않아 관측 token·비용 metric은 존재하지 않는다.

## 10. 데이터와 출처 영향

- 공식 데이터: immutable `0.1.0-initial.2`의 ACTIVE/OFFICIAL 19건과 topic coverage를
  hash로 고정해 읽기만 한다. 변경·승격 0.
- mock/AI 생성: fixed20은 비식별 synthetic fixture이고 official data가 아니다. 모델 출력은
  공식 출처·기관·사실로 저장하지 않는다.
- schema/lineage: API/DB migration·계약·generated type 변경 0. 서버 catalog가 최종 권위다.
- verified date: 2026-07-29 KST offline implementation checkpoint.

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- Q-LLM-PROVIDER-001=A가 local/private classifier-only DeepSeek 사용과 actual exact1을
  승인했다. final answer provider는 여전히 Upstage다.
- public 배포, remote DB, 실제 시민 free-input, 자동 merge는 승인되지 않았다.
- A-074 offline gate와 actual은 아직 실행하지 않았다. 각각 실행되면 성공·실패와 관계없이
  자동 재실행하지 않는다.
- actual readiness에서 ignored `DEEPSEEK_API_KEY`가 유효하지 않으면 lease를 소비하지 않고
  generic readiness failure로 중단한다. 값 자체는 읽거나 보고하지 않는다.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- ProviderAttemptLedger는 역할별 estimator를 주입받아 DeepSeek cache hit가 있어도 acceptance
  비용은 전 input cache miss로 보수 계상한다.
- response observer는 value-free stage와 aggregate usage/HTTP class만 센다.
- offline wrapper는 lock을 실제 획득한 process만 result를 쓰며 child 종료가 확인되지 않으면
  mutable log hash를 발행하지 않는다.
- readiness-only는 client/network/lease/report/temp file을 만들지 않는다.

## 13. 인수인계·재현·롤백

### 재현

- Offline focused/area 검증은 approved plan Task 6 명령을 사용한다.
- Gate exact1 전에는 `docs/runbooks/DEEPSEEK-CLASSIFIER-ACTUAL.md`의 artifact-absence와 clean
  source 절차를 따른다.
- actual은 같은 source SHA의 offline PASS 뒤 readiness-only를 먼저 실행하고, PASS일 때만
  runbook의 actual 명령을 정확히 한 번 실행한다.

### 롤백

- runtime rollback: ignored local environment의 `CLASSIFIER_PROVIDER=disabled`.
- code rollback: A-074 provider commits를 revert한다. DB·official data·public contract rollback은
  필요 없다.
- 실행한 one-shot lease/report는 감사 증거이므로 삭제하거나 덮어쓰지 않는다.

### 다음 개발자 시작점

- Task 6 source checkpoint commit을 기준으로 clean HEAD를 확인한다.
- Task 7 새 A-074 wrapper exact1 → Task 8 same-SHA review/readiness/actual exact1 순서를 바꾸지
  않는다.
- A-073 root wrapper와 Upstage actual은 어떤 이유로도 재실행하지 않는다.

## 14. 남은 위험·미해결 질문·다음 단계

- DeepSeek actual 응답이 exact wire/oracle에 맞는지는 아직 증명되지 않았다.
- ignored local key의 실제 유효성은 readiness까지 Pending이다.
- 한 번 실행한 actual이 FAIL이면 결과를 보존하고 새 인간 승인 없이는 재실행하지 않는다.
- public/remote 운영에는 개인정보·약관·비용·rate-limit 별도 ADR이 필요하다.

## 15. 자체 리뷰

- [x] A-073 증거 불변과 A-074 offline 구현 요청 충족
- [x] Task 6 area/repository 검증
- [x] source-of-truth/계약/버전 동기화 — 공개 계약은 불변
- [x] 개인정보 원문·provider body·invalid value·secret 노출 없음
- [x] 구현 노트 INDEX 갱신
- [ ] A-074 offline gate·actual·최종 리뷰·Draft PR
