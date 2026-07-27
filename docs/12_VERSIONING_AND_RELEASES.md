# 버전 관리와 릴리스 기록

## 버전 축

`versions/manifest.json`에서 다음을 독립적으로 관리한다.

- product_spec
- repo_guidance
- application/web/api/shared_contracts
- database_schema
- official_data/mock_data
- prompt_set
- test_suite
- documentation

## 증가 기준

### Major

- 호환성 파괴 API/DB
- 제품 범위 또는 개인정보 정책의 근본 변경
- 데이터 의미/평가 정의 변경

### Minor

- 호환 가능한 기능·필드 추가
- KB 분야/공식 데이터 추가
- 새 테스트 군/프롬프트 기능

### Patch

- 버그·문구·오탈자·비호환 없는 내부 수정

## 구현 노트 기록 예시

```text
Before
- api: 0.1.0-draft
- schema: 0.1.0-draft
- data: 0.0.0

After
- api: 0.2.0
- schema: 0.2.0
- data: 0.1.0
```

Git commit가 아직 없으면 `uncommitted`라고 기록하고, 현재 HEAD를 함께 적는다.

## 현재 local DB 기준선과 manifest

DB-001의 historical 2026-07-18 baseline 뒤, 2026-07-22 local/private core-loop migration과
supported DATA-SEED-002 actual cycle이 현재 기준선을 갱신했다.

```text
product_spec: 2.6.0
repo_guidance: 1.7.9
application: 0.12.1-bounded-hybrid-rag
web: 0.8.0-guided-chat
api: 4.0.0-draft
shared_contracts: 1.0.0
database_schema: 0.5.0-local
official_data: 0.1.0-initial.2
mock_data: 0.0.0-not-populated
prompt_set: 0.4.0-topic-coverage
test_suite: 2.1.1-bounded-hybrid-rag-closeout
documentation: 2.29.0
```

승격 근거는 current local source gate pgTAP 11 files/385 tests, 11-stage rollback
absence/reapply, pinned
patched runtime, actual exact one `127.0.0.1:54322`, backend integration,
compensation/absence/reset/replay와
DATA-SEED `.2` baseline·identity·A/B concurrency·19/3/10·replay·cleanup PASS다. root full integration
first attempt는 stale Web env expectation 1건(집중 수정/통과)과 Windows PowerShell subprocess timeout
9건 때문에 최종 green으로 주장하지 않는다. 별도 final local application rehearsal의 `/ready=200`과
20번째 ACTIVE, sample 20/20, final API/Web/contracts/E2E/scanner, clean disposable DB와 root offline은
PASS했다. current application/Web는 CHAT-NATURAL Slice 1~3 위에 CHAT-HYBRID-RAG
Tasks 1~10 구현·검증을 포함하고 API는 `4.0.0-draft`를 유지한다. Task 10 actual은
정확히 한 번 실행했으나 strict accepted usage/provider match 0으로 FAIL했으며 재실행하지 않았다.
manual demo·actual PASS·configured remote smoke 완료를 뜻하지 않는다.
`local` suffix는 공개·원격·production release가 아님을 명시한다. D-046/D-092의 `00700`
local 구현·검증은 끝났고, remote 운영은 ADR-0026 gate가 별도다.

`0.11.1-classifier-runtime`은 `CLASSIFIER-RUNTIME-WIRING-001`에서 누락됐던 실제 local factory
classifier 주입과 combined shared ledger를 교정한 patch다. 공개 API·DB·공식 데이터는 바꾸지
않았고, provider-disabled default와 public/remote 금지는 유지한다.

Documentation `2.26.0`은 Q-RAG-001=A/Q-DATA-RAG-001=A와 설계 1~3부 승인에 따라
ACTIVE topic catalog, coverage grounding, same-tab region UX, certificate 3-option hierarchy,
local interactive 80/100/160·USD0.20 budget과 48-case synthetic UAT를 하나의 written
specification과 ADR-0027로 동결한 minor documentation release다. Application/Web/API/shared/DB,
official/mock data, prompt/test runtime은 아직 변경하지 않았다. written specification review와
실행계획 승인 전 구현·actual provider 호출은 0이다.

