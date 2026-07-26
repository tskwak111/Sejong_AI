# IMP-20260726-012 — OFFICE API runtime parity 구현

- Date/Time (KST): 2026-07-26T16:23:57+09:00
- Final-review fix (KST): 2026-07-26T17:16:49+09:00
- Task ID: OFFICE-API-001
- Type: implementation
- Status: Done — Subagent-Driven implementation complete; human-review Draft PR pending
- Author/Agent: repository owner / Codex Task 6 worker / final-review fix worker
- Branch: `codex/OFFICE-API-001-design`
- Source baseline: private `origin/main` `8ebc66b65a67f106b05976112de345a8c849b631`
- Task 6 base/HEAD at start: `a0cdf8340315b31f14f10a212611a36f36db8744`
- Final-review fix base: `a306be525d03a73e7a86724f4ba073b22c20d45b`
- Related plan/ADR/RFP: [approved specification](../superpowers/specs/2026-07-26-office-api-runtime-parity-design.md), [approved execution plan](../superpowers/plans/2026-07-26-office-api-runtime-parity.md), ADR-0009, ADR-0011, ADR-0019, ADR-0020, SFR-004, D-078/D-079/D-080

## 1. 사용자 요청과 완료 기준

### 요청

승인된 OFFICE-API-001 실행계획의 Task 6을 수행한다. Tasks 1~5 구현을 변경하지 않고 active
API/readme/release/task/changelog/version 문서를 실제 동작과 일치시키고, exact version axes와
재현 가능한 closeout 증거를 기록한다. aggregate gate는 한 번만 실행하며 bootstrap failure이면
모든 constituent gate를 실행한다. local closeout commit까지만 만들고 push, Draft PR 생성,
merge, deploy, remote/public 인프라는 controller에게 남긴다.

Final whole-branch review 뒤에는 exact findings contract에 따라 runtime OpenAPI 503
`Retry-After` schema, D-080 실행 승인 audit trail, manifest-derived active API-version drift test와
세 stale current-state 문서를 한 bounded fix wave로 보정한다. 기존 aggregate와 actual-smoke
evidence는 판정을 바꾸지 않고 유지한다.

### Acceptance Criteria

- default/local `GET /api/v1/offices`의 match/valid-empty 200, invalid 422, closed/readiness/DB 503을
  active docs에 기록한다.
- runtime-generated OpenAPI의 office 503에 tracked contract와 같은 exact `Retry-After`
  description/integer/minimum schema를 선언한다.
- OFFICIAL-only server mapping, deterministic `public_id` order와 public
  `department_label` 부재를 기록한다.
- application `0.10.0-office-directory-runtime`, API `3.3.0-draft`, shared contracts `0.6.0`,
  tests `1.7.1-office-directory-review-fix`, docs `2.20.9`를 exact하게 맞춘다.
- D-080을 published plan approval과 Subagent-Driven implementation authority로 사용하고 D-079의
  historical written-specification approval을 다시 쓰지 않는다.
- manifest API version에서 expected 값을 파생해 active README/CODEX index/tracked OpenAPI/FastAPI
  metadata/generated banner의 정합을 검증한다.
- product/repository guidance/Web/DB schema/official·mock data/prompt 축을 유지한다.
- DB/data/Web/LLM/provider/dependency/lockfile/public/remote mutation 0을 diff로 증명한다.
- aggregate와 constituent gate 결과를 구분하고 actual endpoint smoke를 실행했는지 정직하게
  기록한다.
- 이 note와 INDEX 한 행, post-edit gate와 local closeout commit을 완료한다.

## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 사용자가 Q-API-OFFICES-001=A/D-078로 설계, D-079로 written specification, exact `1번 구현 시작`/D-080으로 published plan과 Subagent-Driven start를 승인했다. Tasks 1~6 worker가 구현했고 final-review fix worker가 bounded correction·검증·local commit을 담당한다. controller와 사람이 scoped re-review/push/Draft PR/merge를 소유한다. |
| When — 언제 | 2026-07-26 KST, Task 6 base `a0cdf83`에서 시작했고 final-review fix base `a306be5`에서 correction wave를 수행했다. |
| Where — 어디서 | linked worktree `.worktrees/office-api-001-design`, FastAPI/docs/contracts/version/implementation-note 영역. local/remote DB와 public infrastructure는 작업하지 않았다. |
| What — 무엇을 | existing office contract의 default/local FastAPI runtime parity와 runtime 503 header schema, 승인 audit trail, active version drift coverage, exact release axes, test evidence, rollback과 handoff를 닫는다. |
| Why — 왜 | tracked OpenAPI대로 호출할 때 404였던 drift를 제거하고, dependency 부재를 false empty로 위장하지 않는 OFFICIAL 기관 read surface를 제공하기 위해서다. |
| How — 어떻게 | Tasks 1~6 commits와 final findings를 검토하고, runtime-header RED→GREEN 뒤 active-version-consistency RED→GREEN, D-080/docs/version sync, full constituent/security/scope/diff gate, self-review와 단일 local fix commit 순서로 수행한다. |
| How much — 어느 정도 | review fix는 one Python route declaration, two test files와 active docs/version evidence만 변경한다. DB/data/Web/provider/dependency/lockfile/public/remote mutation과 외부 비용은 0이다. |

## 3. 시작 전 상태

- 관련 파일: `apps/api/src/sejong_ai_api/api/offices.py`, `office/{response,service}.py`,
  `contracts/offices.py`, `main.py`, `local.py`, affected tests, `contracts/openapi-v1.yaml`,
  `packages/shared-contracts`, active docs와 version manifest.
- 기존 동작 at `origin/main`: tracked OpenAPI와 DB function/repository에는 office lookup이 있지만
  default/local FastAPI router가 없어 contract call이 404였다.
- Task 6 base 동작: default/local route, strict list model, shared mapper, fail-closed service/readiness,
  local injection, tracked/generated contract가 구현·task-scoped review clean이었다.
- 실제 predecessor commits:
  - `4d36759` — `refactor(api): share official office response mapping`
  - `0068a1a` — `feat(api): add fail-closed office directory service`
  - `5ffd227` — `feat(api): expose official office directory route`
  - `5706c57` — `feat(api): compose local office directory`
  - `a0cdf83` — `feat(contract): publish office directory runtime schema`
- planning provenance: `c7c34f3` written specification, `d353f8e` execution plan.
- Git 상태: clean named branch `codex/OFFICE-API-001-design`; linked worktree와 supplied Task 6 base가
  모두 `a0cdf8340315b31f14f10a212611a36f36db8744`였다.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| A-051 | Resolved human decision | endpoint를 제거할지 runtime에 구현하고 어떤 plan mode로 시작할지 | Q-API-OFFICES-001=A/D-078 존치·구현; `1번 구현 시작`/D-080 plan 승인·Subagent-Driven | API runtime/contract minor |
| T6-ENV-001 | Environment | actual local endpoint smoke에 필요한 ignored environment가 현재 worktree/process에 있는지 | file/value를 읽지 않고 이름·존재만 확인; 둘 다 없어 Pending | actual Docker/Supabase smoke만 Pending |
| T6-GATE-001 | Environment | aggregate verifier가 repo-local/PATH uv를 찾을 수 있는지 | 한 번 실행하고 failure를 그대로 기록; 설치나 rerun 없이 pinned uv로 constituents 실행 | aggregate FAIL과 constituent PASS를 분리 |
| T6-PUBLISH-001 | Explicit ownership | 실행계획 Step 7의 push/Draft PR과 controller 지시의 경계 | 더 구체적인 controller 지시를 따라 local commit만 생성 | controller가 final review/push/PR 수행 |

계약·architecture·data·security·external integration을 바꾸는 새 blocker는 발견되지 않았다.

## 5. 설계 결정과 대안

### 선택

- strict `OfficeListResponse`, shared server mapper, typed directory service/readiness guard,
  always-registered router와 local-only injection을 그대로 closeout한다.
- 정상 no-match와 dependency failure를 `200 items=[]` 대 `503 SERVICE_UNAVAILABLE`로 구분한다.
- actual smoke prerequisite가 없으므로 secret이나 다른 checkout의 `.env`를 가져오지 않고 Pending으로
  기록한다.
- aggregate failure를 constituent PASS로 바꾸어 표현하지 않는다.

### 이유

기존 OFFICIAL-only DB capability와 typed repository를 재사용해 계약 drift를 가장 작게 닫으면서,
default import safety와 local actual composition을 분리한다. 정상 empty와 장애를 구분하고 source
metadata를 서버 소유로 유지해 시민에게 fabricated 기관 정보를 반환하지 않는다.

