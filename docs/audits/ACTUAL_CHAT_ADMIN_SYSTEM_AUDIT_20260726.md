# 실제 Chat·Admin 전체 동작 감사 — 2026-07-26

- Task: `ACTUAL-SYSTEM-AUDIT-001`
- 대상: private/local `main@c945303`
- 환경: Windows loopback Web `127.0.0.1:3000`, API `127.0.0.1:8000`, local DB
- 방식: 실제 브라우저, UTF-8 API 질문 표본, read-only 관리자/기관 API, 코드·계약·권위 문서 대조
- 안전 경계: provider 호출, DB reset/seed/purge, 관리자 상태 변경, 공개/remote 작업 없음

## 1. 결론

핵심 시민 답변 경로는 동작한다. 구체적인 네 분야 질문은 `SUCCESS`와 공식 출처를 반환했고,
개인조회·법적판단·범위 밖·개인정보 미해결은 정해진 안전 폴백으로 분리됐다. 15분
client-carried context도 같은 탭의 후속 질문에서 유지됐다.

다만 아래 세 P0 흐름은 현재 source-of-truth가 표현하는 일반 기능보다 좁다.

1. generic 증명서 선택을 누르면 같은 네 분야 질문이 반복된다.
2. 관리자 후보 작성은 임의의 적격 실패 질문이 아니라 예약된 WASTE-03 한 건만 지원한다.
3. 시민이 첫 지역을 선택할 진입점이 없어 실제 기관 카드에 도달하기 어렵다.

“관리자 KB 초안이 보이지 않는다”는 현상은 AI key 부재가 원인이 아니다. 현재 DB에는
승인 완료 후보 한 건이 존재하지만 후보 화면이 `PENDING_APPROVAL`만 표시해 숨긴다. 또한
current P0 정책상 AI는 공식 답변·수수료·담당 부서·출처를 작성하지 않는다. 운영자가 공식
근거를 입력하고 다른 사람이 승인해야 한다.

## 2. 실제 질문 표본 결과

Windows PowerShell 5.1의 기본 문자열 전송은 UTF-8이 아니므로 첫 시도에서 한글이 손상됐다.
이는 애플리케이션 결함으로 분류하지 않았다. `UTF8.GetBytes()`와 JSON charset을 명시한
재실행 결과는 다음과 같다.

| ID | 질문 유형 | 실제 결과 | 판정 |
|---|---|---|---|
| C01 | 구체적인 전입 신고 | `SUCCESS / MOVE_IN / TEMPLATE / source 1` | PASS |
| C02 | 모호한 이사 질문 | `FOLLOWUP / UNKNOWN / options 4` | PASS |
| C03 | generic 증명서 발급 | `FOLLOWUP / UNKNOWN / options 4` | FAIL — 분야를 이미 말했는데 다시 분야 선택 |
| C04 | 구체적인 주민등록등본 | `SUCCESS / CERTIFICATE_ISSUANCE / TEMPLATE / source 1` | PASS |
| C05 | 구체적인 대형폐기물 | `SUCCESS / BULKY_WASTE / TEMPLATE / source 1` | PASS |
| C06 | 지방세 일반 안내 | `SUCCESS / LOCAL_TAX / TEMPLATE / source 1` | PASS |
| C07 | 날씨 질문 | `FALLBACK / OUT_OF_SCOPE` | PASS |
| C08 | 개인 세금 조회 | `FALLBACK / UNKNOWN / PERSONAL_LOOKUP` | PASS |
| C09 | 법적 판단 요구 | `FALLBACK / UNKNOWN / LEGAL_JUDGMENT` | PASS |
| C10 | 이름 포함 질문 | `FALLBACK / UNKNOWN / PRIVACY_UNRESOLVED` | PASS |

추가 브라우저 확인:

- `주민등록등본은 어떻게 발급받나요?`는 구조화 답변, 공식 출처 카드, 확인일,
  출처 링크를 표시했다.
- 그 뒤 `그럼 수수료는?`는 같은 공식 증명서 답변으로 이어져 15분 대화 context가 작동했다.
- `증명서 발급해야해` → `증명서 발급` 버튼은 같은 generic 네 분야 FOLLOWUP을 다시
  표시해 반복 루프를 재현했다.
- 브라우저 console error/warning은 0건이었다.
- `/`, `/chat`, `/admin`, `/admin/failures`, `/admin/kb-candidates`를 390px·430px에서
  확인했고 가로 overflow는 0건이었다.

