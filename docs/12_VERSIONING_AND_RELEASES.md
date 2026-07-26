# 버전 관리와 릴리스 기록

## 버전 축

`versions/manifest.json`에서 다음을 독립적으로 관리한다.

- product_spec
- repo_guidance
- application/web/api
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
product_spec: 2.5.0
repo_guidance: 1.7.8
application: 0.9.1-grounded-local-chat-evidence
web: 0.6.0-answer-mode
api: 3.2.0-draft
shared_contracts: 0.5.0
database_schema: 0.4.0-local
official_data: 0.1.0-initial.2
mock_data: 0.0.0-not-populated
prompt_set: 0.2.0-grounded-live-chat
test_suite: 1.6.1-grounded-actual
documentation: 2.20.5
```

승격 근거는 current local source gate pgTAP 9 files/356, rollback absence/reapply 36/36, pinned
patched runtime, actual exact one `127.0.0.1:54322`, backend integration,
compensation/absence/reset/replay와
DATA-SEED `.2` baseline·identity·A/B concurrency·19/3/10·replay·cleanup PASS다. root full integration
first attempt는 stale Web env expectation 1건(집중 수정/통과)과 Windows PowerShell subprocess timeout
9건 때문에 최종 green으로 주장하지 않는다. 별도 final local application rehearsal의 `/ready=200`과
20번째 ACTIVE, sample 20/20, final API/Web/contracts/E2E/scanner, clean disposable DB와 root offline은
PASS했다. application `0.8.1-main-stabilization`은 PR #9로 통합된 local/private MVP와
POST-MVP owner dev-origin 안정화 slice를 뜻한다. 현재 owner Draft PR, manual demo·accessibility와
public/remote/provider/`00700` readiness 완료를 뜻하지 않는다.
`local` suffix는 공개·원격·production release가 아님을 명시한다. D-046에서 방향이 확정된 `00700`
구현·검증은 계속 별도 public blocker다.

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