### 고려했지만 선택하지 않은 대안

- OpenAPI endpoint 제거: 승인된 SFR-004 surface와 generated consumer를 후퇴시켜 기각했다.
- OpenAPI 선언만 유지: runtime 404 drift를 남겨 기각했다.
- closed/readiness/DB failure를 200 empty로 변환: 정상 no-match로 위장하므로 기각했다.
- chat mapper 복제 또는 router에서 concrete DB 사용: source drift와 composition 결합을 만들어
  기각했다.
- 다른 checkout의 `.env`를 읽거나 복사하고 Docker/DB를 시작해 actual을 강제: 명시적 secret,
  local-data, no-mutation 경계를 위반하므로 실행하지 않았다.
- aggregate rerun, uv/pnpm install 또는 build approval: one-attempt와 dependency 정책에 따라
  실행하지 않았다.

## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| `apps/api/src/sejong_ai_api/contracts/offices.py`, `office/response.py`, `chat/response.py` | strict list와 chat/directory shared server mapping | public metadata drift와 internal field 노출 방지 |
| `apps/api/src/sejong_ai_api/office/service.py`, `api/offices.py` | typed service, closed default, readiness/DB fail-closed route | valid empty와 dependency failure 분리 |
| `apps/api/src/sejong_ai_api/main.py`, `local.py` | default route always registered; local existing repository/probe injection | OpenAPI discovery와 local data path 분리 |
| office/route/local/chat tests | match, empty, invalid, closed/readiness/DB error와 mapper regression | 모든 승인 public/safety case 자동 검증 |
| `contracts/openapi-v1.yaml`, `packages/shared-contracts` | API 3.3 strict response/errors와 generated TS 0.6 | tracked/runtime/generated parity |
| `apps/api/src/sejong_ai_api/api/offices.py`, `apps/api/tests/test_offices_route.py` | runtime-generated 503 `Retry-After` exact header schema와 RED→GREEN regression | tracked/runtime OpenAPI parity |
| `scripts/tests/test_repository_scaffold.py`, `README.md`, `CODEX_FILE_INDEX.md` | manifest-derived active API-version consistency와 stale current-state marker 교정 | independent source of truth와 active artifact drift 방지 |
| `apps/api/README.md`, `docs/05_API_AND_CONTRACTS.md` | request/response, 200/422/503, default/local, OFFICIAL-only, no internal field, smoke/rollback | 운영자와 consumer 재현 |
| `docs/decisions/DECISION_LOG.md`, ambiguity/spec/TASKS | D-080 plan authority와 implementation-complete/Draft-PR-pending status | 인간 승인 audit trail |
| `docs/12_VERSIONING_AND_RELEASES.md`, `versions/manifest.json` | exact review-fix axes와 unchanged axes/evidence | release 식별 |
| `TASKS.md`, `CHANGELOG.md` | 완료 상태, behavior, aggregate/smoke gate truth, non-goals | active backlog/release sync |
| 이 note와 `INDEX.md` | command/security/data/rollback/handoff 증거와 exact one row | AGENTS 구현 노트 의무 |

### 데이터 흐름/상태 변화

```text
required region + supported intent
→ FastAPI typed validation
→ shared readiness gate
→ existing PsycopgSejongRepository.list_offices
→ existing app_api.list_offices
→ OFFICIAL-only / public_id ordered OfficeRecord
→ server-owned public Office mapping
→ strict OfficeListResponse
```

질문 text, masker, chat context, event/failed-question/candidate writer, idempotency persistence와 LLM/provider
경로를 통과하지 않는다. Task 6 자체는 runtime code, DB row, file data와 external state를 변경하지
않는다.

### 오류·빈 상태·롤백

- missing/unsupported query: repository call 0, value-free 422 `VALIDATION_ERROR`.
- valid no-match: exact HTTP 200 `{"items":[]}`.
- default closed dependency, readiness false, typed DB unavailable: value-free 503
  `SERVICE_UNAVAILABLE`, `Retry-After: 30`.
- programming/model validation error: empty/503으로 숨기지 않고 test/500으로 보인다.
- rollback은 mapper/model/service/router/local composition, tracked OpenAPI, generated TypeScript와
  tests/docs/version을 함께 revert한다. migration·seed·data가 없으므로 data rollback은 없다.

