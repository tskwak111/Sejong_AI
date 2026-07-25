# POST-MVP-001 private main 안정화 실행계획

- Plan ID: POST-MVP-001-PLAN
- 상태: **Approved / In Progress**
- 작성일: 2026-07-24 KST
- 기준: `origin/main` at `4cc2f4e5e478668e1d7216fddc08874c9285274b`
- 브랜치: `codex/POST-MVP-001-main-stabilization`
- 설계: [private main 안정화 설계](../specs/2026-07-24-post-mvp-main-stabilization-design.md)

## Task 1. 기준선과 변경 경계

- [x] 최신 private `origin/main`을 fetch하고 clean 기준 SHA를 기록한다.
- [x] 격리 worktree를 생성하고 Web 48 unit, lint, typecheck 기준선을 확인한다.
- [x] PR #10은 Web CI PASS, owner-reviewed config 경계 때문에 collaboration policy FAIL임을
  확인한다.
- [x] public 평가 저장소와 remote/public/provider/DB/data 변경을 범위에서 제외한다.

## Task 2. local dev-origin TDD

- [x] 실제 `next.config.ts`를 import하는 exact config 테스트를 먼저 추가한다.
- [x] 현재 main 설정에서 예상 assertion failure를 확인한다.
- [x] `allowedDevOrigins: ["127.0.0.1"]`만 추가한다.
- [x] 집중 테스트가 GREEN인지 확인한다.

## Task 3. 활성 정본 동기화

- [x] D-069에 확정 서비스명 `세종 민원이음`을 기록한다.
- [x] D-070에 PR #10 owner 인계와 협업 경계 유지 결정을 기록한다.
- [x] 활성 제품 소개·source-of-truth의 서비스명을 동기화한다.
- [x] `TASKS.md`의 PR #9 merge와 WEB-DEV-ORIGIN owner-review 상태를 갱신한다.
- [x] seed runbook 순서가 이미 일치함을 확인하고 불필요한 변경을 만들지 않는다.
- [x] manifest의 product/Web/test/docs 축을 갱신한다.

## Task 4. 구현 노트와 검증

- [x] 구현 노트를 생성하고 6W1H, RED/GREEN, 보안·데이터·롤백·인수인계를 작성한다.
- [x] Web unit, lint, typecheck, build를 실행한다.
- [x] 127.0.0.1 local dev-origin 집중 E2E 또는 동등한 실제 dev-server 증거를 실행한다.
- [x] 문서 검사, 비밀 패턴 검사, `git diff --check`를 실행한다.
- [x] requirement-by-requirement diff review와 독립 Critical/Important 리뷰를 수행한다.

## Task 5. 게시

- [x] 의도한 파일만 stage하고 commit한다 (`887f150`).
- [x] owner 브랜치를 private origin에 push한다.
- [x] `main` 대상 [Draft PR #11](https://github.com/tskwak111/Sejong_AI/pull/11)을 만들고
  자동 merge하지 않는다.
- [x] 기존 팀원 PR #10은 자동 merge/close하지 않고 대체 관계를 사용자에게 알린다.

## 버전 계획

| 축 | 전 | 후 |
|---|---|---|
| product spec | 2.4.0 | 2.4.1 |
| repo guidance | 1.7.7 | 1.7.8 |
| application | 0.8.0-pr8-frontend-baseline | 0.8.1-main-stabilization |
| Web | 0.5.0-pr8-citizen-admin-baseline | 0.5.1-local-dev-origin |
| test suite | 1.5.0-pr8-web-baseline | 1.5.1-local-dev-origin |
| documentation | 2.16.0 | 2.17.0 |

공개 API, shared contract, DB schema, official/mock data, prompt set은 변경하지 않는다.

## 롤백

Draft PR을 merge하지 않거나 owner commit을 revert한다. config 한 줄 제거로 기존 개발 서버
동작으로 돌아가며 DB migration, data restore, secret rotation은 필요 없다. 제품명 문서 동기화는
별도 revert 가능하고 역사 문서를 재작성하지 않는다.
