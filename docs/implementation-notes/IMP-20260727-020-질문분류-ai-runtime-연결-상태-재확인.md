# IMP-20260727-020 — 질문분류 AI runtime 연결 상태 재확인

- Date/Time (KST): 2026-07-27
- Task ID: CLASSIFIER-RUNTIME-STATUS-001
- Type: status-confirmation
- Status: Done
- Author/Agent: 사용자 제품 결정자 / Codex
- Branch: codex/ACTUAL-P0-UX-GAPS-001
- Base commit: 6f12416
- Related: CHAT-NATURAL-001, ADR-0025, IMP-20260727-018

## 1. 요청과 답

- 요청: 현재 질문 분류에 실제 AI가 들어갔는지 확인한다.
- 답: 아니다. classifier 구성요소와 actual 평가 증거는 있지만 local 시민 API runtime에는 아직
  조립되지 않았다.

## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who | 사용자, Codex |
| When | PR #18 병합 뒤 runtime 실행 준비 중 |
| Where | `apps/api` local app composition |
| What | 질문분류 AI 실제 호출 여부 |
| Why | 평가 adapter 존재와 시민 runtime 연결을 혼동하지 않기 위해 |
| How | 기존 진단 IMP-018과 constructor trace 재사용 |
| How much | 코드·DB·환경·외부 호출 변경 0 |

## 3. 실제 상태

- 존재: classifier prompt, strict enum parser, Upstage adapter, settings, attempt ledger,
  고정 60문항 actual 60/60.
- 존재: `ChatService`의 optional `question_classifier` port.
- 누락: `create_local_app()`에서 classifier settings/client/ledger를 만들고
  `ChatService(question_classifier=...)`로 전달하는 composition.
- 현재 실제 질문분류: deterministic safety/classification 경로.
- 현재 실제 AI 가능 경로: exact profile을 켰을 때 ACTIVE/OFFICIAL 근거 기반 답변 문장 생성.

## 4. 보안·데이터·버전 영향

- 변경 파일: 이 note와 INDEX만.
- application/web/api/DB/data/prompt/test/docs version: unchanged.
- 질문, PII, key, DSN, provider 호출, DB write: 0.

## 5. 테스트와 증거

- 새 테스트 미실행: 상태 재확인은 IMP-018의 static constructor trace를 재사용했다.
- 실제 AI 분류가 된다고 주장할 수 있는 citizen API evidence는 현재 0이다.
- adapter actual 60/60은 runtime integration 증거가 아니다.

## 6. 인간이 알아야 할 내용

- `UPSTAGE_CLASSIFIER_MODE=true`만 설정해도 현재 시민 API 분류에는 연결되지 않는다.
- 완전한 hybrid AI를 위해서는 local runtime composition을 TDD로 추가해야 한다.
- 개인정보·policy 분류는 수정 후에도 deterministic/provider outbound 0이어야 한다.

## 7. 다음 단계와 롤백

- 다음 구현: shared attempt ledger, classifier client/runtime, service injection, lifespan close,
  disabled/combined/PII 회귀와 local actual.
- 이번 상태 note의 rollback은 note와 INDEX 행만 revert한다.

## 8. 자체 리뷰

- [x] 질문에 직접 답변
- [x] adapter/evaluation/runtime 구분
- [x] 미실행 테스트를 PASS로 주장하지 않음
- [x] 비밀·개인정보·데이터 변경 0
- [x] INDEX 갱신
