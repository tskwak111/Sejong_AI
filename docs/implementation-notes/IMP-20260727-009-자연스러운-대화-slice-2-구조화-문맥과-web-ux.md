# IMP-20260727-009 — 자연스러운 대화 Slice 2 구조화 문맥과 Web UX

- Date/Time (KST): 2026-07-27T03:26:09+09:00
- Task ID: CHAT-NATURAL-001-S2
- Type: implementation-frontend-accessibility
- Status: Done
- Author/Agent: Codex `/root`
- Branch: codex/ACTUAL-P0-UX-GAPS-001
- Base commit: 7f5319d
- Related plan/ADR/RFP: D-089~D-091, ADR-0010, CHAT-NATURAL-001 spec/plan, accessibility P0

## 1. 사용자 요청과 완료 기준

### 요청

원문 transcript를 서버에 저장하지 않으면서도 증명서·수수료·서류·온라인·기관 후속질문과
지역 선택/변경이 자연스럽게 이어지는 시민 Web 대화를 구현한다.

### Acceptance Criteria

- context v2는 closed IDs만 담고 15분 TTL이며 v1은 TTL 동안 read-only다.
- stale/invalid context는 이전 질문을 복원하지 않고 안전하게 무시한다.
- 지역 선택·변경, 새 대화, exact certificate choice가 keyboard/mobile에서 동작한다.
- waiting 단계와 fallback copy가 정책·저장 상태를 정확히 말한다.

## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 사용자 제품 결정자, Codex API/Web 구현자 |
| When — 언제 | 2026-07-27 KST |
| Where — 어디서 | API context/service, `/chat`, Web E2E 3 viewport |
| What — 무엇을 | context v2, 후속 transition, 지역 선택, reset, 단계형 waiting UX |
| Why — 왜 | 메뉴 반복 대신 질문 맥락과 다음 행동을 유지하기 위해 |
| How — 어떻게 | signed text-free context + server transitions + browser memory-only state |
| How much — 어느 정도 | chat focused 256건, Web 62건, fixture E2E 24건 PASS |

## 3. 시작 전 상태

- 관련 파일: API context/service tests, `apps/web/src/app/chat`, Web components/E2E.
- 기존 동작: 단발 응답 위주였고 최초 지역 선택·분야별 후속 질문이 약했다.
- 발견한 충돌/부채: raw text를 context에 넣으면 transcript 무저장 원칙이 깨진다.
- Git 상태: 격리 worktree, primary user 변경 미접촉.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| A-014 | 인간 확정 | text-free client-carried context | v2 issue/v1 read-only | 대화·privacy |
| A-055 | B/High 해소 | 최초 지역 선택 진입점 | 직접 읍면동 selector | office cards |

## 5. 설계 결정과 대안

### 선택

서명된 context에는 topic/pending slot/dialog act/region 같은 closed ID만 넣고 질문·답변 문장은
브라우저 현재 화면 메모리 외에 전달·저장하지 않는다.

### 이유

챗봇다운 연속성을 제공하면서 원문 transcript를 서버/DB/token에 남기지 않는다.

### 고려했지만 선택하지 않은 대안

- 서버 세션 transcript: 보관·삭제·인증 범위가 커 제외.
- URL query 질문 전달: 브라우저 기록/로그 노출 때문에 금지.
- 무기한 context: stale 의도 재사용 위험 때문에 15분 TTL 유지.

## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| API context/service | v2 claims·transition·stale protection | 원문 없는 연속 대화 |
| Web chat | certificate choices, region select/change/reset | 시민 다음 행동 |
| Web status/fallback | 단계형 waiting·저장 정책 문구 | 정직한 상태 전달 |
| Playwright | 390/430/desktop 후속·접근성 | 실제 viewport 회귀 |

### 데이터 흐름/상태 변화

현재 입력과 text-free context만 POST하고, 서버가 새로운 v2 token과 구조화 응답을 발급한다.
새 대화는 client memory/context를 지우며 DB row를 만들지 않는다.

### 오류·빈 상태·롤백

invalid/expired/stale token은 이전 문장을 복원하지 않고 현재 질문만 처리한다. v2 issuer를
비활성화하고 Web controls commit을 revert하면 v1 TTL read-only 호환 기간 동안 rollback 가능하다.

## 7. 버전 전후

### 생성 시 매니페스트
- product_spec: 2.6.0
- repo_guidance: 1.7.9
- application: 0.10.0-office-directory-runtime
- web: 0.6.0-answer-mode
- api: 3.3.0-draft
- shared_contracts: 0.6.0
- database_schema: 0.4.0-local
- official_data: 0.1.0-initial.2
- mock_data: 0.0.0-not-populated
- prompt_set: 0.2.0-grounded-live-chat
- test_suite: 1.8.0-local-demo-readiness
- documentation: 2.23.1

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Application | 0.10.0 | 0.11.0-natural-dialogue | context transition |
| Web | 0.6.0 | 0.7.0-natural-dialogue | 자연 대화 UX |
| API | 3.3.0-draft | 4.0.0-draft | context v2 |
| DB schema | 0.4.0-local | 0.5.0-local | 통합 release |
| Official data | `.2` | 동일 | 변경 없음 |
| Mock data | not-populated | 동일 | 변경 없음 |
| Prompt set | 0.2.0 | 0.3.0 | 통합 release |
| Test suite | 1.8.0 | 1.9.0 | context/Web 회귀 |
| Docs | 2.23.1 | 2.24.0 | 세 Slice 기록 |

## 8. 명령과 테스트 증거

| 명령/검증 | 결과 | 시간/개수 | 증거 경로 |
|---|---|---|---|
| API context/chat focused tests | PASS | 256 | API tests |
| Web unit/lint/typecheck/build | PASS | 62 tests, 0 errors | Web |
| Playwright fixture | PASS | 24, 390/430/desktop | `tools/web-e2e` |

### 미실행 검증과 이유

actual 19→20 browser E2E는 clean formal seed가 필요한 Task 15에서 한 번만 실행한다.

## 9. 보안·개인정보·접근성·성능 영향

- Privacy: token·URL·DB에 원문/과거 transcript 0.
- Security: HMAC token, TTL, version/transition allowlist.
- Accessibility: 44px 이상 controls, labels, keyboard, responsive E2E.
- Performance/cost: waiting UX만 추가, provider 호출 수를 늘리지 않는다.

## 10. 데이터와 출처 영향

- 공식 데이터: 불변.
- mock/AI 생성: fixture는 시연용으로만 표시.
- schema/lineage: DB row 변화 없음.
- verified date: 2026-07-27.

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- 대화기억은 원문 기억이 아니라 안전한 상태 ID 기억이다.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- transition table과 Web reducer는 공개 contract enum을 공유한다.

## 13. 인수인계·재현·롤백

### 재현

API focused tests 뒤 Web test/lint/typecheck/build 및 3 viewport Playwright를 실행한다.

### 롤백

v2 issuer/Web context commits를 revert하고 provider modes false를 유지한다.

### 다음 개발자 시작점

actual browser E2E에서 지역 선택·동일 질문 개선 흐름을 최종 확인한다.

## 14. 남은 위험·미해결 질문·다음 단계

- 실제 사용자 수동 접근성 확인과 public browser smoke는 후속 통합에 포함한다.

## 15. 자체 리뷰

- [x] 요청 충족
- [x] 테스트/검증
- [x] source-of-truth/계약/버전 동기화
- [x] 개인정보 원문 노출 없음
- [x] 구현 노트 INDEX 갱신
