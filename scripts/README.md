# Scripts

```bash
python scripts/new_implementation_note.py --title "제목" --task-id TASK-001 --type feature
python scripts/capture_repo_state.py
python scripts/check_scope_drift.py
python scripts/validate_codex_package.py
python -B scripts/validate_data_staging.py prepare --draft-dir data/staging/data-001/0.1.0-draft.1 --submitted-at 2026-07-18T18:00:00+09:00
python -B scripts/validate_data_staging.py migrate-pending --draft-dir data/staging/data-001/0.1.0-draft.1 --submitted-at 2026-07-18T21:15:00+09:00
python -B scripts/validate_data_staging.py validate --draft-dir data/staging/data-001/0.1.0-draft.1 --report data/processed/data-001/0.1.0-draft.1/validation-report.json
```

위 Python 유틸리티와 `scripts/tests/`의 저장소 경계 검사는 Python 표준 라이브러리만 사용한다.

## Upstage 합성 평가 runner

```powershell
python -B scripts/run_upstage_synthetic_evaluation.py
python -B scripts/run_upstage_synthetic_evaluation.py --review
```

이 runner는 local/private 환경의 exact Upstage `solar-pro3` 설정과 canonical
`data/evaluation/sample_questions_20.csv`의 `T-01`~`T-10`만 사용한다. local DB readiness가
PASS한 뒤에만 client/provider를 만들며, 모델·URL·key·fixture·출력 경로·cap·질문은 CLI로 받을 수
없다. `--review`는 stdin/stdout이 모두 TTY인 경우에만 첫 valid 합성 결과 10건을 메모리에서
검수하고 1~5점과 closed reason code만 받는다.

본문 없는 aggregate JSON은 고정 ignored 경로
`artifacts/llm-002/upstage-synthetic-evaluation.json`에 원자적으로 기록된다. 정상 종료는
`LLM_EVALUATION_COMPLETE`, 고정 `REPORT`, `OVERALL_PASS` 세 줄만 출력한다. 설정/인수/TTY 오류는
exit `2`, local DB/readiness 오류는 exit `3`, 실행·무결성 오류는 exit `4`이며 오류 상세·key·DSN·
질문·답변은 출력하지 않는다. 이 도구는 실제 시민/free-input/public/remote provider 연결을
활성화하지 않는다.

## Q-PM local actual 개선 루프 runner

```powershell
python -B scripts/verify_actual_mvp_regression.py
```

이 runner는 **state-changing local/private 전용**이다. 인수를 받지 않으며 clean reset과 immutable
`.2` seed로 ACTIVE 19를 확인하고 local login과 process-only `CONTEXT_TOKEN_SECRET`,
`SEJONG_ADMIN_DATABASE_URL`을 준비한 뒤 정확히 한 번 실행한다. 성공 뒤 DB는 ACTIVE 20이므로
같은 상태에서 재실행하지 말고 disposable local DB를 다시 reset+seed한다. 실패는
`ACTUAL_MVP_REGRESSION_FAILED` 한 줄과 nonzero exit만 내며 질문·UUID·DSN·secret·provider
payload를 출력하지 않는다.

정상 성공 stdout은 아래 고정 15줄이다.

```text
PASS ready
PASS initial-active count=19
PASS personal-lookup persistence event_delta=0 failed_delta=0
PASS initial-fallback
PASS business-replay
PASS insufficient-grounding event_delta=1 failed_delta=1
PASS failed-new count=1
PASS reason-confirmed
PASS candidate-created
PASS candidate-submitted
PASS self-approval-blocked
PASS candidate-approved
PASS improved-requery public_id=KB-WASTE-03
PASS old-replay
PASS final-active total=20 categories=4 count_each=5
```

첫 delta는 `interaction_events`와 `failed_questions` 두 table에만 대한 무변화 증거다. 별도 근거
부족 질문은 두 count를 정확히 1씩 늘린다. candidate `activated_kb_id`는 내부 UUID이며 public
`KB-WASTE-03`은 최종 chat source에서 증명한다. 이 runner는 Upstage key/network/provider,
remote DB, Docker 외부 노출, public admin·배포를 사용하거나 승인하지 않는다.

### Opt-in actual desktop browser

backend runner가 성공한 DB는 이미 ACTIVE 20이므로, browser evidence 전에 다시 disposable reset과
immutable `.2` seed로 clean ACTIVE 19를 만든다. 첫 터미널에서 실제 secret을 출력하지 않고 local
API를 시작한다.