## 3. 관리자 actual 상태

read-only API 결과:

| 항목 | 실제 상태 |
|---|---:|
| `/ready` | 200 |
| 실패 질문 | 1 |
| `REASON_CONFIRMED` 실패 | 1 |
| KB 후보 | 1 |
| `APPROVED` 후보 | 1 |

화면 결과:

- 실패 질문 화면은 WASTE-03 질문을 `사유 확정`, `초안 생성됨`으로 표시한다.
- 후보 화면은 `승인 대기 0건`과 빈 상태만 표시한다.
- 실제 후보는 삭제된 것이 아니라 승인 완료 상태라 화면의
  `status === PENDING_APPROVAL` 필터에서 제외된다.

## 4. 핵심 발견과 우선순위

| 우선도 | 발견 | 근거와 영향 | 권고 |
|---|---|---|---|
| P0 / B-High | generic 증명서 FOLLOWUP 반복 루프 | classifier에 generic `증명서` cue가 없고 UNKNOWN service가 네 분야 options만 반환한다. 선택 label도 다시 UNKNOWN이다. | category-aware `CERTIFICATE_ISSUANCE + FOLLOWUP`과 CERT 전용 options |
| P0 / B-High | 일반 적격 실패 질문의 후보 작성 경로 부재 | `buildActualCandidateDraft`가 exact WASTE-03 한 건만 hardcode하고 나머지는 `ACTUAL_CANDIDATE_DRAFT_NOT_APPROVED`로 거부한다. | 운영자 수동 구조화 작성 폼을 만들고 공식 필드는 사람만 입력 |
| P0 / B-High | 첫 지역 선택 진입점 부재 | office API는 정상이나 초기 `/chat`에 region selector가 없고 API도 region followup을 반환하지 않는다. | 채팅 상단/답변 전 직접 지역 선택을 제공 |
| P1 / C | 승인·반려 후보 이력 미표시 | 후보 화면이 pending만 표시해 “초안 없음”으로 오해시킨다. | 대기/승인/반려 탭과 상태별 건수 |
| P1 / C | 관리자 화면의 AI 작성 문구가 실제와 다름 | current candidate는 hardcoded canonical demo draft이며 일반 AI 작성 경로가 없다. | “운영자가 작성한 공식 KB 후보”로 정정; 실제 보조 기능이 생긴 뒤에만 AI 표기 |
| P1 / C | 품질 KPI 미연결 | `/admin`이 실제 quality-summary 미확정을 명시한다. source-of-truth상 P1 Pending이다. | 현재는 Pending 표시 유지, KPI 권위 DB를 정할 때 구현 |
| Dev / D | `next dev`가 tracked `next-env.d.ts`를 변경 | build types import가 dev types import로 바뀌어 정상 실행만으로 worktree가 dirty해진다. | Next 권장 생성물 정책을 확인한 뒤 tracked 안정화; 지금 사용자 변경 보존 |

## 5. Source-of-truth 대조

| 권위 기준 | 현재 actual | 차이 |
|---|---|---|
| SFR-005 모호 질문은 선택형 FOLLOWUP | 네 분야 선택은 제공 | 이미 선택한 `증명서 발급`도 같은 질문 반복 |
| P0-09 근거 부족 질문만 KB 후보 작성 | exact WASTE-03 개선 루프는 완료 | 다른 적격 질문용 작성 UI/capability 연결 없음 |
| 운영자가 공식 KB 필드를 작성, 별도 승인자 검수 | 예약 fixture의 별도 승인은 완료 | 일반 운영자 작성 폼 없음 |
| P0-07 지역 선택·공식 기관 카드 | office API는 OFFICIAL-only로 정상 | 시민의 최초 지역 선택 UI 경로 없음 |
| P1 감사 이력 | DB metadata/audit 기반은 존재 | 후보 화면에서 승인·반려 이력을 볼 수 없음 |
| P1 KPI | 화면이 Pending임을 솔직히 표시 | 아직 실제 집계 미완료 |

## 6. AI 연결과 KB 초안의 정확한 경계

Upstage grounded chat은 시민 `SUCCESS` 답변 표현을 보조하는 별도 기능이다. 모든 공식 사실과
출처는 서버가 ACTIVE/OFFICIAL KB에서 다시 결합하며 실패하면 template로 폴백한다.

