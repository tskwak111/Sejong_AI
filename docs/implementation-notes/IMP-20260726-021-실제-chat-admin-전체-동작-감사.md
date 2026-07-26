# IMP-20260726-021 — 실제 Chat·Admin 전체 동작 감사

- Date/Time (KST): 2026-07-26T23:32:00+09:00
- Task ID: `ACTUAL-SYSTEM-AUDIT-001`
- Type: audit-diagnosis
- Status: Done — product code unchanged; one B/High decision and two confirmed P0 gaps
- Author/Agent: Codex
- Branch: `codex/POST-PR17-HUMAN-CHECKLIST-001`
- Base commit: `885638b` (documentation worktree), audited product `main@c945303`
- Related plan/ADR/RFP: `AGENTS.md`, SFR-001~005/011~013, ADR-0004/0007/0009/0010/0011/0021/0023,
  `APPROVAL_POLICY.md`, `KB_GUIDE.md`

## 1. 사용자 요청과 완료 기준

### 요청

여러 시민 질문과 다른 화면·동작을 실제로 테스트해 부족한 부분, 버그, 개선점을 찾는다.
관리자 KB 초안이 생성되지 않는 것처럼 보이는 이유와 AI 연결 필요 여부도 확인한다.

### Acceptance Criteria

- 실제 Web/API/admin/office 경로를 여러 질문·화면 크기로 검사한다.
- 문제를 재현하고 source-of-truth·계약·코드에서 root cause를 확인한다.
- 개인정보·DB final state·provider actual을 오염시키지 않는다.
- 발견을 우선순위와 인간 결정/AI 기본값으로 분리해 감사 문서에 기록한다.
- 제품 코드는 승인 없이 수정하지 않는다.

## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 사용자가 actual UX와 관리자 초안 문제를 제보했고 Codex가 시민·관리자·계약·코드를 교차 감사했다. |
| When — 언제 | 2026-07-26 KST |
| Where — 어디서 | local Web/API/DB, `/chat`, `/admin`, `/admin/failures`, `/admin/kb-candidates`, office API, 격리된 docs worktree |
| What — 무엇을 | 질문 10종, browser 흐름, admin actual state, 반응형 5 routes×2 widths, 전체 API/Web/contract tests를 검사했다. |
| Why — 왜 | 데모 통과만이 아니라 source-of-truth가 약속한 일반 시민·운영자 흐름이 실제로 도달 가능한지 확인하기 위해서다. |
| How — 어떻게 | 실제 browser, UTF-8 request bytes, read-only API, focused/full automated tests, 코드와 권위 문서 역추적 |
| How much — 어느 정도 | actual 질문 10종, responsive 10 route-width 조합, API 2044/Web 56/contracts 90 tests; product mutation 0 |

## 3. 시작 전 상태

- 관련 파일: chat classifier/service/response, Web chat/admin pages, candidate draft builder,
  office endpoint/client, active contracts와 approval policy.
- 기존 동작: 구체 질문과 final 19→20 승인 rehearsal은 완료됐으나 generic followup,
  일반 후보 authoring, 최초 region entry는 actual 일반화 검증이 없었다.
- 발견한 충돌/부채: 화면은 “AI가 작성한 초안”이라고 표현하지만 candidate builder는
  exact WASTE-03 hardcoded canonical draft이며 일반 AI draft transport가 없다.
- Git 상태: primary `main@c945303`의 tracked `apps/web/next-env.d.ts`는 사용자 `next dev`가
  만든 변경 1건이 있어 보존했다. 본 작업은 기존 documentation worktree에서만 수행했다.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| Q-CHAT-FOLLOWUP-001 | B/High | CERT 전용 option | Pending; A 추천 | 시민 완주, classifier/service/Web tests |
