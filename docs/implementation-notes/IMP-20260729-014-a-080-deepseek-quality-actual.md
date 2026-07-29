# IMP-20260729-014 — A-080 DeepSeek classifier quality actual

- Date/Time (KST): 2026-07-29T16:50:39+09:00
- Task ID: A-080-DEEPSEEK-CLASSIFIER-QUALITY
- Type: implementation-provider-actual
- Status: Done — Actual FAIL / fail-closed; post-actual exact-field correction offline
- Author/Agent: Codex
- Branch: `codex/a-080-deepseek-classifier-quality`
- Source/Base commit: `f2c3aec50c6b615cbbaf989a9d7bf5760d1436c4`
- Related plan/ADR/RFP: [A-080 specification](../superpowers/specs/2026-07-29-deepseek-classifier-semantic-route-rubric-design.md), [A-080 plan](../superpowers/plans/2026-07-29-deepseek-classifier-semantic-route-rubric.md), [ADR-0028](../adr/0028-selectable-deepseek-classifier-provider.md), SFR-002, D-133~D-137.
- Aggregate evidence: [A-080 actual report](../test-reports/CHAT-HYBRID-RAG-001-DEEPSEEK-A080-ACTUAL.md)

## 1. 사용자 요청과 완료 기준

### 요청

사용자가 정확한 승인 문구 `A-080 DeepSeek actual 1회 실행 승인`을 제공했다. 승인된 clean source와
immutable A-080 offline evidence에 묶인 고정 20문항 local/private DeepSeek classifier actual을
정확히 한 번 실행하고, 재실행 없이 aggregate-only 결과와 안전 경계를 기록한다.

### Acceptance Criteria

- clean source SHA와 A-080 offline PASS를 다시 검증한다.
- readiness-only가 PASS한 동일 source에서 actual invocation을 정확히 1회만 수행한다.
- selected/skip은 `20/0`, deterministic/provider는 `11/9`, privacy/policy outbound는 `0`이어야
  한다.
- provider 9건의 outbound/response/HTTP 2xx/strict parse/server acceptance/oracle match가 모두
  `9`여야 전체 acceptance가 PASS다.
- retry/rerun은 `0/0`, concurrency는 `1`, max output은 `128`, 실제 비용은 VAT 포함 USD `0.20`
  이하여야 한다.
- 질문, 마스킹 질문, provider request/response body, invalid value, secret을 보관하지 않는다.
- 결과가 FAIL이어도 자동 재실행하지 않고 기존 결정론적 폴백과 local/private 경계를 유지한다.

## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 사용자가 exact one-shot actual을 승인했고, Codex root controller가 critical 실행을 소유했다. 이 노트는 별도 문서 작업자가 aggregate evidence만 정리했다. |
| When — 언제 | 2026-07-29 KST. Offline, readiness와 actual은 같은 clean source에 묶였고 actual은 승인 뒤 1회만 실행됐다. |
| Where — 어디서 | owner-controlled local/private Windows 저장소와 승인된 DeepSeek classifier endpoint에서 수행했다. public/remote/real-citizen 환경은 사용하지 않았다. |
| What — 무엇을 | 고정 20문항 중 deterministic 11건과 provider 대상 9건의 classifier 품질을 aggregate-only로 평가했다. |
| Why — 왜 | A-079의 transport/wire 성공과 quality `6/9`를 분리해 보존하면서, A-080 semantic route rubric이 고정 oracle 기준을 충족하는지 확인하기 위해서다. |
| How — 어떻게 | one-shot offline gate → readiness-only → exact-one actual 순서로 실행하고, 기존 strict parser·catalog·server oracle이 provider 결과를 다시 검증했다. |
| How much — 어느 정도 | selected `20`, skip `0`, provider-free/provider `11/9`, outbound/response/2xx/strict/accepted/oracle `9/9/9/9/9/8`, 비용 USD `0.002961266`, provider retry/rerun `0/0`이다. |

Final review에서는 actual을 재실행하지 않고 source 계보와 prompt exact field만 provider-free로
교정했다. Rebase 전 실행 commit `f2c3aec...`와 rebased checkpoint `6a44201...`의 tree는
`9ad169344c8b115d5d943c6118af213683fdd940`로 동일했고, 게시 branch ancestry에 원 실행 commit을
보존한다. 이후 undefined `I=supported`를 approved `intent=supported`로 TDD 교정했으므로 이
post-actual source의 live 품질은 미검증이다.

## 3. 시작 전 상태

