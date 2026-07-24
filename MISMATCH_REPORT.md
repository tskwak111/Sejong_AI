# MISMATCH_REPORT — 프론트엔드 ↔ 계약·백엔드 전면 대조 감사

- 감사일: 2026-07-24 / 브랜치: `feat/web-p1-complete`
- 기준(우선순위 순): `contracts/openapi-v1.yaml` → `contracts/chat-response.schema.json`·`kb-record.schema.json` → `contracts/fixtures/**`(valid·invalid 전체) → `packages/shared-contracts/src/generated/api.ts` → `apps/web/src/lib/chat-api.ts`·`admin-api.ts` → `apps/api/src/sejong_ai_api/contracts/`·`api/`·`chat/`·`admin/`
- 대조 대상: **`apps/web/src` 전체** (시민 화면·이음센터·데이터 계층·fixture).
  `frontend/` 폴더는 커밋 `096ef48`에서 삭제되어 현재 **빈 폴더**다. IDE에 열린
  `frontend/types/api.ts`는 삭제 전 버퍼이며 감사 대상이 아니다.
- 이 세션에서는 어떤 코드도 수정하지 않았다. 보고서만 작성.

표기: 심각도 = 상 / 중 / 소. "actual"은 `CHAT_UI_MODE=actual`·`ADMIN_UI_MODE=actual`(실 API 경유), "fixture"는 로컬 시연 버전(demo-fixtures)을 뜻한다.

---

## 요약

| 분류 | 건수 | 핵심 |
|---|---|---|
| A. 필드명·구조 | 1 (경미) | 이관 커밋(9dea281)에서 계약 생성 타입으로 전면 교체되어 필드명 수준 불일치는 사실상 해소됨 |
| B. 개념 | 9 | caution·딥링크·피드백 전송·KPI 스키마 등 "계약에 없는 UI 데이터"가 다수 — 전부 UI 상수/미연결로 이미 방어됨 |
| C. 흐름 | 5 | **백엔드 구현이 PERSONAL_LOOKUP·LEGAL_JUDGMENT를 실패 큐에 저장하지 않음(계약과도 다름)** — 최대 이슈 |
| D. 정책 | 1 (+일치 확인 다수) | 폴백 카드의 "30일 보관" 고지가 백엔드 실제 저장 범위보다 넓음 |
| E. 데모 영향 | fixture 0 / actual 3 | fixture 모드 5문항은 코드 검토상 완주 가능. actual 모드는 #4→#5 큐 유입이 깨짐 |

---

## A. 필드명·구조 불일치 (기계적 매핑으로 해결 가능)

`packages/shared-contracts/src/generated/api.ts`의 생성 타입을 `chat-api.ts`/`admin-api.ts`/컴포넌트가 직접 import하므로, 필드명·중첩 구조 수준의 불일치는 컴파일 타임에 차단된다. 잔여 항목은 1건뿐.

| 화면/컴포넌트 | 프론트 기대 | 계약/백엔드 실제 | 심각도 | 수정 방향 |
|---|---|---|---|---|
| 이음센터 목록 카운트 (`admin/failures/page.tsx:209`, `admin/page.tsx` 등) | `items.length`로 건수 재계산, 응답의 `total` 미사용 | `FailedQuestionListResponse`·`KBCandidateListResponse`는 `total` 필수(`invalid-list-missing-total.json`이 누락을 금지) | 소 | 표시 건수를 `total`로 교체(현재는 페이지네이션이 없어 값이 같음) |

**작업량 추정: 소** (반나절 미만).

---

## B. 개념 불일치 (계약에 없는 데이터 / 계약에 있는데 안 쓰는 데이터)

