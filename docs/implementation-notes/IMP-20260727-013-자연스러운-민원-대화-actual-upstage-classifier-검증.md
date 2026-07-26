# IMP-20260727-013 — 자연스러운 민원 대화 actual Upstage classifier 검증

- Date/Time (KST): 2026-07-27T05:00:47+09:00
- Task ID: CHAT-NATURAL-001-T16
- Type: testing-provider-actual
- Status: Done
- Author/Agent: 사용자 승인자 / Codex
- Branch: codex/ACTUAL-P0-UX-GAPS-001
- Base commit: 8e02950
- Related plan/ADR/RFP:
  - `docs/superpowers/plans/2026-07-27-natural-civic-dialogue-and-operations.md`
  - `docs/superpowers/specs/2026-07-27-natural-civic-dialogue-and-operations-design.md`
  - ADR-0025, ADR-0026

## 1. 사용자 요청과 완료 기준

### 요청

- 실제 Upstage 호출과 DB reset/seed, public/remote 작업까지 승인하고 가능한 범위를 계속
  진행한다.

### Acceptance Criteria

- exact 60 synthetic cases, deterministic 40/provider 20, skip 0
- policy/privacy provider outbound 0, secret·실제 PII·본문 기록 0
- classifier cap 20/combined cap 40/retry 0/concurrency 1/USD 0.05 stop
- 집계 보고서와 재현 runbook, 버전·INDEX 동기화
## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 사용자 승인자, Codex 구현·보안·검증 담당 |
| When — 언제 | 2026-07-27 04:35~05:02 KST |
| Where — 어디서 | isolated worktree, local Windows process, Upstage `solar-pro3` |
| What — 무엇을 | 고정 60문항 classifier fixture·runner·tests·actual 집계·runbook |
| Why — 왜 | deterministic-only 오분류를 줄이면서 PII·출처·저장 권한을 LLM에 넘기지 않기 위해 |
| How — 어떻게 | RED/GREEN, exact profile preflight, 20-call cap, payload-free aggregate |
| How much — 어느 정도 | 60 cases, actual 2 bounded runs, cumulative USD 0.003873210 |

## 3. 시작 전 상태

- 관련 파일: classifier prompt/adapter/settings/cost, privacy redaction, Task 16 plan
- 기존 동작: adapter 단위 테스트는 있었으나 frozen 60 fixture·actual runner·actual evidence는 없었다.
- 발견한 충돌/부채: 첫 actual에서 schema/limit/privacy는 통과했지만 route 정확도가 54/60이었다.
- Git 상태: base `8e02950`, isolated `codex/ACTUAL-P0-UX-GAPS-001`; primary checkout의 사용자
  변경과 `.env`는 수정하지 않았다.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| A-057 | Resolved | primary `.env`에는 classifier exact non-secret profile이 없음 | key는 읽기 전용·process-only, exact profile도 process-only | tracked secret 0 |
| A-058 | Resolved | 첫 actual 54/60 | 지원 분야 동의어·scope gap 경계를 prompt에 명시하고 corrective run | prompt patch bump |

## 5. 설계 결정과 대안

### 선택

- 40 deterministic/20 provider 고정 분할
- 정책·개인조회·법적판단은 provider 0
- 보수적 다음 호출 비용 검사와 실제 usage 완전성 검사
- provider payload를 쓰지 않는 aggregate-only Markdown report
### 이유

- 안전·정책 경로의 결정권은 서버에 남기고 모호한 분야 분류에만 LLM을 쓴다.
- 실제 호출 비용과 JSON 안정성을 수치로 증명하면서 질문·응답 본문 재노출을 막는다.
### 고려했지만 선택하지 않은 대안

- 60건 모두 provider 전송: 불필요한 개인정보·비용·장애 표면 때문에 기각
- 첫 실패 후 fixture 기대값 완화: 제품 계약을 모델 결과에 맞추게 되므로 기각
- provider 응답 전문 저장: 디버깅 편의보다 privacy/retention 위험이 커서 기각
## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| `classifier-60.json` | 정확한 5그룹·60 합성 PII-free case | acceptance 동결 |
| `classifier_prompt.py` | 네 분야 자연어 동의어·scope gap 예시 명시 | 최초 54/60 root cause 교정 |
| `run_upstage_classifier_evaluation.py` | exact path/profile/cap/cost/usage/report runner | actual 재현성과 fail-closed |
| runner/adapter tests | fixture 분포·outbound·report·profile·prompt 경계 | RED/GREEN 증거 |
| runbook/report | 안전 실행·복구와 aggregate 결과 | 운영 인수인계 |

