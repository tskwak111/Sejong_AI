# IMP-20260726-011 — OFFICE API 명세 승인과 실행계획

- Date/Time (KST): 2026-07-26T15:14:12+09:00
- Task ID: OFFICE-API-001-PLAN
- Type: decision-plan
- Status: Decision-only Done / Execution Plan Review
- Author/Agent: Codex primary agent
- Branch: `codex/OFFICE-API-001-design`
- Source baseline: private `origin/main` `8ebc66b65a67f106b05976112de345a8c849b631`
- Predecessor commit: `c7c34f3` (`docs(api): specify office directory runtime parity`)
- Related plan/ADR/RFP: [execution plan](../superpowers/plans/2026-07-26-office-api-runtime-parity.md), [approved written specification](../superpowers/specs/2026-07-26-office-api-runtime-parity-design.md), ADR-0009, ADR-0011, ADR-0019, ADR-0020, SFR-004, D-078/D-079, A-051

## 1. 사용자 요청과 완료 기준

### 요청

사용자가 `OFFICE-API-001 명세 승인`으로 기존 `GET /api/v1/offices` runtime-parity 서면 명세를
승인했다. 이번 요청에서는 제품 코드를 즉시 구현하지 않고 현재 저장소의 실제 interface와 테스트
경계에 맞춘 실행 가능한 TDD 계획을 작성해야 한다.

### Acceptance Criteria

- 명세 승인 사실을 결정 로그·모호성 등록부·TASKS에 기록한다.
- 기존 DB adapter, readiness, FastAPI app factory, OpenAPI와 생성 타입을 실제 파일에서 대조한다.
- strict response→shared mapper→service/readiness guard→route→local 조립→contract generation→closeout
  순서의 RED→GREEN 계획을 정확한 파일·interface·명령·commit 단위로 작성한다.
- migration·seed·official/mock data·Web·LLM·dependency·public/remote 변경을 계획 범위에서 배제한다.
- 계획의 명세 커버리지, placeholder, type consistency를 자체 검토한다.
- 구현 노트·INDEX와 documentation version을 동기화하며 제품 코드는 변경하지 않는다.

## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 사용자가 서면 명세를 승인했고 Codex primary agent가 계획·거버넌스·문서 정합을 담당했다. 후속 구현은 사용자가 선택한 실행 방식의 agentic worker가 수행하고 인간이 Draft PR을 검토·merge한다. |
| When — 언제 | 2026-07-26 15:14 KST 시작, 같은 작업 턴에 계획과 검증을 마감했다. |
| Where — 어디서 | 격리 worktree `.worktrees/office-api-001-design`, 활성 docs/TASKS/version/implementation-note 영역. |
| What — 무엇을 | OFFICE-API-001 서면 명세 승인 기록과 6-task TDD 실행계획을 발행했다. |
| Why — 왜 | tracked OpenAPI와 PostgreSQL adapter에는 기관 조회가 있으나 default/local FastAPI에는 route가 없어 계약 호출이 404가 되는 drift를 안전하게 해소하기 위해서다. |
| How — 어떻게 | source-of-truth와 승인 spec을 기준으로 실제 모델·repository·readiness·route 패턴·생성 계약·검증 스크립트를 대조하고 RED→GREEN→focused gate→commit 단위로 계획했다. |
| How much — 어느 정도 | 제품 코드/DB/data/provider/dependency 변경 0, 신규 실행계획 1개, 결정 1개(D-079), implementation note 1개와 INDEX 1행, docs patch version 1회. |

## 3. 시작 전 상태

- 관련 파일: `apps/api/src/sejong_ai_api/main.py`, `local.py`, `chat/response.py`,
  `chat/readiness.py`, `db/repository.py`, `db/models.py`, `contracts/openapi-v1.yaml`,
  `packages/shared-contracts`, `scripts/verify.ps1`.
- 기존 동작: `PsycopgSejongRepository.list_offices(region, intent)`와
  `app_api.list_offices`는 OFFICIAL-only typed records를 deterministic `public_id` 순서로 반환한다.
  chat은 private `_public_office` helper로 기관 카드를 결합한다.
- 발견한 충돌/부채: tracked OpenAPI에는 `GET /api/v1/offices`가 있지만 `create_app`은 router를
  등록하지 않는다. standalone strict list model, directory service/readiness guard, dependency seam도
  없다. OpenAPI 200 schema는 inline이고 422/503 선언이 없다.
- Git 상태: 시작 시 `codex/OFFICE-API-001-design`은 `origin/main`보다 기존 specification commit
  1개 앞선 clean 상태였다.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| A-051 | 인간 결정 완료 | declared office endpoint를 제거할지 구현할지 | Q-API-OFFICES-001=A와 D-078로 존치·구현, 이번 요청으로 written specification 승인 | API minor version, runtime route |
