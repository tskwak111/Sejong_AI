# IMP-20260726-002 — LLM-003 local actual 실행과 aggregate 증거

- Date/Time (KST): 2026-07-26T09:49:33+09:00
- Task ID: LLM-003-ACTUAL
- Type: implementation-test-security
- Status: Done — local/private actual PASS
- Author/Agent: 사용자 승인 / Codex 실행·검토
- Branch: codex/LLM-003-local-actual-evidence
- Base commit: c575809
- Related plan/ADR/RFP: D-075 / ADR-0023 / LLM-003 plan / SFR-001 / SER-001

## 1. 사용자 요청과 완료 기준

### 요청

`local actual 실행 승인`.

### Acceptance Criteria

- 실제 local DB와 `/api/v1/chat`을 통해 고정된 비개인 10문항을 exact `solar-pro3`로 실행한다.
- stdout은 승인된 aggregate field만 포함하고 질문·답변·provider body·key·DSN은 출력하지 않는다.
- source 10/10, official mismatch 0, PII-free fixture typed write-boundary forbidden-value
  위반 0, outbound 10, GENERATED 최소 1,
  VAT 포함 USD 0.05 이하를 만족한다.
- 별도 forced timeout은 provider outbound 없이 TEMPLATE로 복구한다.
- 종료 뒤 grounded profile을 disabled로 되돌려 `/ready=200`, TEMPLATE regression을 확인한다.

## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 사용자가 network 실행을 승인했고 Codex가 local actual·TDD·검토를 수행 |
| When — 언제 | 2026-07-26 09:49~10:07 KST |
| Where — 어디서 | Windows local worktree, loopback Docker/Supabase PostgreSQL, Upstage direct API |
| What — 무엇을 | LLM-003 실제 10건, forced timeout, token/cost aggregate, DB login rerun 보정 |
| Why — 왜 | “근거가 없으면 지어내지 않는다”는 경계를 실제 provider에서도 증명 |
| How — 어떻게 | strict hash-bound runner, 실제 FastAPI TestClient/DB, server-owned source 비교, aggregate-only 출력 |
| How much — 어느 정도 | 최종 10 calls, GENERATED 4/TEMPLATE 6, legacy cost lower-bound USD 0.001319835, configured upper USD 0.0135168; DB schema·official data mutation 0 |

## 3. 시작 전 상태

- 관련 파일: LLM adapter/contracts, local DB provisioner, LLM-003 plan/report/runbook.
- 기존 동작: PR #12의 offline 구현과 provider-disabled final repository gate가 PASS했고 actual만
  인간 gate로 Pending이었다. actual 전용 runner와 content-free token aggregate는 없었다.
- 발견한 충돌/부채: local DB는 잘못된 상태가 아니라 승인 루프 뒤 ACTIVE 20이었다.
  기존 non-superuser login rotation이 PostgreSQL 17에서 no-op `NOSUPERUSER`를 다시 지정해
  `42501`을 냈다. 첫 semantic PASS는 dependency metadata가 aggregate 뒤에 출력됐다.
- Git 상태: base `c575809`, 격리 branch `codex/LLM-003-local-actual-evidence`.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| D-075 | Human | actual provider/key/network 사용 | 사용자 명시 승인 | 10-call gate 1회 승인; corrective second run은 별도 승인 없음 |
| A-048 | Resolved | 생성 결과의 안전 기준 | strict server fact gate 실패 시 전체 TEMPLATE | 공식 사실·출처 보존 |
| DB state | Internal | seed-cycle이 19만 기대하지만 현재 20 | reset하지 않고 `.2` 19 + 별도 승인 20 lineage 확인 | 승인 workflow 보존 |

## 5. 설계 결정과 대안

### 선택

실제 endpoint와 DB를 통과하는 인수 없는 고정 runner가 10건을 실행하고, provider result의 token
usage만 content-free 내부 값으로 전달해 최종 aggregate 비용을 계산한다. timeout은 별도 local
injection으로 검증해 외부 11번째 호출을 만들지 않는다.