## 7. 버전 전후

### 생성 시 매니페스트

- product_spec: 2.5.0
- repo_guidance: 1.7.8
- application: 0.10.0-office-directory-runtime
- web: 0.6.0-answer-mode
- api: 3.3.0-draft
- shared_contracts: 0.6.0
- database_schema: 0.4.0-local
- official_data: 0.1.0-initial.2
- mock_data: 0.0.0-not-populated
- prompt_set: 0.2.0-grounded-live-chat
- test_suite: 1.7.1-office-directory-review-fix
- documentation: 2.20.9

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Product specification | 2.5.0 | unchanged | 범위/제품 결정 변경 0 |
| Repository guidance | 1.7.8 | unchanged | repository policy 변경 0 |
| Application | 0.9.1-grounded-local-chat-evidence | 0.10.0-office-directory-runtime | default/local office runtime |
| Web | 0.6.0-answer-mode | unchanged | Web consumer/behavior 변경 0 |
| API | 3.2.0-draft | 3.3.0-draft | additive office response/error 명세 |
| Shared contracts | 0.5.0 | 0.6.0 | generated consumer minor |
| DB schema | 0.4.0-local | unchanged | migration/function 변경 0 |
| Official data | 0.1.0-initial.2 | unchanged | release/seed/row 변경 0 |
| Mock data | 0.0.0-not-populated | unchanged | mock 생성/혼합 0 |
| Prompt set | 0.2.0-grounded-live-chat | unchanged | LLM/provider/prompt 변경 0 |
| Test suite | 1.6.1-grounded-actual | 1.7.1-office-directory-review-fix | office contract/service/route/local regression과 final runtime/version drift coverage |
| Documentation | 2.20.7 | 2.20.9 | implementation closeout와 D-080/final-review fix |

Review-fix 자체의 exact before/after는 test suite
`1.7.0-office-directory→1.7.1-office-directory-review-fix`, documentation
`2.20.8→2.20.9`다. application, API, shared contracts, Web, DB schema, official/mock data,
prompt, product와 repository guidance는 변경하지 않았다.

## 8. 명령과 테스트 증거

### Task 6 historical closeout evidence

| 명령/검증 | 결과 | 시간/개수 | 증거 경로 |
|---|---|---|---|
| `git diff --check`; `git diff --stat origin/main...HEAD`; `git diff --name-status origin/main...HEAD` | PASS; whitespace 0, only approved Python/contract/test/docs/version history | pre-closeout 1회 | terminal evidence |
| `git diff --exit-code origin/main...HEAD -- database supabase data apps/web pnpm-lock.yaml apps/api/uv.lock` | PASS; forbidden diff 0 | pre-closeout 1회 | terminal evidence |
| `rg -n "department_label\|DATABASE_URL\|LLM_API_KEY\|UPSTAGE_API_KEY" apps/api/src/sejong_ai_api/api/offices.py apps/api/src/sejong_ai_api/office apps/api/src/sejong_ai_api/contracts/offices.py` | PASS by no-match exit 1; prohibited identifier 0 | pre-closeout 1회 | terminal evidence |
| process env-name/local file existence only | `DATABASE_URL=false`, `CONTEXT_TOKEN_SECRET=false`, worktree `apps/api/.env=false`; values/file content not read | 1회 | bounded-smoke prerequisite check |
| `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/verify.ps1` | **NOT PASS** — PowerShell/Node/pnpm preflight PASS, then `[FAIL] step=PREFLIGHT-UV reason=exception code=2`; invocation wrapper returned 124 after 1.846s and no later aggregate stage ran | aggregate exactly 1 attempt | terminal evidence |
| `uv run --directory apps/api --frozen ruff format --check src tests` | PASS — 105 files already formatted | constituent 1회 | pinned uv 0.11.28 |
| `uv run --directory apps/api --frozen ruff check src tests` | PASS — all checks passed | constituent 1회 | terminal evidence |
| `uv run --directory apps/api --frozen mypy src tests` | PASS — no issues in 105 source files | constituent 1회 | terminal evidence |
| `uv run --directory apps/api --frozen pytest -q -p no:cacheprovider` | PASS — 2,043 passed, 8 local-DB-only skipped, 5 subtests passed, 1 pre-existing Starlette warning | 13.74s | terminal evidence |
| `$env:PNPM_CONFIG_VERIFY_DEPS_BEFORE_RUN='false'`<br>`corepack pnpm --filter @sejong-ai/shared-contracts generate:check` | PASS — fresh render drift 0 | constituent 1회 | terminal evidence |
| `$env:PNPM_CONFIG_VERIFY_DEPS_BEFORE_RUN='false'`<br>`corepack pnpm --filter @sejong-ai/shared-contracts test` | PASS — 90/90 | 1.334s | terminal evidence |
| `python -B scripts/check_repository_docs.py` | PASS — repository documentation check passed | pre-edit constituent 1회 | terminal evidence |
| `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/check_secret_patterns.ps1 -RepositoryRoot .` | PASS — finding 0 | pre-edit constituent 1회 | terminal evidence |
| `git diff --check` | PASS | pre-edit constituent 1회 | terminal evidence |
| `python scripts/new_implementation_note.py --title "OFFICE API runtime parity 구현" --task-id "OFFICE-API-001" --type "implementation"` | PASS — note 012 생성, INDEX exact one append | 1회 | 이 note와 `INDEX.md` |
| `python -B -m json.tool versions/manifest.json > $null` | PASS — valid JSON | post-edit 1회 | `versions/manifest.json` |
| `python -B scripts/check_repository_docs.py` | PASS — repository documentation check passed | post-edit 1회 | terminal evidence |
| `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/check_secret_patterns.ps1 -RepositoryRoot .` | PASS — finding 0 | post-edit 1회 | terminal evidence |
| `$env:PNPM_CONFIG_VERIFY_DEPS_BEFORE_RUN='false'`<br>`corepack pnpm --filter @sejong-ai/shared-contracts generate:check` | PASS — generated TypeScript unchanged | post-edit 1회 | terminal evidence |
| `git diff --check`; `git status --short` | PASS — whitespace 0; exact planned closeout files 8 | post-edit 1회 | terminal evidence |

