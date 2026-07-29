# 관리자 KB 후보 제출 복구 설계

- Status: Approved
- Date: 2026-07-29
- Decision: Q-FEEDBACK-001=A의 연계 UX 교정

## 목표

`create(DRAFTED) → submit(PENDING_APPROVAL)` 두 단계 중 어느 단계가 실패했는지 운영자가 이해하고,
create 성공 후 submit 실패로 남은 DRAFTED 후보를 새 후보 없이 다시 제출할 수 있게 한다.

## 결정

- 기존 API·DB 상태 머신과 공개 payload는 바꾸지 않는다.
- `AdminTransportError`가 HTTP status와 안정된 `error.code`만 보존한다. 서버 message/exception
  원문은 UI나 로그로 전파하지 않는다.
- client validation 실패는 폼 상단 `role=alert` 요약과 첫 invalid field focus를 함께 제공한다.
- 공식 출처 허용 host를 폼에 표시한다.
- create 실패는 “저장되지 않음”, submit 실패는 “초안은 저장됐지만 승인 요청 실패”로 구분한다.
- DRAFTED 후보는 실패 질문 행에서 `승인 요청 다시 시도` 액션을 제공한다.
- 성공하면 목록을 다시 읽고 `PENDING_APPROVAL` 상태를 확인한 뒤 승인 화면 링크를 보여준다.
- 403/409/422/5xx는 역할·상태·입력·일시 장애에 맞는 값 비노출 문구로 매핑한다.

## 인수 기준

- create 실패 시 submit을 호출하지 않는다.
- create 성공/submit 실패 시 후보 ID를 잃지 않고 재시도할 수 있다.
- 새로고침 후에도 listCandidates의 DRAFTED 후보로 재시도 액션이 복원된다.
- 중복 create가 발생하지 않는다.
- OPERATOR만 재제출할 수 있다.
- Web actual/fixture 테스트와 접근성 테스트가 통과한다.
