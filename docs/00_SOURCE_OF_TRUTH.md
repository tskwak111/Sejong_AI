# Source of Truth와 문서 충돌 해결 규칙

## 1. 목적

기존 업로드 패키지에는 초기 아이디어, 넓은 기능 범위, 오래된 스타터 코드가 함께 있다. 이 문서는 Codex와 인간 개발자가 어떤 문서를 정답으로 사용해야 하는지 고정한다.

## 2. 권위 순서

| 순위 | 위치 | 역할 |
|---:|---|---|
| 1 | `AGENTS.md` | 작업 방식·안전·기록 의무 |
| 2 | `docs/source-of-truth/TEAM_DECISIONS.md` | 최종 제품·범위·기술·정책 결정 |
| 3 | `docs/source-of-truth/PROJECT_PLAN.md` | 일정·P0/P1/P2·인수 기준 |
| 4 | `docs/source-of-truth/RFP_MATRIX.md` | 요구사항 추적과 구현 수준 |
| 5 | `docs/source-of-truth/PRIVACY_POLICY.md`, `APPROVAL_POLICY.md`, `KB_GUIDE.md` | 영역별 필수 정책 |
| 6 | `docs/adr/` | 아키텍처 결정과 트레이드오프 |
| 7 | `contracts/`, `database/` | 현재 코드가 따라야 할 실행 계약 초안/확정본 |
| 8 | `docs/implementation-notes/` | 실제 구현 이력과 증거 |
| 9 | `legacy/` | 역사·참고만 가능, 활성 범위가 아님 |

상위 문서와 하위 문서가 충돌하면 상위 문서를 따른다. 다만 상위 문서가 모호하거나 현실 구현과 불일치하면 임의로 해석하지 않고 모호성 레지스터와 인터뷰를 사용한다.

## 3. 현재 절대 범위

- 4개 민원 분야
- 공식 KB 20건
- 페이지 3개
- 표본 질문 20개 + 회귀 1개
- 관리자 승인형 개선 루프
- 실제 GPS/상태조회/다국어/고급 분석은 P2

2026-07-25의 Q-MVP-001 local/private 마일스톤은 위 최종 범위를 줄이지 않는다. 19개 초기 ACTIVE를
실제 local DB에 반영한 뒤 관리자 개선 루프로 20번째 ACTIVE를 만들고 표본 20·회귀 1·보안·데모를
완주하는 중간 gate다. 외부 LLM 품질 평가, 고급 UI, 100명 부하, 자동 백업과 공개 배포는 이
마일스톤 뒤로 연기하지만 최종 P1 백로그에서 삭제하지 않는다. 상세 권위는 D-058/ADR-0020과
승인된 MVP-001 명세·계획이다.

2026-07-23 Q-LLM-005=A/D-065/ADR-0022는 아직 구현되지 않은 DeepSeek 선택을 대체한다. 외부
공급자는 Upstage exact `solar-pro3`이며, 먼저 local/private server-allowlisted 합성
`T-01`~`T-10` 평가로 한국어 품질·strict JSON·비용을 검증한다. 결정론적 시민 경로는 계속
기본이고 실제 시민/free-input/public/remote provider 사용은 선택지 B의 별도 승인 전 금지한다.
2026-07-25 actual은 outbound 30회에서 strict-schema 27/30으로 전체 FAIL했다. 인간 검토 9개
평균 4.8444·최저 4와 VAT 포함 USD 0.004654815는 통과했지만 JSON 100% 기준을 충족하지
못했으므로 D-071에서 선택지 B 미승인과 provider-disabled/template 시민 경로 유지를 확정했다.

이후 사용자는 2026-07-25 Q-LLM-006~012/D-072/ADR-0023으로 **local/private 입찰 시연
MVP에 한해** 근거 제한형 Upstage 시민 답변 생성을 새로 승인했다. 보수적 마스킹, deterministic
supported intent, ACTIVE/OFFICIAL 검색과 근거 gate를 모두 통과한 요청만 마스킹 질문과 최소
KB를 보낸다. 모델은 summary와 server-issued fact ID만 제안하고, 공식 fact text·출처·기관·정책
결과는 서버가 결합한다. 8초·1 attempt·hidden retry 0이며 검증이나 호출 실패 시 모델 결과 전체를
버리고 기존 공식 template로 답한다. LLM-002 actual FAIL 증거는 그대로이며 public/remote/실제
기관 운영은 별도 개인정보·보안·비용·배포 승인 전까지 계속 금지한다. 현재 상태는 설계·D-073
written specification·D-074 8-task 실행계획 승인에 따른 offline 구현·task-scoped review·
provider-disabled final root gate 완료와 D-075 local actual PASS다. final 10건은
GENERATED 4/TEMPLATE 6, 출처 10/10, 공식 사실 mismatch 0, PII-free fixture의 typed
write-boundary forbidden-value 위반 0,
outbound 10이었다. legacy runner의 VAT 포함 USD 0.001319835는 usage completeness를 강제하기
전 reported lower-bound이며, configured maximum USD 0.0135168은 USD 0.05 cap 아래다. 종료 뒤
provider-disabled TEMPLATE로 복원했다.
corrective second 10-call run의 governance incident는 D-076에서 사용자가 사후 확인하고 PR #13
병합을 승인해 A-049를 해결했다. D-077/Q-DB-CLEANUP-001=A에 따라 오표시 metadata 22행은
현재 유지하고 해당 local DB snapshot의 event 통계를 평가 KPI로 사용하지 않는다. 정식 수치가
필요해지는 시점의 local reset·정식 `.2` 재시드·필요한 19→20 승인 흐름 재현은 B의 별도 인간
승인을 받는다. 이는 future provider rerun, DB reset/delete/update, public/remote 또는 실제 기관
운영 승인이 아니다.

2026-07-27 Q-CLASS-001=A/D-086/ADR-0025는 future local/private 질문 분류를 hybrid로
확장하는 방향을 승인했다. PII·policy·명백한 결과는 deterministic server gate가 유지하고,
안전하게 마스킹됐지만 애매한 현재 질문만 Upstage closed-enum classifier에 전달한다. 모델은
답변·출처·저장 여부를 결정하지 못한다. exact budget/schema written spec과 Q-CLASS-002 전
current runtime·provider actual call은 변경하지 않으며 public/remote 금지를 유지한다.

## 4. 변경 절차

제품 범위, 공개 계약, DB, 개인정보, 외부 공급자, 배포 아키텍처가 바뀌면:

1. 인간 승인
2. ADR 또는 결정 로그
3. source-of-truth 갱신
4. 계약/스키마/테스트 갱신
5. 버전 매니페스트 갱신
6. 구현 노트 기록

## 5. Legacy 사용 규칙

- 코드를 재사용하기 전 현재 계약·보안·범위와 비교한다.
- 오래된 엔드포인트/데이터/범위를 그대로 복구하지 않는다.
- 재사용한 코드의 출처와 변경 이유를 구현 노트에 기록한다.
- legacy 자체는 자동 포맷·대규모 수정하지 않는다.