```powershell
$bytes = New-Object byte[] 48
$rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
[Environment]::SetEnvironmentVariable(
  "CONTEXT_TOKEN_SECRET",
  [Convert]::ToBase64String($bytes),
  "Process"
)
apps/api/.venv/Scripts/python.exe -B scripts/run_local_api.py --port 8000
```

`/ready=200`을 확인한 뒤 두 번째 터미널의 저장소 루트에서 actual Web env와 state-changing desktop
spec을 정확히 한 번 실행한다. Playwright config가 `ADMIN_UI_ENABLED=true`를 Web server에도
전달하지만 재현 경계를 명시하기 위해 process env에도 설정한다.

```powershell
$env:ADMIN_UI_ENABLED = "true"
$env:ADMIN_UI_MODE = "actual"
$env:API_INTERNAL_BASE_URL = "http://127.0.0.1:8000"
$env:SEJONG_ACTUAL_LOCAL_E2E = "true"
$env:CI = "true"
corepack pnpm --filter @sejong-ai/web build
corepack pnpm --filter @sejong-ai/web-e2e test -- `
  --project=desktop e2e/actual-local-core-loop.spec.ts
```

PASS 뒤 DB는 final ACTIVE 20이다. 첫 터미널의 API를 `Ctrl+C`로 종료하고 두 터미널의 위 process
env를 제거한다. 실제 질문·PII·provider key를 넣지 않으며, 실패 trace/screenshot은 local
Git-ignored test artifact로만 취급한다. 다시 실행하려면 반드시 clean19부터 복구한다.

## 협업 전환 검사기

### 전체 reachable Git history 비밀 검사

`scripts/check_git_history_secrets.py`는 별도 local 구현·review를 마쳤으며 최종 integration commit에
포함된 뒤 최초 push gate로 사용한다. 모든 reachable ref의 commit/tree/tag/blob을 raw byte로 읽고
일치값 대신 JSON Lines의 `category`, `commit`, `blob`, `path`만 출력한다.

```powershell
python -B scripts/check_git_history_secrets.py --repo .
python -B scripts/check_git_history_secrets.py --repo . `
  --local-secret-file apps/api/.env --local-secret-name DEEPSEEK_API_KEY
```

두 local-secret 옵션은 함께만 사용할 수 있다. 파일은 repository 안의 ignored regular file이어야
하며 1 MiB 이하이고, 지정한 정확한 assignment 값은 process memory에서만 비교한다. Git argv/env,
임시 파일, finding 출력에는 전달하지 않는다. 종료코드는 clean `0`, finding `1`, 입력·Git·한도·
읽기 등 operational failure `2`다. operational failure도 값 없는
`SCANNER_OPERATIONAL_ERROR` JSON record 하나로 fail closed한다.

고정 자원 한도는 reachable object 100,000개, object당 16 MiB, object 합계 256 MiB, Git 명령
출력당 64 MiB, unique tree 20,000개, tree entry 1,000,000개, path 4,096 bytes, path 합계
128 MiB, Git 명령당 60초다. 한도를 넘으면 일부 결과를 PASS로 해석하지 않고 exit 2다. GitHub/
provider token, private-key header, credential DB URL, JWT-like token, actual-question sentinel과 선택적
local secret exact value를 찾지만 변형·분할·암호화·난독화된 값의 부재를 보장하지 않는다.

### PR author·path scope 분류와 구현 노트 append 검증

```powershell
python -B scripts/check_collaboration_scope.py `
  --base-sha <full-40-or-64-hex-commit-sha> `
  --head-sha <full-40-or-64-hex-commit-sha> `
  --pr-author <github-login> `
  --frontend-login <github-login>
```

출력은 file content 없이 JSON 한 줄의 `classification`, change/path count, JSON-escaped path 목록이다.
정상 분류는 `FRONTEND_SELF_MERGE_ELIGIBLE` 또는 `OWNER_REVIEW_REQUIRED`이며 둘 다 exit `0`이다.
SHA/login 누락·형식 오류, commit 미존재, Git/diff failure는 path/content 없이
`OPERATIONAL_ERROR`와 빈 count/path를 출력하고 exit `2`다. 입력 SHA는 full commit object만 받고
`git diff --name-status -z <base> <head> --`만 분류한다.