### 데이터 흐름/상태 변화

- 합성 질문 → deterministic redaction → deterministic route 또는 모호한 20건만 classifier →
  closed decision validation → aggregate counters.
- 시민 API, local DB, official KB와 interaction/candidate/audit row는 호출·변경하지 않았다.

### 오류·빈 상태·롤백

- 설정/경로/fixture/profile/usage/cost 불일치는 네트워크 전 또는 집계 작성 전에 bounded code로
  종료한다.
- prompt 회귀 시 `classifier_prompt.py`와 prompt/test/docs patch version을 revert하고 provider
  modes false를 유지한다.
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
- prompt_set: 0.3.0-hybrid-classifier
- test_suite: 1.9.0-natural-dialogue
- documentation: 2.24.0

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Application | 0.11.0-natural-dialogue | 동일 | public behavior 불변 |
| Web | 0.7.0-natural-dialogue | 동일 | 변경 없음 |
| API | 4.0.0-draft | 동일 | wire 계약 불변 |
| DB schema | 0.5.0-local | 동일 | DB 호출 0 |
| Official data | 0.1.0-initial.2 | 동일 | seed 불변 |
| Mock data | 0.0.0-not-populated | 동일 | fixture는 test-only 합성 |
| Prompt set | 0.3.0-hybrid-classifier | 0.3.1-hybrid-classifier | 경계 설명 보강 |
| Test suite | 1.9.0-natural-dialogue | 1.9.1-natural-dialogue | actual 60 gate |
| Docs | 2.24.0 | 2.24.1 | runbook/report/note |

## 8. 명령과 테스트 증거

| 명령/검증 | 결과 | 시간/개수 | 증거 경로 |
|---|---|---|---|
| focused pytest | PASS | 17 passed | test files |
| Ruff check/format | PASS | changed Python scope | command output |
| Mypy runner | PASS | 1 source file | command output |
| exact profile preflight | PASS | key presence only, cap 20/40 | console aggregate |
| initial actual | accuracy FAIL | 54/60, invalid 0, USD 0.001763025 | report history |
| corrective actual | PASS | 60/60, 20 outbound, 16.763s, USD 0.002110185 | `CHAT-NATURAL-001-UPSTAGE-ACTUAL.md` |

### 미실행 검증과 이유

- 전체 저장소 gate는 final tracked source에서 Task 18에 정확히 한 번 재실행한다.
## 9. 보안·개인정보·접근성·성능 영향

- Privacy: 합성 PII-free만 사용, policy/privacy outbound 0, payload persistence 0.
- Security: key는 process memory에만 있었고 출력·파일 복사·commit 0; provider modes 제거.
- Accessibility: 사용자 UI 변경 없음.
- Performance/cost: corrective p95가 아니라 bounded 전체 elapsed 16.763s; 누적 실제 비용
  USD 0.003873210 < USD 0.05.

## 10. 데이터와 출처 영향

- 공식 데이터: `.2` KB/office/mapping 변경 0.
- mock/AI 생성: 60문항은 test-only 합성 fixture이며 공식 데이터가 아니다.
- schema/lineage: DB/schema migration/row 변경 0.
- verified date: 2026-07-27 KST.

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- actual은 PASS했지만 시민 질문 전체를 LLM에 맡긴 것이 아니다. 안전·명확 경로는 계속
  deterministic이고 모호한 safe 질문만 분류한다.
- 두 actual run의 누적 비용은 USD 0.003873210이다.
- provider가 답변·출처·보관·후보 승인 여부를 정하지 않는다.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- usage response hook, conservative next-attempt cost guard, atomic Markdown writer와 fixture parser는
  같은 공개 계약 안의 내부 구현이다.

## 13. 인수인계·재현·롤백

### 재현

- `docs/runbooks/UPSTAGE-CLASSIFIER-ACTUAL.md`의 offline gate와 exact profile 명령을 따른다.

### 롤백

- provider 세 모드를 false로 복원하고 prompt/runner/fixture/report commit을 revert한다.

### 다음 개발자 시작점

- Task 17의 configured remote target discovery와 시민 route/admin-negative smoke.
## 14. 남은 위험·미해결 질문·다음 단계

- actual provider의 장기 안정성·월별 비용·운영 관측은 public 운영 전 별도 결정이 필요하다.
- remote target/credential 유무는 다음 task에서 값 없이 재감사한다.

## 15. 자체 리뷰

- [x] 요청 충족
- [x] 테스트/검증
- [x] source-of-truth/계약/버전 동기화
- [x] 개인정보 원문 노출 없음
- [x] 구현 노트 INDEX 갱신
