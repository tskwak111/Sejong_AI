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
