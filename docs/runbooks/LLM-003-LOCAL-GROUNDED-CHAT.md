# LLM-003 Local Grounded Chat Runbook

이 문서는 승인된 local/private 입찰 시연에서만 Upstage exact `solar-pro3` grounded chat을
선택하는 순서를 고정한다. Cloud, CI, remote DB, public 배포와 실제 기관 운영에는 사용하지
않는다. 질문·답변·provider body·key·DSN을 터미널, 파일 또는 로그에 출력하지 않는다.

## 전제와 중단 조건

- Docker Desktop이 실행 중이어야 한다.
- 저장소 루트에서 실행하고 tracked 파일과 `data/official/releases/0.1.0-initial.2/`를 수정하지
  않는다.
- `supabase/config.toml`의 `[db.seed].enabled=false`를 유지한다. `db reset --local`은 migration
  replay일 뿐 공식 seed 적용이 아니다.
- patched Supabase CLI, exact loopback binding, immutable `.2` hash 또는 final projection
  검증이 실패하면 API를 시작하지 않는다.
- local DB/context 설정이 유효해도 grounded profile이 disabled 또는 invalid면 API는 정상적인
  TEMPLATE mode로 동작한다.

## 1. 자동 seed 비활성 확인

`supabase/config.toml`에서 아래 값이 그대로인지 확인한다.

```toml
[db.seed]
enabled = false
```

## 2. patched local Supabase 시작

먼저 tracked manifest와 project-local patched binary를 검증한 뒤 이 binary만 사용한다.
stock/PATH fallback은 금지한다.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File scripts/bootstrap_patched_supabase.ps1 -VerifyOnly

$commonGitDir = git rev-parse --path-format=absolute --git-common-dir
$repositoryToolRoot = Split-Path $commonGitDir -Parent
$supabase = Join-Path $repositoryToolRoot `
  ".tools\supabase\v2.109.1-sejong-loopback\supabase.exe"
& $supabase start *> $null
if ($LASTEXITCODE -ne 0) { throw "LOCAL_SUPABASE_START_FAILED" }
```

승인된 기존 DB 절차에 따라 local admin DSN을 **값을 출력하지 않고** 현재 process의
`SEJONG_ADMIN_DATABASE_URL`에 둔다. remote project DSN은 사용하지 않는다.

## 3. immutable `.2` seed-cycle

이 단계는 **빈 disposable DB에서 ACTIVE 19 기준선을 새로 만들 때만** 실행한다. 관리자 승인
루프를 이미 완료해 ACTIVE 20인 DB에는 다시 실행하거나 reset하지 않는다. 그 경우 `.2` 19개
projection과 별도 승인된 20번째 KB의 작성자/승인자 lineage를 read-only로 확인하고 Step 4로
간다.

```powershell
$releaseVersion = "0.1.0-initial.2"
apps/api/.venv/Scripts/python.exe -B scripts/verify_data_seed_db.py `
  seed-cycle --release-version $releaseVersion
```

이 단계는 exact ACTIVE KB 19, OFFICIAL office 3, approved mapping 10과 second-seed 차단을
검증한다.

## 4. final projection 확인

```powershell
apps/api/.venv/Scripts/python.exe -B scripts/verify_data_seed_db.py `
  verify-final --release-version $releaseVersion
apps/api/.venv/Scripts/python.exe -B scripts/provision_local_database_login.py
```

provisioning은 ignored `apps/api/.env`의 `DATABASE_URL`만 회전한다. 기존 non-superuser role도
안전 속성을 확인한 뒤 rerun할 수 있다. DSN과 생성 password를 복사하거나 출력하지 않는다.

## 5. ignored local DB/context 값 설정

`apps/api/.env.example`을 기준으로 ignored `apps/api/.env`를 사용한다.
`DATABASE_URL`은 바로 앞 provisioning 결과를 유지하고, `CONTEXT_TOKEN_SECRET`에는 CSPRNG로
생성한 최소 32-byte 값을 둔다. 값 자체는 명령 기록, 문서, Git 또는 화면 캡처에 남기지 않는다.

## 6. provider mode 하나만 선택

먼저 provider-disabled regression을 위한 기본값을 유지한다.

```dotenv
UPSTAGE_SYNTHETIC_EVALUATION_MODE=false
UPSTAGE_GROUNDED_CHAT_MODE=false
```

offline 전체 gate와 disabled regression이 통과한 뒤 optional grounded actual에서만 다음
non-secret profile을 정확히 선택한다.

