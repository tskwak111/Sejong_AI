# 세종 민원 AI 길잡이 — Codex Ready Repository

이 저장소는 기존 스타터 패키지와 최종 확정 개발 기준을 합쳐, Codex가 **오래된 범위를 정답으로 오인하지 않고**, 발견 → 인터뷰 → 계획 → 구현 → 테스트 → 구현 노트 → 인수인계 순서로 작업하도록 구성한 개발 준비본이다.

## 가장 먼저 할 일

1. 이 폴더를 Git 저장소 루트로 연다.
2. `AGENTS.md`를 확인한다. Codex는 프로젝트 작업 전 `AGENTS.md`를 자동으로 읽는 방식으로 프로젝트 지침을 적용한다.
3. Codex의 첫 메시지로 `CODEX_START_PROMPT.md` 본문을 입력한다.
4. Codex가 저장소 감사를 끝내고 질문할 때까지 큰 코드 변경을 승인하지 않는다.
5. 인터뷰에 답한 뒤 실행계획을 검토하고 `진행`이라고 명시한다.

## 권장 Codex 확인 명령

Codex CLI를 사용한다면 저장소 루트에서 다음처럼 활성 지침을 확인할 수 있다.

```bash
codex --ask-for-approval never "현재 적용 중인 프로젝트 지침 파일과 핵심 규칙을 요약해줘. 코드 변경은 하지 마."
```

Codex 공식 가이드의 핵심 원칙을 반영했다.

- `AGENTS.md`는 저장소의 지속적 프로젝트 지침으로 자동 로드된다.
- 복잡하거나 모호한 작업은 계획과 인터뷰를 먼저 수행한다.
- 테스트·검증·diff 리뷰까지 완료 기준에 포함한다.
- 반복 가능한 절차는 저장소 스킬로 분리할 수 있다.

## 권위 구조

```text
AGENTS.md                       Codex 행동 규칙
CODEX_START_PROMPT.md           첫 세션 발견·인터뷰 프롬프트
docs/00_SOURCE_OF_TRUTH.md      문서 권위와 충돌 해결
docs/source-of-truth/           최종 확정 제품·정책·RFP 기준
docs/adr/                       아키텍처 결정 기록
contracts/                      API·JSON 계약 초안
supabase/migrations/            DB executable timestamp authority
database/                       local baseline 논리 projection·보상·absence proof
docs/implementation-notes/      모든 작업의 재현 가능한 기록
legacy/                         오래된 스타터·문서, 비권위 참고자료
```

## 현재 상태

- 최종 제품과 정책 문서는 확정됨.
- local/private MVP는 final DB의 dedicated Windows application probe에서 `/ready=200`을 확인했고,
  clean governed rehearsal로 19→20 ACTIVE와 `KB-WASTE-03` 재질의 SUCCESS를 확인했다. import-safe
  기본 앱과 public/remote readiness는 별도다. final API 1,640, Web unit 48/lint/type/build/E2E 15,
  contracts 89, clean DB pgTAP 9/356·integration 8/8와 root `verify.ps1 -Offline`이 PASS했다.
  현재 상태는 local/private AI scope complete의 **Review**이며 인간 Draft PR review/merge와 manual
  demo/accessibility가 남았다.
- 독립 local Git과 root workspace 계약은 준비됨: Node 24.12.0, pnpm 11.13.0, Python 3.12.13, uv 0.11.28.
- 개인 GitHub private source remote, Frontend 팀원 전체 수직 흐름 소유, 허용 frontend-only PR
  자가 병합, Codex Cloud Draft-PR-only 운영 명세와
  [COLLAB-001 실행계획](docs/superpowers/plans/2026-07-20-github-codex-cloud-collaboration-transition.md)은
  승인·부분 실행됐다. private `tskwak111/Sejong_AI` bootstrap, matching `main`, hosted policy/Frontend
  CI와 `koregy` write/variable evidence는 검증됐다. PR #1 merge와 post-merge CI, Codex App
  `Only select repositories / Sejong_AI` 사용자 확인도 완료됐다. Task 5는 부분 완료로 teammate
  MFA/recovery와 첫 Task 7 PR-only/no-direct-main-push rehearsal이 남았고, Cloud Draft-PR/manual
  merge와 Frontend onboarding rehearsal도 Pending이다. Q-GIT-004=A로 본인 author
  email의 private collaborator 공개와 기존 history·SHA 보존은 확정됐다.
- root `package.json`은 dependency-free이며 API dependency는 `apps/api/pyproject.toml`·`uv.lock`, Web dependency는 `apps/web/package.json`·root `pnpm-lock.yaml`에 격리됨.
- 역사적 pre-import 기준선에서는 공식/mock DB row 0과 `/ready=503`이 의도한 상태였다. 이는 당시
  검증 기록이며 현재 상태가 아니다. 이후 supported actual seed와 application rehearsal이 local DB
  19→20 ACTIVE 및 `/ready=200`을 별도 증명했다.