### 이유

mock adapter만으로는 실제 network/JSON 변동/fallback 비용을 증명할 수 없다. 반대로 자유 질문이나
본문 출력은 승인 범위와 개인정보 정책을 벗어난다.

### 고려했지만 선택하지 않은 대안

- 기존 합성 evaluator 재사용: 실제 `/api/v1/chat`과 server-bound source를 검증하지 않아 제외.
- 답변별 결과 출력: 질문/답변/provider body 비저장 원칙과 충돌해 제외.
- ACTIVE 20 DB reset/재seed: 이미 승인된 20번째 KB를 손상하므로 제외.
- timeout도 실제 provider로 호출: 불필요한 비용과 비결정성을 추가해 제외.

## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| `llm/chat_contracts.py`, `llm/upstage_chat.py` | 성공/실패 모두 content-free `TokenUsage` 전달, strict usage parse | 비용 증거와 fail-closed 타입 경계 |
| `scripts/run_upstage_grounded_chat_actual.py` | hash-bound 10건, endpoint/DB/source/leak 검사, clean aggregate, forced timeout | 승인된 actual acceptance 자동화 |
| `scripts/tests/test_run_upstage_grounded_chat_actual.py` | fixture/source/cost/stdout/event-loop/suppression/value-free failure, usage completeness, forced-timeout consumption과 pre-write 10 tests | 실제 실행 전 보안 경계 |
| `scripts/provision_local_database_login.py` | 기존 role의 exact safe flags, 양방향 membership, capability role·exact member allowlist 확인 후 no-op `NOSUPERUSER` 생략 | PostgreSQL 17 non-superuser rerun-safe |
| LLM/provision tests | token usage와 role replay RED→GREEN | 회귀 방지 |
| plan/report/runbook/source-of-truth/version/note | D-075와 실제 수치 동기화 | 문서 권위 일치 |

### 데이터 흐름/상태 변화

원문 → 기존 마스킹/분류/ACTIVE·OFFICIAL retrieval/grounding → 최소 masked payload → Upstage
draft → strict ID/fact 검증 → GENERATED 또는 전체 TEMPLATE → 서버가 공식 source 결합.
tracked official data와 DB schema는 바뀌지 않았다. 각 성공 run은 10건과 forced timeout의
metadata-only interaction event 11건을 썼고 typed write shape에는 원문·답변·key 필드가 없었다.
출력 경계 보정으로 두 번 성공 실행했으므로 local DB에는 22건이 추가됐다. Final review에서 이
22건이 evaluation이 아니라 `is_test=false`로 잘못 표시됐음을 확인했다. 질문·답변·provider
payload는 없지만 EVENT/KPI 증거에서는 제외해야 한다. 현재 runner는 future write를
`is_test=true`로 강제하며 forbidden-value 감지 시 delegate 전 중단한다.

### 오류·빈 상태·롤백

초기 RNG one-liner 호환 오류는 provider call 0에서 fail closed했다. DB seed-cycle 오류는 실제
ACTIVE 20 상태를 확인해 reset하지 않았다. provision `42501`은 catalog flag 검증과 no-op 속성
생략으로 수정했다. 출력 경계 1차 실패는 suppression 테스트를 추가한 뒤 actual을 재실행했다.

## 7. 버전 전후

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Application | 0.9.0-grounded-local-chat | 0.9.1-grounded-local-chat-evidence | 내부 token evidence와 local runner |
| Web | 0.6.0-answer-mode | unchanged | 변경 없음 |
| API | 3.2.0-draft | unchanged | 공개 wire 변경 없음 |
| DB schema | 0.4.0-local | unchanged | migration 없음 |
| Official data | 0.1.0-initial.2 | unchanged | tracked release 불변 |
| Mock data | 0.0.0-not-populated | unchanged | mock 미사용 |
| Prompt set | 0.2.0-grounded-live-chat | unchanged | prompt 불변 |
| Test suite | 1.6.0-grounded-live-chat | 1.6.1-grounded-actual | actual/provision 회귀 추가 |
| Docs | 2.20.0 | 2.20.1 | D-075 actual evidence 동기화 |