### Final-review fix evidence

| 명령/검증 | 결과 | 시간/개수 | 증거 경로 |
|---|---|---|---|
| repo uv `pytest tests/test_offices_route.py::test_generated_openapi_declares_the_office_retry_after_header -q -p no:cacheprovider` before production edit | expected **RED** — `KeyError: 'headers'`; 1 failed, pre-existing Starlette warning 1 | 0.75s | terminal evidence |
| same focused runtime-header test after minimal route declaration | **GREEN** — 1 passed, pre-existing warning 1 | 0.57s | terminal evidence |
| repo uv focused `ruff format --check`, `ruff check`, `mypy`, `pytest tests/test_offices_route.py` | PASS — 2 files formatted, Ruff clean, MyPy 2 files clean, route 11 passed with pre-existing warning 1 | 1 focused wave | terminal evidence |
| `python -B -m unittest ...test_should_align_active_api_version_artifacts_with_manifest -v` before README/index edits | expected **RED** — manifest `3.3.0-draft`; only README current markers 2 and CODEX contract row 1 were `3.2.0-draft` | 0.008s | terminal evidence |
| same manifest-derived active-version test after three bounded doc edits | **GREEN** — 1 test OK | 0.007s | terminal evidence |
| repo uv `run --project apps/api --frozen python -B -m unittest scripts.tests.test_repository_scaffold -v` | PASS — pinned Python 3.12.13, 7/7 | 0.007s | terminal evidence |
| repo uv full API `ruff format --check src tests`; `ruff check src tests`; `mypy src tests`; `pytest -q -p no:cacheprovider` | PASS — 105 files formatted, Ruff/MyPy clean, 2,044 passed, DB-only 8 skipped, 5 subtests passed, pre-existing warning 1 | pytest 17.75s | pinned Python 3.12.13 / uv 0.11.28 |
| direct system `python -B -m unittest discover -s scripts/tests -p test_*.py -q` diagnostic attempt | **NOT PASS** — system Python was 3.14.0 and linked worktree lacked gitignored patched runtime; 431 ran, 3 failed, 2 skipped | 359.600s | superseded environment diagnosis, not PASS evidence |
| shared local `.tools` runtime availability check | PASS — existing main-checkout Supabase binary present and SHA-256 equals tracked runtime manifest; gitignored worktree junction created, install/build/copy 0 | 1 check | no tracked diff |
| repo uv `run --project apps/api --frozen python -B -m unittest discover -s scripts/tests -p test_*.py -q` | PASS — pinned Python 3.12.13, 431 tests OK, 2 skipped; printed `[FAIL] step=...` lines are expected negative-fixture diagnostics | 394.480s | terminal verdict exit 0 / `OK (skipped=2)` |
| `$env:PNPM_CONFIG_VERIFY_DEPS_BEFORE_RUN='false'`; shared `generate:check`; shared `test` | PASS — fresh generated drift 0; shared contracts 90/90 | 4.7s | install/build approval 0 |
| repo uv manifest JSON parse; repository docs checker; secret-pattern scanner | PASS — pinned Python 3.12.13, valid JSON, docs check passed, scanner exit 0/finding 0 | one final wave | terminal evidence |
| forbidden diff from fix base across DB/Supabase/data/Web/LLM provider/GitHub/dependency/lock/env paths; `git diff --check` | PASS — forbidden diff 0, whitespace error 0, exact 14 bounded tracked files | one final wave | fix base `a306be5` |