| A-054 | B/High | arbitrary eligible failure authoring | P0 requirement already confirmed; implementation pending | admin Web/transport/validation |
| A-055 | B/High | 최초 지역 선택 | direct selection P0 already confirmed; implementation pending | region state, office card E2E |
| A-056 | C | 승인/반려 이력과 정확한 문구 | status tabs와 non-AI copy 기본값 | admin UX |

## 5. 설계 결정과 대안

### 선택

진단 단계에서는 제품 동작을 바꾸지 않았다. 일반 후보 authoring은 LLM 자동 작성이 아니라
운영자 구조화 폼을 권고한다. 공식 답변·수수료·담당 부서·출처는 사람이 승인된 근거에서
작성하고, AI를 쓰더라도 대표 질문 일반화 등 비공식 보조에만 제한한다.

### 이유

`APPROVAL_POLICY.md`가 공식 필드의 인간 작성과 별도 승인을 요구한다. provider 연결로
초안을 자동 생성하면 출처 hallucination과 승인 책임 혼동이 생긴다.

### 고려했지만 선택하지 않은 대안

- Upstage key를 admin draft에 바로 연결: 승인된 정책 밖이고 공식 사실 생성 위험이 있어 제외.
- exact WASTE-03 demo-only 유지: 빠르지만 일반 운영센터라고 보기 어려워 B안으로만 남김.
- approved 후보를 현재처럼 숨김: 데이터는 보존돼도 사용자가 “초안이 없다”고 오해해 제외 권고.

## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| `docs/audits/ACTUAL_CHAT_ADMIN_SYSTEM_AUDIT_20260726.md` | actual matrix, root cause, gap, 질문, 검증 증거 | 재현 가능한 감사 |
| `docs/11_AMBIGUITY_REGISTER.md` | A-053~A-057 | 인간 결정과 defaultable/internal 분리 |
| `CHANGELOG.md`, `versions/manifest.json`, version docs | docs 2.21.6→2.21.7 | 버전 정합 |
| product/API/Web/DB/data/provider/tests | 변경 없음 | diagnosis scope |

### 데이터 흐름/상태 변화

read-only 조회만 수행했다. UTF-8 actual 질문은 normal metadata 경로를 통과할 수 있으나
새 failed row는 0이었고 기존 failed/candidate는 각각 1/1로 유지됐다. 관리자 create/approve,
reset/seed/purge는 실행하지 않았다.

### 오류·빈 상태·롤백

관리자 후보 empty state는 실제 후보 0이 아니라 pending 후보 0이다. 승인 후보 1건은
DB/API에 남아 있다. 문서 rollback은 이 docs-only commit을 revert하면 되며 DB rollback은 없다.

## 7. 버전 전후

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Application | 0.10.0-office-directory-runtime | 동일 | 제품 미변경 |
| Web | 0.6.0-answer-mode | 동일 | Web source 미변경 |
| API | 3.3.0-draft | 동일 | 계약·route 미변경 |
| DB schema | 0.4.0-local | 동일 | migration/write 없음 |
| Official data | 0.1.0-initial.2 | 동일 | ACTIVE data 변경 없음 |
| Mock data | 0.0.0-not-populated | 동일 | mock 없음 |
| Prompt set | 0.2.0-grounded-live-chat | 동일 | provider actual 0 |
| Test suite | 1.8.0-local-demo-readiness | 동일 | test source 미변경 |
| Docs | 2.21.6 | 2.21.7 | actual chat/admin audit |

## 8. 명령과 테스트 증거

| 명령/검증 | 결과 | 시간/개수 | 증거 경로 |
|---|---|---|---|
| 실제 browser chat | 구체 CERT SUCCESS+source, context followup PASS, generic CERT loop FAIL | 3 흐름 | audit report |
| UTF-8 API matrix | 정상/모호/정책/PII 10종 실행 | 9 expected, 1 UX fail | audit report |
| admin/office read-only API | ready 200, failed 1, approved candidate 1, office match 1 | 5 checks | audit report |
| responsive browser audit | horizontal overflow 0 | 5 routes×390/430 | audit report |
| API focused | PASS | 106 passed | local stdout |
| API full | PASS with gated skips | 2044 passed, 8 skipped, warning 1 | local stdout |
| Web focused/full | PASS | 21/56 passed | local stdout |
| Web lint/typecheck | PASS/PASS | Web | local stdout |
| contract generate/tests | PASS | 90 passed | local stdout |
| secret pattern scan | PASS | tracked tree | local stdout |

