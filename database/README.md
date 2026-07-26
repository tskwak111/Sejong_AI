# Database

DB-001의 manifest 의미 버전은 disposable local/private `0.4.0-local`이다. pinned patched
Supabase CLI의 exact single `127.0.0.1:54322`, current 9 forward/9 matching rollback,
pgTAP 9 files/356 assertions와 rollback absence/reapply 36/36을 검증했다. 이는
production/public readiness를 뜻하지 않는다.
Q-SEC-003=A/D-046으로 exact privileged function 22 signatures의 property-only `00700`
보정 방향을 확정했고 D-092가 public 준비·실행을 승인했다. 먼저 `00680` scope-gap queue를
추가한 뒤 `00700`·matching rollback·전체 regression을 수행한다. 완료 전 remote migration과
배포를 금지하며, 완료 뒤에도 ADR-0026에 따라 인증 없는 public admin/API는 비활성이다.

## 권위와 계보

- 실행 권위: `supabase/migrations/`를 timestamp 오름차순으로 적용한다.
- 보상: `database/rollbacks/`를 timestamp 역순으로 실행하며 disposable local DB에만 쓴다.
- 논리 투영: `database/schema-v1.draft.sql`은 7 enum·9 table·5 index를 읽기 쉽게 보여주는
  참고본일 뿐 직접 실행하지 않는다.
- 공식 filesystem release 권위: historical `.1`과 corrected immutable
  `data/official/releases/0.1.0-initial.2/`가 함께 보존되며 `.2`의 19/3/10 projection과
  create-once artifact가 게시·검증됐다. `supabase/seed.sql`은 `.2` seed와 byte-identical이고
  `[db.seed].enabled=false`다. 2026-07-22 지원 actual DB cycle은 concurrency A/B, seed,
  compensation/replay와 cleanup까지 PASS하여 local DB에 ACTIVE/OFFICIAL KB 19·official office 3·
  approved mapping 10을 반영했고 `official_data=0.1.0-initial.2`로 승격됐다. 이 initial seed는
  20번째 ACTIVE admin regression이나 `/ready=200` 증거를 대신하지 않는다. 이들은 별도 final local
  application rehearsal에서 PASS했으며 public/remote readiness는 계속 뜻하지 않는다.

Forward migration과 matching compensation은 현재 각각 9개다. 적용·commit된 migration은
수정하지 않고 보정이 필요하면 새 reviewed forward migration을 추가한다. 현재 local 전체
보상 순서는 `00670 → 00660 → 00650 → 00600 → 00500 → 00400 → 00300 → 00200 → 00100`이며, 이어
`database/verify_db001_absent.sql`로 DB-001 객체 부재를 증명한다.

CHAT-NATURAL 구현 목표 순서는 `00700 → 00680 → 00670 → ... → 00100` rollback이다. 구현 전
문서에 적힌 목표 순서를 current executable count로 오인하지 않는다.

## 로컬 실행과 검증 — patched repository gate만 허용

Q-SEC-004=A와 Q-SEC-005=A의 Docker Desktop 보정만으로는 IPv6 wildcard가 남았고,
Q-SEC-006=A/D-031과 Q-TOOL-001=A/D-032에서 official v2.109.1 source의 local DB HostIP만
고정한 project-local patched CLI, short checkout/path-budget, patched-only runner를 구현했다.
DB 검증은 아래 repository command만 사용한다. stock/bare `supabase db start/reset`, remote push와
다른 DB/volume 조작은 지원하지 않는다.

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/bootstrap_supabase.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/verify_database.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/verify_database.ps1 -SkipStart
```

첫 DB gate는 pinned Supabase CLI `2.109.1`을 runner가 고정 loopback network로 시작하고 actual
single `127.0.0.1:54322`를 검증한다. 이후에만 reset, login rotation, pgTAP, 9단계 보상,
부재 확인, reset/replay,
pgTAP, 실제 backend integration을 순서대로 수행한다. `-SkipStart`는 이미 실행 중인 local
DB를 재사용할 때만 쓴다. `-SkipRollbackReplay`는 진단 옵션이며 완료 증거가 아니다.

Docker Desktop의 `local-only-port-binding` 설정은 유지하지만 완료 근거가 아니다. 완료 근거는
patched runner가 actual container에 exact one `127.0.0.1:54322` binding을 확인한 결과다.
bare/direct `db start`로 우회하지 않는다.

필요할 때 local login만 별도로 회전하려면 관리자 DSN을 값이 노출되지 않는 process
environment의 `SEJONG_ADMIN_DATABASE_URL`에 넣고 다음을 실행한다.

```powershell
apps/api/.venv/Scripts/python.exe -B scripts/provision_local_database_login.py
```

스크립트는 ignored `apps/api/.env`의 `DATABASE_URL` 한 줄만 원자적으로 갱신하고 다른
provider 설정은 보존한다. DSN, password, status 원문을 문서·로그·shell history에 남기지
않는다.

선택적 종료는 다음과 같다. Docker volume 삭제·prune은 하지 않는다.

```powershell
.\.tools\supabase\v2.109.1\supabase.exe stop
```

## 데이터와 readiness

`supabase/seed.sql`은 현재 `.2` release `seed.sql`과 byte-identical이다. 단 Supabase reset의
자동 seed는 `[db.seed].enabled=false`로 비활성이다. immutable `.2`는 기존 migration의
ADMIN/INHERIT/SET effective-option union 권위와 동일한 guard로 게시됐고 `.1`/v1 byte는
보존됐다.

이전 3회는 concurrency B에서 중단됐지만, relation observer의 accepted lock mode를 수정한 뒤
2026-07-22 지원 actual cycle은 baseline, exact identity, forced rollback(`tables=8 partial=0`),
concurrency A/B, 19/3/10 seed, replay·compensation guard, final citizen 19/exclusions 0/
operational 0와 cleanup을 모두 PASS했다. final exact-owned runtime process/container는 0이다.
`.1`·`.2` immutable artifacts는 변경하지 않았다. `/ready=200`과 20번째 ACTIVE regression은 별도
final local application rehearsal에서 PASS했으며, 이 seed report를 public/remote readiness로 확장하지
않는다. 상세 evidence는
[`DATA-SEED-002 lineage`](../docs/data-lineage/DATA-SEED-002-0.1.0-initial.2.md)와
[`DATA-SEED-002 local verification`](../docs/test-reports/DATA-SEED-002-LOCAL-VERIFICATION.md)을
따른다.

현재 근거는 [ADR-0008](../docs/adr/0008-supabase-cli-sql-migrations.md),
[ADR-0011](../docs/adr/0011-layered-database-and-backend-enforcement.md),
[ADR-0012](../docs/adr/0012-deferred-active-question-trigger-execution.md),
[승인된 설계](../docs/superpowers/specs/2026-07-16-db-001-layered-enforcement-design.md),
[차단된 실행계획](../docs/superpowers/plans/2026-07-16-db-001-layered-enforcement.md),
[local baseline candidate report](../docs/test-reports/DB-001-LOCAL-BASELINE.md)다.
