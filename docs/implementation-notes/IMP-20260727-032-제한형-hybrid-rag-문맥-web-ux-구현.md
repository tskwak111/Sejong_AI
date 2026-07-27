# IMP-20260727-032 — 제한형 Hybrid RAG 문맥·Web UX 구현

- Date/Time (KST): 2026-07-27T23:18:35+09:00
- Task ID: CHAT-HYBRID-RAG-001-T5-T6
- Type: implementation-fullstack
- Status: Done
- Author/Agent: 사용자 승인 / Codex main 통합 / task별 구현·독립 검토 에이전트
- Branch: `codex/CHAT-HYBRID-RAG-001`
- Base commit: `2a443b6`
- Implementation commits: `3ebc114`, `440d3ce`, `a8a244e`, `b86c956`, `c2c1861`, `9b90919`
- Related: [plan](../superpowers/plans/2026-07-27-bounded-hybrid-rag-conversation.md),
  [ADR-0027](../adr/0027-active-topic-catalog-and-coverage-grounding.md), D-097/D-098/D-102/D-104

## 1. 사용자 요청과 완료 기준

### 요청

민원 챗봇이 generic 질문에서 네 분야 전체 메뉴를 반복하지 않고 intent별 선택지를 주며,
증명서 3단계 진입·관련 질문·지역 선택을 자연스럽고 접근 가능하게 제공한다.

### Acceptance Criteria

- certificate는 등본/초본/차이 exact 3개와 `CERTIFICATE_KIND` signed context를 사용한다.
- move/waste/tax generic 질문은 현재 ACTIVE topic에서 유도한 exact 옵션만 제시한다.
- context에는 free text가 아니라 topic/pending-slot/region/dialog-act ID만 담는다.
- 지역 선택은 항상 보이고 새 대화에서도 같은 탭 memory만 유지한다.
- source-backed 관련 질문, 키보드·label·390/430/desktop E2E가 통과한다.

## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 사용자가 UX 결정을 승인하고 Backend/Web 구현자와 별도 reviewer가 검증했다. |
| When — 언제 | 2026-07-27 KST, Tasks 5~6 |
| Where — 어디서 | API followup/context/response/service, contracts/shared types, `/chat` Web components/E2E |
| What — 무엇을 | intent-specific FOLLOWUP, closed context facets, related questions, persistent-in-tab region UX |
| Why — 왜 | “어떤 것부터” 반복과 무관한 네 분야 메뉴를 없애고 대화를 이어가기 위해서다. |
| How — 어떻게 | source-backed option derivation, signed context, typed client, accessible controls, TDD/review |
| How much — 어느 정도 | generic intent 4종, certificate 3 options, same-tab region 1 state, Web tests 68, E2E 27 |

## 3. 시작 전 상태

- generic certificate가 과거 flat option 또는 전체 분야 menu로 돌아갈 수 있었다.
- 새 대화가 transcript/context와 함께 region까지 지워 사용자가 다시 선택해야 했다.
- followup option을 raw string factory로 만들 수 있어 provenance가 약했다.
- 관련 질문과 control label의 고유성 회귀가 필요했다.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| Q-UX-REGION-001 | 인간 결정 | 새 대화 후 지역 | A: 같은 탭 memory 유지 | Web state |
| Q-UX-CERT-001 | 인간 결정 | 증명서 진입 구조 | A: 등본/초본/차이 3개 | API/Web copy |
| option provenance | 내부 | raw string 생성 허용 여부 | typed source/catalog factory만 허용 | 안전성/회귀 |

## 5. 설계 결정과 대안

### 선택

`FollowupPlan`은 typed catalog/source만 보유하고 시민 label은 서버가 계산한다. context v2에는
closed `PendingSlot`과 topic facet만 서명하며 Web region은 storage 없이 React memory에 둔다.

### 이유

관련 질문과 후속 선택지가 현재 ACTIVE KB로 추적되고, 질문 원문이나 장기 사용자 profile 없이도
최소한의 대화 연속성을 제공한다.

### 고려했지만 선택하지 않은 대안

- 모든 분야 고정 menu: 질문 intent를 무시해 제외.
- local/session storage region: 보관 범위를 넓혀 제외.
- raw string option factory: source provenance가 없어 제외.
- transcript 서버 저장: 개인정보 원문 미저장 원칙으로 제외.

## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| `chat/followup.py`, `context.py` | typed plan, exact option, closed pending slot | 자유 text/state 차단 |
| `service.py`, `response.py` | intent별 FOLLOWUP·source-backed related questions | 근거 있는 대화 연결 |
| OpenAPI/schema/generated TS/fixtures | 기존 shape 안의 behavior example 정렬 | FE/BE 계약 drift 방지 |
| `chat-screen.tsx` | region state를 새 대화와 분리 | 같은 탭 편의 |
| `RegionSelect`, `FollowupCard`, `AnswerCard` | 상시 선택/변경, exact labels, 관련 질문 | 접근 가능 guided chat |
| Vitest/Playwright | label uniqueness, reset, mobile/desktop | 실제 UI 회귀 방지 |

### 데이터 흐름/상태 변화

FOLLOWUP 응답의 `followup_options`와 signed `context_token`을 Web이 표시한다. 선택 질문은 새
요청으로 전송되며 서버가 다시 ACTIVE catalog를 확인한다. 새 대화는 transcript/context만
삭제하고 selected region은 같은 component lifetime에 유지한다.

### 오류·빈 상태·롤백

option source가 없거나 context가 invalid/expired면 generic 안전 경로로 닫는다. rollback은
Tasks 5~6 commit을 역순 revert하고 contract fixture/generated type을 함께 되돌린다.

## 7. 버전 전후

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Application | `0.11.1-classifier-runtime` | `0.12.0-bounded-hybrid-rag` | guided backend behavior |
| Web | `0.7.0-natural-dialogue` | `0.8.0-guided-chat` | region/followup/related UX |
| API | `4.0.0-draft` | 동일 | 공개 field 변경 0 |
| Shared contracts | `1.0.0` | 동일 | shape 호환 |
| DB/official/mock | 기존 | 동일 | 저장·data 변경 0 |
| Prompt set | `0.3.1` | `0.4.0-topic-coverage` | 전체 release와 묶음 |
| Test suite | `1.9.2` | `2.0.0-bounded-hybrid-rag` | Web/UAT 회귀 |
| Docs | `2.26.1` | `2.27.0` | 구현 계보 |

## 8. 명령과 테스트 증거

| 명령/검증 | 실제 결과 | 증거 |
|---|---|---|
| Task 5 focused API | 196 PASS | task report/review |
| Task 5 chat area | 323 PASS | task report/review |
| shared contracts | 96 PASS | Task 5와 Task 9 gate |
| Web Vitest | 68 PASS | Task 6/Task 9 gate |
| Web lint/typecheck/build | PASS | Task 6/Task 9 gate |
| Playwright 390/430/desktop | 27/27 PASS | Task 6 report/review |

Task 9 build에서 Next.js workspace-root warning 1건이 있었으나 build는 PASS했고 오류·tracked
drift는 없었다. actual browser 수동 demo는 이 노트에서 실행하지 않았다.

## 9. 보안·개인정보·접근성·성능 영향

- Privacy: transcript/context/region을 DB·browser storage에 저장하지 않는다.
- Security: context는 server-signed closed ID이며 raw option factory를 제한했다.
- Accessibility: label/control ID 고유성, keyboard, mobile/desktop E2E를 검증했다.
- Performance/cost: deterministic followup과 region UX는 provider 호출 0이다.

## 10. 데이터와 출처 영향

- 공식 데이터/DB: 변경 0.
- option/related question은 ACTIVE record service name과 approved metadata에서 유도한다.
- Web demo fixture는 계약 시연용이며 공식 사실로 승격하지 않는다.
- verified date: 2026-07-27.

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- 지역은 같은 탭 메모리에만 남고 새로고침·새 탭·브라우저 종료 후 유지되지 않는다.
- related question은 신청 처리나 개인 조회가 아니라 현재 공식 안내로 가는 버튼이다.
- public/remote UI와 실제 기관 연계는 승인되지 않았다.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- option label은 typed source catalog에서 계산하고 public `string[]` shape는 유지한다.
- region control의 label ID를 option마다 고유하게 만들어 중복 접근성 이름을 막았다.

## 13. 인수인계·재현·롤백

### 재현

shared generation/test, Web lint/typecheck/test/build, Playwright 390/430/desktop를 실행한다.

### 롤백

`3ebc114..9b90919`을 역순 revert하며 API fixture/generated TS/Web fixture를 함께 되돌린다.

### 다음 개발자 시작점

`chat/followup.py`, `chat/context.py`, `chat-screen.tsx`, `RegionSelect.tsx` 순서로 읽는다.

## 14. 남은 위험·미해결 질문·다음 단계

- actual local provider와 final full root gate는 Tasks 10~11.
- manual 발표용 browser walkthrough는 final demo에서 별도 수행한다.
- local memory UX는 production 사용자 profile 동기화를 제공하지 않는다.

## 15. 자체 리뷰

- [x] 요청 충족
- [x] 테스트/검증
- [x] source-of-truth/계약/버전 동기화
- [x] 개인정보 원문 노출 없음
- [x] 구현 노트 INDEX 갱신