Documentation `2.26.1`은 사용자의 `명세 승인`으로 위 written specification을 Approved로
전환하고 11개 reviewer-worthy task의 exact RED/GREEN 실행계획을 게시한 patch다. plan은
ACTIVE catalog→closed selector→typed grounding→chat/context→Web→cost→48 offline→20 actual→
final gate 순서와 파일·명령·커밋 경계를 고정한다. Application/Web/API/shared/DB/data/prompt/test
runtime은 변경하지 않았으며 실행계획 승인 전 제품 코드와 actual provider 호출은 계속 0이다.

Application `0.12.1-bounded-hybrid-rag`, Web `0.8.0-guided-chat`, prompt set
`0.4.0-topic-coverage`, test suite `2.1.1-bounded-hybrid-rag-closeout`, documentation `2.29.0`은
CHAT-HYBRID-RAG-001 Tasks 1~11의 local/private 구현·검증 기준선이다. request-local
ACTIVE/OFFICIAL catalog, closed topic+coverage selector, typed grounding, intent별 FOLLOWUP,
bounded context와 same-tab region UX, 80/100/160·USD0.20 local budget, 48-case synthetic UAT를
포함한다. immutable official `.2`의 runtime 교집합은 19이고 local DB의 별도 승인 20번째
ACTIVE를 official `.2`에 역기록하지 않는다. API `4.0.0-draft`, shared contracts `1.0.0`,
DB `0.5.0-local`, official/mock data는 불변이다. offline UAT는 91 PASS·skip 0,
official examples 57/57, classifier 60/60이다. 실제 Upstage 20-case는 한 번 실행해
20 selected·skip 0·11 provider-free·9 outbound였으나 strict accepted usage/provider match
0으로 FAIL했다. durable SUCCESS/REGION FOLLOWUP replay는 validated topic을 보존한다.
browser 27/27, API 2,357 pass·8 local-DB skip, contracts 96/96, Mypy 114와
secret/bundle/protected diff 0을 기록했다. final wrapper는 FORMAT-API exit 1이라 PASS가 아니고,
formatter 교정 뒤 미실행 constituent를 별도로 모두 통과했다. public/remote, DB reset/seed,
automatic merge 완료를 뜻하지 않는다.

