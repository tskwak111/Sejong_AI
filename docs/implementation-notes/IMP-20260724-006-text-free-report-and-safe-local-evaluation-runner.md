# IMP-20260724-006 — Text-free report and safe local evaluation runner

- Date/Time (KST): 2026-07-24T02:14:27+09:00
- Task ID: LLM-002
- Type: implementation
- Status: Done — Task 5 / LLM-002 In Progress
- Author/Agent: Codex integration, Task 5 implementation and independent review subagents
- Branch: codex/LLM-002-upstage-synthetic-evaluation
- Base commit: 2d46c9b
- Related plan/ADR/RFP:
  - [승인 실행계획](../superpowers/plans/2026-07-23-upstage-solar-pro3-synthetic-evaluation.md)
  - [승인 명세](../superpowers/specs/2026-07-23-upstage-solar-pro3-synthetic-evaluation-design.md)
  - [Task 4.5 checkpoint](IMP-20260724-005-content-free-per-attempt-evaluation-evidence.md)

## 1. 사용자 요청과 완료 기준

### 요청

승인된 합성 평가를 실제 local human gate에서 안전하게 실행할 수 있도록 text-free aggregate
report와 fixed-path runner를 TDD로 구현하되 실제 DB/key/network는 사용하지 않는다.

### Acceptance Criteria

- report에는 질문·답변·본문·secret·DSN·path·시간·계정 식별자가 없다.
- final outcome과 per-attempt count, tokens, budget, Decimal cost가 서로 일치한다.
- 정확히 30 case, T-01~T-10 review/score, 모두 PASS/OK와 품질·비용 gate여야 overall PASS다.
- Windows selector policy, canonical fixture, local readiness가 provider 생성보다 앞선다.
- CLI는 override/value/exception을 echo하지 않고 fixed ignored JSON만 atomic write한다.
- success/failure 모든 resource cleanup과 독립 review를 통과한다.
## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 구현·review subagents와 Codex가 TDD·독립검토·통합했다. |
| When — 언제 | 2026-07-24 KST, Task 4.5 review-clean 뒤 Task 5 checkpoint |
| Where — 어디서 | internal report, root local runner, fake pool/repository/client tests |
| What — 무엇을 | strict aggregate/report validation, PM score contract, readiness-first Windows runner |
| Why — 왜 | actual 실행에서 content/secret 유출과 partial/fabricated PASS를 막기 위해 |
| How — 어떻게 | RED→GREEN, 30 report +14 runner +123 LLM tests, independent fix/re-review |
| How much — 어느 정도 | production/report 1, runner 1, tests 2, README 1, 2 commits; DB/key/network 0 |

## 3. 시작 전 상태

- 관련 파일: EvaluationRun/attempt trace/cost, local settings/pool/repository/readiness, fixed artifact
  ignore rule, scripts runner patterns.
- 기존 동작: 안전한 in-memory run은 있었지만 aggregate serialization, PM scoring, actual lifecycle
  entrypoint는 없었다.
- 발견한 충돌/부채:
  - 첫 구현은 높은 점수+closed FAIL, mismatched final trace, forged token totals로 PASS 가능했다.
  - runner unittest patch typing과 pool/client/review cleanup path 증거가 부족했다.
  - secret scanner가 test DSN/변수명을 보수적으로 match해 값 없는 형태로 보정했다.
- Git 상태: 시작 `2d46c9b`, 구현 `4a972a6`, integrity fix `bfe350e`, re-review Approved.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| REPORT-PROJECTION | 개인정보 | dataclass 직렬화 위험 | exact explicit dict only | content-free artifact |
| HUMAN-PASS | 품질 | high score + FAIL 모순 | 10개 모두 PASS/OK 필수 | overall gate |
| TRACE-INTEGRITY | 증거 | final/attempt mismatch | per-case state matrix | failure metrics |
| TOKEN-INTEGRITY | 비용 | forged totals/cost | run cases와 report를 runner 재대조 | cost evidence |
| RUNNER-ORDER | 보안 | provider 조기 생성 | readiness PASS 뒤 client/provider | local safety |

## 5. 설계 결정과 대안

### 선택

- root/nested report keys를 explicit projection하고 deterministic compact JSON으로 atomic replace한다.
- `HumanFixtureScore`는 exact int 1..5, closed reason, derived decision만 허용한다.
- safe parser는 `--review` 외 입력을 모두 bounded code로 거부한다.
- runner는 args/TTY→Windows policy→settings→fixture hash→pool/readiness→provider 순서다.

### 이유

actual 실패 증거를 남기면서도 질문/답변/secret을 저장하지 않고, report/runner 양쪽에서 totals를
검증해 위조·부분 실행의 PASS를 차단한다.

### 고려했지만 선택하지 않은 대안

- `asdict(run)`: in-memory question/answer 유출 위험.
- CLI key/model/path override: 승인 범위를 우회하므로 제외.
- readiness 없이 DB open만 확인: ACTIVE/OFFICIAL projection을 증명하지 못해 제외.
- timestamp/user/path metadata: 평가 판정에 불필요하고 식별 위험이 있어 제외.
## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| `llm/report.py` | exact aggregate, score validation, strict PASS matrix | report 권위 |
| `test_report.py` | text-free/schema/score/trace/token/cost/partial run matrix | integrity regression |
| root runner | safe args/lifecycle/readiness/reconciliation/review/atomic write | local entrypoint |
| runner unittest | ordering/output/cleanup/tamper/fixed path/TTY tests | no-real-resource proof |
| `scripts/README.md` | local-only command와 boundary | handoff |
| plan/version/note | Task 5 완료, docs 2.13.7 | durable status |