| 화면/컴포넌트 | 프론트 기대 | 계약/백엔드 실제 | 심각도 | 수정 방향 |
|---|---|---|---|---|
| B1. SUCCESS 답변 카드 주의사항 (`AnswerCard.tsx`) | CLAUDE.md §4-A: `caution` 값이 있으면 반드시 표시 | `ChatResponse`에 caution 필드 없음. `kb-record.schema.json`·`KBCandidateSummary`에는 존재하나 응답으로 전달되지 않음 (`build_success_response`도 미포함) | 중 | 현행대로 표시 포기 유지. 계약 변경 목록 ①로 이관 |
| B2. 딥링크 CTA (`AnswerCard.tsx:309`, `FallbackCard.tsx:139`) | "정부24에서 바로 신청"·"위택스에서 조회" 버튼 | 계약 응답에 deep_link 없음 → intent별 UI 상수(`labels.ts DEEP_LINK_BY_INTENT`, `PERSONAL_LOOKUP_DEEP_LINK`)로 대체 중 | 중 | 상수 유지(공식 대표 주소만). 계약 변경 목록 ④ |
| B3. 만족/불만족 전송 (`FeedbackButtons.tsx`, `FeedbackReasonSheet.tsx`) | 분야+사유 코드 전송 (제안서 3.2) | 계약에 피드백 엔드포인트 자체가 없음. `interaction-event.schema.json`에도 만족도 필드 없음. 사유 코드 4종(INACCURATE 등)은 FE 임의 정의 | 중 | 현행(탭 메모리 소비, 미전송) 유지. 계약 변경 목록 ② |
| B4. Overview KPI 5종 (`admin/page.tsx`, `demo-fixtures.ts DEMO_KPI`) | `total_questions`·`auto_answer_rate` 등 5개 필드 | `/api/v1/admin/quality-summary`는 200 응답 스키마 미정의(`content` 없음)이고, **백엔드에는 라우트 자체가 없음**(`api/admin.py`에 미구현). DEMO_KPI 필드명은 FE 임의 | 중 | fixture 전용 표시 + actual "미제공 안내" 현행 유지. 계약 변경 목록 ③ |
| B5. FOLLOWUP 관련 민원 한 줄 제안 (데모 #3, CLAUDE.md §4-B) | "대형폐기물 배출도 확인해 보세요" 류 제안 | 계약 `followup_options`는 `string[]`뿐, 관련 민원 필드 없음 → `FollowupCard.tsx` 미구현 | 소 | 계약 변경 목록 ⑦. 필요 시 UI 상수로도 가능하나 P0 범위 아님 |
| B6. `/api/v1/offices` | (미사용 — "동 변경"은 재질문으로 대체) | 계약·생성 타입에는 존재. **백엔드 `main.py`에 offices 라우터 미탑재** — 양쪽 모두 안 씀 | 소 | 그대로 두거나 계약 변경 목록 ⑧ |
| B7. 계약 기능 미사용: `listFailedQuestions`의 `reason`/`status` 쿼리 필터, `GET /failed-questions/{id}` 상세, `Source.used_fields` | 목록 클라이언트 필터링·목록 재사용으로 대체 (`failures/page.tsx`, `kb-candidates/page.tsx`) | 계약은 서버 필터·상세 조회·사용 필드 목록을 제공 | 소 | 기능상 문제 없음. 데이터가 커지면 서버 필터로 전환 |
| B8. 오류 envelope 내용 미소비 (`chat-api.ts:44`, `admin-api.ts:69`) | HTTP status로만 retryable 분기, `error.request_id`·`retryable`·`Retry-After` 미파싱 | 503 envelope `retryable: true` 고정, `Retry-After` 헤더 제공 | 소 | 현행 status 분기 결과가 계약 상수와 동치라 실질 문제 없음. 문의용 request_id 표시는 선택 개선 |
| B9. `repeat_count`(반복 질문 수) | 미표시 (CLAUDE.md 구버전 언급) | 계약에 없음 | 소 | 표시 포기 확정 (이미 §14에 보고된 항목) |

**작업량 추정: 중** — 단, B1~B5는 전부 계약 확정이 선행돼야 하며 FE 단독으로 지금 할 일은 없음(이미 상수/미연결로 방어 완료). FE 단독 몫(B7·B8)은 소.

---

## C. 흐름 불일치 (상태 전이·엔드포인트 순서)

| 화면/컴포넌트 | 프론트 기대 | 계약/백엔드 실제 | 심각도 | 수정 방향 |
|---|---|---|---|---|
| C1. 폴백→실패 큐 유입 (`FallbackCard.tsx:196` 저장 문구, `demo-fixtures.ts enqueueFailure`, 이음센터 전체) | 계약 `StoredFailureReason` 3종(INSUFFICIENT_GROUNDING·PERSONAL_LOOKUP·LEGAL_JUDGMENT)이 큐에 저장됨 (fixture도 3종 저장 구현) | **백엔드 구현은 INSUFFICIENT_GROUNDING만 저장** — `chat/service.py:257-271`에서 PERSONAL_LOOKUP·LEGAL_JUDGMENT는 `interaction=None`으로 이벤트·실패 행 모두 미생성. OUT_OF_SCOPE는 이벤트만 기록(행 미생성, 계약과 일치) | **상** | FE 잘못 아님 — **계약(3종 저장) vs 백엔드 구현(1종 저장)의 충돌**. 백엔드 팀과 어느 쪽이 정본인지 확정 필요. FE는 결정 전까지 D1 문구만 방어적으로 손보면 됨 |
| C2. 지역(동) FOLLOWUP (`chat-screen.tsx selectFollowup`, `FollowupCard.tsx` 지도핀 분기, 데모 #2 파생) | 지역명 3개가 `followup_options`로 내려오면 `selected_region`으로 승격해 원 질문 재전송 | 백엔드는 지역 FOLLOWUP을 발급하지 않음 — `_FOLLOWUP_OPTIONS`는 항상 4개 분야 라벨(`response.py:34-39`)뿐. 지역은 `selected_region` 파라미터/context_token으로만 반영되고 질문 텍스트에서 동을 파싱하지 않음 | 중 | 지역 승격 로직은 fixture 전용으로 남음(문자열 계약이라 위반은 아님). actual에서 지역 반영은 "동 변경" 인라인 선택 경로만 유효 — 데모 #2를 actual로 돌릴 계획이면 백엔드 지역 FOLLOWUP 발급 또는 질문 내 동 파싱 필요 |
| C3. FOLLOWUP 선택지 재전송 방식 (`chat-screen.tsx:198-209`) | 선택지 문자열을 그대로 새 질문으로 POST | 계약·백엔드에 "선택지 회신" 개념 없음(문자열 계약이니 합법). 백엔드 라벨("전입·주민등록"·"지방세 일반 안내" 등)은 키워드 분류기(`_EXPLICIT_INTENT_TERMS`)에 걸리도록 구성돼 있어 실동작 가능성 높음 — 다만 보장은 없음 | 소 | 현행 유지 가능. 구조화가 필요하면 계약 변경 목록 ⑤ |
| C4. 사유 확정 (`failures/page.tsx confirmReason`) | 현재 저장된 사유를 그대로 `PATCH /reason`으로 확정 (재분류 UI 없음) | 계약·백엔드는 3종 중 임의 사유로 **재분류하며 확정**하는 것을 허용 (`admin/service.py confirm_reason`) — 확정 시 candidate_eligible도 사유에 맞춰 갱신 | 소 | 동작은 계약에 부합. 데모 #5의 "사유 분류" 연출을 살리려면 확정 전 사유 선택 드롭다운 추가(선택 개선) |
| C5. `data_origin` 판정 (`demo-fixtures.ts OFFICIAL_SOURCE_URLS`, `KbCandidateReview.tsx` MOCK 차단) | fixture: 허용 URL 1개만 OFFICIAL, 그 외 MOCK → 승인 차단 시연 | 백엔드 `create_candidate`는 항상 `DataOrigin.OFFICIAL`로 생성하되, 출처 호스트 allowlist 6개(`admin/service.py:80-89`) 밖이면 422로 거절 — **actual에서는 MOCK 후보가 API로 생성될 수 없음** | 소 | FE의 MOCK 처리 UI는 무해(계약상 MOCK이 목록에 올 수 있으므로 유지). fixture 판정 로직이 백엔드와 다르다는 것만 인지 |
| C6. 이음센터 오류 구분 (`admin-api.ts AdminTransportError`) | status≥500만 retryable, 403/404/409/422 미구분 — 모든 실패가 동일 토스트 | 계약은 `ADMIN_FORBIDDEN`(403)·`ADMIN_NOT_FOUND`(404)·`ADMIN_INVALID_STATE`(409)·`ADMIN_VALIDATION_FAILED`(422) 5종 코드 제공 | 소 | FE가 자기검수·상태 조건을 사전 차단하고 있어 실사용 영향 낮음. 코드별 토스트 문구 분기는 선택 개선 |

일치 확인(문제 없음): KB 후보 생성 조건(REASON_CONFIRMED + INSUFFICIENT_GROUNDING + candidate_eligible)의 FE 버튼 노출 조건 일치 · `DRAFTED→PENDING_APPROVAL→APPROVED/REJECTED` 전이와 create→submit 연쇄 호출 일치 · 자기검수 금지·APPROVER 전용 판정·review_comment 필수 일치 · Idempotency-Key 발급/재시도 재사용 규칙 일치 · X-Demo-Actor-Id/Role 헤더와 허용 actor 2종(`OPERATOR-LOCAL-001`/`PM-LOCAL-001`)이 백엔드 `_ALLOWED_DEMO_ACTORS`와 정확히 일치.

**작업량 추정: 중~대** — C1은 FE 단독으로 해결 불가(계약·백엔드 결정 종속). FE 몫(C2 방어 확인, C4·C6 선택 개선)은 중.

---

## D. 정책 불일치 (저장·미보관·파기·마스킹)

| 화면/컴포넌트 | 프론트 기대(표시) | 계약/백엔드 실제 | 심각도 | 수정 방향 |
|---|---|---|---|---|
| D1. 폴백 카드 저장 고지 (`FallbackCard.tsx:193-197`) | INSUFFICIENT_GROUNDING·PERSONAL_LOOKUP·LEGAL_JUDGMENT 모두 "개인정보를 가린 채 30일간만 보관돼요" | 계약 기준으로는 3종 저장이 맞지만, **백엔드 구현은 INSUFFICIENT_GROUNDING만 저장(C1)** → PERSONAL_LOOKUP·LEGAL_JUDGMENT에서 실제로는 저장하지 않는데 저장한다고 고지(과잉 고지) | 중 | C1 결정에 종속. 계약이 구현 쪽으로 바뀌면 두 사유의 문구를 "저장되지 않았습니다"로 분기 — FE 수정량은 조건식 한 곳 |

일치 확인(invalid fixture 대조 포함):
- **PRIVACY_UNRESOLVED 고정 문구** — fixture(`demo-fixtures.ts:325-334`)와 표시가 계약 상수(제목·메시지·next_actions 1건)와 문자 단위 일치. `invalid-privacy-copy.json`이 금지하는 "원문 재전송 유도" 없음. office 항상 null 전제(`invalid-privacy-office` 금지 형태)도 준수 — FE는 office 분기 자체를 타지 않고 "질문 내용은 저장되지 않았습니다"만 표시.
- **NULL 파기 행** — `FailureTable`·Overview·`KbCandidateReview`가 `masked_question === null`을 "보관 기간 경과 (질문 텍스트 파기됨)"로 안전 렌더링. 파기 행은 KB 후보 생성 버튼 차단("텍스트 파기로 후보 작성 불가"). `invalid-failed-*` 불변식(텍스트↔purge 동시 전이, 만료 전 파기 금지, 30일 정확)은 서버 책임이며 FE는 어느 형태가 와도 깨지지 않음.
- **context_token** — React ref(탭 메모리)만 사용, FALLBACK 응답 시 null 초기화(`chat-screen.tsx:112-113`), 표시·로그·스토리지 저장 없음. 계약 `x-chat-context-policy`(current-tab-memory-only) 준수. 만료 토큰은 오류가 아닌 무맥락 처리 — 별도 만료 UI 없음도 계약과 일치.
- **브라우저 스토리지** — `apps/web/src`에 localStorage/sessionStorage 사용처 없음(대화는 state, 이음센터 mock DB는 모듈 스코프 메모리).
- **오류 시 입력 echo** — FE 오류 UI가 질문 원문을 오류 메시지에 싣지 않고, 값 없는 `ChatTransportError`만 사용(`invalid-admin-error-echo`·`invalid-admin-error-message`가 금지하는 패턴 없음).
- **불만족 피드백** — 자유 텍스트 입력란 자체가 없음(분야+사유 코드 라디오만), 질문 원문 미포함.
- **OUT_OF_SCOPE "저장되지 않았습니다"** — 백엔드도 행 미생성(비식별 이벤트만 기록)이라 고지 정확.
- **질문 입력 maxLength 1000** — 계약 `question` max 1000과 일치.

**작업량 추정: 소** (D1 문구 분기 한 곳 — 단 C1 결정 이후).

---

## E. 데모 영향 (5문항 완주를 직접 깨뜨리는 것만)

**fixture 모드(= 로컬 시연 버전, 제안서 7.4 백업): 깨뜨리는 불일치 없음.**
데모 #1~#4 응답, #4 폴백의 큐 상시 존재(`DEMO_PERSONAL_FAILURE_ID` NEW 고정), #5의 사유 확정→초안 생성→제출→승인(ACTIVE) 전 구간이 계약 불변식을 지키며 인메모리 스토어로 이어짐을 코드 검토로 확인.

**actual 모드로 시연할 경우 깨지는 것:**

| # | 데모 단계 | 깨지는 지점 | 원인(위 분류) | 심각도 |
|---|---|---|---|---|
| E1 | #4 → #5 전환: "제 자동차세…" 폴백이 이음센터 큐에 **도착하는 순간** | PERSONAL_LOOKUP 폴백이 실패 질문 행을 만들지 않아 큐에 아무것도 도착하지 않음. 신규 도착 하이라이트(`failures/page.tsx knownFailureIds`) 연출도 무의미해짐 | C1 (백엔드 구현 ≠ 계약) | **상** |
| E2 | #2 "아름동에서 대형폐기물…" 지역 조건 반영 | 백엔드는 질문 텍스트의 동을 파싱하지 않고 지역 FOLLOWUP도 발급하지 않음 → `selected_region` 미지정 시 office 없는 답변(또는 KB 부족 시 폴백). "질문에 동이 포함된 경우" 요구(CLAUDE.md §5)가 actual에서 미충족 | C2 | 중 |
| E3 | #5 마무리 화면(운영 현황 KPI) | quality-summary 미구현·스키마 미정의로 actual에서는 "미제공 안내"만 표시 | B4 | 소 |

참고(완주는 되지만 요구 요소 누락): 데모 #3의 "관련 민원 한 줄 제안"(B5), 데모 #1 카드의 caution(B1)은 fixture·actual 모두에서 표시 불가 — 계약에 필드가 없기 때문.

**수정 우선순위 1번은 E1(=C1)이다.** 단 이것은 프론트 수정 사항이 아니라 계약↔백엔드 정합 결정 사항이며, 결정 전까지 데모는 fixture 모드로 완주 가능하다.

---

## 계약 쪽이 바뀌는 게 합리적으로 보이는 지점 (계약은 수정하지 않음 — 목록만)

1. **SUCCESS 응답에 `caution` 추가** — KB record·KB 후보에는 이미 있는 필드가 응답에서만 유실된다. CLAUDE.md §4-A("값 있으면 반드시 표시")를 만족할 유일한 경로.
2. **만족/불만족 피드백 엔드포인트 + 사유 코드 enum** — 현재 FE 수집 UI가 전송처 없이 떠 있음. 제안서 3.2의 "과잉 폴백 판정 데이터"가 어디에도 쌓이지 않는다.
3. **`/api/v1/admin/quality-summary` 200 응답 스키마 확정** — KPI 카드 5종(총 질문 수·자동 답변 성공률·폴백률·평균 응답시간·출처 표기율) 필드명을 계약으로. 백엔드 라우트 구현도 함께 필요.
4. **딥링크 필드** — SUCCESS(신청 채널)·PERSONAL_LOOKUP(공식 조회 채널)의 대표 URL을 KB/응답 레벨로. 현재는 FE 상수 하드코딩이라 KB가 늘면 유지 불가.
5. **FOLLOWUP 선택지 구조화** — `string[]` → `{ id, label, kind: INTENT|REGION|QUESTION }`. "지역명이면 selected_region 승격"이라는 FE 휴리스틱과 "라벨을 질문으로 재전송" 의존을 제거할 수 있다.
6. **`StoredFailureReason` 정합 결정** — 계약은 3종 저장, 백엔드 구현은 INSUFFICIENT_GROUNDING만 저장. 계약을 구현에 맞춰 1종으로 좁히든(이 경우 폴백 저장 고지·이음센터 필터 3종도 축소), 구현을 계약에 맞추든 한쪽으로 확정해야 한다. **데모 #5 큐 유입이 이 결정에 걸려 있다.**
7. **FOLLOWUP 관련 민원 제안 필드**(`related_question` 류) — 데모 #3 요구 요소.
8. **`/api/v1/offices` 존치 여부** — FE 미호출·BE 미구현. 쓸 계획이 없으면 계약에서 제거가 깔끔하다.
9. **`Fallback.next_actions` 구조화** — 자유 문자열이라 FE가 CTA(전화·URL)로 연결할 수 없어 별도 상수로 CTA를 재구성 중. `{ label, href? }`면 폴백 CTA도 계약 데이터로 구동 가능.
