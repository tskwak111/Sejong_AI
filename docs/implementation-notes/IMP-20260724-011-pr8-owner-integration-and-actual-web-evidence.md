# IMP-20260724-011 — PR #8 owner 통합과 actual Web 증거 정리

- Date/Time: 2026-07-24T13:12:35+09:00
- Task/Request ID: WEB-PR8-INTEGRATION-001
- Type: integration-test-documentation
- Status: Done — actual Web/DB와 final root gate PASS, 인간 수동 검수·Draft PR review Pending
- Base commit: `f22bd00`
- Related plan/ADR/RFP:
  - [`PROJECT_PLAN.md`](../source-of-truth/PROJECT_PLAN.md)
  - [`TEAM_DECISIONS.md`](../source-of-truth/TEAM_DECISIONS.md)
  - [`RFP_MATRIX.md`](../source-of-truth/RFP_MATRIX.md)
  - [`ADR-0019`](../adr/0019-private-github-role-scoped-collaboration.md)
  - [`TASKS.md`](../../TASKS.md)

## 1. 사용자 요청과 완료 기준

### 요청

PR #8 frontend baseline을 owner가 통합한 현재 상태와 후속 교정 commit을 기준으로 actual Web 증거를
정리한다. `scripts/README.md`의 오래된 actual E2E 명령을 현재 Playwright opt-in 계약에 맞추고,
`[db.seed].enabled=false`를 유지한 채 reset 후 immutable `.2`를 별도
`seed-cycle → verify-final → provision`하는 운영 순서를 명확히 한다.

### Acceptance Criteria

- 실제 browser 명령은 `E2E_ACTUAL=1`, `pnpm --dir tools/web-e2e`,
  `--project=actual-desktop`, `e2e/admin-core-loop.actual.spec.ts`를 사용한다.
- `db reset --local`을 자동 seed로 오인하지 않으며, immutable `.2` 별도 seed 단계를 기록한다.
- 현재 증거를 actual E2E `1/1 PASS`, final ACTIVE `20`, `KB-WASTE-03` `1`, `/ready=200`으로
  한정한다.
- final root gate는 실패 원인을 숨기지 않고 교정 뒤 fresh PASS 증거를 기록한다.
- `allowedDevOrigins: ["127.0.0.1"]`은 별도 Frontend PR Pending이며 이 변경에 포함하지 않는다.
- Cloud/local Codex가 Draft PR을 자동 merge하지 않는 협업 경계를 유지한다.
- 새 dependency와 API/DB/data/contract/prompt는 바꾸지 않는다. PR #8 Web 기준선, 후속
  actual/접근성/승인 gate, repository guidance와 version manifest를 owner 범위로 통합한다.

## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 사용자가 owner 통합과 협업 경계를 승인했고, Codex가 명령·증거 문서를 교정하며 인간 owner가 Draft PR을 검토·병합한다. |
| When — 언제 | 2026-07-24 KST, PR #8 baseline 통합과 commit `6cd540d`, `f22bd00` 교정 후 |
| Where — 어디서 | local/private Windows 저장소의 `scripts/README.md`와 이 구현 노트; actual Web은 local API/DB와 `tools/web-e2e`에서 실행 |
| What — 무엇을 | 실제 E2E opt-in 명령, DB reset/별도 seed 경계, 현재 PASS/Pending 증거와 협업 경계를 정리 |
| Why — 왜 | 오래된 env/project/spec 명령으로 잘못된 테스트를 실행하거나 빈 reset DB를 seeded DB로 오인하는 데모 위험을 제거하기 위해 |
| How — 어떻게 | 현재 Playwright config, immutable `.2` verifier, local login provisioner와 현재 commit/evidence를 대조하고 문서만 최소 수정 |
| How much — 어느 정도 | PR #8 63-path owner 통합, 후속 제품·E2E 9개 파일, 문서·지침·버전 동기화; dependency·계약·DB schema·공식 데이터 변경 0, provider/remote/public 사용 0 |

## 3. 시작 전 상태

- 관련 파일:
  - [`scripts/README.md`](../../scripts/README.md)
  - [`playwright.config.ts`](../../tools/web-e2e/playwright.config.ts)
  - [`admin-core-loop.actual.spec.ts`](../../tools/web-e2e/e2e/admin-core-loop.actual.spec.ts)
  - [`supabase/config.toml`](../../supabase/config.toml)
  - [`verify_data_seed_db.py`](../../scripts/verify_data_seed_db.py)
  - [`provision_local_database_login.py`](../../scripts/provision_local_database_login.py)