### 미실행 검증과 이유

- state-changing admin actual E2E: final 20 ACTIVE DB를 오염시키므로 미실행.
- local DB pgTAP/integration: full API에서 8개 local gate skip.
- Web build: 사용자의 `next dev`와 같은 `.next` 동시 사용 충돌 방지.
- provider actual: future rerun은 매회 인간 승인이 필요해 0회.
- root aggregate 최초 1회: 124초 timeout으로 결과를 폐기하고 잔여 process를 종료했다.

## 9. 보안·개인정보·접근성·성능 영향

- Privacy: 개인조회·법적판단·PRIVACY_UNRESOLVED는 failed row 증가 0을 확인했다.
- Security: secret/DSN/value 출력 0, provider call 0, DB state-changing admin call 0.
- Accessibility: 390/430 overflow 0, 실제 버튼·heading 존재 확인. 수동 screen reader는 미실행.
- Performance/cost: actual provider 비용 0. 이번 감사는 performance benchmark가 아니다.

## 10. 데이터와 출처 영향

- 공식 데이터: 변경 0; 구체 질문 source card는 승인된 metadata에서 결합됨을 확인.
- mock/AI 생성: 사용 0.
- schema/lineage: 변경 0.
- verified date: 2026-07-26 KST.

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- 관리자 초안 문제는 AI 연결 문제가 아니다.
- Q-CHAT-FOLLOWUP-001의 exact option 선택만 인간 확인이 필요하다.
- 일반 운영자 작성 폼과 최초 지역 직접 선택은 이미 P0로 확정됐으므로 재승인 질문이 아니다.
- 현재 approved candidate는 존재하며 pending-only 화면에서 숨겨져 있다.
- public/remote/provider rerun/DB reset은 이번 감사가 승인하지 않는다.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- classifier generic cue와 service UNKNOWN options가 certificate loop의 server root cause다.
- candidate page의 `PENDING_APPROVAL` filter가 approved candidate visibility root cause다.
- exact WASTE-03 guard와 hardcoded canonical fields가 general authoring gap의 root cause다.
- office API 자체는 정상이므로 region 문제는 Web entry-state 문제다.

## 13. 인수인계·재현·롤백

### 재현

감사 보고서의 질문 matrix와 화면 경로를 사용한다. PowerShell 5.1에서는 한글 JSON을
`[Text.Encoding]::UTF8.GetBytes()`로 전송해야 test client 인코딩 오진을 피할 수 있다.

### 롤백

docs-only 변경 commit을 revert한다. product/DB/data/provider rollback은 없다.

### 다음 개발자 시작점

Q-CHAT-FOLLOWUP-001 답을 받은 뒤 certificate FOLLOWUP을 먼저 닫고, 이미 확정된 P0인
admin authoring/history → region entry 순서로 각각 spec/plan/TDD vertical slice를 진행한다.

## 14. 남은 위험·미해결 질문·다음 단계

- generic certificate loop는 사용자 완주를 막으므로 가장 먼저 수정한다.
- admin general authoring이 없으면 운영센터는 WASTE-03 demo 전용에 머문다.
- region entry가 없으면 P0 office card의 actual 접근성이 닫혀 있다.
- KPI·performance Phase B·public deploy는 별도 결정 뒤 P1/P2로 유지한다.

## 15. 자체 리뷰

- [x] 요청 충족
- [x] 테스트/검증
- [x] source-of-truth/계약/버전 동기화
- [x] 개인정보 원문 노출 없음
- [x] 구현 노트 INDEX 갱신