자가 병합 allowlist는 `apps/web/src/**`, `tools/web-e2e/e2e/**`와 선택적으로 정확히 한 개의 신규
`docs/implementation-notes/IMP-YYYYMMDD-NNN-web-*.md` + 기존 INDEX 마지막 한 행 append다. delete,
allowlist 밖 rename, `.github`, API/contract/generated type, DB/migration, official/staging data,
ADR/policy, env/example, README, package metadata·lockfile는 owner review다. PR author가 설정된 Frontend
login과 다르거나 변경이 비어 있어도 owner review다.

`scripts/check_collaboration_note_append.py`는 standalone CLI가 아니라 scope classifier가 import하는
scope-bounded interface다. `validate_note_and_index_append(base_sha, head_sha, note_path) -> bool`은 두 파일만
대상으로 `--no-ext-diff --no-textconv --no-color` unified diff를 읽어 신규 web note 전체가 add-only이고
INDEX의 기존 전체 내용이 context로 보존된 채 일치하는 행 하나만 마지막에 추가됐는지 검사한다.
diff는 최대 1,000,000 context lines를 요청한다. standalone exit code는 없으며 형식 위반은 `False`라서
owner review, Git operational failure는 scope classifier exit `2`가 된다.

### tracked active Markdown·JSON 검사

```powershell
python -B scripts/check_repository_docs.py
python -B scripts/check_repository_docs.py --repository-root <candidate-repository-root>
```

`--repository`는 `--repository-root`의 alias다. 검사기는 지정 Git worktree의 index에서 active tracked
regular blob만 읽고 Markdown의 repository-local target과 strict JSON을 검증한다. candidate mode는
신뢰한 base의 스크립트를 실행하면서 PR head가 checkout된 별도 repository root를 지정하는 CI
interface다. symlink/gitlink/staged conflict 같은 지원하지 않는 tracked entry는 읽지 않고 fail closed한다.
단일 active blob 2 MiB, active Markdown/JSON blob 합계 32 MiB, cat-file header 256 bytes가 한도다.
성공은 exit `0`, missing target·invalid JSON·Git/read/limit operational failure는 exit `1`이며 오류는
escaped source path와 line/ordinal 또는 stable code만 포함하고 target/content 값은 출력하지 않는다.

## 단일 로컬 검증 gate

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/verify.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/verify.ps1 -Offline
```

러너는 Windows PowerShell 5.1+, Node 24.12.0, pnpm 11.13.0, uv 0.11.28과 API venv Python 3.12.13을 먼저 확인한다. 이어 frozen pnpm/uv sync, root tests, 필수 DATA-001 canonical marker/schema/staging validator, Web lint/typecheck/test/synthetic-secret build, API format/lint/mypy/pytest, 계약 생성·diff·test, 두 secret scanner, package validator와 `git diff --check`를 fail-fast로 실행한다. canonical marker/schema/staging 중 하나라도 없으면 `VALIDATE-DATA-001`은 skip하지 않고 실패한다. `TEST-ROOT`은 하위 프로세스 정리 회귀를 포함해 조용한 시간이 길 수 있으므로, 2026-07-18 Remediation 3의 direct 171-test discovery(511.715s)와 fresh full gate PASS 이전에 조기 종료했던 기록을 정지 결함으로 해석하지 않는다.

## DATA-001 staging validation

`prepare`는 세 content JSON의 count와 SHA-256, AI 권고를 묶은 `PENDING_PM_REVIEW` manifest를 최초 한 번만 원자적으로 쓴다. 동일 bytes의 미검수 PENDING 재실행만 무쓰기 성공하며, 다른 PENDING 또는 PM 결정·comment·reviewer metadata가 있는 manifest는 덮어쓰지 않는다. `migrate-pending`은 과거 AI 권고가 `decision`에 있던 정확한 canonical legacy PENDING bytes만 새 `recommended_decision`/null PM 결정 shape로 한 번 전환한다. UTF-8(BOM 없음), LF, 2-space indent, sorted keys, trailing LF를 포함해 값·타입·key/array 순서·공백·중복 member가 하나라도 다르면 쓰기 전에 거부한다. 세 production 명령은 exact canonical draft와 registry만 받으며 경로 구성요소·artifact·schema·승인 매트릭스·네 source audit의 symlink/junction/reparse를 읽기 전에 거부한다. 상대 draft·registry·report 인수는 현재 작업 디렉터리가 아니라 저장소 root를 기준으로 해석하고, 검증 뒤 실제 read/write에는 resolved canonical 절대 경로만 전달한다. `approved-source-matrix.json`은 독립 validator code SHA-256 pin을 먼저 통과한 뒤 content/registry/공식 출처/기관 공개 연락처/매핑 권고와 tracked source-audit hash를 exact 비교한다. `validate --report`는 정확히 `data/processed/data-001/0.1.0-draft.1/validation-report.json`만 쓸 수 있다. tracked runtime 검사는 기존 실행 트리 외에도 `ops`, `operations`, `config`, `.config`, `deploy`, `deployment`, `infra`, `infrastructure` 아래 PowerShell/JSON/TOML/YAML 설정을 포함하되 `docs/`와 `data/` 산출물은 제외한다. `validate`는 PENDING·APPROVED·REJECTED 상태를 상태별로 검사하고 staging을 변경하지 않는다. 유효한 PENDING은 AI의 `recommendation_projection`과 `PM_REVIEW_REQUIRED` 경고만, 유효한 APPROVED는 PM의 `approval_projection`만 report에 제공하며, REJECTED 또는 validation issue가 있는 제출물의 두 projection은 `null`이고 PM 검수 준비 경고도 없다. manifest·registry·content의 원문·출처 값·PII/비밀값을 report나 CLI 출력에 복사하지 않는다. 성공 출력은 `[PASS] step=VALIDATE-DATA-001`이고, validation failure는 stable issue-code count만 출력하며 1로 종료한다. 사용법 오류는 2로 종료한다.

공개 옵션은 `-Offline` 하나뿐이다. 오프라인 모드는 warm cache를 요구하며 pnpm/uv offline을 강제한다. 성공·실패 하위 명령의 원문 출력은 비밀·경로 유출을 막기 위해 전달하지 않고 stable step ID만 표시한다. child 실패는 해당 종료코드를 보존하고, 버전·실행·복원 같은 운영 오류는 2를 반환한다. 러너 자체는 삭제와 서버 실행을 하지 않는다.

## 프로젝트 로컬 Supabase CLI

```powershell
# Stock reference only
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/bootstrap_supabase.ps1 -VerifyOnly

