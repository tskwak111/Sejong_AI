# IMP-20260724-010 — Q-PM-DEMO-001 반영: PL·LJ 완전 미저장과 fixture 강등

- Date/Time (KST): 2026-07-24
- Task ID: WEB-QPM-DEMO-001
- Type: implementation/security/frontend
- Status: Done — PR #8 merged; owner integration에서 note ID·INDEX 정규화
- Author/Agent: Claude Code (결정: PM Q-PM-DEMO-001·Q-MVP-002/D-059, 명세: 곽태성)
- Branch: `feat/web-p1-complete` (PR #8 source branch; owner integration `c15f61b`에 병합)
- Base: `9989ff8` (태성 리뷰 반영, IMP-20260724-009로 정규화)
- Related: [PR #8 역사적 mismatch 감사 C1/E1](../audits/FRONTEND_PR8_MISMATCH_REPORT.md),
  D-059/D-068, `apps/web/CLAUDE.md` §15, `apps/web/DESIGN.md` 부록 B

## 1. 사용자 요청과 완료 기준

### 요청

PM 결정 Q-PM-DEMO-001을 태성 명세대로 반영. `contracts/`·`apps/api/`·
`database/`·`supabase/` 수정 금지, manifest/lockfile·신규 production 의존성
금지, 실제 공식 데이터·비밀값 추가 금지, merge 금지.

### Acceptance Criteria

- [x] 질문 원문 URL 전달 제거 (`/chat?q=`·useSearchParams 폐지, 상태 전달) — IMP-20260724-009에서 선반영, 본 세션에서 유지 확인
- [x] PERSONAL_LOOKUP·LEGAL_JUDGMENT 미저장화: enqueueFailure에서 두 사유 제거, 초기 fixture PL 행 제거, 해당 폴백 "질문 내용은 저장되지 않았습니다" 표시 (INSUFFICIENT_GROUNDING만 30일 보관 고지)
- [x] fixture 강등: OFFICIAL 판정·APPROVED/ACTIVE 전환 로직 제거(전부 MOCK), fixture 승인·반려 버튼 비활성(사유 툴팁), 전 화면 샘플 배너, 미설정 기본 actual
- [x] 데모 #5 정합: 근거 부족 예시를 "침대 2인용 프레임 수수료" 계열로 교체 (fixture 문안만, 백엔드 시드 무변경)
- [x] CLAUDE.md·DESIGN.md에 제출 기준선 보존 + 구현 단계 변경 append (사유: 개인정보 최소수집 강화)
- [x] fixture 설명 "UI 개발·상태 확인 도구"로 수정 (README·.env.example·코드 주석)
- [x] README 실행 방법 actual 데모 기준 갱신 (run_local_api.py + local DB + env 4종)
- [x] 구현 노트 + INDEX 1행 append
- [x] lint·typecheck·unit test·build 전부 통과 + 신규 테스트 3종

## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who | 결정: PM(Q-PM-DEMO-001)·Q-MVP-002/D-059. 명세: 곽태성. 구현: Claude Code. 병합: owner/local integration `c15f61b`. |
| When | 2026-07-24 KST, PR #8 Draft 구현 뒤 owner integration 완료. |
| Where | `apps/web/src`(demo-fixtures·FallbackCard·KbCandidateReview·kb-candidates page·admin-flow.test), `apps/web/{README.md,CLAUDE.md,DESIGN.md,.env.example}`, `docs/implementation-notes/`. contracts/api/database/supabase·manifest/lockfile 무변경. |
| What | ① PL·LJ 실패 행 완전 미저장(초기 fixture PL 행 제거 포함) ② 폴백 저장 고지를 ISG만 30일 보관으로 축소 ③ fixture 후보 전부 MOCK·판정(승인·반려·ACTIVE) 비활성 ④ 데모 #5 근거 부족 예시를 침대 프레임 수수료로 재구성 ⑤ 문서: 기준선/변경 구분 append, fixture=개발 도구, actual 실행 가이드 |
| Why | 개인정보 최소수집 강화 — 개인별 조회·법적 판단 질문은 본인 식별 맥락 가능성이 높아 마스킹 후에도 미보관. D-059/D-068이 [역사적 감사 C1](../audits/FRONTEND_PR8_MISMATCH_REPORT.md)의 당시 모호성을 local/private의 "INSUFFICIENT_GROUNDING만 저장"으로 해소했다. fixture가 공식 데이터·실제 승인 흐름처럼 보이는 위험 제거(전부 MOCK + 배너 + 판정 비활성). |
| How | fixture transport의 `enqueueFailure`를 ISG 전용 시그니처로 축소, `reviewCandidate`는 항상 거부(throw), `data_origin` 고정 "MOCK". UI는 `reviewLocked` prop(=`mode==="fixture"`)으로 판정 바 비활성 + 사유 캡션·title 툴팁. 라우팅은 침대/프레임 키워드를 대형폐기물 SUCCESS 분기보다 먼저 검사. |
| How much | 코드 5파일 + 테스트 1파일 재작성 + 문서 4파일 + 노트/INDEX. 테스트 40/40. |

## 3. 테스트 기록

```text
Command: corepack pnpm --filter @sejong-ai/web typecheck && lint && test && build
Result: typecheck PASS / eslint PASS / vitest 8 files, 40/40 passed / next build exit 0

신규·갱신 테스트 3종 (admin-flow.test.tsx / chat-screen.test.tsx):
1) "stores only INSUFFICIENT_GROUNDING - PERSONAL_LOOKUP and OUT_OF_SCOPE
   leave zero rows" — PL·OOS 라우팅 후 failed row 총계 불변 + PL 행 0건,
   ISG만 +1 행. PASS
2) "creates fixture candidates as MOCK only and never transitions them to
   ACTIVE" — data_origin=MOCK 고정, APPROVED/REJECTED 판정 모두 reject,
   status PENDING_APPROVAL·activated_kb_id null 유지. PASS
3) "auto-sends the home-screen question from tab memory, consuming it once"
   — 질문 원문 URL 미포함(window.location.search === "") + 탭 메모리 1회성
   소비. PASS (page.test.tsx의 href="/chat" 검증과 쌍)

잔존 검색:
- grep "?q=|useSearchParams" apps/web/src → 기능 코드 0건 (설명 주석만)
- grep "PERSONAL_LOOKUP" demo-fixtures.ts → enqueue 경로 0건 (폴백 카드
  표시·라벨만 잔존 - 계약 표시용)
```

브라우저 확인 (fixture 명시 모드): 시민 #1(SUCCESS)·#2(지역 FOLLOWUP→SUCCESS)·
#3(FOLLOWUP)·#4(PERSONAL_LOOKUP 폴백 + "질문 내용은 저장되지 않았습니다")
렌더, 이음센터 열람(침대 프레임 ISG 행·PL 행 부재·승인/반려 비활성+캡션) 확인.
#5 완주는 actual 전용으로 fixture에서는 검증하지 않음 (Q-PM-DEMO-001).

Not run: actual 경로 end-to-end (local Supabase/Postgres + run_local_api.py
조합) — DB 기동이 필요한 별도 리허설. README 실행 방법에 절차 기록.

## 4. 데이터·보안·프라이버시 영향

- PERSONAL_LOOKUP·LEGAL_JUDGMENT 질문 텍스트가 fixture 스토어에도 일절
  저장되지 않는다 (이전 임시 상태였던 null 행 적재도 제거 — 행 자체 미생성).
- 폴백 저장 고지가 실제 저장 범위와 일치하게 됨 (과잉 고지 해소).
- fixture 데이터의 공식 데이터 오인 경로 차단: 전부 MOCK + 전 화면 배너 +
  판정 비활성 + 미설정 기본 actual.
- 실제 공식 데이터·비밀값 추가 없음. 계약·백엔드·DB·seed 무변경.

## 5. 위험과 롤백

- 경계: 계약 `StoredFailureReason` enum의 3종 범위는 PERSONAL_LOOKUP·
  LEGAL_JUDGMENT 저장을 승인하지 않는다. D-059/D-068의 local/private 생성 정책은
  `INSUFFICIENT_GROUNDING`만 저장하도록 유지되며, 이를 넓히려면 공개 계약과 개인정보
  정책에 대한 별도 인간 승인·결정 로그·테스트가 먼저 필요하다.
- 위험: actual 경로 데모 리허설(#5 침대 프레임 시나리오)은 백엔드 KB/시드
  상태에 의존 — 백엔드 시드는 이 PR에서 건드리지 않았으므로 리허설에서
  근거 부족 판정이 실제로 나는지 확인 필요.
- 롤백: `apps/web` + `docs/implementation-notes` 커밋 revert로 충분.
  계약·백엔드·DB 의존 없음.
