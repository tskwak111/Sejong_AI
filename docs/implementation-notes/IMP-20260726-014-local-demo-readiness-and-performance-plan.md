# IMP-20260726-014 — local demo readiness and performance plan

- Date/Time (KST): 2026-07-26T19:18:26+09:00
- Task ID: DEMO-001-PERF-001
- Type: implementation-verification-plan
- Status: Done for AI scope — automated local rehearsal PASS; manual accessibility Pending; PERF
  Phase A Ready / Phase B A-052 gate
- Author/Agent: 사용자 승인 / Codex 구현·검증
- Branch: codex/FINAL-DEMO-PERF-PLAN-001
- Source baseline: `bcaf39cdd8d7e903fa35705cda6f7d6c7fb433d7`
- Planning commit: `94cbcce5b2b5b48ee13477944e0b0acf6d00f614`
- Related plan/ADR/RFP: D-077, D-082, A-052, ADR-0020, ADR-0023, DEMO-001,
  PERF-001, PER-001, PER-002,
  `docs/superpowers/specs/2026-07-26-local-demo-readiness-and-performance-smoke-design.md`,
  `docs/superpowers/plans/2026-07-26-local-demo-readiness-and-performance-smoke.md`

## 1. 사용자 요청과 완료 기준

### 요청

- PR #16 merge를 latest source authority로 확인한다.
- `CONTEXT_TOKEN_SECRET`를 안전하게 생성해 ignored local 환경에 반영한다.
- 외부 provider를 호출하지 않는 최종 local demo rehearsal을 실행한다.
- 100-user performance smoke의 실행 경계와 계획을 진행한다.

### Acceptance Criteria

- secret 값을 stdout, Git, 문서, PR 또는 로그에 노출하지 않는다.
- primary checkout의 정확한 ignored `apps/api/.env`만 갱신한다.
- latest main의 `/health`, `/ready`, 정상 chat/source, PERSONAL_LOOKUP, office, admin read와 Web
  responsive flow를 provider 0으로 검증한다.
- reset, seed, migration, purge, delete, public/remote/provider 작업을 하지 않는다.
- performance smoke는 100 VU·60초, 오류율 <1%, 평균 ≤3초와 aggregate-only 결과를 유지한다.
- chat metadata write 대상이 정해지기 전 Phase B를 실행하지 않는다.
- 문서, version manifest, handoff, test report와 구현 노트를 동기화한다.
## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 사용자가 PR #16 merge·secret 반영·rehearsal을 승인했고 Codex가 구현·검증했다. 최종 수동 접근성 판단과 Phase B DB 선택은 사용자/PM 책임이다. |
| When — 언제 | 2026-07-26 KST, PR #16 merge 확인 직후 |
| Where — 어디서 | private Sejong_AI의 격리 worktree, primary ignored API `.env`, loopback Docker/Supabase, API test process, fixture-isolated Web browser |
| What — 무엇을 | safe secret provisioner, 최종 자동 demo evidence, 2단계 performance plan, source-of-truth·version·handoff |
| Why — 왜 | 빈/임시 context secret을 제거하고 평가 직전 local MVP의 실제 동작을 재확인하며 DB 오염 없는 부하 경계를 정하기 위해 |
| How — 어떻게 | 고정 target+CSPRNG+atomic env update TDD, provider-off actual aggregate probe, Web lint/typecheck/unit/build/E2E, Phase A/B 분리 |
| How much — 어느 정도 | provisioner 테스트 7개, API 집중 테스트 64개, Web unit 56개와 browser 21개; provider 0, DB reset/seed/migration/delete 0, 새 dependency 0 |

## 3. 시작 전 상태

- 관련 파일: `scripts/provision_local_context_secret.py`, LLM-003 runbook, TASKS,
  PROJECT_PLAN/RFP_MATRIX, ambiguity/decision log, current handoff, versions, test report.
- 기존 동작: PR #16까지 office runtime parity와 bounded post-merge smoke는 완료됐지만
  primary `.env`의 context secret은 운영자가 안전하게 채워야 했고 final demo 자동 증거와
  PERF 실행 분리가 없었다.
