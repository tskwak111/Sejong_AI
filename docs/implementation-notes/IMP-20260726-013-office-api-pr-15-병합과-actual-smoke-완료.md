# IMP-20260726-013 — OFFICE API PR 15 병합과 actual smoke 완료

- Date/Time (KST): 2026-07-26T18:30:51+09:00
- Task ID: OFFICE-API-001
- Type: verification
- Status: Done — PR #15 merged; bounded read-only local actual smoke PASS
- Author/Agent: repository owner / Codex
- Branch: `codex/OFFICE-API-001-post-merge-smoke`
- Base commit: `b66e18c635728c5d502fd09c9c18e2f764367338`
- Related plan/ADR/RFP: [OFFICE-API-001 plan](../superpowers/plans/2026-07-26-office-api-runtime-parity.md), D-078~D-081, SFR-004

## 1. 사용자 요청과 완료 기준

### 요청

사용자가 PR #15 병합을 알리고 다음 작업의 빠른 계속 진행을 승인했다. 첫 진단에서 managed
sandbox가 Git/Docker/WSL access를 막았고, 사용자가 권한을 unrestricted로 변경한 뒤 최신 main
동기화와 기존 Pending office actual smoke를 완료한다.

### Acceptance Criteria

- `origin/main`이 PR #15 merge commit인지 확인한다.
- 최신 main 기반 isolated worktree에서 office/local baseline을 확인한다.
- Docker/Supabase actual은 reset·seed·purge·DB write 없이 read-only로 실행한다.
- `/ready=200`, match `200/count=1`, valid empty `200/count=0`을 status/count만 출력한다.
- `.env`를 복사하지 않고 record, DSN, secret과 provider payload를 출력하지 않는다.
- active status/source-of-truth/version/note/INDEX를 actual evidence와 동기화한다.

## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 사용자가 PR #15를 병합하고 local permission을 변경했으며 Codex가 actual smoke와 문서 정합을 수행했다. |
| When — 언제 | merge 2026-07-26T18:06:11+09:00, actual verification은 같은 날 18:30 KST 이후다. |
| Where — 어디서 | private `tskwak111/Sejong_AI`, latest-main worktree `.worktrees/office-api-post-merge-smoke`, loopback Docker/Supabase다. |
| What — 무엇을 | merge provenance, baseline 51 tests, readiness와 office match/empty read-only route를 확인하고 Pending 문서를 PASS로 갱신했다. |
| Why — 왜 | tracked/runtime/injected PASS 뒤 남아 있던 실제 local DB endpoint 증거를 닫기 위해서다. |
| How — 어떻게 | existing allowlisted DB config, process-only CSPRNG context secret, LLM-disabled custom read-only lifespan과 FastAPI TestClient를 사용했다. |
| How much — 어느 정도 | baseline 51 tests, actual HTTP route 3건, match count 1/empty count 0, DB/provider write 0, 비용 0원이다. |

## 3. 시작 전 상태

- 조사 파일: `apps/api/src/sejong_ai_api/{local.py,main.py,api/offices.py,office/service.py}`,
  `scripts/run_local_api.py`, tracked seed mappings, OFFICE plan/spec/IMP-012와 active status/release docs.
- 기존 동작: PR #15 이전 constituent/injected integration은 PASS했지만 actual Docker/Supabase
  endpoint smoke는 local prerequisite 부재로 Pending이었다.
- Git: original checkout은 unrelated branch라 수정하지 않았다. `git fetch origin main` 뒤
  `origin/main=b66e18c`를 확인하고 latest main에서 새 isolated branch/worktree를 만들었다.
- 환경: Docker client/server 29.2.1, context `desktop-linux`,
  `supabase_db_sejong-ai-local` healthy.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| ENV-OFFICE-001 | Resolved environment | managed sandbox Docker/WSL/Git denial | 사용자가 permission 변경; fetch와 Docker API 정상 | actual 실행 가능 |
| CONFIG-OFFICE-001 | Resolved environment | persisted `CONTEXT_TOKEN_SECRET`가 local loader 기준 invalid | 파일을 수정하지 않고 runbook대로 process-only CSPRNG secret 사용 | secret persistence 변경 0 |
| ENCODING-OFFICE-001 | Resolved internal | PowerShell stdin의 한글 region literal이 변형되어 422 | ASCII Unicode escape로 exact `아름동` 전달 | API/contract 변경 0 |

