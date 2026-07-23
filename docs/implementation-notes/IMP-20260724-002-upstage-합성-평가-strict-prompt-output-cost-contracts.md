# IMP-20260724-002 — Upstage 합성 평가 strict prompt output cost contracts

- Date/Time (KST): 2026-07-24T00:23:02+09:00
- Task ID: LLM-002
- Type: implementation
- Status: Done — Task 2 / LLM-002 In Progress
- Author/Agent: Codex integration, Task 2 implementation and independent review subagents
- Branch: codex/LLM-002-upstage-synthetic-evaluation
- Base commit: cafe1ee
- Related plan/ADR/RFP:
  - [승인 실행계획](../superpowers/plans/2026-07-23-upstage-solar-pro3-synthetic-evaluation.md)
  - [승인 명세](../superpowers/specs/2026-07-23-upstage-solar-pro3-synthetic-evaluation-design.md)
  - [ADR-0022](../adr/0022-upstage-solar-pro3-synthetic-evaluation.md)
  - [Task 1 checkpoint](IMP-20260724-001-upstage-합성-평가-구현-시작과-fail-closed-설정.md)

## 1. 사용자 요청과 완료 기준

### 요청

승인된 LLM-002 계획을 계속 실행해, 실제 API key·network 사용 전 단계인 strict output,
source-free prompt, conservative input preflight, exact Decimal 비용 계약을 TDD와 독립 리뷰로
완료한다.

### Acceptance Criteria

- provider 출력이 정해진 6개 필드 외 source/status/intent 등을 포함하면 거부한다.
- prompt에는 masked 합성 질문과 허용된 KB projection만 포함한다.
- canonical UTF-8 byte upper bound를 사용하고 4096 이하를 증명한다.
- 비용은 supplied aggregate token usage를 한 번만 계산하며 VAT와 cached input을 분리한다.
- SUCCESS는 answer와 최소 1 provider attempt를 요구한다.
- focused pytest, Ruff, Mypy, docs/secret/diff gate와 독립 spec/quality 리뷰를 통과한다.
- key/network/public API/DB/data/dependency/lockfile 변경·사용은 0이다.
## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 사용자가 연속 진행을 승인했고, 구현 subagent가 TDD, reviewer가 독립 spec/quality, Codex가 통합·보안 판정을 수행했다. |
| When — 언제 | 2026-07-24 KST, Task 1 review-clean 뒤 Task 2 checkpoint |
| Where — 어디서 | isolated linked worktree의 internal `sejong_ai_api.llm`와 focused tests |
| What — 무엇을 | immutable contracts, source-free Korean prompt, UTF-8 preflight upper bound, exact aggregate cost |
| Why — 왜 | provider가 근거·출처·상태를 만들지 못하게 하고 실제 실행 전에 입력·비용·실패 상태를 닫기 위해 |
| How — 어떻게 | RED→GREEN, independent bounded-diff review, Critical/Important findings 별도 fix와 re-review |
| How much — 어느 정도 | production 3개/test 4개, 17 focused tests, 2 commits; key/network/DB/data/dependency 0 |

## 3. 시작 전 상태

- 관련 파일: Task 1 settings, LLM-002 design/plan/ADR, DB `Intent`/`KnowledgeRecord`,
  `apps/api/src/sejong_ai_api/llm/`, `apps/api/tests/llm/`.
- 기존 동작: exact provider settings만 있었고 output/prompt/cost/outcome 계약은 없었다.
- 발견한 충돌/부채:
  - 계획의 단일 `TokenUsage(4096, 0, 1024)` snapshot에 30-attempt aggregate 금액
    `0.0405504`가 잘못 기재돼 있었다.
  - 최초 구현이 이 값을 맞추기 위해 모든 usage에 30을 곱해 실제 aggregate를 다시 30배로
    과금하는 Critical 결함이 있었다.
  - 최초 outcome은 `SUCCESS`와 `attempts_used=0`을 허용했다.
- Git 상태: 시작 `cafe1ee`, 구현 `12953a2`, review fix `c59f0b3`, re-review Approved.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| COST-AGGREGATE | 계약 | 단일 사용량과 30-attempt aggregate snapshot 충돌 | supplied actual aggregate를 정확히 한 번 계산 | 비용 보고·run cap |
| OUTCOME-ATTEMPT | 계약 | SUCCESS 0 attempts 허용 여부 | SUCCESS는 1 이상; preflight/failure는 0 가능 | 결과 일관성 |
| SOURCE-GUARD | 내부 | 금지 metadata 문자열 검사 | 승인 계획대로 Task 2에서는 유지 | allowlisted fixture 범위 |
| ACTUAL-GATE | 인간 | provider key/call 시점 | Tasks 1~6 offline PASS 뒤 Task 7 local only | 현재 call 0 |

