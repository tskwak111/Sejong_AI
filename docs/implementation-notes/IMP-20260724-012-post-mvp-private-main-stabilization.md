# IMP-20260724-012 — POST MVP private main stabilization

- Date/Time (KST): 2026-07-24T22:18:36+09:00
- Task ID: POST-MVP-001
- Type: implementation/platform
- Status: Review — 검증·독립 리뷰 완료, owner Draft PR 게시 전
- Author/Agent: 사용자(owner 결정) / Codex(설계·구현·검증)
- Branch: `codex/POST-MVP-001-main-stabilization`
- Base commit: `4cc2f4e5e478668e1d7216fddc08874c9285274b`
- Related plan/ADR/RFP:
  [설계](../superpowers/specs/2026-07-24-post-mvp-main-stabilization-design.md),
  [실행계획](../superpowers/plans/2026-07-24-post-mvp-main-stabilization.md),
  D-069/D-070, WEB-DEV-ORIGIN-001

## 1. 사용자 요청과 완료 기준

### 요청

평가용 public snapshot 작업을 마친 뒤 private `tskwak111/Sejong_AI` 개발을 재개한다. 우선
팀원 PR #10의 local dev-origin 수정을 owner가 인계하고, 제품명·병합 상태 같은 활성 정본
드리프트를 정리한 뒤 commit·push·Draft PR까지 진행한다.

### Acceptance Criteria

- 최신 private `origin/main`에서 격리된 owner branch를 사용한다.
- `allowedDevOrigins`는 exact `127.0.0.1` 한 항목이고 public CORS로 확대하지 않는다.
- 회귀 테스트는 현재 main에서 RED, 최소 설정 뒤 GREEN을 증명한다.
- Web unit/lint/typecheck/build와 실제 Next dev-origin browser gate를 통과한다.
- 공식 서비스명 `세종 민원이음`, PR #9 merge, PR #10 owner 경계를 활성 정본에 반영한다.
- DB/API/contract/official data/dependency/public 평가 저장소는 변경하지 않는다.
- 비밀·개인정보를 출력하거나 커밋하지 않고 Draft PR까지만 게시한다.

## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 사용자가 선택지 A와 제품명을 승인하고 Codex가 owner 구현·검증·게시를 수행 |
| When — 언제 | 2026-07-24 KST, PR #9 merge와 평가 snapshot 제출 뒤 |
| Where — 어디서 | private `Sejong_AI`, 격리 worktree, `apps/web`, 활성 source-of-truth와 task/version 문서 |
| What — 무엇을 | local Next dev-origin 회귀, owner 인계, 서비스명·PR 상태 정합성 |
| Why — 왜 | 팀원 config 변경이 의도된 owner 경계에서 CI 실패했고 활성 문서가 실제 결정·Git 상태보다 뒤처졌기 때문 |
| How — 어떻게 | 최신 main 기준선→설계/계획→RED/GREEN→dev browser→문서/보안 gate→owner Draft PR |
| How much — 어느 정도 | production config 1개, unit 1개, E2E spec/config 2개, 활성 문서·계획·노트·version만 변경; DB/데이터/provider 호출 0 |

## 3. 시작 전 상태

- Git: local root `main`은 clean이지만 `origin/main`보다 56 commits 뒤였다. 새 worktree는
  `4cc2f4e`에서 생성했다.
- PR #10: `apps/web/next.config.ts` 1개 파일, Frontend CI PASS. 작성자 `koregy`가 owner-reviewed
  config path를 변경해 Collaboration policy만 FAIL했다.
- Web 기준선: 11 files/48 tests, lint, typecheck PASS.
- 활성 문서: 서비스명은 옛 작업명, MVP-001은 이미 병합된 Draft PR #9를 open으로 표시했다.
- seed: `[db.seed].enabled=false`와 별도
  `seed-cycle → verify-final → provision_local_database_login` 순서는 정본과 런북이 일치했다.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| A-046 | 인간 결정 | 공식 서비스명 | `세종 민원이음` / D-069 | 활성 제품 문서만 교정 |
| A-047 | 인간 결정 | 팀원 config PR 처리 | owner branch 인계 / D-070 | 협업 allowlist 불변 |
| DEV-ORIGIN-D1 | 내부 진단 | Windows `localhost` 바인딩 | `::1`임을 직접 확인하고 wildcard 없이 cross-origin resource probe 사용 | 재현 가능한 E2E harness |

추가 A/Blocker는 없다. public CORS, remote deploy, actual citizen provider는 이 작업에서 승인되지
않았다.

## 5. 설계 결정과 대안

### 선택

