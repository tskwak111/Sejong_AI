# ADR-0018: public 준비 시 privileged function search path 전수 보정

- Status: Accepted / implementation authorized by D-092
- Date: 2026-07-20
- Deciders: 사용자, Codex
- Related: Q-SEC-003, D-046, A-021, ADR-0012, DB-001-A021 audit

## Context

read-only audit는 privileged execution graph를 `app_api` SECURITY DEFINER 9개와
중첩/helper/trigger `app_private` 13개, 합계 22개로 고정했다. `00600`이
`app_private.validate_active_kb_question()` 하나만 `search_path=pg_catalog, pg_temp`로
보정해 나머지 21개는 `pg_catalog` 단독이다. application relation/helper는 qualified이고
dynamic SQL은 0이지만, PostgreSQL 17의 안전한 SECURITY DEFINER 작성 지침을 public 경계에서
충족했다고 볼 수 없다.

## Decision

Q-SEC-003 선택지 A를 채택했다. D-092에서 public 준비와 실행을 승인했으므로 통합
CHAT-NATURAL 계획에서 구현한다.

- 새 forward migration `00700`은 audit에 기록된 exact 22 signature allowlist만 대상으로 한다.
- 함수 body, owner, signature, ACL, table, data와 public API는 바꾸지 않고 function property의
  `search_path`만 정확히 `pg_catalog, pg_temp`로 통일한다.
- matching compensation과 exact catalog/ACL/body fingerprint/behavior/compensation/replay
  regression을 함께 구현한다.
- 통합 written specification, matching rollback/pgTAP과 실행계획을 먼저 검증한다.
- `00700` 검증 전 remote migration/deploy는 차단한다. 검증 뒤에도 ADR-0026에 따라
  public admin/API는 인증이 없어 비활성이다.

## Alternatives considered

- 현재 posture를 영구 유지: local 범위에는 가능하지만 public 배포를 계속 막으므로 최종
  방향으로 선택하지 않았다.
- 함수 body rewrite 또는 TEMP revoke: property-only 최소 변경보다 영향 범위가 넓어 별도
  증거와 인간 승인이 없으면 수행하지 않는다.

## Consequences

현재 executable migration은 `00100`~`00670` 아홉 개이고
`database_schema=0.4.0-local`, pgTAP 9 files/356 assertions다. scope queue `00680` 뒤
`00700`을 적용한다. public citizen readiness는 두 migration·rollback·전체 regression과
ADR-0026의 configured-target smoke가 끝날 때까지 완료로 선언하지 않는다.

## Rollback

구현 전에는 이 ADR/결정 문서만 revert한다. 구현 후에는 적용된 `00700`을 수정하지 않고
matching rollback 또는 reviewed successor forward migration을 사용한다.