- 발견한 충돌/부채: current DB에는 D-077의 비-KPI metadata가 있으므로 chat load가 만드는
  새 interaction/idempotency row를 평가 KPI로 오해하면 안 된다. worktree에는 의도적으로
  ignored `.tools`가 없어 patched Supabase verifier를 그 경로에서 직접 실행할 수 없다.
- Git 상태: latest `origin/main=bcaf39c`에서 새 worktree/branch를 만들었다. 사용자 primary
  branch와 기존 변경은 수정하지 않았다.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| D-082 | 확정 | safe secret 반영, final local demo, performance plan | 사용자 승인 범위대로 실행 | local ignored env, demo evidence, PERF plan |
| A-052 | B/High | Phase B chat load의 DB write 대상 | 추천 disposable clean DB; 무응답이면 Phase B HOLD | DB event/idempotency row, KPI 해석, rollback |

## 5. 설계 결정과 대안

### 선택

- secret provisioner는 인자를 받지 않고 Git common dir에서 primary checkout을 찾아 정확한
  ignored `apps/api/.env`만 갱신한다.
- final demo는 provider modes를 process에서 강제로 끄고 latest main의 actual API/DB read와
  fixture-isolated browser 흐름을 함께 검증한다.
- PERF Phase A는 `/health`와 official office read만 사용해 DB write 0으로 harness를 검증한다.
  Phase B cached/fixed chat은 A-052 해결 뒤 별도로 실행한다.

### 이유

- 값 또는 DSN 노출 없이 반복 가능한 local 설정을 제공한다.
- provider 품질/비용 변수를 배제하고 template/source/security 경계를 확인한다.
- current non-KPI DB를 무단 reset하거나 새 metadata로 더 오염시키지 않는다.

### 고려했지만 선택하지 않은 대안

- shell one-liner로 secret을 생성·기록: 명령 기록/escaping/대상 실수 위험과 실행 정책
  차단 때문에 거부했다.
- worktree `.env` 또는 `.tools` 복사: source-of-truth와 secret/tool provenance를 분기시키므로
  거부했다.
- 즉시 chat 100-user load: DB write 대상과 rollback이 미결정이므로 거부했다.
- 새 k6/Locust dependency: 기존 production dependency 금지와 불필요한 공급망 변경 때문에
  표준 locked Python/httpx harness 계획을 선택했다.
## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| `scripts/provision_local_context_secret.py` | common Git dir 기반 fixed target, CSPRNG, ignore/symlink check, atomic replacement, value-free status | 안전한 반복 실행 |
| `scripts/tests/test_provision_local_context_secret.py` | target·보존·invalid·ignore·출력 7개 TDD | regression 차단 |
| `scripts/README.md`, LLM-003 runbook | 명령과 안전 경계 | 운영 재현 |
| DEMO/PERF spec·plan | 자동 demo와 PERF Phase A/B 절차·threshold·중단 조건 | 실행 권위 |
| TASKS/PROJECT_PLAN/RFP/ambiguity/decision | D-082와 A-052, readiness 상태 | source-of-truth 정합 |
| final test report/current handoff | aggregate evidence와 수동 Pending | 평가·인수인계 |
| CHANGELOG/version files/INDEX | 독립 version 축과 변경 계보 | release hygiene |

### 데이터 흐름/상태 변화

- provisioner: OS CSPRNG → memory validation → exact ignored env key atomic replacement. 값 출력 0.
- API rehearsal: PII-free fixture ID → mask/classify/ACTIVE search/grounding/template → server-owned
  source. 정상 supported request의 기존 metadata-only event path 외 seed/official row 변화 0.
- PERSONAL_LOOKUP: exact reason/candidate false 확인. 이번 run은 기존 governed 0/0 DB forensic을
  대체하지 않는다.
- PERF plan: Phase A read-only; Phase B 미실행.

### 오류·빈 상태·롤백