| P-001 | Internal | `OfficeRecord | None` mapping을 chat과 standalone이 어떻게 공유할지 | overload를 가진 `build_public_office` 하나로 이동 | chat wire regression 방지 |
| P-002 | Internal | unsupported `UNKNOWN`/`OUT_OF_SCOPE`를 route에서 차단할 타입 | 기존 `SupportedIntent` Literal을 export하고 route query type으로 재사용 | typed 422, repository 호출 0 |
| P-003 | Internal | default app route discovery와 dependency 부재를 함께 처리할 방법 | always-registered router + `ClosedOfficeDirectory` 503 | 404 drift 제거, fail closed |
| P-004 | Internal | actual local smoke 전제 부재 | Docker/local DB가 준비된 경우 bounded status/count만 실행, 아니면 Pending을 정직하게 기록 | secret/DSN/data 노출 방지 |

추가 A/Blocker는 발견되지 않았다. public/remote 배포, DB/data 변경, 새 dependency는 명세상 명시적
비범위이므로 질문을 재개하지 않았다.

## 5. 설계 결정과 대안

### 선택

- strict `OfficeListResponse(items: list[Office])`를 별도 contract module에 둔다.
- existing chat mapper를 public shared helper로 이동한다.
- repository protocol/service/readiness guard/closed default를 `office/service.py`에 둔다.
- router는 DB concrete type을 모르고 typed query와 공개 envelope만 조립한다.
- default/local 모두 route를 등록하고 local만 existing repository/probe 조합을 주입한다.
- tracked OpenAPI와 generated TypeScript를 runtime과 같은 task에서 3.3.0/0.6.0으로 승격한다.

### 이유

각 파일의 책임이 하나이고 default app의 OpenAPI parity와 local actual read를 분리한다. 기존
repository/DB invariant를 재사용하므로 migration·seed 위험이 없고, readiness/DB 불능은 404나
빈 공식 결과로 위장하지 않고 safe 503으로 닫힌다.

### 고려했지만 선택하지 않은 대안

- OpenAPI endpoint 제거: 이미 승인된 SFR-004 surface와 generated consumer contract를 후퇴시킨다.
- 선언만 유지: 실제 호출 404 drift를 남긴다.
- router에서 DB adapter 직접 사용: default import safety, test seam, fail-closed composition을 깨뜨린다.
- chat mapper 복사: source/URL/검증일 변환 drift를 만든다.
- 새 migration/seed: 필요한 function/adapter/data가 이미 존재하므로 불필요하고 승인 범위를 넘는다.

## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| `docs/superpowers/plans/2026-07-26-office-api-runtime-parity.md` | 정확한 file map/interface와 6-task RED→GREEN 계획 | 후속 worker가 문맥 없이 재현 가능 |
| approved specification | 상태를 Written Specification Approved / Execution Plan Review로 변경 | 인간 승인 반영 |
| `docs/decisions/DECISION_LOG.md` | D-079 추가 | 승인 범위·미승인 범위 고정 |
| `docs/11_AMBIGUITY_REGISTER.md` | A-051을 specification resolved/plan review로 변경 | blocker 상태 정합 |
| `TASKS.md` | spec 승인과 실행계획 링크 반영 | backlog/source-of-truth 정합 |
| `versions/manifest.json`, `docs/12_VERSIONING_AND_RELEASES.md` | docs `2.20.6→2.20.7` | 계획 발행 버전 계보 |
| `CHANGELOG.md` | 제품 변경 0인 계획 발행 기록 | Unreleased 변경 성격 명시 |
| 이 노트와 `INDEX.md` | 재현·보안·인수인계 기록 1건 | AGENTS 구현 노트 의무 |

### 데이터 흐름/상태 변화

이번 요청의 runtime·DB 데이터 흐름 변화는 0이다. 후속 승인 후 계획은
`typed query→readiness→existing repository→OFFICIAL OfficeRecord→server mapper→strict response`를
구현한다.

### 오류·빈 상태·롤백

이번 요청은 문서만 변경하므로 runtime 오류/빈 상태 변화가 없다. 문서 롤백은 이 planning commit을
revert하면 되며 DB/data rollback은 없다.

## 7. 버전 전후

### 생성 시 매니페스트

- product_spec: 2.5.0
- repo_guidance: 1.7.8
- application: 0.9.1-grounded-local-chat-evidence
- web: 0.6.0-answer-mode
- api: 3.2.0-draft
- shared_contracts: 0.5.0
- database_schema: 0.4.0-local
- official_data: 0.1.0-initial.2
- mock_data: 0.0.0-not-populated
- prompt_set: 0.2.0-grounded-live-chat
- test_suite: 1.6.1-grounded-actual
- documentation: 2.20.6

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Application | 0.9.1-grounded-local-chat-evidence | unchanged | 제품 코드 0 |
| Web | 0.6.0-answer-mode | unchanged | 비범위 |
| API | 3.2.0-draft | unchanged | 후속 구현 Task 5 전 계약 변경 금지 |
| Shared contracts | 0.5.0 | unchanged | 후속 구현 Task 5 전 생성 계약 변경 금지 |
| DB schema | 0.4.0-local | unchanged | migration 0 |
| Official data | 0.1.0-initial.2 | unchanged | seed/data 0 |
| Mock data | 0.0.0-not-populated | unchanged | mock 0 |
| Prompt set | 0.2.0-grounded-live-chat | unchanged | LLM 0 |
| Test suite | 1.6.1-grounded-actual | unchanged | 테스트 구현 0 |
| Docs | 2.20.6 | 2.20.7 | 명세 승인·실행계획 발행 |