Aggregate PASS를 주장하지 않는다. bootstrap이 실패한 exact step과 모든 substitute constituent
evidence를 분리한다. pnpm fallback은 dependency auto-verification을 false로 설정했고 install/build
approval을 실행하지 않았다. fallback 후 workspace/lock/dependency drift는 0이었다.
각 `uv` constituent command 앞에는 process-local
`$env:PATH = 'C:\Users\ss020\바탕 화면\sejong_ai\sejong_ai_codex_ready_project\.tools\uv;' + $env:PATH`
를 설정해 pinned uv 0.11.28을 사용했다. 실행 파일만 기존 main checkout에서 사용했으며 worktree
밖의 source, environment 또는 secret을 읽거나 복사하지 않았다.

### 미실행 검증과 이유

- Bounded actual Docker/Supabase endpoint smoke:
  `Pending — local prerequisite unavailable`. worktree에 local `.env`가 없고 current process에
  required setting 이름도 없었다. 다른 checkout의 `.env`를 읽거나 복사하지 않았으며 Docker,
  Supabase, migration/reset/seed, DB query와 LLM을 시작하지 않았다. injected local integration이
  match 200, valid-empty 200, false readiness 503을 대신 검증한다.
- Web test/build, DB pgTAP/integration, data validation: 해당 file/behavior를 변경하지 않았고
  forbidden-path diff 0이다.
- remote/public/hosted checks: 별도 승인 대상이며 이번 local/private closeout 범위 밖이다.

## 9. 보안·개인정보·접근성·성능 영향

- Privacy: question/raw/masked text, PII, IP, device ID, context/provider payload를 처리·저장·출력하지
  않았다. environment는 이름 존재 boolean만 확인했고 값은 보지 않았다.
- Security: `.env`, DSN, key/token, record/query result를 읽거나 출력하지 않았다. safe 422/503
  body와 log는 query/internal cause를 echo하지 않는다. secret scanner finding 0이다.
- Accessibility: Web/UI 변경 0. 기존 frontend 기관 카드 consumer behavior는 변경하지 않았다.
- Performance/cost: 새 pool/background task/provider call/dependency가 없고 외부 비용 0원이다.
  existing indexed DB read path를 재사용한다. 실제 DB latency/capacity는 이번 Pending smoke로
  검증하지 않았다.

## 10. 데이터와 출처 영향

- 공식 데이터: immutable `0.1.0-initial.2` artifact, seed와 actual row 변경 0. runtime은 기존
  DB function의 `data_origin=OFFICIAL` filter만 소비한다.
- mock/AI 생성: 생성·수정·혼합 0. LLM/provider call 0.
- schema/lineage: DB schema `0.4.0-local`, migration/rollback/function/seed 변경 0.
- verified date: endpoint는 existing record의 date를 서버가 전달한다. Task 6은 실제 기관 record를
  조회하거나 확인일을 갱신하지 않았다.

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- exact `1번 구현 시작`은 D-080의 published execution-plan approval과 Subagent-Driven
  implementation authority다. D-079는 historical written-specification approval로 보존했다.
- aggregate verifier는 PASS하지 않았다. worktree에서 uv를 발견하지 못한 `PREFLIGHT-UV code=2`
  bootstrap failure이고, plan-listed constituent gates는 모두 PASS했다.
