# ADR-0026: 인증 없는 관리자를 제외한 controlled public citizen verification

- Status: Accepted / local hardening and preflight implemented / remote target not configured
- Date: 2026-07-27
- Decision authority: D-092, 사용자 actual/DB/public·remote 실행 승인
- Depends on: ADR-0002, ADR-0004, ADR-0018, ADR-0023, ADR-0025

## Context

프로젝트는 local/private MVP를 검증했지만 public hardening `00700`, remote DB와 배포는 보류돼
있었다. 사용자는 actual Upstage, DB reset/seed와 public/remote 작업을 명시적으로 승인했다.
그러나 현재 `/admin` actor header는 local demo capability이며 production 인증·RBAC가 아니다.
광범위한 승인을 인증 없는 관리자 공개나 실제 개인정보 전송으로 해석하면 비협상 안전 규칙을
위반한다.

## Decision

1. ADR-0018의 exact 22 signature `00700` property-only hardening과 matching rollback·pgTAP을
   구현한다.
2. 구성된 remote target과 credential이 있을 때 시민 `/health`, `/ready`, `/api/v1/chat`,
   `/api/v1/offices`만 배포·검증한다.
3. remote/public에서 `/admin`과 `/api/v1/admin/*`는 server-side로 비활성화하고 negative smoke를
   수행한다.
4. remote에 필요한 secret·DSN은 environment secret store로만 전달하고 출력·commit하지 않는다.
5. actual Upstage는 PII-free allowlisted synthetic fixture로만 수행한다. real citizen/free-input
   outbound는 개인정보·약관·법무 운영 gate 전에는 활성화하지 않는다.
6. target/credential이 없으면 새 계정이나 target을 추측해 만들지 않고 deploy를
   `Not executed: target not configured`로 기록한다.
7. remote migration·seed 실패 시 version/official_data를 승격하지 않고 마지막 검증 version으로
   rollback한다.

## Consequences

- public citizen demo를 준비·검증할 수 있으면서 인증 없는 관리자 노출을 막는다.
- remote 환경에서 template 시민 chat은 가능하지만 actual free-input LLM 운영은 아직 아니다.
- 배포 대상 계정·리전·비용·DNS가 저장소에 없으면 코드와 runbook까지만 완료될 수 있다.
- `00700`과 remote smoke는 local schema를 production-ready라고 자동 선언하지 않는다.
- 2026-07-27 actual discovery에서 public application target, remote DB project, deployment
  credential/origin/saved version이 모두 없었다. 따라서 remote migration·seed·deploy·smoke는
  `Not executed: target not configured`이며, 이는 실패나 완료를 과장하지 않는 승인된
  fail-closed 결과다.

## Rejected alternatives

- local demo header를 public 관리자 인증으로 사용: actor spoofing 위험 때문에 기각한다.
- 모든 public 시민 질문을 즉시 Upstage로 전송: 개인정보·약관·법무 운영 gate가 없어 기각한다.
- remote target을 자동 생성: 비용·소유권·리전 결정을 추측하므로 기각한다.

## Rollback

- `00700` matching rollback으로 function property를 복원한다.
- remote application은 마지막 검증 version으로 되돌리고 admin-disabled와 provider-disabled를
  확인한다.
- secret은 환경에서 rotate/revoke하며 Git history에 남기지 않는다.

## References

- D-046, D-092
- `docs/superpowers/specs/2026-07-27-natural-civic-dialogue-and-operations-design.md`