# Patched build/runtime authority
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/bootstrap_patched_supabase.ps1 -BuildCandidate
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/bootstrap_patched_supabase.ps1 -Install
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/bootstrap_patched_supabase.ps1 -VerifyOnly
```

stock `-VerifyOnly`는 기존 공식 Windows amd64 release 설치물을 참조용으로만 확인한다.
데이터베이스 runner의 실행 권위는 official v2.109.1 exact source의 local DB start
HostIP만 보정한 `.tools/supabase/v2.109.1-sejong-loopback/supabase.exe`다. patched
bootstrap은 고정 source/tag/commit·Go archive·patch·runtime manifest를 검증하고, 두 독립
build의 SHA-256 일치를 거쳐 설치한다.

이 CLI는 로컬 개발 도구이며 production dependency가 아니다. 스크립트는 Supabase `login`,
`link`, `db push` 또는 다른 remote project operation을 수행하지 않는다.
stock CLI의 직접 `db start`, PATH fallback과 `db diff` shadow DB는 승인된 안전 경로 밖이다.

## 로컬 PostgreSQL gate

Supabase v2.109.1이 생성한 프로젝트는 DB-001에 필요한 로컬 PostgreSQL 경로만 실행한다.
Data API, Auth, Realtime, Storage, Studio, Local SMTP/Mailpit, Analytics, Edge Runtime과 DB pooler는
비활성화했다. DATA-001의 PM 승인 전까지 seed는 의도적으로 비어 있다.

DB-001의 6개 version migration/compensation과 6개 pgTAP suite가 존재하며 다음
Docker-backed gate가 executable local baseline을 검증한다.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/verify_database.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/verify_database.ps1 -SkipStart
```

기본 경로는 Docker Engine 28+와 고정 `sejong-ai-local-loopback` network를 확인한 뒤 pinned patched
CLI의 `db start --network-id sejong-ai-local-loopback`을 runner 내부에서 호출한다. bare/direct
stock Supabase start나 PATH에서 발견한 CLI는 runner의 provenance와 actual binding 검증을
우회할 수 있으므로 사용하지 않는다. runner는 고정
project/container identity와 HostConfig 요청, actual `NetworkSettings.Ports`의 exact single
`127.0.0.1:54322`를 reset/status/env 전에 검증한다. `supabase test db`가 pgTAP 실행 중 일회성 `pg_prove` container를
사용할 수 있지만, 이는 persistent project runtime의 PostgreSQL-only 경계를 넓히지 않는다.