Q-LLM-006~012/D-072의 local/private 근거 제한형 시민 chat 설계는 product specification
`2.5.0`, D-073의 written specification과 plan publication은 documentation `2.19.1`,
D-074의 plan 승인·Subagent-Driven 구현 시작 checkpoint는 documentation `2.19.2`다. Tasks 1~7은
additive API `3.2.0-draft`, grounded prompt/profile, bounded fallback/idempotency, local composition과
Web `answer_mode` disclosure를 offline으로 구현·task-scoped 검토했다. 위 closeout axes는
`versions/manifest.json`, package metadata와 implementation-note INDEX에 통합됐고, final
provider-disabled root offline gate도 PASS했다. DB schema, official data, mock data, dependency와
lockfile은 변경하지 않았다. D-075 local provider actual은 10건 GENERATED 4/TEMPLATE 6,
출처 10/10, 공식 mismatch 0, PII-free fixture typed write-boundary 위반 0, outbound 10으로
PASS했다. VAT 포함 USD 0.001319835는 legacy-reported lower-bound이며 configured maximum
USD 0.0135168은 USD 0.05 cap 아래다.
`3.2.0-draft`와 이 local 증거는 public/remote 사용 승인과 다르다.
Documentation `2.20.2`는 D-076에서 corrective second 10-call incident를 사후 확인하고 PR #13
병합을 승인해 A-049를 해결한 기록이다. application/API/DB/data/prompt/test 축은 바꾸지 않으며
future rerun·22행 삭제·public/remote·자동 merge 권한을 추가하지 않는다.
Documentation `2.20.3`은 D-077/Q-DB-CLEANUP-001=A로 오표시 22행을 현재 유지하고 해당 local
DB의 event 통계를 평가 KPI로 사용하지 않는 결정을 기록한다. 정식 수치가 필요한 시점의
reset·정식 `.2` 재시드·필요한 19→20 승인 흐름 재현은 B의 별도 인간 승인 대상으로 남긴다.
application/API/DB/data/prompt/test 축과 실제 DB 행은 바꾸지 않는다.
Documentation `2.20.4`는 2026-07-26 current MVP status audit과 handoff를 기록한다. PR #11
병합·Cloud/Frontend rehearsal 완료, actual local DB의 ACTIVE 20/office 3/mapping 10, API/Web
비실행 상태, OpenAPI의 `/api/v1/offices`·`/api/v1/admin/quality-summary` 대비 current runtime
gap과 hosted backend CI 부재를 다음 P1 후보로 기록한다. 제품/API contract/DB/data/prompt/test
축과 실제 runtime/data는 변경하지 않는다.
Documentation `2.20.5`는 위 결정·상태 문서를 Draft PR #14로 게시하고, active contract의
OFFICE API를 존치·runtime에 구현할지 인간이 승인하기 전 제품 구현을 시작하지 않는 설계 gate를 기록한다.
제품/API contract/DB/data/provider/prompt/test 축과 actual runtime/data는 변경하지 않는다.
Documentation `2.20.6`은 Q-API-OFFICES-001=A/D-078의 설계 승인과 OFFICE-API-001 written
specification을 기록한다. existing endpoint의 required filter·OFFICIAL-only·deterministic
order를 runtime에 구현하고 unavailable을 value-free 503으로 닫는 계획이며, specification
review와 실행계획 승인 전 제품/API contract/DB/data/provider/prompt/test 축은 변경하지 않는다.
Documentation `2.20.7`은 D-079의 OFFICE-API-001 written specification 승인과
[`2026-07-26-office-api-runtime-parity.md`](superpowers/plans/2026-07-26-office-api-runtime-parity.md)
실행계획 발행을 기록한다. strict response·shared mapper·typed service/readiness guard·always-registered
route·local composition·OpenAPI/generated TypeScript·closeout gate를 RED→GREEN 순서로 고정했으며,
계획 승인 전 application/API/shared contract/test 축과 DB/data/Web/provider/dependency는 변경하지 않는다.
Documentation `2.20.8`은 OFFICE-API-001 runtime parity 구현 closeout이다. application
`0.9.1-grounded-local-chat-evidence→0.10.0-office-directory-runtime`, API
`3.2.0-draft→3.3.0-draft`, shared contracts `0.5.0→0.6.0`, tests
`1.6.1-grounded-actual→1.7.0-office-directory`로 승격했다. required region+supported intent,
OFFICIAL-only server mapping, valid-empty 200, value-free 422와 `Retry-After: 30` safe 503을
default/local FastAPI와 tracked/generated contract에 정렬했다.

aggregate `scripts/verify.ps1`은 PowerShell/Node/pnpm preflight 뒤 repo-local/PATH `uv` 부재로
`PREFLIGHT-UV reason=exception code=2`에서 중단되어 PASS로 기록하지 않는다. pinned
uv 0.11.28로 실행한 constituent API Ruff/MyPy/pytest, shared generation/contracts,
repository docs/secret/diff gate는 모두 PASS했다. API는 2,043 PASS·DB-only 8 skip·subtests 5
PASS이며 기존 Starlette warning 1건, shared contracts는 90/90 PASS다. actual Docker/Supabase
endpoint smoke는 secret environment와 local prerequisite가 없어 Pending이고 injected local
integration은 PASS했다. product specification, repository guidance, Web, DB schema, official/mock
data와 prompt 축은 정확히 유지했으며 migration·seed·data·provider·dependency·lockfile·
public/remote 변경은 없다.

Documentation `2.20.9`는 D-080에 따라 published OFFICE-API-001 실행계획 승인과
Subagent-Driven 구현 완료, human-review Draft PR Pending을 기록한 final-review fix다. runtime
OpenAPI의 office 503 `Retry-After` header schema를 tracked contract와 정렬하고,
`versions/manifest.json`에서 API version을 읽어 active README, CODEX index, tracked OpenAPI,
FastAPI metadata와 generated TypeScript banner를 함께 검증한다. test suite는
`1.7.0-office-directory→1.7.1-office-directory-review-fix`로 승격하며 application/API/shared
contracts/Web/DB/data/prompt 축은 유지한다. fresh constituent API 2,044 PASS·DB-only 8 skip·
subtests 5 PASS, pinned root 431 PASS·2 skip, shared 90/90와 docs/secret/diff gate를 통과했다.
aggregate `scripts/verify.ps1`은 기존
`PREFLIGHT-UV reason=exception code=2` 때문에 **NOT PASS**이고, actual Docker/Supabase endpoint
smoke도 `Pending — local prerequisite unavailable` 그대로다. public/remote/deploy/automatic
merge는 승인되지 않았다.