새 아키텍처·공개 계약·DB/data/security 정책 결정은 없다. D-081은 merge와 actual evidence만
기록하며 public/remote/deploy 권한을 넓히지 않는다.

## 5. 설계 결정과 대안

### 선택

- 최신 main 기반 새 linked worktree에서 검증했다.
- `load_local_settings`에 existing env file path와 process-only CSPRNG context secret을 전달했다.
- production local lifespan의 purge 작업은 실행하지 않고 pool open, readiness refresh,
  read route, pool close만 수행하는 custom lifespan을 사용했다.
- provider는 `LLM_ENABLED=false` process override로 조립·호출하지 않았다.

### 이유

실제 repository/readiness/route를 검증하면서도 expired-row purge, seed/reset, event/admin write와
provider outbound를 모두 피할 수 있는 최소 actual 경계다.

### 고려했지만 선택하지 않은 대안

- 기존 merged feature branch에서 계속 작업: latest main provenance가 아니므로 기각했다.
- `.env`를 새 worktree로 복사: secret duplication을 만들므로 기각했다.
- persisted context secret을 임의 수정: smoke에 필요하지 않고 human secret-management 범위를
  넓히므로 기각했다.
- normal local lifespan 사용: startup purge가 read-only 증거를 깨므로 기각했다.
- API response record 전체 출력: 공식 record·contact data가 불필요하게 로그에 남으므로 기각했다.

## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| `TASKS.md`, A-051, OFFICE spec | PR #15 merged와 bounded actual PASS | active 상태 동기화 |
| `apps/api/README.md`, `docs/05_API_AND_CONTRACTS.md` | historical Pending과 post-merge actual 결과 구분 | 운영·consumer 재현 |
| `DECISION_LOG.md` | D-081 merge/actual evidence와 unchanged boundaries | 인간 audit trail |
| `CHANGELOG.md`, `docs/12_VERSIONING_AND_RELEASES.md`, manifest | documentation 2.20.10 및 actual evidence | release 정합 |
| IMP-012/INDEX, 이 note | merge 후속과 재현 증거 | 구현 노트 의무 |

제품 함수, API/OpenAPI/generated contract, DB migration/schema/data, Web, prompt/provider,
dependency/lockfile은 변경하지 않았다.

### 데이터 흐름/상태 변화

```text
existing ignored local DB config
+ process-only CSPRNG context secret
+ LLM_ENABLED=false
→ read-only pool open
→ readiness projection read
→ OFFICIAL-only list_offices read
→ status/count only
→ pool close
```

### 오류·빈 상태·롤백

- first config attempt: inline Korean absolute path encoding으로 env path가 깨져
  `SMOKE_CONFIGURATION_INVALID`; Git common dir에서 path를 전달해 원인을 분리했다.
- second attempt: persisted context secret invalid를 확인해 process-only CSPRNG로 보정했다.
- third route attempt: stdin Korean region encoding으로 safe 422; Unicode escape로 exact region을
  전달해 expected 200/1, 200/0을 확인했다.
- 제품 버그나 data repair는 없었다. 문서 rollback은 이 commit을 revert하면 된다.

## 7. 버전 전후

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Product specification | 2.5.0 | unchanged | 범위 변경 0 |
| Repository guidance | 1.7.8 | unchanged | policy 변경 0 |
| Application | 0.10.0-office-directory-runtime | unchanged | 제품 코드 변경 0 |
| Web | 0.6.0-answer-mode | unchanged | Web 변경 0 |
| API | 3.3.0-draft | unchanged | 공개 계약 변경 0 |
| Shared contracts | 0.6.0 | unchanged | generated artifact 변경 0 |
| DB schema | 0.4.0-local | unchanged | migration/write 0 |
| Official data | 0.1.0-initial.2 | unchanged | seed/record 변경 0 |
| Mock data | 0.0.0-not-populated | unchanged | mock 생성 0 |
| Prompt set | 0.2.0-grounded-live-chat | unchanged | provider/prompt 변경 0 |
| Test suite | 1.7.1-office-directory-review-fix | unchanged | 새 test/code 변경 0 |
| Documentation | 2.20.9 | 2.20.10 | merge/actual evidence와 active 상태 sync |

## 8. 명령과 테스트, 실제 결과