- 기존 동작: Playwright는 이미 `E2E_ACTUAL=1`일 때 `actual-desktop`과 actual spec만 수집하지만
  README는 제거된 env, `desktop` project, 존재하지 않는 이전 spec을 안내했다.
- 발견한 충돌/부채: README가 reset과 seed의 분리 원칙은 서술했지만
  `[db.seed].enabled=false`와 별도 세 명령을 실행 순서로 고정하지 않았다.
- Git 상태: base HEAD `f22bd00`; 이 작업 시작 전부터 다른 lane의 문서 및 actual spec 변경이
  worktree에 존재하므로 보존하고 이 노트의 변경으로 주장하지 않는다.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| WEB-DEV-ORIGIN-001 | B/High, 확정 | Next 개발 origin 경고 교정 | 사용자가 별도 Frontend PR로 승인; 이번 문서 PR에는 미포함 | 이후 `allowedDevOrigins: ["127.0.0.1"]` 변경·검증 필요 |
| WEB-ROOT-GATE-001 | 실행 gate | PR #8 이후 저장소 전체 gate | 현재 Pending; actual 1/1 증거로 대체하지 않음 | 최종 통합 판단 |
| WEB-MANUAL-A11Y-001 | 인간 검수 | 키보드·screen reader·대비 실기 검수 | Pending | 데모 완료 판정 |

## 5. 설계 결정과 대안

### 선택

- 실제 E2E는 하나의 명시적 opt-in `E2E_ACTUAL=1`과 현재 config의
  `actual-desktop`/`admin-core-loop.actual.spec.ts`를 사용한다.
- reset은 migration replay, seed는 immutable `.2` verifier, login은 provisioner로 단계와 책임을
  분리한다.
- 현재 PASS는 coordinator가 제공한 local actual 실행 결과와 exact aggregate만 기록한다.

### 이유

기본 fixture CI가 실제 backend/DB를 건드리지 않는 경계를 유지하면서, state-changing actual
흐름을 우발적으로 중복 실행하지 않게 한다. 자동 seed를 꺼 둔 정책과 실제 운영 명령을 일치시켜
ACTIVE 19 시작 상태를 재현 가능하게 한다.

### 고려했지만 선택하지 않은 대안

- 제거된 `SEJONG_ACTUAL_LOCAL_E2E`와 수동 `ADMIN_UI_MODE` env 유지: 현재 config의 권위와 달라 제외.
- `db.seed=true`로 reset에 seed 결합: reset 의미와 승인된 불변 release 경계를 바꾸므로 제외.
- actual PASS를 전체 root PASS로 간주: 검사 범위가 다르므로 제외.
- 이 변경에 `allowedDevOrigins`를 함께 추가: 제품 설정 변경이므로 별도 Frontend PR로 분리.

## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| `c15f61b` PR #8 owner integration | Frontend baseline 63 paths와 note ID `009`/`010` 정규화 | 사람이 병합한 PR을 owner 기준선에 통합 |
| `6cd540d` actual 흐름 | actual candidate를 승인된 `KB-WASTE-03` 정본으로 fail-closed, current actual E2E 복구 | fixture→OFFICIAL 승격 회귀 차단 |
| `f22bd00` 접근성·승인 gate | dialog focus/Escape/restore와 승인 checklist 3/3 | 키보드 접근성과 별도 검수 강제 |
| [`admin-core-loop.actual.spec.ts`](../../tools/web-e2e/e2e/admin-core-loop.actual.spec.ts) | 현재 SourceBadge의 문서명과 `원문 보기` 링크를 각각 검증 | 실제 UI의 accessible name과 계약 증거 일치 |
| [`scripts/README.md`](../../scripts/README.md) | `db.seed=false`, reset→`.2` seed-cycle→verify-final→provision 순서와 현재 actual Web 명령 기록 | 잘못된 초기 상태 및 오래된 명령 방지 |
| `apps/web/AGENTS.md`, SOT, TASKS, CHANGELOG, versions, frontend 참고 문서 | PR #8 권위·범위·후속 task·버전 정합성 갱신 | 새 기준선의 단일 해석 유지 |
| `apps/web/.env.example`, `scripts/tests/test_security_boundaries.py` | admin gate는 false로 유지하고 chat/admin mode 기본 actual 계약을 동기화 | PR #8 동작과 root 보안 테스트 drift 제거 |
| 이 구현 노트와 INDEX | PR #8 통합·후속 교정·actual 증거·Pending/승인 경계 기록 | 재현, 검토, 롤백, 인수인계 |

### 데이터 흐름/상태 변화