`-SkipStart`는 이미 실행 중인 disposable local PostgreSQL container를 재사용한다.
`-SkipRollbackReplay`는 진단 중 compensation/replay 증명만 생략하므로 완료 gate가 아니다.
러너는 child 출력을 숨기고, 임시 process 환경변수를 복원하며, stable phase ID만
출력한다. 안전하지 않은 새 runtime은 fail-closed 정지하되 pre-existing/`-SkipStart` runtime과
Docker volume은 변경하지 않는다. 완료 조건은 exact loopback 뒤 pgTAP 6 files/282 assertions,
exact six-stage rollback/absence/reset/replay와 backend integration 8/8의 fresh 재검증이다.

역사적으로 Docker Desktop 4.62.0/Engine 29.2.1은 optioned network에서도 stock CLI의
HostIP 생략을 `127.0.0.1`+`::` wildcard binding으로 해석했다. Q-SEC-006/A-024의
Task 4는 이 원인을 보정한 고정 artifact만 runner가 선택하게 한다. 실제 single
`127.0.0.1:54322`, full pgTAP·compensation/replay·backend integration 증명은 Task 5에
남아 있으므로 현재 DB-001은 아직 완료가 아니다. runner가 새 runtime을 시작한
경우에는 `db start`가 일부 생성 뒤 실패하거나 post-start binding 검증이 실패해도
해당 project stack을 중지하고 container 부재를 확인한다. 기존 runtime이나
`-SkipStart` 경로는 자동 중지하지 않는다. 이 선택은 공개 API, DB schema/data,
dependency와 readiness 상태를 바꾸지 않는다.
[Docker published ports](https://docs.docker.com/engine/network/port-publishing/)와
[Supabase local development](https://supabase.com/docs/guides/local-development/)를 따른다.

credential provisioning은 Supabase status의 admin DSN을 runner process memory/environment에서만 사용하고
`sejong_local_login`을 생성하거나 password를 회전한 다음 `sejong_backend` capability만
부여한다. 무시된 `apps/api/.env` 전체 bytes를 읽어 `DATABASE_URL`만 원자 갱신하고
주석·순서·다른 provider 값을 파싱하지 않은 채 byte-identical하게 보존한다. 이 파일은
commit하지 않는다.

ordered SQL helper는 resolve 결과가 `database/` 안에 남는 명시적인 파일만 받는다.
disposable local DB-001 compensation과 absence proof에만 사용하며 remote나 실제 데이터 DB에
파괴적 SQL을 실행하라는 승인이 아니다.

선택적 local stop은 `.\.tools\supabase\v2.109.1-sejong-loopback\supabase.exe stop`을 사용한다. volume
삭제·prune은 하지 않는다. local stack은 기본 개발 credential과 TLS/rate-limit 부재를
전제로 하므로 공개하지 않는다. Q-SEC-003=A/D-046의 `00700`은 public 준비까지 구현 보류이며,
그 migration·compensation·전체 regression 전에는 remote/public 배포·public admin/API·public
backend DB credential을 차단한다.

## 보안 경계 검사

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/check_secret_patterns.ps1
node scripts/check_web_bundle_secrets.mjs apps/web/.next
```

첫 명령은 Windows PowerShell 5.1 호환 저장소 secret pattern 검사이고, 두 번째 명령은 Node
표준 라이브러리만 사용하는 browser artifact 검사다. 둘 다 clean 0, leak 1, 입력 누락·읽기
실패 같은 운영 오류 2 이상을 반환하며 출력에는 경로·stable rule ID·개수만 포함한다. 검사
범위와 제외 대상, 보장하지 않는 항목은 `SECURITY.md`를 따른다. secret assignment 검사는
일반/`export`, PowerShell `$env:NAME=value`, cmd `set NAME=value` 형식을 포함하지만 등호 없는
`setx NAME value`는 현재 P2 한계로 탐지하지 않는다.

별도 candidate checkout은 trusted scanner에 `-RepositoryRoot <candidate>`를 전달한다. 이 모드는
Git stdout 32 MiB·stderr 1 MiB·60초, regular file당 4 MiB·전체 16 MiB에서 fail closed하고
legacy/runtime/reparse 경계를 제외한다. limit failure는 값 없는 stable rule과 exit 2다.
