# IMP-20260724-007 — Upstage offline security architecture gate

- Date/Time (KST): 2026-07-24T03:04:10+09:00
- Task ID: LLM-002
- Type: implementation
- Status: Done — Task 6 / LLM-002 In Progress
- Author/Agent: Codex integration, Task 6 implementation and independent review subagents
- Branch: codex/LLM-002-upstage-synthetic-evaluation
- Base commit: a249b50
- Related plan/ADR/RFP:
  - [승인 실행계획](../superpowers/plans/2026-07-23-upstage-solar-pro3-synthetic-evaluation.md)
  - [승인 명세](../superpowers/specs/2026-07-23-upstage-solar-pro3-synthetic-evaluation-design.md)
  - [ADR-0022](../adr/0022-upstage-solar-pro3-synthetic-evaluation.md)

## 1. 사용자 요청과 완료 기준

### 요청

Upstage 합성 평가의 actual 실행 전에 offline security·architecture·regression gate를 완료하고,
공유 버전·권위 문서를 동기화한다. 실제 key/network/DB/public route는 사용하지 않는다.

### Acceptance Criteria

- public/import-safe 앱은 LLM package를 전이 로드하거나 provider client를 만들지 않는다.
- API key·질문·응답·PII·source metadata가 URL/body/log/model schema로 새지 않는다.
- canonical allowlist, fallback, 30-attempt cap, strict contract 경계를 테스트한다.
- full API, root 범위, Ruff, Mypy, 문서·secret·dependency·protected-diff gate를 확인한다.
- 독립 review 지적을 닫고 actual provider 결과 없이 Task 6을 기록한다.
## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 사용자 승인 아래 구현·review subagent와 Codex 통합 담당 |
| When — 언제 | 2026-07-24 KST, Task 5 review-clean 직후 |
| Where — 어디서 | FastAPI/LLM test boundary, root environment contract, version/docs |
| What — 무엇을 | offline provider isolation, leak matrix, full regression, version promotion |
| Why — 왜 | 실제 호출 전에 비밀·개인정보·계약·비용 경계를 자동 증명하기 위해 |
| How — 어떻게 | RED/GREEN, adversarial LogRecord/MockTransport tests, 독립 re-review |
| How much — 어느 정도 | test 4파일, docs/version 9파일; actual key/network/DB/data/public route 0 |

## 3. 시작 전 상태

- 관련 파일: `apps/api/tests/llm/test_{architecture,security}.py`,
  `apps/api/tests/test_architecture.py`, `scripts/tests/test_security_boundaries.py`, plan/manifest/docs.
- 기존 동작: evaluator/runner의 기능·unit gate는 있었지만 public transitive import와 Python
  structured logging extras까지 포함한 end-to-end isolation 증거가 없었다.
- 발견한 충돌/부채: 첫 review는 정상 `/api/v1/chat` handler 및 provider factory zero-call
  증거와 structured `LogRecord` custom extra 검사를 요구했다. root 회귀에는 superseded DeepSeek
  env-template 기대 1건과 linked-worktree ignored Supabase binary 부재 2건이 드러났다.
- Git 상태: 시작 `96e6773`; test commits `45edd05`, `8f885bd`, `2c6dcd1`; env fix `a249b50`.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| LLM-LOG-EXTRA | 보안 | custom LogRecord extra에 key가 들어갈 수 있음 | all structured extras 검사 | secret leakage gate |
| LLM-NORMAL-HANDLER | 아키텍처 | 422 override만으로 normal path isolation 불충분 | valid request 503 + provider factory 0 | public disabled proof |
| ROOT-ENV | 회귀 | template test가 DeepSeek를 기대 | 승인된 exact Upstage 값으로 보정 | root security contract |
| WORKTREE-RUNTIME | 환경 | ignored CLI binary가 worktree에 없음 | primary checkout에서 exact 2 tests | DB/tooling evidence |

## 5. 설계 결정과 대안

### 선택

- sentinels를 URL/query/body/non-auth header/log message/args/exception/stack/custom extra 전부에서
  찾고 Authorization 외 key 사용을 금지한다.
- import-safe/default app, valid `/api/v1/chat`, modified canonical case에서 provider factory/transport
  construction 자체가 0임을 증명한다.
- environment-specific ignored runtime는 primary checkout의 exact manifest/binary 테스트로 대체한다.

### 이유

provider transport mock만 보아서는 import·handler·logging 단계의 누출이나 조기 client 생성을
증명하지 못한다. 각 경계를 직접 실패시키는 회귀가 actual gate보다 먼저 필요하다.

### 고려했지만 선택하지 않은 대안

- 실제 Upstage 호출로 smoke 확인: Task 7 human gate 전 비용·비밀·network 사용이므로 제외.
- worktree에 ignored Supabase binary 복사: 저장소 변화가 아니고 primary exact evidence가 있어 제외.
- root 전체를 사소한 env test 수정 뒤 다시 반복: 7분 이상 걸리는 동일 gate 대신 실패한 exact
  module과 environment-specific exact cases를 재실행하고 기록했다.
## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| LLM architecture tests | transitive import·router absence·provider construction zero | public isolation |
| LLM security tests | key/PII/content/source/allowlist/fallback/30·31 cap matrix | leak/cap safety |
| root architecture tests | valid chat handler 및 modified canonical pre-provider stop | integration proof |
| env security test | DeepSeek 기대를 exact Upstage disabled template로 교체 | decision drift 제거 |
| manifest/docs | offline evaluator axes 승격·Task 6 status 동기화 | release/handoff |