문서가 설명하는 actual 흐름은 clean reset schema → immutable `.2` ACTIVE 19/office 3/mapping 10
→ local login 회전 → `/ready=200` → 시민 실패 질문 → 후보 작성·별도 승인 → runtime-only
`KB-WASTE-03` ACTIVE 1건 추가 → final ACTIVE 20 → 같은 질문 SUCCESS/공식 출처 확인 순서다.
이 문서 작업 자체는 DB를 실행하거나 변경하지 않았다.

### 오류·빈 상태·롤백

reset, seed-cycle, verify-final, provision, ready 중 하나라도 실패하면 API/E2E를 시작하지 않는다.
actual E2E 실패 artifact는 Git-ignored local 경로에만 두고 질문·PII·secret을 커밋하지 않는다.
final20에서 같은 state-changing spec을 재실행하지 않고 clean19로 복구한다.

## 7. 버전 전후

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Application | `0.7.0-local-synthetic-evaluator` | `0.8.0-pr8-frontend-baseline` | PR #8와 current actual Web 기준선 통합 |
| Web | `0.4.0-chat-admin-local-integration` | `0.5.0-pr8-citizen-admin-baseline` | 시민·관리자 actual UI와 접근성·승인 gate |
| API | `3.1.0-draft` | 동일 | API 변경 없음 |
| DB schema | `0.4.0-local` | 동일 | migration/seed 설정 변경 없음 |
| Official data | `0.1.0-initial.2` | 동일 | immutable `.2` 변경 없음 |
| Mock data | `0.0.0-not-populated` | 동일 | mock 변경 없음 |
| Prompt set | `0.1.0-upstage-solar-pro3-synthetic` | 동일 | provider/prompt 사용 없음 |
| Test suite | `1.4.0-q-pm-actual-evidence` | `1.5.0-pr8-web-baseline` | current fixture·actual·접근성 증거 |
| Docs | `2.15.0` | `2.16.0` | owner 통합·런북·권위 위생·구현 노트 |

## 8. 명령과 테스트 증거

| 명령/검증 | 결과 | 시간/개수 | 증거 경로 |
|---|---|---|---|
| coordinator 제공 current actual browser run | PASS | Playwright `1/1` | `admin-core-loop.actual.spec.ts`; local terminal evidence |
| coordinator 제공 final DB/readiness probe | PASS | ACTIVE `20`, `KB-WASTE-03` `1`, `/ready=200` | local/private aggregate evidence |
| Web unit/lint/typecheck/build | PASS | 11 files·48 tests, lint/type/build exit 0 | local terminal, 2026-07-24 KST |
| fixture Playwright | PASS | 390/430/desktop `18/18` | local terminal, 2026-07-24 KST |
| actual Playwright collection | PASS | canonical actual-desktop spec exactly 1 | local terminal, 2026-07-24 KST |
| first `verify.ps1 -Offline` | FAIL — source test 전 `PREFLIGHT-UV` | worktree PATH에 repo-pin UV 부재 | 기존 root `.tools/uv/uv.exe`를 PATH로 선택, 소스 변경 0 |
| second `verify.ps1 -Offline` | FAIL — `TEST-ROOT` | PR #8 actual mode와 기존 fixture 기대 1건 drift | environment boundary test RED→GREEN |
| environment boundary focused test | PASS | `1/1` | `EnvironmentBoundaryTest.test_web_template_has_only_the_approved_server_assignment` |
| final `verify.ps1 -Offline` | PASS — `verification=complete` | root/data/Web/API/contracts/secret/bundle/package/diff 전체 | local terminal, 2026-07-24 KST |
| `python -B scripts/check_repository_docs.py` | PASS — `repository documentation check passed` | 1 repository docs gate | local terminal, 2026-07-24 KST |
| `git diff --check` | PASS — 출력 없음, exit 0 | current shared-worktree diff | local terminal, 2026-07-24 KST |

### 미실행 검증과 이유

- 자동 접근성·viewport gate는 PASS지만 screen reader·대비 실기 검수는 인간 작업이라 Pending이다.
- Upstage actual, remote DB, public deploy는 승인 범위 밖이며 사용 횟수 0이다.

## 9. 보안·개인정보·접근성·성능 영향

- Privacy: 질문 원문·답변·PII를 문서/DB/log에 새로 기록하지 않았다. actual 질문은 local test
  process 경계를 벗어나지 않아야 한다.
- Security: DSN, secret, local login password를 출력·복사·커밋하지 않는다. `db.seed=false`,
  local loopback, ACTIVE-only, 작성자와 승인자 분리를 유지한다.
- Accessibility: follow-up commit `f22bd00`의 review checkbox/dialog 자동 gate가 현재 baseline이다.
  인간 키보드·screen reader·대비 실기 검수는 Pending이다.