| 명령/검증 | 실제 결과 |
|---|---|
| GitHub PR #15 metadata | `merged=true`, head `6e51ede7...`, merge `b66e18c...` |
| `git fetch origin main`; `git show origin/main` | PASS — latest main `b66e18c` |
| `git worktree add ... origin/main` | PASS — isolated branch at exact merge |
| pinned uv office/local pytest | PASS — 51 passed, pre-existing Starlette warning 1 |
| `docker version/context/ps` | PASS — client/server 29.2.1, `desktop-linux`, local DB healthy |
| allowlisted config diagnostics | DB URL valid; persisted context secret invalid; values 출력 0 |
| first actual config attempt | expected fail-closed `SMOKE_CONFIGURATION_INVALID`; DB query 0 |
| first valid-config route attempt | readiness 200; Korean stdin encoding으로 office 422/422 |
| corrected read-only actual | PASS — ready 200, match 200/count 1, empty 200/count 0 |

최종 smoke는 response record, address, phone, source URL, DSN와 secret을 출력하지 않았다.
정상 route request metadata log에는 method/path/status/request_id만 있었다.

### Exact baseline command

```powershell
$uv = "C:\Users\ss020\바탕 화면\sejong_ai\sejong_ai_codex_ready_project\.tools\uv\uv.exe"
& $uv run --directory apps/api --frozen pytest `
  tests/test_offices_route.py tests/test_local.py -q -p no:cacheprovider
```

실제 결과는 `51 passed`, pre-existing Starlette warning 1건이었다.

### Exact corrected read-only actual command

아래 명령은 env file을 복사하지 않고 Git common directory에서 existing file path만 계산한다.
process-only secret은 출력하거나 저장하지 않는다.

```powershell
$common = (git rev-parse --path-format=absolute --git-common-dir).Trim()
$mainRoot = Split-Path $common -Parent
$env:SEJONG_SMOKE_ENV_PATH = Join-Path $mainRoot "apps\api\.env"
$env:PYTHONPATH = (Resolve-Path "apps/api/src").Path
$uv = Join-Path $mainRoot ".tools\uv\uv.exe"
@'
from __future__ import annotations

import asyncio
import os
import secrets
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from sejong_ai_api.chat.readiness import RepositoryReadinessProbe
from sejong_ai_api.db.pool import create_pool
from sejong_ai_api.db.repository import PsycopgSejongRepository
from sejong_ai_api.local import load_local_settings
from sejong_ai_api.main import create_app
from sejong_ai_api.office.service import GuardedOfficeDirectory, OfficeDirectoryService

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

env_path = Path(os.environ.pop("SEJONG_SMOKE_ENV_PATH"))
settings = load_local_settings(
    environ={"LLM_ENABLED": "false", "CONTEXT_TOKEN_SECRET": secrets.token_urlsafe(32)},
    env_path=env_path,
)
if settings is None:
    print("SMOKE_CONFIGURATION_INVALID")
    raise SystemExit(1)

pool = create_pool(settings.database_url)
repository = PsycopgSejongRepository(pool)
probe = RepositoryReadinessProbe(repository)
directory = GuardedOfficeDirectory(probe, OfficeDirectoryService(repository))
app = create_app(readiness_probe=probe, office_directory=directory)

@asynccontextmanager
async def read_only_lifespan(_app: FastAPI) -> AsyncIterator[None]:
    try:
        await pool.open(wait=True)
        await probe.refresh()
        yield
    finally:
        await pool.close()
        probe.disable()

app.router.lifespan_context = read_only_lifespan
region = "\uc544\ub984\ub3d9"
with TestClient(app) as client:
    ready = client.get("/ready")
    match = client.get(
        "/api/v1/offices",
        params={"region": region, "intent": "BULKY_WASTE"},
    )
    empty = client.get(
        "/api/v1/offices",
        params={"region": region, "intent": "LOCAL_TAX_GENERAL"},
    )

match_body = match.json() if match.status_code == 200 else {}
empty_body = empty.json() if empty.status_code == 200 else {}
match_count = len(match_body.get("items", [])) if isinstance(match_body, dict) else -1
empty_count = len(empty_body.get("items", [])) if isinstance(empty_body, dict) else -1
print(f"READY_STATUS={ready.status_code}")
print(f"MATCH_STATUS={match.status_code}")
print(f"MATCH_COUNT={match_count}")
print(f"EMPTY_STATUS={empty.status_code}")
print(f"EMPTY_COUNT={empty_count}")
if (
    ready.status_code,
    match.status_code,
    match_count,
    empty.status_code,
    empty_count,
) != (200, 200, 1, 200, 0):
    raise SystemExit(1)
