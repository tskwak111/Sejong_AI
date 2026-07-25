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
application: 0.8.1-main-stabilization
web: 0.5.1-local-dev-origin
api: 3.1.0-draft
shared_contracts: 0.4.0
database_schema: 0.4.0-local
official_data: 0.1.0-initial.2
mock_data: 0.0.0-not-populated
prompt_set: 0.1.0-upstage-solar-pro3-synthetic
test_suite: 1.5.1-local-dev-origin
documentation: 2.19.1
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
`2.5.0`, D-073의 written specification 승인과 8-task TDD 실행계획은 documentation
`2.19.1`이다. 이 문서 버전은 제품 코드·API `3.1.0-draft`·shared contracts·DB·공식 데이터·
prompt runtime·test suite가 아직 변하지 않았다는 계획 단계다. 계획 승인과 구현 뒤에만 각
축을 실행 결과에 맞춰 승격한다.

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