## 5. 설계 결정과 대안

### 선택

- Pydantic strict/frozen/extra-forbid `GeneratedAnswer` 6필드와 immutable dataclass 계약을 사용한다.
- provider prompt에는 masked question, deterministic intent, approved KB projection, output schema만
  넣고 source/public ID/date/examples를 제외한다.
- 완전한 canonical messages의 UTF-8 byte 수를 dependency 없는 보수적 token proxy로 사용한다.
- `estimate_cost_usd()`는 제공된 aggregate usage를 한 번 계산하고 non-cached/cached/output/VAT를
  exact Decimal로 분리한다.

### 이유

서버가 intent/status/source를 소유하고, 모델 출력은 공식 KB를 쉬운 한국어 구조로 바꾸는 일에만
제한한다. 실제 token totals를 별도로 합산한 뒤 같은 함수로 재현 가능한 비용을 계산한다.

### 고려했지만 선택하지 않은 대안

- provider SDK/새 tokenizer: 새 production dependency 금지이며 기존 HTTPX와 conservative proxy로 충분.
- LLM 생성 source/status: 비협상 서버 결합 원칙 위반.
- 내부 30배 multiplier: 실제 aggregate를 다시 곱하므로 폐기.
- prompt value에 금지 문자열이 포함된 경우 구조 key만 검사하도록 확장: 현재 T-01~T-10
  allowlist에는 필요 없고 승인 Task 2 범위를 넘어 후속 review 대상으로 남겼다.
## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| `llm/contracts.py` | strict/frozen answer, grounded fixture, token usage, closed outcome codes/state | provider-neutral contract |
| `llm/prompt.py` | exact source-free Korean messages와 canonical UTF-8 upper bound | grounding/PII/source 경계 |
| `llm/cost.py` | Decimal 가격, cached subtraction, VAT, USD 0.05 cap constant | actual aggregate 비용 재현 |
| `tests/llm/conftest.py` | T-09 typed approved fixture와 exact settings | 후속 task 재사용 |
| `test_contracts.py` | extra/source, invalid tokens, success/failure/attempt state | closed schema regression |
| `test_prompt.py` | allowlisted projection, Korean instructions, source exclusion, input bound | prompt safety regression |
| `test_cost.py` | single, aggregate 30, cache, type guard snapshot | 비용 중복 방지 |
| plan/version/note | Task 2 완료, snapshot 정정, docs 2.13.3 | 재현·계보 |

### 데이터 흐름/상태 변화

masked synthetic question + deterministic intent + approved `KnowledgeRecord` → source-free canonical
messages → preflight upper bound. Provider 응답은 strict `GeneratedAnswer`로만 수용하고 token
aggregate는 Decimal 비용으로 한 번 계산한다. 아직 HTTP 전송은 없다.

### 오류·빈 상태·롤백

invalid fixture/usage/outcome/extra output은 stable bounded reason으로 거부한다. SUCCESS에는
answer와 attempt≥1이 필요하며 failure는 answer를 가질 수 없다. 파일 추가만 있어 revert 가능하고
DB/data 복구는 없다.
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
- documentation: 2.13.2

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Application | 0.6.0-local-core-loop | 동일 | 전체 offline evaluator gate Task 6 전까지 유지 |
| Web | 0.4.0-chat-admin-local-integration | 동일 | UI 변경 0 |
| API | 3.1.0-draft | 동일 | route/OpenAPI 변경 0 |
| DB schema | 0.4.0-local | 동일 | migration/DB 사용 0 |
| Official data | 0.1.0-initial.2 | 동일 | record/lineage 변경 0 |
| Mock data | 0.0.0-not-populated | 동일 | mock 변경 0 |
| Prompt set | 0.0.3-upstage-solar-pro3-synthetic-selected | 동일 | 선택 버전의 internal prompt 구현 |
| Test suite | 1.2.1-core-loop-closeout | 동일 | 전체 evaluator gate Task 6에서 승격 |
| Docs | 2.13.2 | 2.13.3 | Task 2 계약·review 증거 |

## 8. 명령과 테스트 증거

