# IMP-20260729-013 — A-080 semantic route rubric offline 구현

- Date/Time (KST): 2026-07-29T16:15:00+09:00
- Task ID: A-080-DEEPSEEK-CLASSIFIER-QUALITY
- Type: implementation-provider-offline
- Status: Done — Offline Review
- Author/Agent: Codex
- Branch: codex/a-080-deepseek-classifier-quality
- Base commit: e13ad39e40dc2cb5df0f9ab7b2a7958cf4e46c16
- Related plan/ADR/RFP: [A-080 specification](../superpowers/specs/2026-07-29-deepseek-classifier-semantic-route-rubric-design.md), [A-080 plan](../superpowers/plans/2026-07-29-deepseek-classifier-semantic-route-rubric.md), ADR-0028, SFR-002, D-133~D-135.

## 1. 사용자 요청과 완료 기준

### 요청

A-080 Tasks 1~3의 provider-free implementation truth를 authority documents, version manifest,
task board and implementation note에 동기화한다. 실제 provider, DB, data, public/remote 변경이나
호출은 하지 않는다.

### Acceptance Criteria

- application/prompt/tests/docs를 각각 `0.13.3-classifier-semantic-rubric`,
  `0.4.4-semantic-route-rubric`, `2.2.9-a080-quality`, `2.32.3-a080-quality-offline`로 기록한다.
- API/shared contracts/Web/DB/official·mock data/dependency는 보존한다.
- D-135는 provider-free checkpoint만 기록하고 A-080 root/offline/readiness/actual PASS나
  provider quality PASS를 주장하지 않는다.
- SFR-002는 A-079 transport/wire verified, quality FAIL 6/9를 유지한다.
- INDEX에는 정확히 하나의 IMP-013 row를 남긴다.

## 2. 육하원칙(6W1H)

| 항목 | 기록 |
|---|---|
| Who — 누가 | 인간은 D-133~D-134 및 승인 plan authority를 제공했고, Codex가 provider-free documentation synchronization을 수행했다. |
| When — 언제 | 2026-07-29 KST; 기준 commit은 `e13ad39e40dc2cb5df0f9ab7b2a7958cf4e46c16`이다. |
| Where — 어디서 | local/private repository의 authority docs, manifest, task board와 implementation note만 변경했다. |
| What — 무엇을 | shared semantic route rubric과 disjoint A-080 evidence identities의 offline implementation evidence 및 version axes를 기록했다. |
| Why — 왜 | A-079의 quality FAIL 6/9 후속을 정확히 추적하되 transport/wire success를 quality success로 오인하거나 실제 호출 권한을 확대하지 않기 위해서다. |
| How — 어떻게 | approved spec/plan과 task evidence를 대조하고 D-135, ADR, SFR, ambiguity/task/changelog/index를 같은 status와 version으로 맞췄다. |
| How much — 어느 정도 | 문서·manifest 11개만 변경했다. provider/actual/root/readiness, DB, official/mock data, dependency, public/remote 변화는 0이다. |

## 3. 시작 전 상태

- 관련 파일: `versions/manifest.json`, source-of-truth, DECISION_LOG, ADR-0028, ambiguity register,
  `TASKS.md`, `CHANGELOG.md`, implementation-note INDEX.
- 기존 동작: A-079는 provider transport/exact wire 9/9와 oracle 6/9 FAIL을 immutable actual evidence로
  보존했고, A-080은 specification Approved/plan Review 상태였다.
- 발견한 충돌/부채: generated filename에는 한글 `-구현` suffix가 붙었지만 task contract가 지정한
  `...-offline.md`로 normalize했다; INDEX row도 하나만 유지했다.
- Git 상태: base commit에서 docs task 시작; unrelated product/provider/DB/data changes는 만들지 않았다.

## 4. 미지의 영역·가정·인터뷰

| ID | 구분 | 내용 | 결정/기본값 | 영향 |
|---|---|---|---|---|
| A-080-ACTUAL | human gate | provider-free evidence는 one live evaluation 권한이 아니다. | exact `A-080 DeepSeek actual 1회 실행 승인` 전 actual 0으로 유지한다. | provider call/cost와 quality verdict |
| A-080-QUALITY | evidence | offline prompt/wrapper passes는 live oracle quality를 증명하지 않는다. | SFR-002와 all authority docs에 A-079 quality FAIL 6/9를 유지한다. | product default promotion 금지 |

## 5. 설계 결정과 대안

### 선택

D-135는 approved plan 아래 provider-free Tasks 1~3 completion만 선언한다. 새 rubric과 A-080
evidence identities의 검증 identity를 기록하되 actual/root/offline/readiness는 미실행으로 둔다.

### 이유

Prompt, provider-boundary and controlled-wrapper tests are implementation evidence; they are not a
network execution nor a nine-case quality result. Existing A-079 aggregate is the last quality
authority until a separately approved A-080 actual completes.