'@ | & $uv run --project apps/api --frozen python -
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
```

### 미실행 검증과 이유

- seed/reset/migration/pgTAP/full DB gate: data mutation 없는 bounded route verification 범위다.
- chat/provider actual: OFFICE endpoint와 무관하며 future provider rerun은 별도 승인 대상이다.
- public/remote/deploy: 승인되지 않았다.

## 9. 보안·개인정보·접근성·성능 영향

- Privacy: 질문 원문·PII·IP·device/context 처리·저장·출력 0.
- Security: `.env` copy 0, DSN/key/token value 출력 0, CSPRNG secret은 process 종료와 함께 폐기됐다.
- Accessibility: UI 변경 0.
- Performance/cost: 3 bounded route calls, provider outbound 0, 외부 비용 0원. 부하 성능 수치는 아니다.

## 10. 데이터와 출처 영향

- official data: 기존 OFFICIAL mapping을 read-only 조회했으며 record 내용은 출력하지 않았다.
- mock/AI 생성: 0.
- schema/lineage: DB `0.4.0-local`, official `0.1.0-initial.2` unchanged.
- verified date: smoke 2026-07-26; 기관 record의 verified_at 자체는 변경하지 않았다.

## 11. 인간이 반드시 알아야 하는 내용

- PR #15는 merge commit `b66e18c`로 main에 반영됐다.
- 실제 local DB에서 `/ready=200`, match 1, valid empty 0을 확인했다.
- persisted `CONTEXT_TOKEN_SECRET`는 loader 기준 invalid지만 이번 smoke는 process-only secret으로
  안전하게 완료했다. 정상 local API를 직접 오래 실행할 때는 별도의 human-managed valid secret이
  필요하다.
- historical aggregate `scripts/verify.ps1`의 `PREFLIGHT-UV` NOT PASS는 actual smoke로 덮지 않는다.
- public/remote/deploy/admin exposure와 future provider call은 여전히 승인되지 않았다.

## 12. AI 내부 구현 세부 — 인간이 굳이 이해하지 않아도 되는 내용

- custom lifespan은 `pool.open → probe.refresh → read requests → pool.close`만 수행한다.
- empty fixture는 approved mapping에 의도적으로 없는 `아름동 + LOCAL_TAX_GENERAL`이다.
- Unicode escape는 PowerShell stdin encoding 차이만 제거하며 wire value는 exact `아름동`이다.

## 13. 재현·인수인계·롤백

### 재현

1. latest main `b66e18c` 이상과 Docker local DB healthy를 확인한다.
2. allowlisted DB config는 출력하지 않고 loader로만 읽는다.
3. process-only CSPRNG context secret, provider disabled, read-only lifespan을 사용한다.
4. ready status, match status/count, empty status/count만 출력한다.
5. pool/process를 종료하고 DB write path를 호출하지 않았음을 확인한다.

### 롤백

제품·DB/data 변화는 없어 rollback이 없다. 문서 sync가 잘못되면 이 documentation commit만
revert한다.

### 다음 개발자 시작점

문서 gate와 secret/diff 검사를 실행하고 commit·push·Draft PR을 만든다. 사람 검토 전 merge하지
않는다. 다음 product backlog는 이 smoke와 별개로 새 spec/plan에서 시작한다.

## 14. 남은 위험·미해결 질문·다음 단계

- persisted local `CONTEXT_TOKEN_SECRET` invalid: 이번 process-only smoke에는 영향 없지만 장기 local
  server 실행 전 human-managed secret 설정 필요.
- aggregate verifier의 historical UV bootstrap NOT PASS는 별도 tooling backlog다.
- public/remote/hosted backend CI, 100-user performance, backup/deploy는 이번 범위 밖이다.

## 15. 자체 리뷰

- [x] 요청과 bounded actual 인수 기준 충족
- [x] baseline/actual verification
- [x] source-of-truth/status/version 동기화
- [x] 개인정보·secret·record 출력 없음
- [x] 구현 노트 INDEX 갱신