## 8. 명령과 테스트 증거

| 명령/검증 | 결과 | 시간/개수 | 증거 경로 |
|---|---|---|---|
| `rg`/`Select-String` interface audit | PASS | main/local/repository/readiness/contracts/tests/verify 경계 확인 | 실행계획 File Map |
| `python scripts/new_implementation_note.py ...` | PASS | note 1개, INDEX 1행 생성 | 이 노트, `INDEX.md` |
| plan placeholder/type/spec self-review | PASS after correction | 422 runtime schema와 exact follow-up note/docs version 보정 | 실행계획 Self-Review |
| `python -B -m json.tool versions/manifest.json` | PASS | JSON parse 1회 | `versions/manifest.json` |
| `python -B scripts/check_repository_docs.py` | PASS — `repository documentation check passed` | 1회 | repository docs/link rules |
| `powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/check_secret_patterns.ps1 -RepositoryRoot .` | PASS, finding 0 | 1회 | tracked/current tree secret-pattern gate |
| `git diff --check` | PASS | whitespace error 0 | current worktree diff |
| forbidden product/data-path diff from `c7c34f3` | PASS | changed file 0 | `apps/api`, contracts/packages, DB/Supabase/data/Web/lockfiles |
| plan red-flag scan | PASS | prohibited placeholder match 0 | execution plan |

### 미실행 검증과 이유

API pytest, Ruff, MyPy, contract generation, DB/local smoke는 제품 코드가 없는 planning-only
요청이므로 실행하지 않는다. 후속 실행계획 Task 1~6에 집중/전체 gate가 명시되어 있다.

## 9. 보안·개인정보·접근성·성능 영향

- Privacy: 질문 원문·masked question·PII·event/failed row를 읽거나 쓰지 않았다.
- Security: key/token/DSN을 읽거나 출력하지 않았다. public/remote/배포/권한 변경 0이다.
- Accessibility: Web와 사용자 UI 변경 0이다.
- Performance/cost: runtime/provider/DB call 0, 외부 API 비용 0원. 후속 endpoint는 기존 read path만 사용한다.

## 10. 데이터와 출처 영향

- 공식 데이터: immutable `.2`와 actual local DB 모두 변경 0.
- mock/AI 생성: 생성·혼합 0.
- schema/lineage: migration/seed/lineage 변경 0.
- verified date: 기관 record를 조회·갱신하지 않았다.

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- 서면 명세는 승인됐지만 실행계획은 아직 Review다. 다음 단계에서 사용자가 실행 방식을 선택하거나
  동등한 구현 승인을 해야 제품 코드와 API minor contract를 변경한다.
- 구현 완료 시 API `3.3.0-draft`와 shared contracts `0.6.0`으로 additive minor 승격한다.
- public/remote 배포, 실제 기관 운영, DB/data 변경, LLM/provider 사용, 자동 merge는 승인되지 않았다.
- 구현 PR은 Draft로 게시하고 사람이 검토·merge한다.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- `SupportedIntent` export, overloaded mapper, Protocol 이름, fake 분할, focused-test commit 경계는
  승인된 wire contract와 안전 규칙 안의 내부 선택이다.
- 후속 구현은 task마다 fresh RED 확인 후 최소 GREEN과 focused gate를 수행하고 마지막 한 번만 full
  repository gate를 수행한다.

## 13. 인수인계·재현·롤백

### 재현

1. source baseline과 branch를 확인한다.
2. approved specification과 execution plan을 순서대로 읽는다.
3. `main.py`, `local.py`, `db/repository.py`, `chat/readiness.py`, tracked OpenAPI를 대조한다.
4. 계획 승인 후 Task 1부터 순서대로 checkbox를 갱신하며 실행한다.

### 롤백

이번 planning commit 하나를 revert한다. product/API/DB/data rollback은 없다.

### 다음 개발자 시작점

사용자에게 실행 방식 두 가지를 제시한다. Subagent-Driven을 선택하면
`superpowers:subagent-driven-development`, Inline Execution을 선택하면
`superpowers:executing-plans`를 먼저 읽고 Task 1 RED부터 시작한다.

## 14. 남은 위험·미해결 질문·다음 단계

- 실행계획 인간 승인/방식 선택이 Pending이다.
- local Docker/Supabase가 후속 closeout 시 준비되지 않으면 actual endpoint smoke만 Pending으로 남고
  injected local integration은 반드시 실행한다.
- 현재 hosted backend CI가 없으므로 local full gate가 구현 PR의 권위다.
- 다음 단계: 사용자가 Subagent-Driven 또는 Inline Execution을 선택하고 구현을 승인한다.

## 15. 자체 리뷰

- [x] 요청 충족
- [x] 테스트/검증
- [x] source-of-truth/계약/버전 동기화
- [x] 개인정보 원문 노출 없음
- [x] 구현 노트 INDEX 갱신