- 관련 파일: A-080 specification/plan, ADR-0028, IMP-013, A-080 offline evidence와 actual runner.
- 기존 동작: A-079는 DeepSeek transport/exact wire를 `9/9`로 검증했지만 fixed oracle은 `6/9`라
  quality FAIL이었다. A-080은 shared provider-neutral semantic rubric을 offline 구현했다.
- 실행 전 gate: clean source
  `f2c3aec50c6b615cbbaf989a9d7bf5760d1436c4`, A-080 offline `PASS`
  (`invocation=1`, `rerun=0`), readiness-only `PASS`.
- Git 상태: actual 직전 tracked source는 clean이었다. actual 결과로 새 immutable aggregate report
  한 파일만 생성됐으며 질문·provider body·비밀값은 생성물에 없다.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| A-080-ACTUAL | human authority | live provider 호출은 provider-free plan 승인에 포함되지 않았다. | 사용자의 exact 문구를 받은 뒤에만 1회 실행했다. | provider 호출·비용 |
| A-080-QUALITY | evidence | Aggregate-only 정책으로 어느 개별 fixture가 oracle과 달랐는지는 보관하지 않는다. | `8/9`만 기록하고 개별 실패를 추론하거나 노출하지 않는다. | 진단 해상도 제한 |
| A-080-PROMOTION | product boundary | transport·strict parse·server acceptance 성공만으로 quality 또는 public 준비를 선언할 수 없다. | oracle `9/9` 미달이므로 overall FAIL과 deterministic fallback을 유지한다. | 제품 기본 경로 |
| A-080-LINEAGE | evidence reproducibility | rebase 뒤 원 실행 SHA가 branch ancestry에서 사라질 수 있었다. | 동일-tree checkpoint를 확인하고 원 실행 commit을 final branch merge ancestry에 보존한다. | 제3자 fetch/checkout |
| A-080-ROUTE-SHAPE | final review | Approved plan은 exact `intent`지만 runtime/test가 undefined `I`를 사용했다. | post-actual TDD로 exact field를 교정하되 live quality PASS를 주장하지 않는다. | prompt clarity·version |

## 5. 설계 결정과 대안

### 선택

기존 exact five-string wire, strict server parser, request-local catalog와 server-owned oracle을
바꾸지 않고 고정 PII-free fixture로 one-shot actual을 실행했다. 결과는 transport/contract
`9/9`이지만 oracle `8/9`이므로 전체 acceptance를 `FAIL`로 닫았다.

### 이유

Classifier provider의 정상 응답과 제품 분류 품질은 별도 gate다. 아홉 provider 결과가 모두 HTTP
2xx, strict parse, server acceptance를 통과했어도 고정 기대 결정과 하나라도 다르면 승인된 exact
acceptance를 충족하지 못한다.

### 고려했지만 선택하지 않은 대안

- `8/9`를 부분 성공 또는 PASS로 승격: 승인된 `9/9` 기준을 완화하므로 선택하지 않았다.
- 실패한 개별 fixture나 provider body 기록: 질문·응답·invalid value 비보관 정책을 위반하므로
  선택하지 않았다.
- 즉시 corrective rerun: actual은 PASS/FAIL과 무관하게 1회로 소진되므로 수행하지 않았다.
- DeepSeek를 public/default classifier로 승격: local/private synthetic evidence 범위를 넘으므로
  수행하지 않았다.
- Review 결함을 무시하거나 actual을 재실행: 전자는 approved exact contract를 위반하고 후자는
  immutable one-shot 경계를 위반하므로 선택하지 않았다.

## 6. 구현·실행 상세

| 파일/영역 | 변경 또는 실행 내용 | 이유 |
|---|---|---|
| A-080 one-shot offline gate | 동일 source에서 `PASS`, invocation `1`, rerun `0`을 보존했다. | provider actual 전 immutable source/gate 확인 |
| A-080 readiness-only | actual lease를 소비하기 전 `PASS`를 확인했다. | source·input·settings·evidence precondition 확인 |
| A-080 actual runner | invocation `1`, retry `0`, rerun `0`, provider outbound `9`로 실행했다. | exact human approval 범위 준수 |
| A-080 aggregate report | 허용된 count·usage·cost·retention 필드만 생성했다. | 재현성과 개인정보·비밀 비보관 동시 충족 |
| `classifier_prompt.py` | `NO_TOPIC_MATCH:I=supported`를 exact `intent=supported`로 교정했다. | approved plan·wire field 이름 정합 |
| prompt/provider tests | undefined abbreviation을 금지하고 exact field를 고정했다. | 회귀 방지 |
| Git publication lineage | 원 실행 commit을 final branch의 merge parent로 보존한다. | immutable report source 재현 |
| API/DB/Web/data/dependency | 변경 없음 | provider quality evidence가 공개 계약이나 제품 범위를 암묵적으로 바꾸지 않도록 보존 |

