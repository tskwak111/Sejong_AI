# IMP-20260729-002 — A-072 API key replacement diagnosis

- Date/Time (KST): 2026-07-29T01:02:20+09:00
- Task ID: A-073-KEY-CHANGE-DIAGNOSIS
- Type: diagnosis-guidance
- Status: Done — key replacement not recommended from current evidence
- Author/Agent: 사용자 질문 / Codex evidence review
- Branch: `codex/a-072-strict-classifier-wire`
- Base commit: `73510a2`
- Related: D-117, A-073,
  [actual report](../test-reports/CHAT-HYBRID-RAG-001-UPSTAGE-ACTUAL.md)

## 1. 사용자 요청과 완료 기준

사용자는 A-072 actual FAIL이 API 키 문제인지, 키를 변경해야 하는지 물었다. 비밀값이나
provider body를 읽지 않고 aggregate evidence로 인증/전송 단계와 contract 검증 단계를
구분해 권고하는 것이 완료 기준이다.

## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 인간 결정자 사용자, 진단자 Codex |
| When — 언제 | 2026-07-29 KST, D-117 exact-one actual 직후 |
| Where — 어디서 | local/private A-072 aggregate report와 결정 로그 |
| What — 무엇을 | API 키 교체가 현재 실패에 유효한 조치인지 진단 |
| Why — 왜 | 무관한 키 교체와 승인되지 않은 재호출을 막기 위해 |
| How — 어떻게 | key presence, HTTP family, usage, terminal stage를 경계별로 대조 |
| How much — 어느 정도 | 9/9 HTTP 2xx·usage 성공, 9/9 enum/shape 거절 |

## 3. 조사한 상태와 증거

- `key_present=True`
- provider HTTP 2xx 9, HTTP 4xx 0, transport no-response 0
- accepted usage 9, usage rejection 0
- `KEY_SET_REJECTED` 0, `ENUM_SHAPE_REJECTED` 9
- accepted decision과 route/topic match 0, 최종 FAIL

이 증거는 현재 키가 요청 인증과 모델 접근을 통과해 정상 응답·usage를 받았음을 뜻한다.
따라서 현재 실패 경계는 키가 아니라 provider 응답을 기존 closed enum/shape 규칙으로
검증하는 단계다. 응답 본문은 보관하지 않았으므로 어떤 필드 값 조합이 어긋났는지는 아직
단정하지 않는다.

## 4. 선택과 버린 대안

- 선택: 현재 키 유지, 추가 actual 호출 중단, A-073에서 content-free enum/shape 진단 설계.
- 기각: 다른 키로 즉시 재실행. 같은 request/parser에 다른 유효 키를 사용해도 enum/shape
  계약은 바뀌지 않으며 비용과 증거 혼선만 늘 가능성이 높다.
- 키 교체가 필요한 예외: 키 폐기·노출 의심, 401/403, key invalid/expired, 모델 접근 권한
  변화가 별도 증거로 확인될 때다. 현재 D-117에는 해당 증거가 없다.

## 5. 변경·버전·테스트

- 제품 코드/API/DB/data/prompt/profile/secret 변경 0.
- 모든 버전은 `versions/manifest.json`의 documentation `2.30.3` 포함 전 축 불변.
- 읽기 전용 확인:
  current report에서 key presence·HTTP·usage·stage·acceptance aggregate만 조회.
- 실제 provider 호출·재실행·키 출력 0.

## 6. 보안·개인정보·접근성·성능

- 키 값, 질문, provider body, status detail, DSN을 읽거나 출력하지 않았다.
- 시민 runtime, UI, 접근성, 성능 변화 0. 추가 비용 USD 0.
- 공식 `.2`, mock, DB lineage 변화 0.

## 7. 인간이 반드시 알아야 하는 내용

현재는 키를 바꾸지 않는 것이 맞다. 다음 필요한 작업은 키 교체가 아니라 A-073
enum/shape 거절의 content-free 진단 설계다. 새 provider actual은 별도 승인 전 금지한다.

## 8. AI 내부 구현 세부와 인수인계

인증/전송 성공은 HTTP 2xx와 usage acceptance로, contract 실패는 terminal
`ENUM_SHAPE_REJECTED`로 분리했다. 롤백할 제품 변경은 없으며 이 판단을 취소하려면 이 note와
INDEX 행만 제거하면 된다.

## 9. 남은 위험

aggregate-only 정책 때문에 route/intent/nullable 조합 중 어느 값이 실패했는지는 아직
확정되지 않았다. provider body를 사후 열람하거나 키만 교체해 재호출하는 방식으로 추측하지
않는다.

## 10. 자체 리뷰

- [x] 질문에 evidence-based 답변
- [x] 실행하지 않은 수정·재호출 없음
- [x] 개인정보·secret·공식 데이터 영향 0
- [x] 인간 결정과 내부 세부 분리
- [x] INDEX 갱신