- 공유 계약 package는 OpenAPI 3.1.0-draft, standalone JSON Schema·strict Pydantic과 생성 TypeScript의
  drift를 검증한다. optional UUID `Idempotency-Key`는 correlation request ID와 분리한다.
- DB-001 disposable local/private 기준선은 patched Supabase CLI 2.109.1, PostgreSQL 17.6,
  현재 9개 forward/rollback, forced RLS/capability, pgTAP 9 files/356 assertions와 backend
  integration·rollback·absence·reset/replay 증거를 갖췄다. 실행 권위는 `supabase/migrations/`, 논리 projection은
  `database/schema-v1.draft.sql`이다.
- Windows PowerShell 5.1+ root gate와 별도 Docker DB gate가 exact runtime, frozen install,
  Web/API/계약, secret/package/diff, reset/rollback/replay를 검증한다. initial seed actual DB 반영과
  application `/ready` probe는 서로 다른 증거로 관리한다.
- DATA-SEED-002 immutable `0.1.0-initial.2` filesystem release와 byte-identical local dispatcher는
  불변으로 유지된다. observer 수정 뒤 지원 actual cycle이 baseline·identity·forced rollback,
  concurrency A/B, 19/3/10 seed, compensation/replay, final projection과 cleanup을 모두 PASS했다.
  따라서 `official_data=0.1.0-initial.2`이며 final runtime process/container는 0이다. 이 immutable
  19/3/10 seed 증거 자체는 `/ready=200`·20번째 ACTIVE를 뜻하지 않는다. 이 둘은 별도 final local
  application rehearsal에서 PASS했으며, public/remote readiness는 계속 뜻하지 않는다.
- canonical T-01~T-20 deterministic pure-service 평가는 20/20(SUCCESS 10/10, FOLLOWUP 2/2,
  FALLBACK 8/8)이다. provider/remote/public 또는 HTTP source-card QA로 일반화하지 않는다.
- 기존 FastAPI·CSV·정적 HTML 스타터는 `legacy/`에 보존됨.
- `contracts/`의 API spec revision은 3.1.0-draft다. SUCCESS/FOLLOWUP/5개 정책 폴백,
  HTTPS 전용 공식 링크와 local/private admin envelope를 판별 union으로 동결했다. DB executable authority는 timestamp
  migrations이며 `database/`의 `0.4.0-local` projection은 실제 검증된 local 기준선의 읽기용
  투영이다. 공개·원격 DB 기준선이나 production readiness를 뜻하지 않는다.
- Q-LLM-005=A로 외부 합성 평가 공급자는 Upstage exact `solar-pro3`다. 구현·actual call 전
  명세/계획 승인이 필요하며, 실제 시민·공개 경로는 계속 deterministic disabled/template provider다.
- 권장 배포는 Vercel + Render + Supabase이며 실제 계정·리전·비밀값은 별도 확인이 필요함.
- Q-SEC-003=A/D-046으로 exact privileged function 22 signatures의 property-only `00700`
  hardening 방향은 확정됐지만 public 준비까지 구현을 보류했다. 그전에는 local/private 전용이며
  remote/public 배포, public admin/API, public backend DB credential 사용을 금지한다.

## GitHub·Cloud 협업 준비

- 상세 권한·병합·비밀 경계:
  [승인된 협업 설계](docs/superpowers/specs/2026-07-20-github-codex-cloud-collaboration-design.md)
- Frontend 담당자 시작점:
  [Frontend collaborator handoff](docs/handoffs/HANDOFF-20260720-FRONTEND-COLLABORATOR.md)
- 원격 생성·CI·Codex 연결 순서:
  [COLLAB-001 실행계획](docs/superpowers/plans/2026-07-20-github-codex-cloud-collaboration-transition.md)

private GitHub source remote는 public Web/API나 remote DB 배포가 아니다. Cloud에는 LLM API key,
DB DSN과 context secret을 넣지 않고 Codex는 branch와 Draft PR까지만 만든다. Docker/Supabase와
Upstage 합성 actual 검증은 계속 local-only다.

## 개발 런타임 계약

```text
Node       24.12.0      .node-version
pnpm       11.13.0      package.json#packageManager
Python     3.12.13      .python-version
uv         0.11.28      uv.toml#required-version
```