### 데이터 흐름·상태 변화

- 고정 PII-free fixture 20개 중 11개는 결정론적 provider-free 경로를 유지했고, 안전한 9개만
  DeepSeek classifier로 outbound됐다.
- privacy/policy probe `4`건의 provider outbound는 `0`이었다.
- provider outbound/response/HTTP 2xx/strict parse/server decision accepted는 각각 `9`였다.
- fixed oracle match는 `8`이므로 overall acceptance는 `FAIL`이다.
- 질문·마스킹 질문·request/response body·invalid value·secret은 모두 보관 `0`이다.
- Actual 뒤 prompt exact-field 교정은 provider 호출 없이 수행됐으며 A-080 report·lease·집계값을
  바꾸지 않는다.
- DB row, API contract, Web behavior, official/mock data, migration과 production dependency 변화는
  모두 `0`이다.

### 오류·빈 상태·롤백

Provider runtime failure는 `0`이고 HTTP rejection·transport no-response도 `0`이다. 실패 원인은
transport나 wire가 아니라 aggregate oracle mismatch `1`이지만, 비보관 정책 때문에 개별 질문,
개별 결정 또는 provider 본문을 추론하지 않는다. Runtime은 기존 결정론적 fail-closed fallback을
유지한다. Actual evidence는 immutable이므로 삭제·수정·재실행을 롤백 수단으로 사용하지 않는다.

## 7. 버전 전후

Actual evidence 동기화 시 documentation 축을 먼저
`2.32.3-a080-quality-offline`에서 `2.32.4-a080-quality-actual-fail`로 전진했다. 이후 final
review의 post-actual exact-field correction으로 application/prompt/tests/docs를 아래 최종값으로
전진했다. API/contracts/Web/DB/data/dependency 축은 그대로다.

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Product spec | `2.6.0` | unchanged | 제품 범위 변화 없음 |
| Application | `0.13.3-classifier-semantic-rubric` | `0.13.4-classifier-route-shape-fix` | post-actual exact-field correction |
| Web | `0.8.0-guided-chat` | unchanged | UI 변화 없음 |
| API | `4.0.0-draft` | unchanged | 공개 계약 변화 없음 |
| Shared contracts | `1.0.0` | unchanged | wire/parser 변화 없음 |
| DB schema | `0.5.0-local` | unchanged | migration 없음 |
| Official data | `0.1.0-initial.2` | unchanged | seed/data 변화 없음 |
| Mock data | `0.0.0-not-populated` | unchanged | mock 생성 없음 |
| Prompt set | `0.4.4-semantic-route-rubric` | `0.4.5-explicit-intent-route-shape` | undefined `I`를 exact `intent`로 교정 |
| Test suite | `2.2.9-a080-quality` | `2.2.10-a080-final-review-fix` | RED/GREEN route-shape regression |
| Docs | `2.32.3-a080-quality-offline` | `2.32.5-a080-final-review-fix` | actual FAIL + final review authority synchronization |

## 8. 명령과 테스트 증거

명령은 환경변수 값, 질문, provider body, API key, DSN과 예외 상세가 없는 value-free 형태로만
기록한다.