## 8. 명령과 테스트 증거

| 명령/검증 | 결과 | 시간/개수 | 증거 경로 |
|---|---|---|---|
| focused LLM/chat/local pytest | PASS | 313 passed, 1 existing warning | 터미널 / 본 노트 |
| disabled regression | PASS | 56 passed, 5 subtests, 1 warning | 터미널 / 본 노트 |
| actual runner unit | PASS | 10 passed | runner test |
| local DB provision focused | PASS | 11 passed, 54 deselected, 14 subtests passed | provisioning test |
| full API | PASS | 2,021 passed, 8 local-DB skips, 5 subtests, 1 existing warning | `apps/api/tests` |
| actual + tooling scripts | PASS | 66 passed, 47 subtests | scripts tests |
| Ruff / Mypy | PASS | 7 files lint/format; 4 source files strict typecheck | source/tests |
| docs / secret / package / diff | PASS | documentation, current-tree secret, 12-file package, diff | repository gates |
| current-slice full offline controller | PASS | 모든 root/data/seed/Web/API/contracts/secret/bundle/package/diff step, 749.9s | `scripts/verify.ps1 -Offline` |
| final actual runner | PASS | 10 cases, GENERATED 4/TEMPLATE 6, outbound 10 | report aggregate |
| post-actual rollback | PASS | `/ready=200`, `answer_mode=TEMPLATE` | 본 노트 |
| direct venv scripts collection | FAIL then corrected | 2 attempts, provider/DB call 0 | missing `sejong_ai_api` path; self-contained test bootstrap added |

### Current-slice publication gate와 미실행 범위

Final review 보정 후 현재 최종 트리에서 provider-disabled full `verify.ps1 -Offline`을 다시
실행했다. 첫 시도는 Git에서 의도적으로 제외한 worktree `.tools`에 pinned patched Supabase
binary가 없어 `TEST-ROOT`의 runtime artifact 검사 2건이 실패했다. 원본 local workspace의
binary SHA-256을 tracked runtime manifest와 대조한 뒤 ignored worktree 경로에만 복제했고,
두 실패 테스트를 각각 재실행해 PASS한 다음 controller 전체를 처음부터 재실행했다. 두 번째
controller는 749.9초 후 모든 step PASS로 종료했다. 이 복제는 tracked 파일·비밀·DB를 바꾸지
않았다. public/remote, Cloud/CI, 실제 기관 계정 운영은 승인 범위 밖이므로 실행하지 않는다.

## 9. 보안·개인정보·접근성·성능 영향

- Privacy: stdout/file에는 raw/masked question, answer, provider body, key, DSN 0. actual metric은
  PII-free fixture의 typed `InteractionWrite` pre-write 검사이며 post-read forensic scan이 아니다.
  repository/schema tests가 금지 content field 부재를 별도로 검증한다.
- Security: exact provider/profile/cap, source/fact ownership, forced timeout fallback 유지.
- Accessibility: UI 변경 없음.
- Performance/cost: legacy runner가 최종 run 4183 input/954 output tokens, VAT 포함
  USD 0.001319835를 보고했지만 10/10 usage completeness 전이므로 lower-bound다. configured
  10-call upper bound USD 0.0135168은 cap USD 0.05 아래다. 출력 보정 전 semantic PASS까지
  합친 두 성공 run의 reported lower-bound는 USD 0.002635710, configured upper는 USD 0.0270336이다.

## 10. 데이터와 출처 영향

- 공식 데이터: immutable `.2` 19건과 별도 승인된 local 20번째 ACTIVE lineage를 read-only 확인.
- mock/AI 생성: 실제 모델 문장은 엄격 검증 뒤 4건만 응답에 사용, 6건은 TEMPLATE fallback.
- schema/lineage: migration/official release 변경 0; office 3, mapping 10 유지. local interaction
  metadata event 22건은 `is_test=false` 오표시 때문에 KPI에서 제외한다. 고유 evaluation marker가
  없어 별도 인간 승인 없이 targeted delete하지 않으며, cleanup은 disposable local DB reset 또는
  bounded deletion을 새 DB-data 삭제 승인 아래 수행한다.