- actual Docker/Supabase endpoint smoke는 Pending이다. 실제 local endpoint evidence가 필요하면
  owner가 준비한 non-secret-safe local environment에서 별도 실행해야 하며 reset/seed/data mutation은
  별도 승인 대상이다.
- API/shared/application은 구현 closeout 값을 유지하고 review fix에서 test suite만
  `1.7.1-office-directory-review-fix`, documentation만 `2.20.9`로 올렸다. DB/data/Web/prompt와
  product/repository guidance는 유지된다.
- push, Draft PR 생성, ready/merge, deploy는 수행하지 않는다. controller가 whole-branch review 뒤
  owner branch를 push하고 human-review Draft PR을 만들어야 한다.
- public/remote deployment, 실제 기관 운영, remote DB/admin exposure는 승인되지 않았다.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- `build_public_office` overload와 tuple conversion, dependency override, fake/repository call counter는
  public wire와 안전 경계 안의 내부 구현이다.
- local composition은 chat과 같은 repository/pool/probe를 재사용하며 별도 lifecycle을 추가하지 않는다.
- active-version consistency test는 manifest의 API 값을 expected로 한 번만 읽고 README current
  markers, CODEX contract row, tracked YAML metadata, FastAPI AST metadata와 generated banner의
  실제 값을 독립적으로 추출한다. 별도 hardcoded expected version을 만들지 않는다.
- final-review fix commit은 note 자체에 self-referential SHA를 넣지 않고 final fix report와
  controller handoff가 SHA/subject를 소유한다. predecessor와 fix base SHA는 이 note에 고정했다.

## 13. 인수인계·재현·롤백

### 재현

1. private source baseline `8ebc66b`, branch, Task 6 base `a0cdf83`과 final-review fix base
   `a306be5`를 확인한다.
2. final-review findings, approved specification/plan과 이 note를 순서대로 읽고 D-080 authority를
   확인한다.
3. 두 RED→GREEN focused test와 final-review constituent/full scope/security/diff commands를 실행한다.
4. aggregate는 이미 exactly once 실패했으므로 재실행해 과거 결과를 덮지 않는다. listed constituent
   API/shared/docs/secret/diff gates를 같은 pinned tool versions로 재현한다.
5. local prerequisites가 owner-approved 상태로 이미 준비된 경우에만 records/DSN을 출력하지 않는
   bounded status/count smoke를 별도 실행한다.
6. manifest, TASKS, CHANGELOG, note/INDEX와 final commit/report를 대조한다.

### 롤백

- closeout docs/version commit을 revert하고 product commits
  `a0cdf83`, `5706c57`, `5ffd227`, `0068a1a`, `4d36759`를 역순으로 함께 revert한다.
- tracked OpenAPI와 generated TypeScript, runtime router/service/model/shared mapper를 한 rollback
  boundary로 유지한다.
- DB/data/dependency rollback은 필요 없으며 migration/reset/seed/delete를 실행하지 않는다.

### 다음 개발자 시작점

controller가 final fix report와 scoped re-review를 확인하고 branch를 push한 뒤 Draft PR을 생성한다.
Draft PR에는 aggregate failure/constituent PASS와 exact Pending smoke line을 유지하고 사람이
검토·merge한다. mark-ready/merge/delete/deploy는 별도 인간 결정 전 수행하지 않는다.

## 14. 남은 위험·미해결 질문·다음 단계

- actual Docker/Supabase endpoint status/count smoke Pending.
- aggregate verifier의 uv discovery bootstrap은 unresolved environment issue이며 aggregate PASS 증거가
  없다. constituent evidence로만 closeout한다.
- broad API baseline의 pre-existing Starlette deprecation warning 1건은 failure가 아니지만 dependency
  migration 시 별도 정리가 필요하다.
- hosted backend CI와 public/remote readiness는 별도 backlog/승인 대상이다.
- 다음 한 단계: controller scoped final-fix re-review → push → human-review Draft PR.

## 15. 자체 리뷰

- Independent whole-branch review: Critical 0, Important 2, bounded Minor 1. 이 fix wave에서
  runtime header parity, D-080 approval audit와 manifest-derived active version drift를 모두
  보정했다.
- [x] 요청 충족
- [x] 테스트/검증
- [x] source-of-truth/계약/버전 동기화
- [x] 개인정보 원문 노출 없음
- [x] 구현 노트 INDEX 갱신