owner가 PR #10의 exact 설정을 별도 branch에서 TDD로 인계한다. 팀원 허용 경로를 넓히지 않고
public 평가 snapshot도 수정하지 않는다.

### 이유

`next.config.ts`는 proxy·빌드·보안 동작을 바꿀 수 있어 owner-reviewed 경계가 합리적이다.
Next.js 16 공식 문서는 `allowedDevOrigins`가 개발 내부 자원/HMR의 추가 host allowlist이며
`"127.0.0.1"` host-only 값이 유효함을 확인한다.

### 고려했지만 선택하지 않은 대안

- 팀원 config 권한 확대: 한 줄 수정을 위해 보안 경계를 넓히므로 기각.
- 빨간 PR #10 직접 병합: 협업 감사 정책을 무력화하므로 기각.
- wildcard/LAN origin: local-only와 최소 권한을 깨므로 기각.
- E2E dev server를 `0.0.0.0`으로 bind: 일시적이라도 LAN listener를 만들므로 기각.

## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| `apps/web/next.config.ts` | exact `allowedDevOrigins: ["127.0.0.1"]` | 개발 자원/HMR loopback 허용 |
| `apps/web/src/lib/next-config.test.ts` | 실제 config exact allowlist 회귀 | 설정 누락·확대 방지 |
| `tools/web-e2e/playwright.dev-origin.config.ts` | localhost dev server 전용 집중 config | production server 테스트와 분리 |
| `tools/web-e2e/e2e/dev-origin.spec.ts` | hydration과 127 Referer Next resource 200 | 실제 개발 경계 검증 |
| `AGENTS.md`, `README.md`, `CHANGELOG.md`, start prompt, API README | 활성 서비스명·변경 이력 동기화 | D-069 반영 |
| `docs/source-of-truth/*`, context, guide, active Frontend handoff, versioning guide | 서비스명·PR #9·owner config 경계·current manifest 동기화 | 활성 권위 일치 |
| `TASKS.md`, ambiguity/decision log | PR #9 merge·A-046/A-047·D-069/D-070 | 현재 상태와 결정 추적 |
| `versions/manifest.json` | product/Web/test/docs 축 갱신 | 버전 계보 |
| 설계·계획·본 노트·INDEX | 승인·명령·검증·롤백 기록 | 재현·인수인계 |

### 데이터 흐름/상태 변화

개발 브라우저의 `127.0.0.1` origin이 Next dev server의 `/_next` 자원과 HMR에 접근할 수 있다.
시민 질문, API 요청, DB 상태, official source 결합과 production 동작은 바뀌지 않는다.

### 오류·빈 상태·롤백

첫 Playwright harness는 Windows `localhost → ::1` 바인딩 때문에 IPv4 readiness를 기다리다
120초 timeout됐다. 직접 dev server는 538ms에 Ready였고 `::1:3002`, localhost HTTP 200,
127 HTTP 연결 실패를 확인했다. test harness만 localhost readiness+127 cross-site resource
probe로 교정했으며 제품 설정에는 추가 보정을 하지 않았다.

## 7. 버전 전후

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Product spec | 2.4.0 | 2.4.1 | 공식 서비스명 동기화 |
| Repo guidance | 1.7.7 | 1.7.8 | owner config 경계·활성 안내 |
| Application | 0.8.0-pr8-frontend-baseline | 0.8.1-main-stabilization | post-MVP main 안정화 |
| Web | 0.5.0-pr8-citizen-admin-baseline | 0.5.1-local-dev-origin | local dev-origin |
| API | 3.1.0-draft | unchanged | 공개 계약 불변 |
| Shared contracts | 0.4.0 | unchanged | 생성 계약 불변 |
| DB schema | 0.4.0-local | unchanged | migration 0 |
| Official data | 0.1.0-initial.2 | unchanged | seed/data 0 |
| Mock data | 0.0.0-not-populated | unchanged | mock 0 |
| Prompt set | 0.1.0-upstage-solar-pro3-synthetic | unchanged | provider/prompt 0 |
| Test suite | 1.5.0-pr8-web-baseline | 1.5.1-local-dev-origin | unit+dev browser 회귀 |
| Docs | 2.16.0 | 2.17.0 | 결정·설계·계획·노트 정합 |

## 8. 명령과 테스트 증거