Documentation `2.20.10`은 PR #15 merge commit `b66e18c`와 D-081의 post-merge bounded
read-only actual smoke를 기록한다. 최신 main에서 `/ready=200`, office match `200/count=1`,
valid empty `200/count=0`을 확인했다. process-only CSPRNG context secret을 사용했고 `.env` 복사,
record/DSN/secret 출력, purge/reset/seed/write와 provider call은 0이다. application/API/shared
contracts/test/Web/DB/data/prompt 축은 변경하지 않으며 historical aggregate verifier의
`PREFLIGHT-UV` NOT PASS 증거도 바꾸지 않는다.

Documentation `2.21.0`, repository guidance `1.7.9`, test suite
`1.8.0-local-demo-readiness`는 PR #16 merge commit `bcaf39c` 이후 D-082의 local/private
closeout을 기록한다. 고정된 primary ignored `apps/api/.env`만 갱신하고 값을 출력하지 않는
CSPRNG context-secret provisioner와 7개 테스트를 추가했다. provider-disabled final rehearsal은
`/health=200`, `/ready=200`, chat SUCCESS/TEMPLATE/source 1, PERSONAL_LOOKUP
`candidate_eligible=false`, office match/empty, approved admin read, provider attempt 0과 Web
390/430/desktop 21/21을 확인했다. PERF-001은 read-only Phase A와 metadata-write Phase B로
분리했고 A-052 결정 전 Phase B는 HOLD다. application/Web/API/shared/DB/data/prompt/dependency,
public/remote 범위와 actual official rows는 변경하지 않는다.

Documentation `2.21.1`은 PR #17 merge commit `c945303` 뒤 사람이 직접 수행할 작업을
manual demo/accessibility/presentation, A-052 Phase B DB 선택, teammate MFA/recovery 확인으로
분리한 handoff다. current ACTIVE 20 DB를 reset/reseed하지 않고 개선 후 결과를 시연하며,
Codex 후속은 DB-write-free PERF Phase A다. product/application/Web/API/shared/DB/data/prompt/test
축과 실제 환경·DB·provider는 변경하지 않는다.

Documentation `2.21.2`는 primary ignored `.env`에 `UPSTAGE_GROUNDED_CHAT_MODE`가 없는
상태를 값 비노출로 진단한 기록이다. exact loader는 이 경우 grounded profile을 조립하지 않고
`DISABLED`로 닫힌다. 사람이 의도를 명확히 볼 수 있도록 explicit `false` 한 줄을 권고하지만,
product/application/Web/API/shared/DB/data/prompt/test와 actual environment/provider는
변경하지 않았다.

Documentation `2.21.3`은 사용자가 explicit false를 추가한 뒤 assignment 1개·exact
lowercase false·runtime profile DISABLED·Git ignore를 값 비노출로 재확인한 기록이다.
Docker client/server와 local DB container도 read-only로 준비 상태를 확인했으며 provider call,
DB query/write, product/application/Web/API/shared/DB/data/prompt/test 변경은 0이다.

Documentation `2.21.4`는 사용자 실행 API의 `/ready=200`을 body 없이 재확인하고 ignored
Web local actual 환경 4개를 정확히 준비한 기록이다. Git tracked file, product/application,
Web source/API/shared/DB/data/prompt/test, provider와 DB 상태는 변경하지 않는다.

Documentation `2.21.5`는 production-only로 남아 있던 local `node_modules`와 Next.js의
bare `pnpm` spawn `ENOENT`를 분리 진단하고, Corepack과 frozen lockfile로 선언된 Web
TypeScript 개발 의존성을 복구한 기록이다. package manifest·lockfile·제품 동작·provider·
DB는 변경하지 않았고 Web `tsc --noEmit`으로 해석 가능 상태를 확인했다.