### 고려했지만 선택하지 않은 대안

- Offline PASS 또는 A-080 quality PASS로 표시: root gate/readiness/actual이 0이므로 근거가 없다.
- A-079 FAIL을 A-080 evidence로 덮어쓰기: immutable predecessor evidence와 fail-closed policy를
  위반한다.
- provider 호출 또는 live readiness 실행: explicit actual approval 범위를 넘어가므로 수행하지 않았다.

## 6. 구현 상세

| 파일/영역 | 변경 내용 | 이유 |
|---|---|---|
| `versions/manifest.json` | 네 requested axes만 전진했다. | version authority synchronization |
| source-of-truth/decision/ADR/RFP | D-135, A-080 Offline Review와 A-079 quality FAIL 6/9를 동일하게 기록했다. | 과장 없는 product/requirement authority |
| ambiguity/TASKS/changelog | approved plan, provider-free evidence, separate actual gate와 unchanged boundaries를 기록했다. | execution visibility와 human gate |
| implementation note/INDEX | reproducible 6W1H note와 단일 row를 추가했다. | completion history/hand-off |

### 데이터 흐름/상태 변화

Runtime, provider wire/parser, input/output data flow는 변하지 않는다. Documentation status만
`specification Approved / plan Approved / implementation Offline Review`로 진전했다. A-080 root
offline gate, readiness and actual are still unexecuted; no provider request was formed.

### 오류·빈 상태·롤백

Actual approval이 없거나 any future gate가 fail하면 existing deterministic fail-closed fallback remains
authoritative. Rollback is one docs/version commit revert; no data migration, key rotation, cache purge
or DB rollback is needed.

## 7. 버전 전후

| 축 | Before | After | 변경 이유 |
|---|---|---|---|
| Application | `0.13.2-deepseek-split-timeout` | `0.13.3-classifier-semantic-rubric` | shared rubric implementation |
| Web | `0.8.0-guided-chat` | unchanged | Web surface unchanged |
| API | `4.0.0-draft` | unchanged | public contract unchanged |
| DB schema | `0.5.0-local` | unchanged | no migration |
| Official data | `0.1.0-initial.2` | unchanged | no official data change |
| Mock data | `0.0.0-not-populated` | unchanged | no mock data change |
| Prompt set | `0.4.3-explicit-route-matrix` | `0.4.4-semantic-route-rubric` | shared five-route rubric |
| Test suite | `2.2.8-a079-network-retry` | `2.2.9-a080-quality` | A-080 offline evidence |
| Docs | `2.32.2-a080-quality-plan` | `2.32.3-a080-quality-offline` | D-135 authority synchronization |

## 8. 명령과 테스트 증거

| 명령/검증 | 결과 | 시간/개수 | 증거 경로 |
|---|---|---|---|
| Task 1 semantic prompt RED/GREEN | reported exact command transcripts below | RED `1 failed`; GREEN `22 passed` | Task 1 report |
| independent DeepSeek 20-topic framing bound | reported exact command transcript below | `1 passed` | Task 1 carried-forward evidence |
| Task 2 exact three-suite command | reported exact command transcript below | `133 passed` | Task 2 report |
| Task 3 controlled wrapper RED/GREEN/parser/Ruff | reported exact command transcripts below | RED `9 failed`; GREEN `9 passed`; parser/Ruff PASS | Task 3 report |
| `git diff --check` | PASS | no whitespace errors | Task 2/3 reports and this task |
| task-scoped reviews | clean | Task1/Task2 fix round1 and Task3 first review | supplied A-080 review evidence |
| `apps/api/.venv/Scripts/python.exe -B scripts/new_implementation_note.py ...` | PASS | IMP-013 generated | this note |
| `apps/api/.venv/Scripts/python.exe -B scripts/check_repository_docs.py` | PASS | documentation links/JSON | executed in this task |
| `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check_secret_patterns.ps1 -RepositoryRoot .` | PASS | secret pattern scan | executed in this task |
| `git diff --cached --check` | PASS | staged whitespace check | executed in this task |

### Tasks 1~3 carried-forward exact command transcripts

Task 1 semantic prompt RED (reported outcome: `1 failed in 0.30s`):

```powershell
Push-Location apps/api
.\.venv\Scripts\python.exe -m pytest `
  tests/llm/test_prompt.py::test_classifier_prompt_defines_route_semantics_and_selection_precedence `
  -q
Pop-Location
```

Task 1 prompt GREEN (reported outcome: `22 passed in 0.15s`):

```powershell
Push-Location apps/api
.\.venv\Scripts\python.exe -m pytest tests/llm/test_prompt.py -q
$testExitCode = $LASTEXITCODE
Pop-Location
exit $testExitCode
```