`pnpm-workspace.yaml`은 `apps/*`와 `packages/*`만 활성 workspace로 포함한다. `uv.toml`은 지원되지 않는 uv 버전의 실행을 즉시 거부한다. `.tools/`, `.worktrees/`, `.superpowers/`, dependency/build cache는 Git에 넣지 않는다. root 계약은 `python -B -m unittest scripts.tests.test_repository_scaffold -v`, Web은 `corepack pnpm install --frozen-lockfile --ignore-scripts` 후 `test`·`typecheck`·`lint`·`build` script로 검증한다. 공유 계약은 `corepack.cmd pnpm --filter @sejong-ai/shared-contracts test`로 검증한다.

## 단일 로컬 검증

저장소 루트에서 다음 명령을 실행한다.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/verify.ps1
```

기본 검증을 한 번 통과해 dependency cache가 준비된 뒤에는 warm-cache 오프라인 재현도 확인할 수 있다.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/verify.ps1 -Offline
```

`-Offline`은 미리 받은 cache의 재사용 가능성을 검증하며 빈 PC의 최초 설치를 대신하지 않는다. 러너는 파일을 삭제하거나 서버를 띄우지 않고, 실패 시 하위 명령의 내용 대신 stable step ID와 종료코드만 표시한다. 실제 `/health`·`/ready` HTTP smoke는 서버를 명시적으로 실행하는 별도 검증이다.

Docker Desktop이 실행 중일 때 DB 기준선은 별도 gate로 검증한다.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/bootstrap_patched_supabase.ps1 -VerifyOnly
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/verify_database.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/verify_database.ps1 -SkipStart
```

이 gate의 reset/compensation은 disposable local DB 전용이다. remote project, 실제 데이터,
Docker volume에는 실행하지 않는다.

Q-SEC-004/005의 Docker 전역 보정만으로는 IPv6 wildcard가 남았으므로, D-031/D-032의 tracked
source/runtime manifest와 project-local patched binary를 DB 실행 권위로 사용한다. 2026-07-18
역사적 gate에서 actual binding이 정확히 하나의 `127.0.0.1:54322`였고 당시 pgTAP 8 files/320, backend integration,
역순 보상·absence·reset/replay, final container/process 0이 모두 PASS했다. runner는 여전히 actual
binding을 reset 전에 검사하며 stock/PATH fallback과 `db diff`를 허용하지 않는다. current source gate는
9 forward/rollback·pgTAP 9 files/356 assertions이며, 이후 official `.2` seed 19/3/10과 별도 application
rehearsal의 `/ready=200`·20번째 ACTIVE까지 local actual로 PASS했다.
D-046의 deferred `00700` 구현·검증 전까지 public/remote는 차단된다. [Docker port publishing](https://docs.docker.com/engine/network/port-publishing/), [Supabase local development](https://supabase.com/docs/guides/local-development/)

`73f300b`는 DB child를 bounded process tree로 실행·종료·dispose하도록 보정했다. focused 1/1,
runner 50/50, patched 24/24와 독립 review 0/0/0 뒤 final-code DB gate도 102.746s에 PASS했고 exact
loopback·stop·container 0/0·volume/prune 0을 재확인했다.

다른 현재 디렉터리에서 실행할 때는 `-File`에 이 저장소의 `scripts/verify.ps1` 절대 경로를 전달한다. 러너는 호출된 파일 위치를 기준으로 저장소 루트를 찾는다.

## 개발 시 절대 혼동하지 말 것

기존 업로드 패키지에는 다음 오래된 범위가 남아 있었다.

- 10개 이상 민원 분야
- 100개 테스트
- mock 신청 상태 조회
- 다국어·음성
- 급증 분석·자동 추천·주간 리포트
- 가상 기관 주소와 전화번호

현재 확정 범위는 4개 분야, 20개 표본, 회귀 테스트 1개, 관리자 승인형 개선 루프이다. 자세한 차이는 `docs/02_CURRENT_REPO_AUDIT.md`를 참조한다.

## 구현 노트 생성

```bash
python scripts/new_implementation_note.py --title "초기 저장소 감사" --task-id DISC-001 --type discovery
```

생성된 노트는 `docs/implementation-notes/`와 `INDEX.md`에 반영된다.

## 패키지 구성

- `apps/`: 신규 활성 애플리케이션 위치
- `packages/`: 프론트·백엔드 공용 계약/타입 위치
- `contracts/`: OpenAPI·JSON Schema
- `supabase/migrations/`: DB 실행 권위와 `supabase/tests/database/` pgTAP
- `database/`: 논리 projection·역순 disposable-local compensation·absence proof
- `data/`: 공식·평가·mock 데이터의 활성 위치
- `docs/`: 권위 문서, ADR, 구현 노트, 계획, 테스트, 인수인계
- `scripts/`: 노트 생성·상태 캡처·드리프트 검사
- `legacy/`: 사용자가 업로드한 이전 스타터 전체

## 제출 전 사용자 직접 입력 항목

- 팀명
- 팀원과 역할
- 대표 연락처
- 제출일
- 실제 배포 계정·URL·비밀값
