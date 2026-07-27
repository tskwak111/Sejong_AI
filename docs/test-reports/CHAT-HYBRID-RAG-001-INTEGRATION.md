# CHAT-HYBRID-RAG-001 — local/offline integration evidence

- Date: 2026-07-27 (KST)
- Source HEAD before documentation integration: `9f377d4`
- Scope: Tasks 1~9 local/offline
- Actual provider/network: not executed in this gate
- DB mutation/reset/seed: not executed

## Result

| Area | Command/result | Status |
|---|---|---|
| API tests | `pytest apps/api/tests -q` — 2,356 passed, 8 skipped, 1 warning, 5 subtests; 27.38s | PASS |
| API lint | Ruff — no findings; 0.569s | PASS |
| API types | Mypy — 57 source files; 1.573s | PASS |
| DB regression | DB/admin/Supabase tooling — 345 passed, 8 skipped, 1 warning, 47 subtests; 145.65s | PASS |
| Shared generation | generated contract drift 0 | PASS |
| Shared tests | 96/96 | PASS |
| Web lint/typecheck | errors/warnings 0 | PASS |
| Web tests | 14 files, 68 tests | PASS |
| Web build | Next.js production build | PASS |
| Offline UAT | focused 91 passed, skipped 0 | PASS |
| Secret patterns | PowerShell repository scanner, findings 0 | PASS |
| Documentation | repository documentation check | PASS |
| Package/version | 12 required files and manifest | PASS |
| Diff hygiene | `git diff --check` | PASS |

## Conditional evidence and warnings

- API/DB의 8 skip은 모두 local DB gate 조건이다. 숨긴 실패로 계산하지 않는다.
- API/DB warning 1건은 기존 Starlette/httpx `TestClient` deprecation이다.
- DB regression 첫 동일 실행은 124.1초 wrapper timeout으로 pytest 결과가 없었다. 코드·환경
  변경 없이 timeout만 늘린 재실행이 145.65초에 PASS했다.
- Web build는 Next.js workspace-root 자동 추론 warning 1건을 냈지만 build는 성공했고
  package/lockfile/tracked generated drift는 없다.

## Version and data boundary

```text
application: 0.12.0-bounded-hybrid-rag
web: 0.8.0-guided-chat
api: 4.0.0-draft
shared_contracts: 1.0.0
database_schema: 0.5.0-local
official_data: 0.1.0-initial.2
prompt_set: 0.4.0-topic-coverage
test_suite: 2.0.0-bounded-hybrid-rag
documentation: 2.27.0
```

Immutable official `.2`의 tracked ACTIVE/OFFICIAL projection은 19다. metadata 20건 중 current
runtime catalog는 그 19건 교집합만 사용한다. local DB의 별도 승인 20번째 ACTIVE를 official
`.2` release에 역기록하지 않았고, 이 gate에서 migration/seed/data/provider write는 0이다.

## Privacy and security boundary

- citizen raw question, canonical synthetic phone, provider payload, API key, DSN, context token을
  이 보고서에 기록하지 않았다.
- privacy/policy route는 provider 0과 text/event/failed/scope row 0을 유지한다.
- phone-shaped ordinary MOVE case는 redaction 후 provider 0의 grounded success이며 raw shape
  sink 노출 0을 UAT가 검증한다.
- source title/URL/date는 server-owned ACTIVE metadata에서만 결합한다.

## Pending

- Task 10의 승인된 PII-free 20-case local Upstage actual run.
- Task 11의 final root/security/browser gate와 independent review.
- public/remote deployment, DB reset/seed, official-data 승격, automatic merge는 미실행이다.