관리자 후보 작성은 이 경로와 연결돼 있지 않다. `APPROVAL_POLICY.md`에 따라 current P0에서:

- AI가 보조할 수 있는 것: intent/사유 추천, 대표 질문 일반화, 입력할 필드 위치 안내
- 운영자가 작성해야 하는 것: 공식 답변, 절차, 서류, 기간, 수수료, 담당 부서, 공식 출처
- 금지: LLM이 만든 출처·수수료·담당 부서를 공식 정보처럼 자동 저장

따라서 AI key를 켜도 관리자 일반 초안은 생기지 않는다. 필요한 것은 provider 연결이 아니라
공식 데이터 수동 작성 폼과 저장/검증 transport다.

## 7. 인간 결정과 이미 확정된 요구 구분

Q-CHAT-FOLLOWUP-001. generic 증명서 질문을 증명서 전용 확인 질문으로 바꿀 것인가
- 왜 지금 필요한가: 현재 선택 버튼이 같은 화면을 반복해 시민이 답변에 도달하지 못한다.
- 선택지 A / 장점 / 단점: `CERTIFICATE_ISSUANCE` 전용 5개 선택지를 제공 / 바로 목적을 좁히고 ACTIVE 범위를 정직하게 보여 줌 / classifier·service·Web·회귀 테스트 변경 필요
- 선택지 B / 장점 / 단점: 현재 네 분야 FOLLOWUP 유지 / 변경 없음 / 반복 루프와 낮은 완주율 유지
- 당신의 추천안: A
- 답을 받지 못할 때 사용할 기본값: A를 계획하되 제품 코드는 승인 전 변경하지 않음
- 영향을 받는 파일·계약·데이터·배포: chat classifier/service/response, Web followup copy, API·Web tests; DB/data/provider/deploy 불변

일반 적격 실패 질문의 운영자 작성→별도 승인과 시민의 읍·면·동 직접 선택은
`AGENTS.md`, `PROJECT_PLAN.md`, `APPROVAL_POLICY.md`에서 이미 P0로 확정됐다. 다시 선택을
요구하지 않는다. 구현 시 기본 형태는 다음과 같다.

- 관리자: 운영자 구조화 작성 폼, 공식 필드 수동 입력, existing validation/candidate 저장,
  작성자와 다른 승인자 검수
- 시민: `/chat`에서 직접 읍·면·동 선택, 선택값을 chat 요청에 포함, official office card 표시

답변 예시: `Q-CHAT-FOLLOWUP-001=A`

## 8. 검증 증거

| 검증 | 결과 |
|---|---|
| API focused classification/service/admin | 106 passed, warning 1 |
| API full | 2044 passed, 8 skipped, warning 1, subtests 5 |
| Web focused candidate/admin/chat | 21 passed |
| Web full | 56 passed |
| Web lint | PASS |
| Web typecheck | PASS |
| Contract generation check | PASS |
| Contract tests | 90 passed |
| tracked secret pattern scan | PASS |
| 실제 browser routes × 390/430 | 10/10 no horizontal overflow |
| 실제 browser console | error 0, warning 0 |

미실행/제한:

- 실제 관리자 create/approve E2E는 현재 final 20 ACTIVE DB를 변경하므로 실행하지 않았다.
- local DB pgTAP/integration 8건은 이번 API full run에서 gate skip됐다.
- Web build는 사용자의 실행 중인 `next dev`와 같은 `.next` 충돌을 피하려고 재실행하지 않았다.
- root aggregate 한 번은 124초에 timeout돼 결과로 사용하지 않았고 남은 해당 test process는 종료했다.
- provider actual 호출은 별도 인간 승인 없이는 재실행할 수 없어 0회다.

## 9. 다음 구현 순서

1. Q-CHAT-FOLLOWUP-001 승인 후 반복 루프를 TDD로 수정한다.
2. 이미 확정된 P0에 따라 일반 운영자 작성 폼→후보 저장 수직 흐름을 구현한다.
3. 후보 화면에 대기/승인/반려 이력과 정확한 비-AI 문구를 함께 정리한다.
4. 이미 확정된 P0에 따라 직접 지역 선택→office card E2E를 닫는다.
5. P1 KPI와 performance Phase B는 별도 데이터 권위/DB 결정 뒤 진행한다.
