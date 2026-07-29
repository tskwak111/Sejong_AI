# ADR-0029 — 개인정보 안전 시민 피드백 저장과 관리자 집계

- Status: Accepted for local/private MVP
- Date: 2026-07-29
- Decision: Q-FEEDBACK-001=A / D-138
- Supersedes: 시민 피드백의 Web 탭 메모리 전용 임시 동작
- Related: ADR-0004, ADR-0007, ADR-0011, `docs/source-of-truth/PRIVACY_POLICY.md`

## Context

시민 화면의 만족/불만족은 현재 React state에서만 처리되어 DB·운영 통계에 반영되지 않는다.
불만족 상세 의견은 서비스 개선에 유용하지만 전화번호·주소 등 개인정보가 포함될 수 있다.
질문·답변 본문과 피드백 상세 원문을 함께 저장하면 현재의 원문 미저장 원칙을 훼손한다.

## Decision

1. 공개 시민 계약에 `POST /api/v1/feedback`을 추가한다.
2. 응답 `request_id`는 피드백의 논리적 중복 방지 키로만 사용한다. 질문·답변 본문은 연결하거나
   저장하지 않는다.
3. 만족은 상세값 없이 저장한다. 불만족은 분야와 사유를 필수로 하며 양쪽에 `OTHER`를 허용한다.
4. 상세 의견은 최대 300자다. `reason_code=OTHER`이면 필수이고, 다른 불만족 사유에는 선택이다.
5. 서버가 질문 마스커와 같은 고정 개인정보 탐지·치환 엔진을 사용하되, 일반 피드백 산문을
   질문 문법으로 오인하지 않는 전용 프로필을 적용한다. 이름·상세주소·고위험 숫자·비정상
   유니코드 등 해결되지 않은 위험은 계속 차단하며, 마스킹 불능이면 행을 만들지 않고 값 비노출
   422로 닫는다.
6. DB에는 마스킹 결과만 저장하며 원문·질문·답변·provider body·context token은 저장하지 않는다.
7. 마스킹 상세 텍스트는 생성 후 정확히 30일에 NULL 파기한다. 평점·폐쇄형 분류·생성/파기
   시각은 집계를 위해 유지한다.
8. local/private 관리자에게만 aggregate와 최근 마스킹 의견을 조회하는
   `GET /api/v1/admin/feedback-summary`를 제공한다.
9. table 직접 권한은 금지하고 record/list/aggregate/purge의 fixed
   `SECURITY DEFINER` capability만 backend에 허용한다.
10. 기본 `create_app()`은 피드백 write를 503으로 닫고 local composition만 실제 repository를
    주입한다. 관리자 집계는 기존 local/private admin gate 뒤에 둔다.

## Consequences

- 시민 피드백이 실제 개선 지표에 반영되고 자유 입력 위험은 마스킹·30일 파기로 제한된다.
- 무작위 UUID 제출 방지와 rate limit은 public 운영 전 추가 승인이 필요한 보안 gate다.
- `request_id`가 존재해도 원 질문/답변을 복원할 수 없으므로 운영 통계는 분류형 지표 중심이다.
- applied migration은 수정하지 않고 `00710` forward/rollback/pgTAP으로 확장한다.

## Rejected alternatives

- 브라우저 메모리만 사용: 운영 개선 데이터가 남지 않아 요청을 충족하지 못한다.
- raw 상세 영구 저장: 개인정보 최소수집과 30일 파기 원칙에 위배된다.
- 질문·답변 snapshot 저장: 비협상 원문·감사 snapshot 금지와 충돌한다.
- LLM으로 피드백 분류: 비용·개인정보 outbound·불확실성을 늘리며 폐쇄형 코드로 충분하다.
