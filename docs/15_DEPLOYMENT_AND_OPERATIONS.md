# 배포·운영 기준

## 확정 초기 환경과 향후 권장 환경

- 초기 완료 기준: local-first, 외부 인프라 예산 0원
- Local Web: Node 24.x + pnpm
- Local API: Python 3.12 + uv
- Local DB: Docker + Supabase CLI, `supabase/migrations/` 버전 SQL이 실행 권위
- 향후 공개 배포 추천: Vercel(Web) + Render(API) + Supabase PostgreSQL(DB)
- 공개 배포·배포 URL·녹화본은 계정·리전·로그·CORS·예산과 서버측 admin gate를 별도 승인한 뒤 추가

## 아직 인간 확인이 필요한 것

- 실제 계정과 소유자
- 리전과 데이터 위치
- 무료 플랜 sleep/쿼터
- 도메인/HTTPS
- admin 노출 보호
- CORS origin
- secret rotation
- 인프라 자동 로그 보관
- 공개 환경 LLM 데이터 처리·비용/한도 재승인

현재 위 항목은 공개 배포 전에 확인할 Deferred 항목이다. 초기 구현을 막는 배포 계정 요구사항으로 해석하지 않는다.

Q-GIT/Q-COLLAB 결정의 private source remote bootstrap, hosted policy/Frontend CI, collaborator
accepted write access, repository variable, read-only default Actions permissions과 direct-push
description warning, PR #1 merge/post-merge CI와 Codex App `Only select repositories / Sejong_AI`
사용자 확인은 검증됐다. teammate MFA/recovery, Cloud Draft PR/manual merge와 Frontend onboarding
rehearsal은 여전히 Pending이다. Task 5는 partial이며 첫
Task 7 PR-only/no-direct-main-push rehearsal이 완료돼야 닫힌다. 실행 뒤에도 local Git의
lint·typecheck·test·build·contract·secret 증거를 유지하고 Windows/Docker/Upstage actual gate를
Cloud CI로 대체하지 않는다. 이 source remote는 tracked source/history의 협업 경로이며
Vercel/Render/Supabase application deployment, remote DB, public admin/API 승인이 아니다.

## 필수 엔드포인트

- `/health`: 프로세스 생존
- `/ready`: DB·필수 데이터 준비

health/readiness에 비밀이나 내부 상세를 노출하지 않는다.

## 환경 분리

- development
- test
- demo/staging

실제 production을 주장하지 않는다. demo 데이터와 공식 데이터의 표시가 유지되어야 한다.

## 장애·복구

- DB/LLM/API 장애 시 raw question 임시 저장 금지
- 고정 공식 KB 템플릿 경로
- seed/migration 재현
- 빈 DB `supabase db reset` replay와 위험 변경의 명시적 보상/rollback SQL
- 백업 복구 후 서비스 개방 전 만료된 `masked_question` 재파기
- 배포 rollback 지침
- 발표용 캡처/녹화

local/private 합성 MVP의 기본 복구 목표는 RPO 24시간, RTO 60분이다. 승인 seed와 versioned migration을 1차 복구 수단으로 사용하고 매일 및 파괴적 migration/데모 milestone 직전에 gitignored local logical dump를 만든다. dump에는 비밀·실제 시민 데이터를 넣지 않으며 30일이 지난 dump는 삭제한다. 인수인계 전에 reset/replay 또는 dump restore와 서비스 개방 전 retention purge를 한 번 재현한다. COLLAB-001의 private GitHub remote가 실제 push되면 tracked Git history의 off-device 복사본은 생기지만 `.env`, ignored tool/runtime, Docker state와 logical dump는 백업되지 않는다. 실제·비재현 데이터나 공개 운영 전에는 별도 백업 위치·암호화·RPO/RTO·삭제 전파를 다시 승인한다.

## DB-001 local 운영 절차

1. Docker Desktop을 실행한다.
2. `scripts/bootstrap_patched_supabase.ps1 -VerifyOnly`로 source/runtime manifest와 patched CLI
   `2.109.1` hash를 확인한다.
3. `scripts/verify_database.ps1`로 PostgreSQL-only start, reset, credential rotation,
   pgTAP, 6단계 보상/부재, replay, integration을 실행한다.
4. 이미 DB가 실행 중일 때만 `scripts/verify_database.ps1 -SkipStart`를 사용한다.
5. 필요하면 `.\.tools\supabase\v2.109.1-sejong-loopback\supabase.exe stop`으로 정상 종료한다.

`supabase db reset --local`과 compensation은 disposable local DB에만 허용된다. remote DB,
실제 데이터, Docker volume에 실행하지 않는다. 공식 seed가 0이므로 검증 뒤에도
`/health=200`, `/ready=503`이 정상이며 READY-001이 eventual 200 전환을 소유한다.

local stack에는 개발용 기본 credential이 있고 production TLS/rate limit/admin protection이
없다. 따라서 runner가 Engine 28+와 actual single `127.0.0.1:54322`를 증명하지 못하면 reset
전에 중단한다. Q-SEC-004=A의 `default-local-port-binding`과 Q-SEC-005=A의
`local-only-port-binding`을 적용했지만 actual probe는 모두 `127.0.0.1`과 IPv6 wildcard `::`를
함께 생성했다. Q-SEC-006=A/D-031의 patched CLI는 2026-07-18 actual gate에서 exact one
`127.0.0.1:54322`, pgTAP 282, integration 8/8과 cleanup 0/0을 통과해 DB-001 local/private
기준선이 됐다. direct stock `db start`, PATH fallback과 `db diff`는 승인된 운영 경로가 아니다.
Q-SEC-003=A/D-046/D-092의 exact 22-signature `00700`은 matching compensation과 전체
local regression을 통과했다. remote/public deployment는 ADR-0026의 configured target과
citizen smoke가 별도로 필요하다. 인증 없는 public admin/API와 public backend DB credential은
금지되며 local baseline만으로 production-ready라고 부르지 않는다.

Q-SEC-004=A/D-029와 Q-SEC-005=A/D-030은 적용됐으나 exact local을 달성하지 못했다.
Q-SEC-006=A/D-031과 Q-TOOL-001=A/D-032가 explicit HostIP, short checkout, source/patch/runtime
pin을 구현했다. binary가 없거나 `-VerifyOnly`가 실패하면 DB mutation 없이 중단하고 tracked
manifest로 재빌드한다. unsafe runtime은 runner-owned cleanup으로 container 0을 확인하며 volume
삭제나 prune은 하지 않는다. local schema 복구는 patched runner의 `db reset --local`이고,
6개 compensation은 문서화된 disposable local replay에만 사용한다.

DB child가 timeout/실패하면 `73f300b`의 bounded process-tree cleanup이 descendant까지 종료·dispose한
뒤 runner-owned container cleanup을 수행한다. 재시작 전 project/all container 0/0을 확인하며
임의 process kill, stock fallback, volume delete/prune으로 우회하지 않는다.
[Docker port publishing](https://docs.docker.com/engine/network/port-publishing/), [Docker Desktop settings](https://docs.docker.com/desktop/settings-and-maintenance/settings/)