### 데이터 흐름/상태 변화

EvaluationRun+PM scores→explicit aggregate→run/budget/token/cost reconciliation→fixed ignored JSON.
actual runner만 TTY에 첫 valid 질문/답변을 보여주며 JSON에는 넣지 않는다.

### 오류·빈 상태·롤백

args/config/fixture/DB/review/runtime는 bounded value-free code로 종료한다. report는 overall false도
failure evidence로 쓸 수 있다. temp file은 finally 제거하고 resources는 finally close한다.
## 7. 버전 전후

### 생성 시 매니페스트
- product_spec: 2.4.0
- repo_guidance: 1.7.6
- application: 0.6.0-local-core-loop
- web: 0.4.0-chat-admin-local-integration
- api: 3.1.0-draft
- shared_contracts: 0.4.0
- database_schema: 0.4.0-local
- official_data: 0.1.0-initial.2
- mock_data: 0.0.0-not-populated
- prompt_set: 0.0.3-upstage-solar-pro3-synthetic-selected
- test_suite: 1.2.1-core-loop-closeout
- documentation: 2.13.6

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Application | 0.6.0-local-core-loop | 동일 | Task 6 gate 전 유지 |
| Web | 0.4.0-chat-admin-local-integration | 동일 | 0 |
| API | 3.1.0-draft | 동일 | public route 0 |
| DB schema | 0.4.0-local | 동일 | fake pool only |
| Official data | 0.1.0-initial.2 | 동일 | canonical read only |
| Mock data | 0.0.0-not-populated | 동일 | manifest mock 0 |
| Prompt set | 0.0.3-upstage-solar-pro3-synthetic-selected | 동일 | Task 6에서 승격 |
| Test suite | 1.2.1-core-loop-closeout | 동일 | Task 6에서 승격 |
| Docs | 2.13.6 | 2.13.7 | Task 5 review-clean |

## 8. 명령과 테스트 증거

| 명령/검증 | 결과 | 시간/개수 | 증거 경로 |
|---|---|---|---|
| report/runner RED | missing module/script | expected | ignored task report |
| initial GREEN | report 12, runner 10, LLM 105 | PASS | task report |
| first review | Critical human FAIL, Important trace/token, Minor typing/cleanup | Needs fixes | bounded diff |
| fix RED | report 3 failed, runner 1 failed | expected | task report |
| fix GREEN | report 30, runner 14, LLM 123, Ruff/Mypy PASS | PASS | task report |
| independent re-review | Spec ✅, findings 0, Quality Approved | `2d46c9b..bfe350e` | bounded diff |
| main frozen/offline recheck | LLM 123, runner 14, Ruff/Mypy/docs/secret PASS | PASS | terminal |

### 미실행 검증과 이유

전체 API/root/Web Task 6와 actual DB/provider/PM Task 7은 미실행이다.
## 9. 보안·개인정보·접근성·성능 영향

- Privacy: aggregate에 content/identity 0; TTY review content는 local memory/display only.
- Security: safe parser/value-free errors/readiness-before-provider/cleanup; actual secret/network 0.
- Accessibility: 시민 UI 0; PM CLI는 keyboard/TTY only local gate.
- Performance/cost: concurrency/attempt/cost cap 재검증; actual cost 0.

## 10. 데이터와 출처 영향

- 공식 데이터/DB/schema: 불변·미접근; canonical path/hash만 runner에서 사용.
- mock/AI 생성: test fakes only, actual output 0.
- verified date: 2026-07-24.

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- Task 5 완료는 actual quality PASS가 아니다.
- actual local DB/key/network와 10개 PM score는 Task 7 human gate다.
- public/free-input provider option B는 미승인이다.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- helper/factory injection, ExitStack tests, deterministic JSON details는 내부 구현 세부다.
- Task 6은 transitive public import isolation과 base-protected diff를 실행한다.

## 13. 인수인계·재현·롤백

### 재현

1. `git show 4a972a6`, `git show bfe350e`.
2. common-dir uv frozen/offline로 report/LLM pytest와 runner unittest.
3. Ruff format/check, expanded Mypy, docs/secret/diff.

### 롤백

`git revert bfe350e`, `git revert 4a972a6`. ignored artifact가 존재하면 수동 삭제 가능하며
DB migration/data restore/key revoke는 없다.

### 다음 개발자 시작점

Task 6 brief로 architecture/security/full regression/manifest gate를 실행한다.
## 14. 남은 위험·미해결 질문·다음 단계

- Task 6 offline gate와 Task 7 human actual이 남았다.
- actual artifact는 scanner 제외 경로이므로 report builder explicit projection을 변경하지 않는다.

## 15. 자체 리뷰

- [x] 요청 충족
- [x] 테스트/검증
- [x] source-of-truth/계약/버전 동기화
- [x] 개인정보 원문 노출 없음
- [x] 구현 노트 INDEX 갱신