- verified date: Upstage 공식 가격 2026-07-26 확인; DB actual 2026-07-26.

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- local/private actual은 PASS지만 public/remote 또는 실제 기관 운영 승인이 아니다.
- 최종 run은 GENERATED 4/10이다. 나머지 6건은 오류가 아니라 검증 실패 시 의도된 안전 TEMPLATE다.
- ignored local `.env`의 사용자가 넣은 key는 출력·커밋되지 않았고 process rollback 뒤 비활성이다.
  필요하면 사용자가 별도로 key를 제거/회전할 수 있다.
- 첫 semantic PASS와 clean-output 재실행으로 실제 provider call은 총 20회였다.
- 두 번째 10-call corrective run은 별도 인간 재승인 없이 수행됐다. A-049에서 governance
  incident 사후 확인을 Draft PR merge gate로 남긴다.
- 두 run의 22개 metadata event가 `is_test=false`로 잘못 표시됐다. 현재 runner는 수정됐지만 기존
  행 삭제는 DB-data 변경이므로 사용자의 별도 승인이 필요하다.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- `GroundedChatResult.usage`는 공개 응답에 포함되지 않는 frozen content-free 값이다.
- `_DiscardOutput`은 runner 내부 dependency 로그만 폐기하며 aggregate JSON은 마지막에 직접 쓴다.
- 기존 role은 catalog의 login/inherit/superuser/create-role/create-db/replication/bypass-RLS와
  role setting을 먼저 확인하고, password 게시 전 direct membership이 exact `sejong_backend`
  하나인지와 inbound admin membership이 exact `postgres` 하나인지 검증한다. capability role도
  `NOLOGIN`, 안전한 catalog flag/default, outbound membership 0, inbound member가 exact
  `postgres`와 `sejong_local_login` 두 개인지 검증한다.

## 13. 인수인계·재현·롤백

### 재현

`docs/runbooks/LLM-003-LOCAL-GROUNDED-CHAT.md` 순서대로 patched DB/ignored env를 준비한 뒤
새 인간 승인을 받은 경우에만 `scripts/run_upstage_grounded_chat_actual.py`를 한 번 실행한다.
key/DSN을 명령행에 넣지 않으며 재실행은 다시 승인받는다.

### 롤백

`UPSTAGE_GROUNDED_CHAT_MODE=false`, synthetic mode false로 새 process를 시작하고 `/ready=200`,
SUCCESS `answer_mode=TEMPLATE`을 확인한다. DB schema/official data rollback은 필요 없다.
오표시된 22개 interaction metadata는 KPI에서 제외한다. 자동 삭제하지 않고 인간 승인 뒤 disposable
local DB reset 또는 식별 가능한 bounded cleanup으로 정리한다.

### 다음 개발자 시작점

`scripts/tests/test_run_upstage_grounded_chat_actual.py`와 LLM-003 report의 exact aggregate를 먼저
읽는다. 현재 ACTIVE 20 DB를 19 seed-cycle로 reset하지 않는다.

## 14. 남은 위험·미해결 질문·다음 단계

- provider 응답 변동으로 GENERATED 비율은 run마다 달라질 수 있다. 공식 fact/source와 fallback
  경계가 acceptance authority다.
- existing Starlette/httpx TestClient deprecation warning은 새 dependency 없이 유지했다.
- public 개인정보·법무·계약·비용·배포 gate와 `00700`은 계속 미승인/보류다.

## 15. 자체 리뷰

- [x] 요청 충족
- [x] 테스트/검증
- [x] source-of-truth/계약/버전 동기화
- [x] 개인정보 원문 노출 없음
- [x] 구현 노트 INDEX 갱신
