# PLAN-20260729-A074 — Selectable DeepSeek Classifier Provider

## 상태

Approved / In Progress

The user's exact A-074 instruction approves this plan, Subagent-Driven TDD, one new offline gate,
one DeepSeek actual and Draft PR publication. It does not approve automatic merge.

## 목표와 비목표

- 목표: add DeepSeek `deepseek-v4-flash` as a classifier-only, local/private, explicitly selected
  provider behind the existing exact parser and deterministic safety boundary.
- 목표: preserve the Upstage classifier and separate grounded-answer generator.
- 목표: obtain truthful one-shot aggregate evidence without rerunning A-073.
- 비목표: public/remote/free-input, API/DB/data/Web change, generated facts/sources, new production
  dependency, provider cascade or automatic merge.

## 사용자 가치와 인수 기준

- 사용자 가치: compare a current alternative classifier without weakening grounded citizen
  answers or the no-retention policy.
- Acceptance Criteria:
  - exact five-string wire and uppercase `NONE` unchanged;
  - deterministic 11/provider outbound 9 on fixed 20;
  - privacy/policy outbound and storage 0;
  - HTTP/parse/accept/oracle match 9;
  - timeout 3/retry 0/concurrency 1/output 128;
  - conservative actual cost at most USD 0.20;
  - DeepSeek failure uses deterministic fallback;
  - one new offline wrapper invocation and one actual invocation, rerun 0;
  - all focused/area/full gates and independent review recorded;
  - commit, push and Draft PR; no merge.

## 권위 근거

- RFP ID: local/private Hybrid RAG and approved official-KB answer path
- source-of-truth: `docs/00_SOURCE_OF_TRUTH.md`
- ADR: ADR-0023, ADR-0025, ADR-0027, ADR-0028
- discovery: `docs/discovery/A_074_DEEPSEEK_CLASSIFIER_PROVIDER_AUDIT.md`
- specification:
  `docs/superpowers/specs/2026-07-29-deepseek-classifier-provider-design.md`
- related note: A-073 IMP-005; create one A-074 implementation note during integration

## 현재 상태와 조사 결과

- 활성 코드: provider-neutral classifier port, masked safe question, exact parser, Upstage
  adapter, shared budget ledger, local runtime composition.
- legacy 참고: none used as authority.
- 확인한 명령: Git branch/status/log/diff; focused A-073 tests and reviews already recorded.
- 발견한 충돌: shared cost estimator is Upstage-specific; active docs say classifier is
  Upstage-only; old actual runner/report cannot be reused.
- preserved evidence: A-073 root `NOT VERIFIED/FAIL`, invocation 1, rerun 0; no A-073 or Upstage
  actual rerun.

## 미지의 영역과 인터뷰

| ID | 영향 | 질문 | 상태 | 결정 |
|---|---|---|---|---|
| Q-LLM-PROVIDER-001 | Architecture/security/cost | DeepSeek classifier provider | Resolved | A |
| DeepSeek pricing drift | Cost | Which rates govern actual | Defaulted | Official rates checked 2026-07-29, conservative miss+VAT upper bound |
| Local key presence | Actual only | Is ignored secret configured | Pending readiness | Value-free readiness; no secret read/output |

No implementation blocker remains. Key absence can stop only the actual stage and is recorded
without compromising completed offline work.

## 제안 설계

- 데이터 흐름: deterministic safety → masking → `SafeQuestion` → selected provider → exact parser
  → current catalog validation → existing grounding/fallback.
- 컴포넌트 경계: provider-neutral settings/factory and budget estimator; separate provider
  request adapters; shared parser.
- API/DB 변경: none.
- 보안/개인정보: no raw/body/value/secret/exception retention; fixed synthetic actual only.
- 실패/장애 처리: retry 0 and existing deterministic fail-closed fallback; no provider cascade.

## 단계별 구현

### Task 1 — Provider-neutral cost and usage boundary

Files:

- modify `apps/api/src/sejong_ai_api/llm/limits.py`
- add DeepSeek cost/usage module
- focused tests under `apps/api/tests/llm/`

TDD:

1. RED for provider-specific estimator injection and DeepSeek cache fields.
2. GREEN with existing Upstage behavior unchanged.
3. Prove negative/inconsistent usage and cap overflow fail closed.
4. Commit after focused review.

### Task 2 — Strict settings and provider selection

Files:

- add DeepSeek settings module
- modify provider-neutral runtime settings/factory
- modify `.env.example` without values
- focused settings tests

TDD:

1. RED for exact selector/default disabled/model/base/limits.
2. RED for invalid/conflicting profiles and secret-safe repr/errors.
3. GREEN without reading the key before non-secret profile validation.
4. Preserve explicit Upstage selection and generator configuration.
5. Commit after focused review.

### Task 3 — DeepSeek classifier transport

Files:

- add `deepseek_classifier.py`
- optionally extract value-free shared envelope helper
- add transport/parser/non-retention tests

TDD:

1. RED for exact URL/model/json_object/thinking disabled/temp0/max128.
2. RED for raw-PII outbound protection and request/body/value/secret/exception non-retention.
3. RED for timeout/empty/HTTP/JSON/key/type/enum/shape/catalog/usage failures.
4. GREEN using existing exact parser; network tests use controlled `httpx.MockTransport` only.
5. Commit after focused review.

### Task 4 — Local composition and deterministic routing

Files:

- modify `apps/api/src/sejong_ai_api/local.py`
- focused local/chat integration tests

TDD:

1. RED for `disabled`, `upstage`, `deepseek` exact selection.
2. RED for policy/privacy, obvious NON_CIVIC and obvious supported outbound 0.
3. RED for masked ambiguous outbound at most once and deterministic fallback on failure.
4. Prove separately enabled Upstage grounded generation remains intact.
5. Commit after focused review.

### Task 5 — One-shot DeepSeek actual runner

Files:

- add `scripts/run_deepseek_classifier_actual.py`
- add controlled runner tests
- add `docs/runbooks/DEEPSEEK-CLASSIFIER-ACTUAL.md`
- add new A-074 offline wrapper and tests

TDD:

1. readiness performs no network, lock, report or secret output;
2. actual lease is acquired before network and cannot be reused;
3. fixed input/hash yields 20/0/11/9;
4. four policy/privacy probes produce outbound 0;
5. report is aggregate-only and forbids questions/bodies/invalid values/secrets;
6. PASS requires all 9 HTTP/parse/accepted/oracle matches and cost cap;
7. any failure writes immutable FAIL and rerun remains 0;
8. A-074 offline wrapper invokes root `verify.ps1 -Offline` once, continuously preserves output,
   uses a long timeout and never invokes A-073/Upstage actual.
9. Commit after focused review.

### Task 6 — Area integration, versions and documentation

Files:

- authority and version documents, ADR index, task/changelog/RFP
- A-074 implementation note and INDEX
- A-074 offline and actual report paths

Actions:

1. run complete LLM/chat/local/runner area suite once;
2. Ruff format/check and Mypy;
3. update application `0.13.0`, tests `2.2.0`, docs `2.31.0`; prompt unchanged if bytes unchanged;
4. run docs, secret and diff checks;
5. commit truthful offline implementation evidence.

### Task 7 — New A-074 offline gate exactly once

1. Confirm the A-074 wrapper has no prior result/lock.
2. Start it with a 60-minute bound and continuous ignored stdout/stderr files.
3. Invoke exactly once; poll without losing process/output.
4. Record exit, bounded stage, output hash/byte count and invocation/rerun `1/0`.
5. Never rerun it, including on environment failure.

### Task 8 — Clean-source review and DeepSeek actual exactly once

1. independent code/security/privacy review with no Critical/Important findings;
2. clean committed source SHA and pinned fixture/report paths;
3. value-free readiness without network or lease;
4. if ready, execute actual once;
5. record PASS/FAIL aggregate and rerun 0;
6. do not inspect or retain provider body and do not attempt a correction rerun.

### Task 9 — Final evidence and Draft PR

1. synchronize D-123/D-124, ambiguity, source-of-truth, task, RFP, versions and implementation note;
2. final scoped independent review;
3. docs/secret/diff/status checks;
4. commit and push `codex/a-074-deepseek-classifier-provider`;
5. create Draft PR;
6. do not merge.

## 테스트 계획

- 단위: settings, cost, usage, request shape, exact parser, error paths.
- 계약: exact five keys/all strings/uppercase `NONE`, current catalog validation.
- 통합: chat service and local composition with controlled transports.
- E2E: fixed synthetic 20 runner; no public/remote browser E2E change.
- 보안/PII: outbound capture, caplog, exceptions, report and repository secret scan.
- 접근성: Web unchanged; existing regression only.
- 성능: concurrency 1 and bounded timeout/output; no 100-user target in this task.

Focused tests run during each task. One area suite runs after integration. One new A-074 root
offline gate runs at the final source. The A-073 wrapper and Upstage actual are never rerun.

## 버전 변경 계획

- application: `0.12.4-classifier-wire-diagnostics` →
  `0.13.0-selectable-classifier-provider`
- api/shared/web/database/data/product: unchanged
- prompt: `0.4.3-explicit-route-matrix`, unchanged unless bytes change
- tests: `2.1.7-classifier-wire-correction` → `2.2.0-deepseek-classifier-provider`
- docs: `2.30.7` → `2.31.0-deepseek-classifier-provider`

## 위험과 롤백

- 위험: wrong provider price, selector ambiguity, JSON-mode over-trust, mixed-provider accounting,
  raw/body retention, one-shot evidence loss.
- 조기 신호: setting rejection, unexpected outbound, parser bypass, cost mismatch, forbidden text
  in caplog/report, existing lock/report.
- 롤백: set selector disabled; revert DeepSeek-only adapter/composition; keep Upstage generator;
  no DB/data/API rollback.

## 인간이 승인해야 하는 사항

Already approved:

- DeepSeek classifier-only provider and exact model;
- local/private offline and exactly one actual;
- USD 0.20 cap;
- commit, push and Draft PR.

Still prohibited:

- public/remote/free-input;
- final answer-provider change;
- new dependency;
- automatic merge or actual rerun.

## 진행 기록

- 2026-07-29: A-073 scoped review fix closed as D-121 without rerunning its failed wrapper.
- 2026-07-29: A-074 code, docs and gate discovery audits completed; no A blocker.
- 2026-07-29: ADR-0028, written specification and executable plan drafted under the user's
  explicit approval.

## 결과와 회고

- 실제 결과: pending implementation.
- 계획과 달라진 점: update after execution.
- 다음 단계: Subagent-Driven Task 1.

## Plan self-review

- Every user security, provider, exact-wire, cost, one-shot and no-rerun constraint maps to a task.
- Shared parser/catalog authority is not duplicated.
- Upstage classifier/generator preservation is explicit.
- A-073 failed root evidence and Upstage actual are immutable.
- No public API, DB, data, Web or dependency change is planned.
- Actual readiness and actual lease are separate; actual failure cannot trigger a rerun.

