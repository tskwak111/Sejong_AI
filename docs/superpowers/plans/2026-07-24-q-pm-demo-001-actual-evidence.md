# Q-PM-DEMO-001 local/private actual evidence 실행계획

> **Execution mode:** 승인된 기존 MVP를 다시 설계하지 않는다. 메인이 공유 결정·러너·통합을
> 소유하고, 서로 겹치지 않는 테스트·Frontend 감사만 병렬 위임한다.

- Plan ID: Q-PM-DEMO-001-PLAN
- Status: **Done — backend runner, opt-in actual browser, final DB probe and closeout gates PASS**
- Date: 2026-07-24 KST
- Base: `fcd0f0f` on `codex/LLM-002-upstage-synthetic-evaluation`
- Consumes: D-059/Q-MVP-002=A, MVP-001 final local/private implementation, immutable official `.2`
- Produces: 현재 DB 상태와 분리된 clean 19→20 actual HTTP evidence

## 1. 확정 데모 순서

1. `/ready=200`과 initial ACTIVE/OFFICIAL 19를 확인한다.
2. 데모 #4 `PERSONAL_LOOKUP` 질문을 `/api/v1/chat`에 보낸다.
3. HTTP 200 `FALLBACK`, `intent=UNKNOWN`, reason `PERSONAL_LOOKUP`,
   `candidate_eligible=false`를 확인한다.
4. #4 전후 `interaction_events`와 `failed_questions` count가 모두 동일함을 DB adapter를 통해
   확인한다. backend runner stdout/stderr/log/report에는 질문·UUID·DSN·secret을 출력하지 않는다.
5. 별도 데모 #5 `INSUFFICIENT_GROUNDING` 질문을 보낸다.
6. 실제 event와 candidate-eligible failed row 1건, idempotent replay를 확인한다.
7. OPERATOR가 reason을 확인하고 후보를 작성·제출한다.
8. 같은 작성자의 승인 시도는 차단하고 `PM-LOCAL-001`이 별도 승인한다.
9. 20번째 ACTIVE/OFFICIAL `KB-WASTE-03`와 same-query SUCCESS·서버 결합 공식 출처를 확인한다.
10. old idempotency replay는 기존 fallback을 유지하고 final ACTIVE 20을 확인한다.

## 2. 변경 경계

- Main-owned shared integration:
  `scripts/verify_actual_mvp_regression.py`, decision/source-of-truth, plan, version, note/INDEX.
- Delegated non-conflicting work:
  focused runner tests, Frontend actual API audit.
- Public OpenAPI, generated types, DB migration, official `.2`, package/lockfile는 변경하지 않는다.
- 새 production dependency, Upstage actual, remote DB, public deploy, auto merge는 금지한다.

## 3. TDD 및 검증

- [x] runner fake runtime에 count-only persistence snapshot interface를 RED로 추가한다.
- [x] PERSONAL_LOOKUP response와 zero-row-delta를 RED로 고정한다.
- [x] actual repository adapter가 두 table의 bounded integer count만 반환하도록 GREEN한다.
- [x] 기존 별도 INSUFFICIENT_GROUNDING 19→20 흐름과 출력 allowlist를 보존한다.
- [x] focused runner tests, relevant chat/admin/db tests, Ruff/Mypy를 실행한다.
- [x] clean reset + immutable `.2` seed 뒤 actual backend runner를 1회 실행한다.
- [x] clean 19에서 opt-in actual desktop browser를 1회 실행해 Frontend→API→DB→admin→재질의를 확인한다.
- [x] actual 실패 시 단계명+bounded reason만 기록하고 20/PASS를 주장하지 않는다.
- [x] actual PASS 뒤 영역 gate와 문서·secret·diff gate를 실행한다.
- [x] 최종 통합 직전에만 저장소 전체 gate를 실행한다.

## 4. 안전 중단 조건

- 질문 원문·masked text·UUID·DSN·secret이 stdout/stderr/log/report에 나타남.
- initial ACTIVE가 exact 19가 아니거나 `KB-WASTE-03`이 이미 ACTIVE임.
- PERSONAL_LOOKUP 뒤 event/failed count가 증가함.
- 작성자 본인 승인이 성공하거나 승인 전 KB가 ACTIVE 검색에 나타남.
- official `.2` byte 변경, 새 dependency, remote/public/provider 사용.

## 5. 완료 판정

- `PASS ready`
- `PASS initial-active count=19`
- `PASS personal-lookup persistence event_delta=0 failed_delta=0`
- `PASS insufficient-grounding event_delta=1 failed_delta=1`
- `PASS self-approval-blocked`
- `PASS candidate-approved`
- `PASS improved-requery public_id=KB-WASTE-03`
- `PASS final-active total=20 categories=4 count_each=5`
- actual stdout/stderr의 질문·UUID·DSN·secret 0

위 bounded 문구와 자동 테스트·영역 gate가 모두 통과해야 Done으로 전환한다.

## 6. 2026-07-24 실행 결과

- backend actual runner는 위 항목을 포함한 고정 15개 PASS line을 출력하고 initial 19→final 20,
  네 category 각 5개, target public ID 1개를 확인했다.
- opt-in desktop actual browser 1/1은 비식별 고정 fixture로 PERSONAL_LOOKUP 폴백, 별도
  INSUFFICIENT_GROUNDING, actual 관리자 후보·PM 승인, 동일 질문 SUCCESS와 공식 출처명·URL을
  Frontend→same-origin API→FastAPI→local DB에서 확인했다.
- candidate `activated_kb_id`는 public ID가 아닌 내부 UUID다. 공개 `KB-WASTE-03`은 최종 chat
  `sources[].source_id`에서만 판정한다.
- 브라우저 fixture text는 현재 탭 메모리 UI에 표시된다. 실패 시 local gitignored
  trace/screenshot이 생길 수 있으며, 이 증거는 backend count-delta 무저장 증거를 대체하지 않는다.
- final read-only probe는 ACTIVE 20, target 1, `/ready=200`을 확인했다. Upstage key/network/provider,
  remote DB, public deploy와 새 dependency 사용은 0이다.