- Windows PowerShell static RNG 호출은 런타임 호환성이 없었고 direct secret-write command는
  실행 정책으로 차단됐다. 추적 가능한 fixed-target Python provisioner로 해결했다.
- worktree의 patched Supabase verify는 `.tools` missing code 2로 정직하게 중단했다. 동일
  tracked verifier를 primary checkout에서 실행해 PASS했고 tool을 복사하지 않았다.
- valid empty office query는 `200/items=0`으로 PASS했다.
- provisioner는 target/ignore/generation/write 실패 시 bounded FAIL만 출력하고 nonzero 종료한다.
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
- documentation: 2.20.10

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Product spec | 2.5.0 | 2.5.0 | 제품 동작 불변 |
| Repository guidance | 1.7.8 | 1.7.9 | safe local provision/runbook |
| Application | 0.10.0-office-directory-runtime | 동일 | 제품 코드 불변 |
| Web | 0.6.0-answer-mode | 동일 | 검증만 수행 |
| API | 3.3.0-draft | 동일 | 공개 계약/route 불변 |
| Shared contracts | 0.6.0 | 동일 | 계약 불변 |
| DB schema | 0.4.0-local | 동일 | migration 없음 |
| Official data | 0.1.0-initial.2 | 동일 | seed/row 변경 없음 |
| Mock data | 0.0.0-not-populated | 동일 | mock 없음 |
| Prompt set | 0.2.0-grounded-live-chat | 동일 | provider/prompt 불변 |
| Test suite | 1.7.1-office-directory-review-fix | 1.8.0-local-demo-readiness | 새 provisioner test와 final rehearsal |
| Docs | 2.20.10 | 2.21.0 | D-082, report, PERF plan, handoff |

## 8. 명령과 테스트 증거

| 명령/검증 | 결과 | 시간/개수 | 증거 경로 |
|---|---|---|---|
| provisioner focused RED | 예상된 FAIL | 7 fail — 파일 미존재 | TDD 명령 기록 |
| provisioner focused GREEN | PASS | 7 passed / 1.27s | provisioner test |
| actual provisioner | PASS | value output 0 | bounded stdout |
| local settings/minimum validation | PASS | YES/YES, value output 0 | final report |
| patched Supabase verify | PASS from primary | worktree missing code 2도 보존 | final report |
| API local/chat/office/LLM architecture | PASS | 64 passed / 2.20s, 기존 warning 1 | final report |
| provider-disabled actual API/DB probe | PASS | health/ready/chat/PERSONAL/office/admin, provider 0 | final report |
| Web lint/typecheck/unit/build | PASS | unit 12 files/56 | final report |
| Web fixture-isolated E2E | PASS | 21/21 / 35s, 390/430/desktop | final report |
| aggregate `verify.ps1 -Offline` | NOT PASS | `PREFLIGHT-UV` missing in isolated worktree | final report |
| final provisioner format/lint/test | PASS | Ruff PASS; 7/7 / 1.06s | final report |
| API full format/lint/type/test | PASS | 2,044 pass; 8 DB-only skip; 5 subtests; existing warning 1 | final report |
| root worktree suite | environment-limited | 429 pass, 2 skip, 2 `.tools/supabase.exe` missing failures | final report |
| exact two root checks, identical primary source | PASS | SHA-256 match YES; 2/2 / 1.793s | final report |
| shared contract/docs/secret/package/diff | PASS | contracts 90/90 | final report |

### 미실행 검증과 이유

- manual 200% zoom, visual contrast/large text, keyboard-only five-question demo와 발표 timing은
  사람의 실제 화면·판단이 필요하다.
- PERF Phase A는 이 요청에서 설계/계획 Ready까지이며 harness 구현·실행은 다음 수직 흐름이다.
- PERF Phase B는 A-052 인간 결정 전 미실행이다.
- provider actual, public/remote DB/deploy, reset/seed/purge/delete는 승인 범위 밖이다.
- aggregate root runner는 격리 worktree에 ignored `.tools/uv`가 없어 PASS로 주장하지 않는다.
  동일한 이유의 root 2개 검사만 source hash 일치 확인 뒤 primary tool checkout에서 PASS했다.