- Performance/cost: 문서 변경이며 runtime 비용 0. provider 호출 0.

## 10. 데이터와 출처 영향

- 공식 데이터: immutable `official_data=0.1.0-initial.2`를 수정하지 않는다.
- mock/AI 생성: 추가·승격 0. actual local workflow의 20번째 KB는 runtime-only이며 `.2` release에
  편입하지 않는다.
- schema/lineage: DB schema와 migration 변경 0. final local evidence는 ACTIVE 20과
  `KB-WASTE-03` 1건이지만 clean 재현 시작점은 `.2`의 19/3/10이다.
- verified date: coordinator actual evidence 기준 2026-07-24 KST.

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- 현재 actual E2E `1/1`, final ACTIVE 20/`KB-WASTE-03` 1, `/ready=200`과 final root gate는
  PASS지만 manual accessibility는 아직 Pending이다.
- `allowedDevOrigins: ["127.0.0.1"]`은 이번 변경이 아니라 별도 Frontend PR에서 검토한다.
- PR #8의 `/admin/login`, `/admin/failures`, `/admin/kb-candidates`는 local/private `/admin`
  내부 view로만 승인된 기준선이며 public route 활성화가 아니다.
- 이 변경을 포함한 Draft PR은 Codex가 자동 merge하지 않는다. owner가 diff·CI·Pending을 확인한
  뒤 명시적으로 병합한다.
- final20 DB에서 state-changing runner/spec을 다시 실행하면 안 된다. disposable reset 뒤
  `.2` clean19부터 재현한다.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- Playwright config가 actual opt-in일 때 worker 1, `actual-desktop`, actual spec만 선택하고 Web
  server의 admin transport를 actual로 주입한다.
- seed verifier CLI는 exact release version만 허용하고 stable content-free PASS/FAIL만 출력한다.
- provisioner는 ignored `.env`의 `DATABASE_URL`만 원자 교체하고 나머지 bytes를 보존한다.

## 13. 인수인계·재현·롤백

### 재현

1. Docker Desktop과 patched loopback Supabase가 local/private로만 준비됐는지 확인한다.
2. admin DSN을 출력하지 않고 process-only env에 두고 `scripts/README.md`의 별도 정식 seed
   `reset → seed-cycle → verify-final → provision`을 수행해 ACTIVE 19/office 3/mapping 10을 확인한다.
3. process-only context secret으로 local API를 시작하고 `/ready=200`을 확인한다.
4. 두 번째 터미널에서 README의 `E2E_ACTUAL=1` 명령을 정확히 한 번 실행한다.
5. final aggregate ACTIVE 20/`KB-WASTE-03` 1과 같은 질문 SUCCESS/공식 출처를 확인하고 서버와
   process env를 정리한다.

### 롤백

- 문서 롤백: 이 README 구간과 구현 노트를 revert하되 결정 이력은 삭제하지 말고 superseding
  note로 교정한다.
- runtime 롤백: disposable local `db reset --local` 뒤 immutable `.2`
  `seed-cycle → verify-final → provision`으로 clean19를 복구한다. `.2` 파일을 수정하지 않는다.
- 제품 code rollback이 필요하면 `f22bd00`, `6cd540d`, `c15f61b`을 역순 검토하되, 사용자 승인과
  별도 rollback 계획 없이 이 문서 작업에서 실행하지 않는다.

### 다음 개발자 시작점

- 먼저 [`scripts/README.md`](../../scripts/README.md)의 actual browser와 seed 경계를 읽는다.
- `allowedDevOrigins` 별도 Frontend PR, final root gate, manual accessibility를 차례로 처리한다.
- Draft PR은 owner review 뒤에만 merge한다.

## 14. 남은 위험·미해결 질문·다음 단계

- screen reader·대비 실기·최종 수동 데모 Pending.
- `allowedDevOrigins: ["127.0.0.1"]` 별도 Frontend PR Pending.
- `/admin/*` 영구 route 구조와 checklist server/audit 승격은 public 준비 전 인간 검토 Pending.
- current shared worktree의 다른 lane 변경과 통합 시 INDEX/version/source-of-truth는 owner lane이
  한 번만 갱신해야 한다.

## 15. 자체 리뷰

- [x] 요청 충족
- [x] 테스트/검증 — actual·fixture Web, docs/diff, final root offline gate PASS
- [x] source-of-truth/계약/버전 동기화 — 계약 불변, owner SOT/manifest/INDEX 동기화
- [x] 개인정보 원문 노출 없음
- [x] 구현 노트 INDEX 갱신 — `IMP-20260724-011` 정확히 1행