| 명령/검증 | 결과 | 시간/개수 | 증거 경로 |
|---|---|---|---|
| 최초 RED | expected import failure: `llm.contracts` 없음 | collection 1 error | ignored task report |
| 최초 GREEN | PASS 15; Ruff/Mypy PASS | 15 tests | ignored task report |
| 독립 최초 리뷰 | Critical cost×30, Important SUCCESS=0와 frozen uv evidence | Needs fixes | bounded review package |
| review-fix RED | expected 4 failures: single/aggregate/cache cost와 SUCCESS=0 | 4 failed, 13 passed | ignored task report |
| review-fix GREEN | PASS 17; Ruff/Mypy PASS | 17 tests | ignored task report |
| independent re-review | Spec ✅, Critical/Important/Minor 0, Quality Approved | `cafe1ee..c59f0b3` | bounded review package |
| main Task 1~2 pytest | PASS 23 in 0.11s | 23 tests | terminal |
| main Ruff/Mypy | PASS | 11 source files | terminal |
| docs/secret/diff | PASS | exit 0 | terminal |

### 미실행 검증과 이유

Actual Upstage call/token/quality/PM scoring은 Task 7 전 금지다. HTTPX transport는 다음 Task 3,
canonical fixtures/evaluator/report는 Tasks 4~5, full offline gate는 Task 6 범위다.
## 9. 보안·개인정보·접근성·성능 영향

- Privacy: masked synthetic fixture만 다루며 질문·답변 persistence/logging은 없다.
- Security: source/status/intent 추가 출력 거부, provider/key/network 0, public import 0.
- Accessibility: UI 변경 0.
- Performance/cost: single worst usage USD 0.00135168, separately aggregated 30-attempt worst
  USD 0.0405504 incl VAT < USD 0.05; actual cost 0.

## 10. 데이터와 출처 영향

- 공식 데이터: immutable `.2`와 DB 모두 불변·미접근; test `KnowledgeRecord`는 typed fixture.
- mock/AI 생성: 실제 생성 0; test answer는 schema 검증용 합성 문자열.
- schema/lineage: public API/DB/data lineage 변경 0.
- verified date: 2026-07-24; mutable provider price/policy는 actual Task 7 직전 재확인.

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- Task 2 완료는 실제 모델 연결·품질 PASS가 아니다.
- actual API key 입력, 네트워크 실행, 10개 결과 PM 점수 입력은 Task 7의 인간 local gate다.
- 시민/free-input/public/remote provider 사용 option B는 여전히 미승인이다.
- plan의 비용 snapshot 오류는 실제 호출 전에 수정돼 actual aggregate 이중 과금을 차단했다.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- helper/validation 구성, reusable fixture와 test 분할은 같은 계약 안의 내부 세부다.
- ignored `.superpowers/sdd` report/review package는 작업 증거이며 commit하지 않는다.
- Task 2 independent re-review open finding은 0이다.

## 13. 인수인계·재현·롤백

### 재현

1. `git show 12953a2`와 `git show c59f0b3`를 확인한다.
2. Git common-dir parent의 `.tools/uv/uv.exe`를 `$uv`에 resolve한다.
3. `& $uv run --project apps/api --frozen pytest apps/api/tests/llm/test_contracts.py apps/api/tests/llm/test_prompt.py apps/api/tests/llm/test_cost.py -q`
4. 같은 paths에 Ruff와 Mypy를 실행한다.
5. `TokenUsage(4096,0,1024)`와 30배 aggregate snapshot을 각각 확인한다.

### 롤백

역순으로 `git revert c59f0b3`, `git revert 12953a2`한다. public API/DB/data migration이나
provider key/network가 없으므로 별도 복구·revoke가 필요 없다.

### 다음 개발자 시작점

Task 3 brief에서 `limits.py`와 `upstage.py`만 TDD로 구현한다. existing HTTPX를 사용하고 hidden
retry=0, logical retry≤1, process attempt cap 30, preflight/provider token limit을 지킨다.
## 14. 남은 위험·미해결 질문·다음 단계

- Tasks 3~6 offline evaluator 구현·검증이 남았다.
- Task 7 actual은 공식 가격/policy 재확인, ignored local key, PM score가 필요하다.
- prompt 금지어 guard는 현재 allowlisted fixture에 맞춘 보수적 문자열 검사다.
- full API baseline의 기존 Starlette warning 1건/DB-only skip 8건은 Task 1 baseline과 동일하다.

## 15. 자체 리뷰

- [x] 요청 충족
- [x] 테스트/검증
- [x] source-of-truth/계약/버전 동기화
- [x] 개인정보 원문 노출 없음
- [x] 구현 노트 INDEX 갱신