| 명령/검증 | 결과 | 시간/개수 | 증거 경로 |
|---|---|---|---|
| offline `pnpm install --frozen-lockfile --ignore-scripts` | PASS | 465 packages, network 0 | local stdout |
| 변경 전 Web test/lint/typecheck | PASS | 48 tests | local stdout |
| config RED | expected FAIL | `undefined` vs `["127.0.0.1"]`, 1 failed | `next-config.test.ts` |
| config GREEN | PASS | 1/1 | `next-config.test.ts` |
| Web full test/lint/typecheck/build | PASS | 49/49, 12 files; build 7 routes | local stdout |
| 첫 dev-origin Playwright harness | expected diagnostic FAIL | 120s readiness timeout | 본 노트 §6 |
| direct dev server/network probe | root cause confirmed | Ready 538ms; `::1`; localhost 200; 127 connect fail | 본 노트 §6 |
| corrected dev-origin Playwright | PASS | 1/1, 21.1s | `dev-origin.spec.ts` |
| repository docs | PASS | active links/JSON | `scripts/check_repository_docs.py` |
| secret patterns | PASS | tracked secret match 0 | `scripts/check_secret_patterns.ps1` |
| 독립 정본 리뷰 | CLEAN after fixes | MVP 상태 2곳, version current block, active handoff 제품명 보정 후 Critical/Important 0 | 본 노트 및 변경 diff |

### 미실행 검증과 이유

- DB/API/root full regression: production behavior, public contract, dependency, DB/data를 변경하지
  않은 config/docs slice다. Web 영역 전체와 repository static gates를 실행한다.
- 실제 Upstage call: LLM-002 Task 7의 별도 local human gate이며 이 PR에서 key/network 호출 0.
- remote/public deploy: 승인되지 않았다.

## 9. 보안·개인정보·접근성·성능 영향

- Privacy: 질문·답변·PII·IP·기기 ID를 읽거나 저장하지 않았다.
- Security: wildcard/LAN/public CORS를 추가하지 않았다. exact loopback host만 개발 자원에 허용하고
  팀원 config 권한도 확대하지 않았다. secret scanner를 통과해야 게시한다.
- Accessibility: 기존 UI를 변경하지 않았다. browser hydration을 확인해 client 상태 동작을
  보존했다.
- Performance/cost: production runtime 영향 0. 새 dependency·provider call·비용 0.

## 10. 데이터와 출처 영향

- 공식 데이터: immutable `.2`, ACTIVE 19→20 증거와 source metadata 모두 불변.
- mock/AI 생성: 변경·호출 0.
- schema/lineage: DB/API/shared contract/migration/lineage 변경 0.
- verified date: Next.js 16.2 공식 `allowedDevOrigins` 문서를 2026-07-24 확인.

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- owner Draft PR은 사용자가 검토·병합해야 하며 Codex는 자동 merge하지 않는다.
- PR #10은 코드가 아니라 소유 경계 때문에 실패했다. owner PR 병합 후 사람이 close하면 된다.
- 이 설정은 public CORS나 배포 승인이 아니다.
- 다음 human gate는 LLM-002 Task 7의 ignored local Upstage key 입력과 PM 10결과 채점이다.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- unit test는 Next config object를 직접 import해 exact array를 비교한다.
- Windows의 `localhost` IPv6 바인딩을 감안해 E2E는 localhost에서 hydration을 확인하고
  127 Referer의 cross-site `/_next` request가 200인지 별도 probe한다.
- build의 linked-worktree workspace-root 경고는 기존 root 탐지 특성이며 build는 성공했다.

## 13. 인수인계·재현·롤백

### 재현

```powershell
corepack pnpm --filter @sejong-ai/web test
corepack pnpm --filter @sejong-ai/web lint
corepack pnpm --filter @sejong-ai/web typecheck
corepack pnpm --filter @sejong-ai/web build
Set-Location tools/web-e2e
corepack pnpm --filter @sejong-ai/web-e2e exec playwright test --config playwright.dev-origin.config.ts
```

### 롤백

owner PR을 merge하지 않거나 해당 commit을 revert한다. DB migration/data restore/secret rotation은
필요 없다. config 한 줄 제거 시 기존 local dev-origin 동작으로 돌아간다.

### 다음 개발자 시작점

private `origin/main`과 owner Draft PR을 비교하고 CI를 확인한다. merge 뒤 PR #10을 사람이
close한 다음 `docs/superpowers/plans/2026-07-23-upstage-solar-pro3-synthetic-evaluation.md`
Task 7 preflight에서 재개한다.

## 14. 남은 위험·미해결 질문·다음 단계

- owner Draft PR human merge Pending.
- 팀원 계정 MFA/recovery 확인 Pending.
- LLM-002 actual synthetic evaluation/PM scoring Pending.
- manual a11y, performance 100-user smoke, backup/recovery와 public 준비는 후속 P1/P2 gate.

## 15. 자체 리뷰

- [x] 요청 충족
- [x] 테스트/검증
- [x] source-of-truth/계약/버전 동기화
- [x] 개인정보 원문 노출 없음
- [x] 구현 노트 INDEX 갱신
