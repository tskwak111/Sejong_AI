# Controlled public citizen deployment runbook

## 범위

이 문서는 인증 없는 관리자 기능을 제외한 시민용 공개 demo를 배포할 때의 fail-closed 절차다.
허용 경로는 `/health`, `/ready`, `/api/v1/chat`, `/api/v1/offices`뿐이다.

다음은 이 승인에 포함되지 않는다.

- `/admin`, `/api/v1/admin/*`
- real citizen/free-input Upstage 전송
- 실제 신청·상태조회·결제
- 추측한 project/region/domain 또는 자동 생성한 유료 계정

## 1. target discovery

값을 출력하지 않고 다음 항목의 **이름과 존재 여부만** 확인한다.

```powershell
git ls-files "vercel.json" "render.yaml" ".openai/hosting.json" `
  "supabase/config.toml" ".github/workflows/*.yml"
Get-ChildItem Env: | Where-Object {
  $_.Name -match '^(VERCEL|RENDER|SUPABASE|DATABASE|NEXT_PUBLIC)_'
} | Select-Object -ExpandProperty Name
```

아래 항목을 모두 식별할 수 있어야 다음 단계로 진행한다.

1. 인간이 소유권·비용·리전을 승인한 dedicated demo target
2. tracked deploy mechanism과 immutable source commit
3. server-side secret store
4. exact public citizen origin과 same-origin Web→API routing
5. remote DB identity와 supported migration/seed mechanism
6. saved deployment version과 rollback command

하나라도 없으면 결과는 정확히 `Not executed: target not configured`이며 계정이나 target을
자동 생성하지 않는다.

## 2. preflight

- final repository gate와 secret scan PASS
- 11 forward migration, 11 matching rollback, 11 pgTAP 파일
- `20260727000700_privileged_function_search_path.sql` exact 22 function property-only
- request body logging off
- browser는 same-origin `/api/v1/*`만 사용하고 backend secret을 번들에 넣지 않음
- public app의 admin router 0
- `UPSTAGE_CLASSIFIER_MODE=false`, `UPSTAGE_GROUNDED_CHAT_MODE=false`
- DB·application rollback identifier 확보

## 3. remote DB

tracked·reviewed remote importer가 remote identity를 검증할 때만 순서대로 수행한다.

1. 기존 migration state 확인
2. 미적용 forward migration 적용
3. `00700` catalog/behavior pgTAP
4. 자동 seed 없이 immutable `.2` formal import
5. ACTIVE 19, office 3, mapping 10과 `/ready=200` 확인

bare Supabase command, local DSN 재사용, 실패한 seed의 official-data 승격은 금지한다. 실패 시
matching rollback과 마지막 검증된 DB version을 사용한다.

## 4. saved version deploy와 시민 smoke

exact committed source를 saved version으로 배포한 뒤 비식별 합성 입력으로만 확인한다.

| 경로 | 기대 |
|---|---|
| `GET /health` | `200` |
| `GET /ready` | `200` |
| `GET /api/v1/offices` | `200`, server-owned OFFICIAL data |
| `POST /api/v1/chat` | `200`, ACTIVE/OFFICIAL source, provider outbound 0 |
| `GET /admin` | unavailable |
| `GET /api/v1/admin/failed-questions` | unavailable 또는 fixed disabled response |

URL query, DSN, secret, 시민 질문 본문은 terminal/report/log에 기록하지 않는다.

## 5. rollback

smoke가 하나라도 실패하면 traffic을 마지막 검증 version으로 되돌린다. DB 변경이 원인이면
matching rollback을 사용하고, application/admin/provider 설정을 이전 안전 version과 비교한다.
secret 노출 가능성이 있으면 환경에서 rotate/revoke하고 Git history에는 넣지 않는다.

## 현재 실행 결과

2026-07-27 발견에서는 local `supabase/config.toml`과 CI workflow만 있고 public application target,
remote DB project, deploy credential·secret·origin·saved version은 없었다. 따라서 실제 remote
migration·seed·deploy·smoke는 `Not executed: target not configured`다. 상세 집계는
`docs/test-reports/CHAT-NATURAL-001-REMOTE-VERIFICATION.md`에 있다.