Documentation `2.21.6`은 generic 증명서 요청이 classifier에서 `UNKNOWN + FOLLOWUP`으로
분류되고 service의 고정 네 분야 option을 거쳐 Web generic 확인 질문으로 표시되는 원인을
확인한 기록이다. category-aware certificate FOLLOWUP을 권고하되 exact option은 인간 제품
결정으로 남겼고 product/Web/API/DB/data/provider/test는 변경하지 않았다.

Documentation `2.21.7`은 실제 browser·UTF-8 API·read-only admin/office 경로를 함께 감사해
구체 질문·공식 출처·정책 폴백·15분 context·반응형 화면의 정상 동작을 확인하고,
generic 증명서 반복 FOLLOWUP, exact WASTE-03만 허용하는 관리자 후보 작성, 시민 최초 지역
선택 진입점 부재를 P0 gap으로 기록했다. DB의 APPROVED 후보는 pending-only 화면 필터로
숨겨진 것이며 AI key 부재가 원인이 아님을 확인했다. product/Web/API/DB/data/provider/test
코드는 변경하지 않았다.

Documentation `2.21.8`은 Q-CHAT-FOLLOWUP-001=A/D-083의 generic certificate category-aware
FOLLOWUP 설계와 exact five options를 기록한 written specification이다. unsupported compound
certificate의 OUT_OF_SCOPE, specific supported query의 기존 retrieval, text-free FOLLOWUP,
signed context와 public contract shape를 보존한다. product/Web/API/DB/data/provider/test
코드는 변경하지 않았다.

Documentation `2.21.9`는 D-084의 certificate FOLLOWUP written specification 승인과
classifier priority/invariant→closed server option labels→text-free service orchestration→typed
Web prompt/context→full gate의 5-task RED/GREEN 실행계획을 기록한다. plan 승인 전
product/Web/API/DB/data/provider/dependency/test source는 변경하지 않는다.

Documentation `2.22.0`은 CHAT-CLASSIFICATION-GAPS-001 actual-equivalent fixture 진단을
기록한다. 일반 한국어 두 건의 contextual-name PII false positive와, 현재 taxonomy가
비민원·네 분야 밖 행정 민원·지원 intent의 새 표현을 분리하지 못하는 원인을 확인했다.
Q-CLASS-001/Q-SCOPE-001 전 product/API/Web/test/OpenAPI/DB/data/provider/dependency는
변경하지 않는다.

Documentation `2.22.1`은 Q-SCOPE-001=A/D-085/ADR-0024를 기록한다. 네 분야 밖 행정 민원은
기존 failed-question/KB candidate와 분리된 future `CIVIC_SCOPE_GAP` queue에서 안전하게
마스킹된 text만 30일 보관하고 자동 ACTIVE 전환을 금지한다. `NON_CIVIC`은 무저장이다.
exact wire enum·DB migration·admin workflow는 written specification/plan 승인 전 미구현이며
product/application/API/DB/provider/test version은 유지한다.

Documentation `2.22.6`은 CHAT-NATURAL-001 설계 2부 승인/D-090을 기록한다. public
`CIVIC_SCOPE_GAP` reason과 별도 30일 masked queue, NON_CIVIC·policy/privacy 무저장,
context v2의 closed topic/slot/dialog claim, v1 read-only TTL 전환과 Web 새 대화 reset을
확정했다. exact contract/DB/runtime은 written spec 전 미구현이며 product/application/Web/API/
contract/DB/data/prompt/test/provider actual은 변경하지 않는다.

Documentation `2.22.5`는 사용자의 CHAT-NATURAL-001 설계 1부 승인/D-089를 기록한다.
PII-first deterministic safety와 ambiguous-only classifier, server route, ACTIVE/OFFICIAL
grounding, generated/template, server-owned source 순서와 raw transcript 없는 15분 structured
context 경계를 확정했다. 공개 응답·저장·오류·테스트 상세는 후속 설계 검토 전 미확정이며
product/application/Web/API/contract/DB/data/prompt/test/provider actual은 변경하지 않는다.