Independent DeepSeek 20-topic framing-bound GREEN (reported outcome: `1 passed`; duration was not
provided to this documentation task):

```powershell
Push-Location apps/api
.\.venv\Scripts\python.exe -m pytest `
  tests/llm/test_deepseek_classifier.py::test_approved_twenty_topic_prompt_remains_within_byte_and_framing_bound `
  -q
Pop-Location
```

Task 2 shared-provider GREEN (reported outcome: `133 passed in 0.75s`; the later Task 2 fix-round
report also records `133 passed in 0.79s`):

```powershell
Push-Location apps/api
.\.venv\Scripts\python.exe -m pytest `
  tests/llm/test_prompt.py `
  tests/llm/test_deepseek_classifier.py `
  tests/llm/test_upstage_classifier.py `
  -q
Pop-Location
```

Task 3 controlled-wrapper RED (reported outcome: `9 failed`; before either wrapper existed,
with expected `ModuleNotFoundError` and `FileNotFoundError`):

```powershell
apps/api/.venv/Scripts/python.exe -m pytest `
  scripts/tests/test_run_deepseek_classifier_quality_actual.py `
  scripts/tests/test_run_a080_offline_gate.py `
  -q
```

Task 3 controlled-wrapper GREEN and PowerShell parser (reported outcome: `9 passed in 8.78s`; parser
completed without an exception):

```powershell
apps/api/.venv/Scripts/python.exe -m pytest `
  scripts/tests/test_run_deepseek_classifier_quality_actual.py `
  scripts/tests/test_run_a080_offline_gate.py `
  -q
[void][ScriptBlock]::Create((Get-Content -Raw scripts/run_a080_offline_gate.ps1))
```

Task 3 Ruff (reported outcome: `All checks passed!`):

```powershell
apps/api/.venv/Scripts/python.exe -m ruff check `
  scripts/run_deepseek_classifier_quality_actual.py `
  scripts/tests/test_run_deepseek_classifier_quality_actual.py `
  scripts/tests/test_run_a080_offline_gate.py
```

### 미실행 검증과 이유

A-080 root offline gate, readiness-only and actual were intentionally not run: this documentation
checkpoint has no authority to consume one-shot evidence or contact the provider. Provider calls,
actual calls and cost are 0. No DB/data/provider/API runtime test was newly needed because none changed.

## 9. 보안·개인정보·접근성·성능 영향

- Privacy: no question, masked question, provider body, invalid value, key, DSN or exception detail
  was created or recorded.
- Security: preserves exact parser, server-owned grounding/source and fail-closed boundary; no secret
  or remote access used.
- Accessibility: no Web/UI change.
- Performance/cost: no runtime performance change and provider cost is 0.

## 10. 데이터와 출처 영향

- 공식 데이터: no change; version remains `0.1.0-initial.2`.
- mock/AI 생성: no mock data and no provider-generated content.
- schema/lineage: no API/contract/schema/migration changes.
- verified date: 2026-07-29 KST; source evidence is task-scoped provider-free evidence only.

## 11. 인간이 반드시 알아야 하거나 승인할 내용

- This is not an A-080 quality PASS. A-079 remains transport/wire verified and quality FAIL 6/9.
- Any live A-080 evaluation requires the exact separate approval `A-080 DeepSeek actual 1회 실행 승인`.
- Root offline gate and readiness must precede a one-shot actual; none has been consumed here.

## 12. AI 내부 구현 세부 — 필요할 때만 보면 되는 내용

- The generated note filename was normalized to the task-contract filename and the auto-added INDEX
  row was updated in place, leaving exactly one row.
- The documentation records supplied test evidence rather than rerunning provider-adjacent suites.

## 13. 인수인계·재현·롤백

### 재현

Read D-135, this note, the approved A-080 specification/plan and ADR-0028 sixth amendment. Confirm
the four changed manifest axes and run the repository docs, secret and whitespace checks listed above.

### 롤백

Revert commit `docs(llm): record A-080 offline implementation`; it only reverts documentation and
version metadata. No operational data or evidence lease is affected.

### 다음 개발자 시작점

Do not call the provider. If an exact human approval is received, first use the existing A-080
one-shot root offline gate and readiness-only workflow on a clean committed source, then follow the
approved plan's actual gate exactly once.

## 14. 남은 위험·미해결 질문·다음 단계

- Semantic rubric quality against the fixed nine provider cases is unproven; A-079 remains 6/9 FAIL.
- Root offline gate/readiness/actual have not run, so their results must not be inferred.
- Next step: wait for explicit actual approval; without it, no provider call or cost is permitted.

## 15. 자체 리뷰

- [x] 요청 충족
- [x] 테스트/검증
- [x] source-of-truth/계약/버전 동기화
- [x] 개인정보 원문 노출 없음
- [x] 구현 노트 INDEX 갱신