```dotenv
LLM_PROVIDER=upstage
LLM_MODEL=solar-pro3
LLM_BASE_URL=https://api.upstage.ai/v1
LLM_TIMEOUT_SECONDS=8
LLM_MAX_RETRIES=0
LLM_MAX_CONCURRENCY=1
LLM_MAX_INPUT_TOKENS=4096
LLM_MAX_OUTPUT_TOKENS=1024
LLM_RUN_ATTEMPT_CAP=30
UPSTAGE_SYNTHETIC_EVALUATION_MODE=false
UPSTAGE_GROUNDED_CHAT_MODE=true
```

두 mode를 동시에 켜거나 제한값을 바꾸면 fail closed다.

## 7. ignored key 설정

`LLM_API_KEY`는 ignored `apps/api/.env` 또는 current process에만 둔다. 문서·shell history·Git,
Cloud, CI에 값을 넣지 않는다. key가 없거나 빈 값이면 grounded runtime은 조립되지 않고 TEMPLATE
mode를 유지한다.

## 8. loopback API 시작

```powershell
$commonGitDir = git rev-parse --path-format=absolute --git-common-dir
$uv = Join-Path (Split-Path $commonGitDir -Parent) ".tools\uv\uv.exe"
& $uv run --project apps/api --frozen python `
  scripts/run_local_api.py --port 8000
```

전용 runner는 `127.0.0.1`, one worker, access log off, WebSocket off를 고정한다.

## 9. readiness 확인

별도 터미널에서 body, key 또는 DSN을 출력하지 않고 상태 코드만 확인한다.

```powershell
$response = Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/ready
if ($response.StatusCode -ne 200) { throw "LOCAL_API_NOT_READY" }
```

startup, `/health`, `/ready`는 Upstage 요청을 만들지 않는다.

## 10. provider-disabled regression 후 optional actual

먼저 두 provider mode가 모두 `false`인 별도 API process에서 관련 offline gate와 local chat
smoke를 실행해 SUCCESS가 `answer_mode=TEMPLATE`이고 공식 source가 유지되는지 확인한다. 그
process를 종료한 뒤에만 Step 6~7의 exact grounded profile로 새 process를 시작한다.

```powershell
$commonGitDir = git rev-parse --path-format=absolute --git-common-dir
$uv = Join-Path (Split-Path $commonGitDir -Parent) ".tools\uv\uv.exe"
& $uv run --project apps/api --frozen pytest `
  apps/api/tests/test_local.py `
  apps/api/tests/test_chat_route.py `
  apps/api/tests/test_architecture.py `
  apps/api/tests/llm/test_architecture.py -q
```

optional actual은 전체 offline test가 통과한 뒤 별도 local 인간 gate에서만 한 번 수행한다.
실패·출력 보정 뒤 재실행도 새 10-call network 사용이므로 별도 인간 재승인 없이는 수행하지 않는다.
`FOLLOWUP`, `PRIVACY_UNRESOLVED`, `INSUFFICIENT_GROUNDING`, `PERSONAL_LOOKUP`,
`LEGAL_JUDGMENT`, `OUT_OF_SCOPE`, readiness 실패는 provider call 0이어야 한다. actual 중에도
질문·답변·prompt·provider body를 출력하거나 저장하지 않는다.

승인 후 별도 API process를 직접 띄우는 대신 아래 고정 runner로 10건과 locally injected timeout
증거를 한 번에 실행한다. 인수는 받지 않으며 질문·답변·provider body를 출력하지 않는다.

```powershell
& $uv run --project apps/api --frozen python scripts/run_upstage_grounded_chat_actual.py
```

정상 stdout은 승인된 10개 aggregate field를 가진 JSON 객체 정확히 하나다. `cases_total=10`,
`source_present_count=10`, 두 leak/mismatch count 0, `outbound_attempt_count=10`,
`generated_count>=1`, 비용 USD 0.05 이하여야 한다. 별도 forced timeout은 TEMPLATE이고 provider
outbound를 추가하지 않는다.

## 11. rollback과 종료

1. API process를 종료한다.
2. `UPSTAGE_GROUNDED_CHAT_MODE=false`로 되돌린다.
3. ignored `LLM_API_KEY` 값을 제거한다.
4. API를 다시 시작해 `/ready=200`과 TEMPLATE regression을 확인한다.
5. local stack이 더 필요 없으면 volume/prune 없이 정상 종료한다.

```powershell
& $supabase stop
```

rollback은 DB migration, official data, immutable `.2`, 공개 API 계약을 변경하지 않는다.