| 명령/검증 | 실제 결과 | 횟수/개수 | 증거 경로 |
|---|---|---|---|
| `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_a080_offline_gate.ps1` | PASS | invocation `1`, rerun `0` | ignored A-080 one-shot offline evidence |
| `... run_deepseek_classifier_quality_actual.py --fixture <pinned-fixture> --report <a080-report> --readiness-only` | PASS | readiness `1` | controller execution evidence |
| `... run_deepseek_classifier_quality_actual.py --fixture <pinned-fixture> --report <a080-report>` | overall `FAIL`; runner/runtime failure `0` | actual invocation `1`, retry `0`, rerun `0` | A-080 aggregate actual report |
| actual selection | selected/skip `20/0`; provider-free/provider `11/9` | policy/privacy outbound `0` | A-080 aggregate actual report |
| provider boundary | outbound/response/2xx/strict/accepted/oracle `9/9/9/9/9/8` | rejected/transport failure `0/0` | A-080 aggregate actual report |
| privacy retention | question/masked question/request body/response body/invalid value/secret 모두 `0` | six counters | A-080 aggregate actual report |
| cost check | USD `0.002961266 <= 0.20` including VAT | cap PASS | A-080 aggregate actual report |
| `pytest ... test_prompt.py -q` after test-only change | RED: `2 failed, 20 passed` | exact field missing | final review TDD |
| `pytest ... test_prompt.py -q` after production fix | GREEN: `22 passed` | exact field present | final review TDD |
| prompt+DeepSeek+Upstage focused suites | PASS: `133 passed` | provider-neutral shared messages | final review TDD |
| final related-area suite after review fix | PASS: `587 passed`, dependency warning `1` | post-actual code/tests + one-shot controlled wrappers | controller final verification |
| Ruff format/check | PASS: `123 files` / issues `0` | API src/tests | controller final verification |
| Mypy | PASS: `123 source files`, issues `0` | API src/tests | controller final verification |
| `apps/api/.venv/Scripts/python.exe -B scripts/check_repository_docs.py` | PASS | repository docs links/JSON | 이 노트 작성 후 실행 |
| `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check_secret_patterns.ps1 -RepositoryRoot .` | PASS | secret pattern scan | 이 노트 작성 후 실행 |
| `git diff --check origin/main...HEAD` | PASS | branch whitespace error `0` | controller final verification |
| independent final review round 1 | NOT READY: Critical `0`, Important `2`, Minor `0` | lineage + undefined field fixed | two independent reviewers |
| security re-review after fixes | APPROVED: Critical `0`, Important `0`, Minor `0` | artifact/privacy/lineage clean | independent reviewer |
| specification re-review after fixes | READY: Critical `0`, Important `0`, Minor `0` | contract/docs/final evidence clean | independent reviewer |
| `git push -u origin codex/a-080-deepseek-classifier-quality` | PASS | tracked remote branch created | private source remote |
| Draft PR publication | PASS: [PR #25](https://github.com/tskwak111/Sejong_AI/pull/25) | base `main`, auto-merge off | GitHub |

### 미실행 검증과 이유

- A-080 offline과 actual은 다시 실행하지 않는다. 이미 각각 one-shot evidence를 소진했다.
- Public/remote/real-citizen, remote DB와 final-answer provider 검증은 승인 범위가 아니므로
  실행하지 않았다.
- DB/API/Web/data/dependency 전 영역 전체 gate는 해당 영역 변화가 없어 다시 실행하지 않았다.
  변경된 classifier·provider boundary·one-shot runner의 related-area 587와 Ruff/Mypy123,
  docs/secret/branch-diff는 final review correction 뒤 PASS했다.

## 9. 보안·개인정보·접근성·성능 영향

- Privacy: provider outbound 전 기존 deterministic privacy/policy gate를 보존했다. Privacy/policy
  outbound는 `0`; 질문·마스킹 질문과 모든 provider body 보관은 `0`이다.
- Security: API key, DSN, invalid field value, exception detail을 보고서·노트에 기록하지 않았다.
  Strict parser와 server-owned catalog/grounding authority를 유지한다.
- Accessibility: Web/UI 변경이 없어 영향 없음.
- Performance/cost: concurrency `1`, max output `128`, retry `0`; actual 비용은 VAT 포함
  USD `0.002961266`으로 USD `0.20` cap 이하다. Quality FAIL을 비용·통신 성공으로 덮지 않는다.

## 10. 데이터와 출처 영향

- 공식 데이터: 변경 없음. Approved immutable official release는 `0.1.0-initial.2`다.
- mock/AI 생성: 새 mock 또는 provider-generated official fact/source가 없다. Provider는 classifier
  closed decision만 제안하고 출처·기관·공식 사실은 생성하지 않는다.
- schema/lineage: DB/API/shared contract/migration/data lineage 변경 없음. Actual report는 source,
  fixture, coverage, official-record와 release-manifest hash에 묶인 aggregate evidence다.
- verified date: 2026-07-29 KST.

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- A-080 actual은 `FAIL`이다. Transport, HTTP, strict parse와 server acceptance는 모두 `9/9`이지만
  fixed oracle가 `8/9`라 exact acceptance `9/9`를 충족하지 못했다.
- 이 actual은 1회로 소진됐고 자동 재실행하지 않았다. 추가 corrective provider call에는 새 인간
  결정과 별도 exact 승인이 필요하다.
- Final review의 exact `intent` correction은 actual 뒤 provider-free로 이뤄졌다. 따라서 현재
  source가 `8/9`보다 좋아졌다고 주장할 근거는 없고, immutable actual FAIL은 그대로다.
- DeepSeek는 local/private synthetic classifier evidence 범위만 유지한다. Public/remote,
  real-citizen free-input, default promotion, final citizen-answer provider 변경은 승인되지 않았다.
- DB/API/Web/official data/dependency는 바뀌지 않았다. 제품 runtime은 결정론적 fail-closed
  fallback을 계속 권위로 사용한다.
- Draft PR #25는 사람이 diff·CI를 검토한 뒤에만 병합한다. Codex는 자동 merge하지 않았다.

## 12. AI 내부 구현 세부 — 인간이 굳이 이해하지 않아도 되는 내용

- Runner는 고정 hash와 same-source offline evidence를 검증한 뒤 aggregate count만 기록한다.
- Report의 provider terminal-stage accepted 합계는 `9`이고 다른 rejection stage count는 모두
  `0`이다.
- 이 하위 작업은 충돌 방지를 위해 새 IMP-014 한 파일만 작성하며 INDEX·shared authority
  documents·version manifest는 통합 소유자에게 맡긴다.

## 13. 인수인계·재현·롤백

### 재현

1. ADR-0028의 A-080 amendments, approved specification/plan과 IMP-013을 읽는다.
2. Source SHA가 `f2c3aec50c6b615cbbaf989a9d7bf5760d1436c4`인지 확인한다.
   Final publication branch가 이 commit을 ancestor로 포함하는지도 확인한다. Rebase 직후
   equivalent checkpoint `6a44201`은 동일 tree
   `9ad169344c8b115d5d943c6118af213683fdd940`였지만 post-actual exact-field correction은 별도다.
3. A-080 aggregate actual report에서 selected/skip `20/0`, provider-free/provider `11/9`,
   outbound/response/2xx/strict/accepted/oracle `9/9/9/9/9/8`, retention six counters `0`,
   invocation/retry/rerun `1/0/0`, cost USD `0.002961266`을 확인한다.
4. One-shot offline이나 actual runner를 다시 실행하지 않는다.

### 롤백

- Runtime rollback은 configuration에서 classifier provider를 `disabled`로 유지하거나 승인된 다른
  local selector를 명시적으로 선택한다.
- Prompt code rollback이 필요하면 shared rubric implementation commit을 revert한다. DB/data
  migration이나 Web/API rollback은 필요 없다.
- Immutable actual report는 실패 증거를 포함한 감사 기록이므로 수정·삭제·덮어쓰기하지 않는다.
  Key rotation은 Git 밖에서 수행하며 값을 읽거나 출력하지 않는다.

### 다음 개발자 시작점

이 actual을 quality PASS로 해석하지 않는다. 추가 품질 교정을 제안하려면 aggregate `8/9`만을
출발점으로 새 설계·spec·disjoint evidence identity·인간 actual 승인을 마련해야 한다. 개별
fixture 실패나 provider 응답을 추정해서는 안 된다.

## 14. 남은 위험·미해결 질문·다음 단계

- 한 건의 oracle mismatch가 남아 있지만 aggregate-only 정책상 어느 질문·route/topic인지 알 수
  없다. 관찰성을 높이려면 raw content 없이 fixed value-free mismatch category 같은 별도 설계와
  인간 승인이 필요하다.
- Post-actual `intent` correction은 offline tests만 통과했으며 live DeepSeek 품질은 미검증이다.
- Draft PR #25의 CI/사람 검토와 병합 결정은 Pending이다.
- Offline semantic rubric 성공은 live model 품질 `9/9`을 보장하지 않았으며, 현재 증거는 fixed
  synthetic 20문항과 local/private 환경에만 한정된다.
- 통합 소유자는 IMP-014 INDEX row, version/decision/ADR/RFP/task/changelog 정합성, final scoped
  tests·docs·secret·diff와 독립 리뷰를 완료해야 한다.

## 15. 자체 리뷰

- [x] 정확한 인간 승인과 one-shot invocation/retry/rerun 기록
- [x] actual 집계 수치와 FAIL 판정 일치
- [x] 질문·fixture별 결과·provider body·invalid value·key·DSN·exception 상세 미기록
- [x] 보안·개인정보·비용·local/private 경계 명시
- [x] API/DB/Web/data/dependency 변화 없음 명시
- [x] 재현·롤백·인수인계와 인간/AI 책임 분리
- [x] INDEX·shared authority/version 동기화 — 통합 소유자 완료
- [x] Commit·push·Draft PR #25 게시 — 자동 merge 없음