## 9. 보안·개인정보·접근성·성능 영향

- Privacy: 질문/답변/PII/secret/DSN/provider payload/공식 record 값을 보고서에 기록하지
  않았다. PERSONAL_LOOKUP 무후보 정책을 확인했고 원문 DB forensic은 기존 증거를 authority로
  유지한다.
- Security: fixed target, gitignore, symlink, 최소 길이, ASCII/newline/null, value-free output을
  테스트했다. provider와 public/remote 호출 0.
- Accessibility: 자동 390/430/desktop 21/21 PASS. visual/manual 항목은 Pending을 숨기지 않는다.
- Performance/cost: 이번 rehearsal의 provider 비용 0. PERF threshold는 error <1%, average
  ≤3초이고 p95는 측정만 한다. 실서비스 capacity 보증으로 해석하지 않는다.

## 10. 데이터와 출처 영향

- 공식 데이터: existing approved `0.1.0-initial.2`, ACTIVE 20/office 3/mapping 10을 읽기만
  했다. 승격·재시드 없음.
- mock/AI 생성: API probe는 PII-free canonical fixture를 사용했고 provider 생성 0. browser는
  fixture-isolated임을 명시한다.
- schema/lineage: `0.4.0-local` 불변, migration/rollback 없음.
- verified date: 2026-07-26 KST.

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- 새 context secret은 primary ignored local env에 반영됐으며 값은 어디에도 보고하지 않는다.
- 사람이 manual accessibility/demo checklist를 완료해야 평가 리허설이 완전히 닫힌다.
- PERF Phase A는 다음 수직 흐름에서 실행 가능하다.
- PERF Phase B는 A-052에서 DB write 대상을 선택해야 한다. 추천은 disposable clean DB이고
  답이 없으면 HOLD다.
- current DB event 통계는 D-077에 따라 평가 KPI가 아니다.
- Draft PR은 사람이 검토·merge한다. public/remote/provider actual은 승인되지 않았다.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- provisioner가 기존 database env updater의 atomic byte-preserving helper를 재사용한다.
- tests는 임시 Git repository에서 ignore/no-ignore를 재현하고 실제 비밀값 대신 sentinel만 쓴다.
- actual probe는 provider factory를 호출하면 즉시 실패하도록 주입했다.

## 13. 인수인계·재현·롤백

### 재현

- secret rotation:
  `uv run --project apps/api --frozen python scripts/provision_local_context_secret.py`
- tests:
  `uv run --project apps/api --frozen pytest scripts/tests/test_provision_local_context_secret.py -q -p no:cacheprovider`
- API/Web 기동과 final demo는 LLM-003 runbook과
  `docs/test-reports/FINAL-LOCAL-DEMO-REHEARSAL.md`를 따른다.
- 성능 작업은 published DEMO/PERF plan의 Phase A부터 시작한다.

### 롤백

- code/docs는 이 branch commit을 revert한다.
- local secret은 이전 값을 복원하지 말고 provisioner를 다시 실행해 새 값으로 rotate한다.
- application/API/DB/data rollback은 필요 없다.

### 다음 개발자 시작점

- latest merged main에서 새 branch/worktree를 만든다.
- manual demo evidence가 남았으면 먼저 기록한다.
- PERF Phase A harness를 TDD로 구현·실행하고 aggregate-only report를 작성한다.
- Phase B는 A-052 해결 전 건드리지 않는다.
## 14. 남은 위험·미해결 질문·다음 단계

- 수동 접근성/발표 리허설.
- A-052 Phase B DB write 선택.
- current event KPI cleanup/reset은 별도 B 승인 전 금지.
- public admin auth, `00700`, remote deploy, backup/restore는 기존 Pending.

## 15. 자체 리뷰

- [x] 요청 충족
- [x] 테스트/검증
- [x] source-of-truth/계약/버전 동기화
- [x] 개인정보 원문 노출 없음
- [x] 구현 노트 INDEX 갱신
