# 관리자 KB 후보 작성·승인 기준

## 1. 역할

### 민원 운영자

- 실패 질문 확인
- backend-only 사유 확인 capability로 자동 폴백 사유 검토·정정
- KB 후보 적격성 확인
- KB 후보 작성
- 승인 요청

### KB 승인자

- 공식 출처 검토
- 답변이 출처 범위 안인지 확인
- 개인정보·중복·담당 기관·기준일 확인
- 승인 또는 반려

MVP에서는 local/private 환경의 `/admin` 상단에서만 **데모용 역할 전환**으로 두 역할을 시연한다. 고정 demo actor는 작성자 `OPERATOR-LOCAL-001`, 승인자 `PM-LOCAL-001`이며, 데모 헤더는 인증이 아니다. 백엔드는 `actor_id`, `actor_role`, `created_by`를 검사해 작성자 본인 승인을 거부한다. public 환경에서는 별도 승인된 서버측 gate가 없으면 관리자 UI와 API를 비활성화한다. 실제 운영 단계에서는 기관 SSO와 RBAC로 확장한다.

## 2. 후보 전환 규칙

| 폴백 사유 | 후보 전환 | 처리 |
|---|---|---|
| INSUFFICIENT_GROUNDING | 가능 | 공식 자료 확인 후 후보 작성 |
| PERSONAL_LOOKUP | 불가 | 공식 조회 시스템·담당 부서 안내 |
| LEGAL_JUDGMENT | 불가 | 일반 정보와 전문 담당자 안내 |
| OUT_OF_SCOPE | 불가 | 지원 범위 안내; 범위 확대는 별도 사업 결정 |
| PRIVACY_UNRESOLVED | 불가 | 개인정보를 빼거나 표현을 바꿔 재질문; 질문 text·실패 질문 행 미생성 |
| CIVIC_SCOPE_GAP (planned) | 기존 KB 후보 불가 | 별도 범위확대 검토 queue; PM 범위 편입 결정 전 ACTIVE 전환 금지 |
| NON_CIVIC (planned) | 불가 | 민원 관련 질문 안내; 질문 text·검토 row 미저장 |

모호한 질문은 FOLLOWUP이며 후보 전환 대상이 아니다. `PRIVACY_UNRESOLVED`도 운영 개선용
실패 질문이 아니며 후보·사유 확인 상태 머신에 진입하지 않는다.

`PRIVACY_UNRESOLVED`는 Q-MVP-001/D-058의 API 3.0.0-draft와 local/private `/api/v1/chat`에
적용됐다. 7/25 local 경로에서는 질문 text·실패 질문 행·interaction DB event를 만들지 않는다.
원격/public 운영과 persistent privacy metadata는 reserved `00700` 단계의 별도 승인 전까지 금지한다.

### 사유 확인 불변조건

- 새 실패 행은 `NEW`이며 최초에는 부모 `interaction_events`의 intent와 자동 fallback reason이 일치한다.
- `interaction_events.fallback_reason`은 최초 자동 분류 기록이므로 수정하지 않는다.
- OPERATOR만 별도 backend capability로 `NEW → REASON_CONFIRMED`를 수행할 수 있다.
- 확인값은 `INSUFFICIENT_GROUNDING`, `PERSONAL_LOOKUP`, `LEGAL_JUDGMENT` 중 하나이며 `failed_questions.fallback_reason`에만 저장한다.
- 확인 시 `candidate_eligible = (fallback_reason = INSUFFICIENT_GROUNDING)`을 다시 계산한다.
- 후보 작성은 `REASON_CONFIRMED`, `INSUFFICIENT_GROUNDING`, `candidate_eligible=true`를 모두 만족한 행에서만 가능하다.
- 동시 확인에서는 한 transaction만 성공하고 나머지는 잘못된 상태로 거부한다.

## 3. 상태 머신

```text
NEW
→ REASON_CONFIRMED
→ DRAFTED
→ PENDING_APPROVAL
→ APPROVED 또는 REJECTED
→ APPROVED인 경우 ACTIVE KB 생성
```

한글 UI: 신규 → 사유 확인 → 후보 작성 → 승인 대기 → 승인 완료/반려

## 4. 승인 필수 조건

1. 공식 출처가 존재한다.
2. 답변이 공식 출처의 범위를 벗어나지 않는다.
3. 개인정보가 포함되지 않는다.
4. 담당 기관·부서가 확인됐다.
5. 기존 ACTIVE KB와 중복되지 않는다.
6. 최종 확인일이 입력됐다.
7. 수수료·기간 등 변경 가능한 정보의 기준일과 주의사항이 명확하다.
8. 작성자와 승인자가 다르다.
9. 승인과 반려 모두 비어 있지 않은 `review_comment`가 있다.

## 5. AI의 역할

P0에서 AI는 다음만 보조한다.

- 민원 유형 자동 입력
- 폴백 사유 추천
- 대표 질문의 일반화 초안 보조. 운영자가 직접 검토·정제하고 PII 재검사를 통과해야 저장 가능
- 관련 필드 위치 안내

행정 답변·수수료·담당 부서·공식 출처는 운영자가 작성한다. 공식 문서 기반 답변 초안 자동 생성은 P2이며, 도입하더라도 사람 승인 전 시민 답변에 사용하지 않는다.

## 6. 감사 이력

저장 필드:

```text
actor_id
actor_role
action
target_type
target_id
old_status
new_status
changed_field_names
review_comment
created_at
```

저장하지 않는 항목:

- 질문 전체 본문
- KB 답변 전체 스냅샷
- 개인정보

사유 확인 감사 row는 다음 metadata만 사용한다.

```text
action = FAILED_QUESTION_REASON_CONFIRMED
target_type = FAILED_QUESTION
old_status = NEW
new_status = REASON_CONFIRMED
changed_field_names = 실제 변경된 status/fallback_reason/candidate_eligible 필드명
```

최초 자동 사유나 질문 본문을 snapshot으로 복사하지 않는다. 후보 감사 action은 기존
`CANDIDATE_CREATED`, `CANDIDATE_SUBMITTED`, `CANDIDATE_APPROVED`,
`CANDIDATE_REJECTED`를 유지한다.

## 7. 승인 API 검증

- 운영자 역할의 승인 요청은 403 반환
- OPERATOR 외 역할의 사유 확인·정정은 403 반환
- 이미 확인됐거나 잘못된 상태의 사유 확인은 409 반환
- 작성자와 actor_id가 동일한 승인 요청은 409 또는 403 반환
- 출처·확인일 누락 시 422 반환
- 승인과 반려 모두 공백이 아닌 `review_comment`를 요구
- APPROVED 후보만 ACTIVE KB 생성
- REJECTED 후보는 검색 대상 제외