### 데이터 흐름/상태 변화

테스트는 fakes/MockTransport/isolated subprocess만 사용한다. official `.2`, DB rows, 시민 route와
평가 artifact는 변경하지 않는다.

### 오류·빈 상태·롤백

import-safe 정상 chat은 provider 없이 안전한 503으로 종료하고, malformed/extra client input은
422다. test/docs commits는 migration 없이 순서대로 revert 가능하다.
## 7. 버전 전후

### 생성 시 매니페스트
- product_spec: 2.4.0
- repo_guidance: 1.7.6
- application: 0.7.0-local-synthetic-evaluator
- web: 0.4.0-chat-admin-local-integration
- api: 3.1.0-draft
- shared_contracts: 0.4.0
- database_schema: 0.4.0-local
- official_data: 0.1.0-initial.2
- mock_data: 0.0.0-not-populated
- prompt_set: 0.1.0-upstage-solar-pro3-synthetic
- test_suite: 1.3.0-upstage-synthetic-evaluator
- documentation: 2.14.0

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Application | 0.6.0-local-core-loop | 0.7.0-local-synthetic-evaluator | offline evaluator complete |
| Web | 0.4.0-chat-admin-local-integration | 동일 | 변경 0 |
| API | 3.1.0-draft | 동일 | public contract/route 0 |
| DB schema | 0.4.0-local | 동일 | migration/DB use 0 |
| Official data | 0.1.0-initial.2 | 동일 | read/write 0 |
| Mock data | 0.0.0-not-populated | 동일 | 변경 0 |
| Prompt set | 0.0.3-upstage-solar-pro3-synthetic-selected | 0.1.0-upstage-solar-pro3-synthetic | 구현 고정 |
| Test suite | 1.2.1-core-loop-closeout | 1.3.0-upstage-synthetic-evaluator | gate 완성 |
| Docs | 2.13.7 | 2.14.0 | Task 6 closeout |

## 8. 명령과 테스트 증거

| 명령/검증 | 결과 | 시간/개수 | 증거 경로 |
|---|---|---|---|
| Task 6 focused pytest | PASS | 23 + 5 subtests | terminal/review |
| full API pytest | PASS | 1,782 + 8 local-DB skips + 5 subtests | terminal |
| API Ruff format/check + Mypy | PASS | 46 source files | terminal |
| root unittest initial | 3 fail, 2 skip | 422 tests / 447s | terminal |
| corrected security-boundary module | PASS | 20 tests, 1 symlink skip | terminal |
| primary exact Supabase runtime tests | PASS | 2 tests | primary checkout terminal |
| independent re-review | PASS | Spec ✅, findings 0 | bounded task report |

### 미실행 검증과 이유

root 422-test suite를 env one-line correction 뒤 전부 반복하지 않았다. 실패한 20-test module과
worktree 환경 실패 2개를 본 체크아웃에서 exact 재실행했다. Task 7 actual provider/PM score는
의도적으로 미실행이다.
## 9. 보안·개인정보·접근성·성능 영향

- Privacy: question/response/PII source를 LogRecord/transport/report에 남기지 않는 회귀 추가.
- Security: API key single Authorization location과 provider factory zero-call을 증명.
- Accessibility: 시민 UI 변경 0.
- Performance/cost: actual attempt/token/USD 0; concurrency/30-attempt cap은 offline 증명.

## 10. 데이터와 출처 영향

- 공식 데이터: `0.1.0-initial.2` 불변, DB 접근 0.
- mock/AI 생성: sentinel/fake response만 메모리 테스트에 사용.
- schema/lineage: API/DB/data schema 불변, application/prompt/test/docs version만 승격.
- verified date: 2026-07-24 KST.

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- Task 6 PASS는 모델 한국어 품질 PASS가 아니다.
- Task 7은 ignored local key와 final local DB, PM 점수를 사용하는 별도 human gate다.
- 실제 시민/free-input/public/remote provider 연결 option B는 계속 미승인이다.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- subprocess/module isolation, sentinel traversal, LogRecord extra enumeration은 같은 보안 계약 안의
  내부 테스트 구현이다.

## 13. 인수인계·재현·롤백

### 재현

1. `git show 45edd05`, `git show 8f885bd`, `git show 2c6dcd1`, `git show a249b50`.
2. provider-disabled 환경에서 Task 6 focused/full API/Ruff/Mypy를 frozen/offline 실행한다.
3. primary checkout에서 exact Supabase runtime 2 tests, docs/secret/protected diff gate를 실행한다.

### 롤백

문서 closeout commit 뒤 `a249b50`, `2c6dcd1`, `8f885bd`, `45edd05`를 역순 revert한다. DB/data/
provider artifact/key revoke는 없다.

### 다음 개발자 시작점

Q-PM-DEMO-001=B의 deterministic actual demo evidence를 먼저 분리해 닫고, LLM-002 Task 7은
로컬 human gate에서만 실행한다.
## 14. 남은 위험·미해결 질문·다음 단계

- 실제 Upstage model quality/cost evidence는 Pending.
- public/remote/citizen provider는 금지.
- MVP demo actual DB는 별도 수직 흐름에서 질문 원문·UUID·DSN을 출력하지 않고 검증한다.

## 15. 자체 리뷰

- [x] 요청 충족
- [x] 테스트/검증
- [x] source-of-truth/계약/버전 동기화
- [x] 개인정보 원문 노출 없음
- [x] 구현 노트 INDEX 갱신
