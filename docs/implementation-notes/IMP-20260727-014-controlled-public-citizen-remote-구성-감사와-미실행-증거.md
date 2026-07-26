# IMP-20260727-014 — controlled public citizen remote 구성 감사와 미실행 증거

- Date/Time (KST): 2026-07-27T05:05:35+09:00
- Task ID: CHAT-NATURAL-001-T17
- Type: deployment-preflight-evidence
- Status: Done
- Author/Agent: 사용자 승인자 / Codex
- Branch: codex/ACTUAL-P0-UX-GAPS-001
- Base commit: 7c7f698
- Related plan/ADR/RFP: CHAT-NATURAL plan Task 17, ADR-0018, ADR-0026, D-092/D-095

## 1. 사용자 요청과 완료 기준

### 요청

- 승인된 public/remote 작업을 실제 구성에 맞춰 가능한 범위까지 실행한다.

### Acceptance Criteria

- target/project/credential/origin을 값 없이 발견한다.
- 구성됐을 때만 시민 4경로 smoke를 수행하고 admin/provider는 비활성으로 검증한다.
- target이 없으면 추측·생성·push하지 않고 정확한 미실행 이유와 rollback 한계를 기록한다.
## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 사용자 승인자, Codex 배포·보안 검증 담당 |
| When — 언제 | 2026-07-27 05:02~05:12 KST |
| Where — 어디서 | tracked config, process env names, GitHub secret names, local code boundary |
| What — 무엇을 | remote target discovery, public preflight, conditional non-execution evidence |
| Why — 왜 | 승인만으로 target을 추측하지 않고 공개 노출·비용·데이터 위험을 막기 위해 |
| How — 어떻게 | name-only discovery, route composition inspection, focused 42 tests, runbook/report |
| How much — 어느 정도 | target/credential/write/request 0, focused tests 42 PASS |

## 3. 시작 전 상태

- 관련 파일: ADR-0026, deployment plan Task 17, workflows, Supabase config, FastAPI composition.
- 기존 동작: local 00700/rollback/pgTAP는 PASS했지만 remote target evidence는 없었다.
- 발견한 충돌/부채: 추천 공급자 서술은 있으나 실제 provider/project/region/origin/saved version은
  구성되지 않았다.
- Git 상태: source `7c7f698f76a19fb3b0cb1be0383c9b01bee0046f`; clean에서 discovery.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| A-059 | Resolved | remote target이 구성됐는가 | 0; `Not executed: target not configured` | remote writes 0 |
| A-060 | Pending-human | 향후 공급자·계정·리전·origin·비용·DNS | 현재 선택하지 않음 | 실제 deploy 전 인간 결정 |

## 5. 설계 결정과 대안

### 선택

- local hardening과 code-level citizen/admin/provider boundary는 검증하되 remote write는 0으로
  유지한다.

### 이유

- dedicated target과 rollback version 없이 배포하면 사용자 자산·비용·공개 보안 경계를 추측하게
  된다.

### 고려했지만 선택하지 않은 대안

- Vercel/Render/Supabase 자동 계정·project 생성: 소유권·리전·비용 미결정으로 기각.
- GitHub source remote를 배포 target으로 간주: 실행 환경이 아니므로 기각.
## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| controlled public runbook | future target discovery→preflight→DB→deploy→smoke→rollback | 재현 |
| remote verification report | target 0와 code-level aggregate | 과장 없는 evidence |
| ADR/source-of-truth/D-095 | actual 결과와 미실행 경계 동기화 | 권위 일치 |

### 데이터 흐름/상태 변화

- remote DB migration/seed, public deploy, remote request, provider request 모두 0.

### 오류·빈 상태·롤백

- target 미구성은 bounded non-execution 결과다. saved deployment version이 없어 application
  rollback command도 현재는 기록할 수 없다.
## 7. 버전 전후

### 생성 시 매니페스트
- product_spec: 2.6.0
- repo_guidance: 1.7.9
- application: 0.11.0-natural-dialogue
- web: 0.7.0-natural-dialogue
- api: 4.0.0-draft
- shared_contracts: 1.0.0
- database_schema: 0.5.0-local
- official_data: 0.1.0-initial.2
- mock_data: 0.0.0-not-populated
- prompt_set: 0.3.1-hybrid-classifier
- test_suite: 1.9.1-natural-dialogue
- documentation: 2.24.1

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Application | 0.11.0-natural-dialogue | 동일 | deploy 0 |
| Web | 0.7.0-natural-dialogue | 동일 | deploy 0 |
| API | 4.0.0-draft | 동일 | contract 불변 |
| DB schema | 0.5.0-local | 동일 | remote migration 0 |
| Official data | 0.1.0-initial.2 | 동일 | remote seed 0 |
| Mock data | 0.0.0-not-populated | 동일 | 변경 없음 |
| Prompt set | 0.3.1-hybrid-classifier | 동일 | provider 0 |
| Test suite | 1.9.1-natural-dialogue | 동일 | 기존 focused suite 사용 |
| Docs | 2.24.1 | 2.24.2 | public runbook/report/evidence |

## 8. 명령과 테스트 증거

| 명령/검증 | 결과 | 시간/개수 | 증거 경로 |
|---|---|---|---|
| tracked config/env/GitHub secret name discovery | PASS | deploy targets/secrets 0 | remote report |
| public citizen/security focused pytest | PASS | 42 passed, 1 dependency warning | command output |
| default OpenAPI composition | PASS | citizen 4/admin 0/provider 0 | remote report |
| DB artifact check | PASS | migration/rollback/pgTAP 11/11/11 | remote report |

### 미실행 검증과 이유

- remote migration/seed/deploy/smoke: `Not executed: target not configured`.
## 9. 보안·개인정보·접근성·성능 영향

- Privacy: citizen/provider payload 전송 0.
- Security: secret/DSN value 조회·출력 0; public admin path 0.
- Accessibility: 배포/UI 변경 없음.
- Performance/cost: public cloud 비용·traffic 0.

## 10. 데이터와 출처 영향

- 공식 데이터: local `.2`와 ACTIVE 20 불변; remote 복사 0.
- mock/AI 생성: 없음.
- schema/lineage: 00700 tracked evidence만 확인, remote apply 0.
- verified date: 2026-07-27 KST.

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- public/remote 작업 승인만으로 deploy target이 생기지는 않는다.
- 실제 배포에는 공급자·계정·리전·origin·비용·DNS·saved rollback version이 필요하다.
- 인증 없는 admin과 real citizen provider outbound는 계속 금지다.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- 경로 count, file count, hash와 env/secret **이름 존재 여부**만 검사했다.

## 13. 인수인계·재현·롤백

### 재현

- `docs/runbooks/CONTROLLED-PUBLIC-CITIZEN-DEPLOYMENT.md`를 따른다.

### 롤백

- 실제 remote write가 0이라 현재 롤백할 외부 상태도 0이다.

### 다음 개발자 시작점

- Task 18 final gate와 Draft PR. 실제 target이 향후 구성되면 runbook Step 1부터 새 evidence run.
## 14. 남은 위험·미해결 질문·다음 단계

- A-060: provider/account/region/origin/budget/domain/rollback target은 인간 구성 전 Pending.

## 15. 자체 리뷰

- [x] 요청 충족
- [x] 테스트/검증
- [x] source-of-truth/계약/버전 동기화
- [x] 개인정보 원문 노출 없음
- [x] 구현 노트 INDEX 갱신