Documentation `2.22.4`는 Q-PROD-REAL-001=A/D-088을 기록한다. 제품은 현실형 공식 민원
안내·기관 연결·사람 승인 운영센터를 고도화하며 실제 신청·상태조회·결제·기관 transaction은
P2로 유지한다. CHAT-NATURAL-001은 제품 범위 인터뷰에서 설계 검토로 이동했다. product/
application/Web/API/contract/DB/data/prompt/test/provider actual은 변경하지 않는다.

Documentation `2.22.3`은 Q-CLASS-002=A/D-087의 classifier 1회·3초·retry 0·입력 1,024자·
출력 128 token·sub-cap 20, generation sub-cap 30, combined process cap 40과 VAT 포함
USD 0.05 local synthetic stop line을 기록한다. 또한 active code와 권위 문서를 기준으로
PII 오탐, taxonomy, 얕은 context, keyword 검색, feedback 무연결, 일반 후보 작성, scope-gap,
인증·freshness·rate limit·backup·부하·접근성·실제 기관 연계 격차를 P0/P1/P2로 감사했다.
제품 목표 Q-PROD-REAL-001과 written spec 승인 전 product/application/Web/API/contract/DB/data/
prompt/test/provider actual은 변경하지 않는다.

Documentation `2.22.2`는 Q-CLASS-001=A/D-086/ADR-0025의 future local/private hybrid
classification 방향을 기록한다. deterministic PII·policy·명백한 분류 뒤 안전한 ambiguous
질문만 Upstage closed enum 분류를 사용할 수 있으며 answer/source/KB/storage 권한은 서버에
남는다. Q-CLASS-002 budget과 written spec 전 product/runtime/provider actual call은 0이다.

Q-LLM-005=A/D-065/ADR-0022 당시 product spec `2.4.0`, prompt selection
`0.0.3-upstage-solar-pro3-synthetic-selected`를 기록했다. 이후 offline evaluator 완료,
PR #9 통합과 POST-MVP owner slice가 위 current manifest 값으로 승격했다. D-066의 명세 승인과
Review 실행계획 발행 뒤 D-067 실행 승인, Task 1 review-clean settings, Task 2 strict source-free
prompt/output/outcome와 aggregate-once cost 계약, Task 3 bounded HTTPX/attempt budget 기록으로
documentation을 `2.13.4`로 올렸다. Application/prompt/test 축은 전체 offline evaluator gate인
Task 6 전까지 유지한다. Task 4 hash-bound canonical fixture와 per-generation ACTIVE grounding
checkpoint, Task 4.5 content-free attempt evidence와 Task 5/6 preflight safety correction으로
documentation을 `2.13.6`으로 올렸고, Task 5 text-free report/readiness-first local runner의
review-clean checkpoint로 `2.13.7`까지 올렸다. 현재 production runner는 존재하지만 test는
MockTransport/fake repository/pool만 사용했고 key, DNS/network/실제 DB call 또는 실제 시민
provider 연결은 0이다. 이후 버전 승격은 위 manifest와 `CHANGELOG.md`를 따른다.

## 릴리스 체크

- version manifest
- CHANGELOG
- migration/rollback
- OpenAPI/JSON schema
- tests/report
- data lineage
- implementation notes/handoff

## CHAT-NATURAL-001 grouped implementation promotion

2026-07-27 세 수직 흐름의 계약·코드·DB·Web 검증 완료로 application
`0.11.0-natural-dialogue`, Web `0.7.0-natural-dialogue`, API `4.0.0-draft`, shared contracts
`1.0.0`, database `0.5.0-local`, prompt `0.3.0-hybrid-classifier`, tests
`1.9.0-natural-dialogue`, documentation `2.24.0`으로 승격했다. 공식 데이터
`0.1.0-initial.2`와 mock data는 변경하지 않았다.

API major는 `CIVIC_SCOPE_GAP`과 context v2 공개 계약, shared major는 생성 타입의 동기
승격이다. DB minor는 additive 00680과 property-only 00700을 포함하며 rollback 순서는
00700→00680→…→00100이다. 이 버전은 local schema와 구현 완료를 뜻하고, formal seed
19→20 actual 증거·실제 Upstage 품질·remote/public 배포 완료를 뜻하지 않는다.
