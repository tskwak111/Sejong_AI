# Upstage Classifier Value-Free Response-Stage Diagnostics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Production classifier와 동일한 검증 경로에서 response terminal stage enum 하나만
관찰하고, aggregate-only actual evidence로 D-107의 2xx strict-decision 거부 단계를 찾는다.

**Architecture:** 새 internal diagnostics enum을 classifier contracts와 Upstage response parser가
공유한다. `QuestionClassifier`는 optional observer에 enum만 exactly once 전달하고 기존
`ClassifierDecision | None` 동작을 유지한다. actual runner는 enum별 count만 보고서에 기록한다.

**Tech Stack:** Python 3.12.13, pytest, httpx MockTransport, Ruff, Mypy, existing standard-library
`Counter`; 새 production dependency 없음.

## Global Constraints

- 질문·provider body·status detail·exception·key·DSN을 출력·저장하지 않는다.
- observer는 `ClassifierResponseStage` enum 하나 외의 값을 받지 않는다.
- public API·shared contract·DB·migration·official/mock data·prompt·provider profile은 불변이다.
- classifier는 invalid response를 계속 `None`으로 fail-closed 처리한다.
- actual은 fixed 20, provider-free 11, expected outbound 9, retry 0, concurrency 1,
  classifier/generator/combined 80/100/160, VAT 포함 USD 0.20 cap으로 정확히 한 번만 실행한다.
- D-107 current report는 archive하고 새 source commit 전 actual을 실행하지 않는다.
- actual 결과가 FAIL이어도 재시도하지 않는다.

---

### Task 1: Add typed contract-stage diagnostics

**Files:**
- Create: `apps/api/src/sejong_ai_api/llm/classifier_diagnostics.py`
- Modify: `apps/api/src/sejong_ai_api/llm/classifier_contracts.py`
- Test: `apps/api/tests/llm/test_classifier_contracts.py`

**Interfaces:**
- Produces:

```python
class ClassifierResponseStage(str, Enum):
    HTTP_REJECTED = "HTTP_REJECTED"
    ENVELOPE_REJECTED = "ENVELOPE_REJECTED"
    USAGE_REJECTED = "USAGE_REJECTED"
    CHOICE_REJECTED = "CHOICE_REJECTED"
    FINISH_REASON_REJECTED = "FINISH_REASON_REJECTED"
    MESSAGE_REJECTED = "MESSAGE_REJECTED"
    CONTENT_REJECTED = "CONTENT_REJECTED"
    JSON_REJECTED = "JSON_REJECTED"
    KEY_SET_REJECTED = "KEY_SET_REJECTED"
    FIELD_TYPE_REJECTED = "FIELD_TYPE_REJECTED"
    ENUM_SHAPE_REJECTED = "ENUM_SHAPE_REJECTED"
    CATALOG_REJECTED = "CATALOG_REJECTED"
    ACCEPTED = "ACCEPTED"

@dataclass(frozen=True, slots=True)
class ClassifierDecisionParseResult:
    decision: ClassifierDecision | None
    stage: ClassifierResponseStage

def parse_classifier_decision_with_stage(
    payload: bytes,
    catalog: TopicCatalog,
) -> ClassifierDecisionParseResult: ...
```

- Preserves:

```python
def parse_classifier_decision(payload: bytes, catalog: TopicCatalog) -> ClassifierDecision:
    # failure remains ValueError("CLASSIFIER_DECISION_INVALID")
```

- [x] **Step 1: Write contract-stage RED tests**

Add a literal table that expects `JSON_REJECTED`, `KEY_SET_REJECTED`, `FIELD_TYPE_REJECTED`,
`ENUM_SHAPE_REJECTED`, `CATALOG_REJECTED` and `ACCEPTED` for controlled payloads. Verify the result
contains no payload field and the existing public parser still raises only
`CLASSIFIER_DECISION_INVALID`.

- [x] **Step 2: Run RED**

```powershell
apps/api/.venv/Scripts/python.exe -m pytest `
  apps/api/tests/llm/test_classifier_contracts.py -q
```

Expected: import/function failure because the diagnostic types do not exist.

- [x] **Step 3: Implement minimal typed parser**

Decode JSON, exact keys, nullable string types, enum/route shape and current catalog membership in
that order. Return a fixed enum at the first failed boundary. Wrap the result in the existing public
parser without changing its exception message.

- [x] **Step 4: Run GREEN**

```powershell
apps/api/.venv/Scripts/python.exe -m pytest `
  apps/api/tests/llm/test_classifier_contracts.py -q
```

Expected: all contract tests PASS.

---

### Task 2: Emit exactly one production response stage

**Files:**
- Modify: `apps/api/src/sejong_ai_api/llm/upstage_classifier.py`
- Test: `apps/api/tests/llm/test_upstage_classifier.py`
- Test: `apps/api/tests/llm/test_security.py`

**Interfaces:**
- Consumes: `ClassifierResponseStage`, `parse_classifier_decision_with_stage`.
- Produces:

```python
ResponseStageObserver = Callable[[ClassifierResponseStage], None]

QuestionClassifier(
    *,
    settings: UpstageClassifierSettings,
    client: httpx.AsyncClient,
    ledger: ProviderAttemptLedger,
    response_stage_observer: ResponseStageObserver | None = None,
)
```

- [x] **Step 1: Write transport-stage RED tests**

Use real `QuestionClassifier` plus `httpx.MockTransport`. Cover non-2xx, invalid envelope, usage,
choice, finish reason, message, content, every contract stage and accepted. For each HTTP response:

```python
assert observed == [expected_stage]
assert decision is expected_decision_or_none
```

Also assert timeout emits no response stage and an observer that raises does not change an accepted
decision.

- [x] **Step 2: Run RED**

```powershell
apps/api/.venv/Scripts/python.exe -m pytest `
  apps/api/tests/llm/test_upstage_classifier.py `
  apps/api/tests/llm/test_security.py -q
```

Expected: constructor keyword/stage imports fail before implementation.

- [x] **Step 3: Implement terminal parse result and observer isolation**

Map HTTP/envelope/usage/choice/finish/message/content to fixed stages. Forward the contract parser
stage. Emit at most once after a response exists. Catch observer exceptions without changing the
decision. Transport/timeout continues to return `None` without a response stage.

- [x] **Step 4: Run GREEN**

```powershell
apps/api/.venv/Scripts/python.exe -m pytest `
  apps/api/tests/llm/test_classifier_contracts.py `
  apps/api/tests/llm/test_upstage_classifier.py `
  apps/api/tests/llm/test_security.py -q
```

Expected: all focused tests PASS with no content reflection.

---

### Task 3: Add aggregate-only runner stage counters

**Files:**
- Modify: `scripts/run_hybrid_rag_actual.py`
- Test: `scripts/tests/test_run_hybrid_rag_actual.py`

**Interfaces:**
- Consumes: `ClassifierResponseStage` and `QuestionClassifier(response_stage_observer=...)`.
- Produces:

```python
class _ResponseStageRecorder:
    def capture(self, stage: ClassifierResponseStage) -> None: ...
    @property
    def total(self) -> int: ...
    def count(self, stage: ClassifierResponseStage) -> int: ...
```

Report fields:

```text
provider_response_stage_total
provider_stage_http_rejected_count
provider_stage_envelope_rejected_count
provider_stage_usage_rejected_count
provider_stage_choice_rejected_count
provider_stage_finish_reason_rejected_count
provider_stage_message_rejected_count
provider_stage_content_rejected_count
provider_stage_json_rejected_count
provider_stage_key_set_rejected_count
provider_stage_field_type_rejected_count
provider_stage_enum_shape_rejected_count
provider_stage_catalog_rejected_count
provider_stage_accepted_count
```

- [x] **Step 1: Write runner/report RED tests**

Assert recorder fixed enum counts, report order, `stage_total == provider_response_count`, accepted
PASS fixture stage count 9, transport response-stage count 0, and forbidden sentinels absent from
stdout/report.

- [x] **Step 2: Run RED**

```powershell
apps/api/.venv/Scripts/python.exe -m pytest `
  scripts/tests/test_run_hybrid_rag_actual.py -q
```

Expected: missing recorder/report fields and selector signature failures.

- [x] **Step 3: Implement aggregate recorder wiring**

Store recorder on `_RunEvidence`, pass it through `_create_selector`, and build scalar report fields
from the closed enum. Do not add per-fixture stage. Require stage total to equal response count and
accepted stage count to equal expected provider cases for PASS.

- [x] **Step 4: Run GREEN and static checks**

```powershell
apps/api/.venv/Scripts/python.exe -m pytest `
  scripts/tests/test_run_hybrid_rag_actual.py `
  apps/api/tests/llm/test_classifier_contracts.py `
  apps/api/tests/llm/test_upstage_classifier.py `
  apps/api/tests/llm/test_security.py -q
apps/api/.venv/Scripts/python.exe -m ruff check `
  apps/api/src/sejong_ai_api/llm `
  apps/api/tests/llm `
  scripts/run_hybrid_rag_actual.py `
  scripts/tests/test_run_hybrid_rag_actual.py
apps/api/.venv/Scripts/python.exe -m ruff format --check `
  apps/api/src/sejong_ai_api/llm `
  apps/api/tests/llm `
  scripts/run_hybrid_rag_actual.py `
  scripts/tests/test_run_hybrid_rag_actual.py
apps/api/.venv/Scripts/python.exe -m mypy apps/api/src/sejong_ai_api/llm
```

---

### Task 4: Freeze implementation source and versions

**Files:**
- Modify: `versions/manifest.json`
- Modify: `CHANGELOG.md`
- Modify: `TASKS.md`
- Modify: `docs/00_SOURCE_OF_TRUTH.md`
- Modify: `docs/11_AMBIGUITY_REGISTER.md`
- Modify: `docs/12_VERSIONING_AND_RELEASES.md`
- Modify: `docs/decisions/DECISION_LOG.md`
- Modify: `docs/source-of-truth/TEAM_DECISIONS.md`
- Modify: written specification status
- Archive: D-107 current actual report

**Version targets before actual:**

```text
application: 0.12.2-response-stage-diagnostics
test_suite: 2.1.5-response-stage-diagnostics
documentation: 2.29.7
prompt_set: 0.4.1-json-mode-instruction (unchanged)
```

- [x] **Step 1: Archive D-107 report**

Move the current report to:

```text
docs/test-reports/archive/
CHAT-HYBRID-RAG-001-UPSTAGE-ACTUAL-20260728-D107-2XX-DECISION-REJECT-FAIL.md
```

- [x] **Step 2: Update versions and implementation status**

Record D-109 spec/plan approval, implemented enum-only observer, no API/DB/data/prompt/dependency
change, and actual pending from a clean source.

- [x] **Step 3: Run pre-actual gates**

```powershell
apps/api/.venv/Scripts/python.exe -m pytest `
  apps/api/tests/llm/test_classifier_contracts.py `
  apps/api/tests/llm/test_upstage_classifier.py `
  apps/api/tests/llm/test_security.py `
  scripts/tests/test_run_hybrid_rag_actual.py -q
python -B scripts/check_repository_docs.py
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File scripts/check_secret_patterns.ps1 -RepositoryRoot .
git diff --check
```

- [x] **Step 4: Commit exact source**

```powershell
git add apps/api/src/sejong_ai_api/llm apps/api/tests/llm `
  scripts/run_hybrid_rag_actual.py scripts/tests/test_run_hybrid_rag_actual.py `
  versions/manifest.json CHANGELOG.md TASKS.md docs
git commit -m "test(llm): add value-free response-stage diagnostics"
```

Require a clean working tree and record the exact source SHA.

---

### Task 5: Execute the approved exact-one actual and close evidence

**Files:**
- Create: `docs/test-reports/CHAT-HYBRID-RAG-001-UPSTAGE-ACTUAL.md`
- Create via script: A-071 implementation note
- Modify: `docs/implementation-notes/INDEX.md`
- Modify: decision/ambiguity/SOT/TASKS/version/CHANGELOG with observed result

- [x] **Step 1: Run value-free preflight**

Require clean source, report absent, lock absent, secret scan PASS, exact profile valid, key presence
boolean true, fixed hashes and modes set only in the process.

- [x] **Step 2: Execute exactly once**

```powershell
apps/api/.venv/Scripts/python.exe -B scripts/run_hybrid_rag_actual.py `
  --fixture apps/api/tests/chat/fixtures/hybrid-rag-uat.v1.json `
  --report docs/test-reports/CHAT-HYBRID-RAG-001-UPSTAGE-ACTUAL.md
```

Do not execute this command a second time for any exit code.

- [x] **Step 3: Inspect aggregate evidence only**

Record 20 selected, skip, provider-free/outbound, HTTP/usage/decision/match, stage counts, cost,
acceptance and elapsed time. Do not inspect or recover response content.

- [x] **Step 4: Verify safe restoration**

Confirm ignored `.env` modes false/false, lock 0, no secret/PII findings and no DB/data changes.

- [x] **Step 5: Complete implementation note and final verification**

Run focused tests, Ruff, Mypy, docs, secret and diff gates again. Record any warning or unrun
repository-wide gate honestly.

- [x] **Step 6: Commit evidence**

```powershell
git add docs/test-reports/CHAT-HYBRID-RAG-001-UPSTAGE-ACTUAL.md `
  docs/implementation-notes docs/implementation-notes/INDEX.md `
  versions/manifest.json CHANGELOG.md TASKS.md docs
git commit -m "docs(llm): record response-stage actual evidence"
```

Do not push or merge without a separate user instruction.

---

## Plan Self-Review

### Specification coverage

- production same-path observer: Tasks 1~2
- enum-only and exactly-once: Tasks 1~2
- aggregate-only report and total invariant: Task 3
- public parser/fallback preservation: Tasks 1~2
- TDD/static/security verification: Tasks 1~4
- clean source and D-107 archive: Task 4
- fixed exact-one bounded actual: Task 5
- versions/decision/note/handoff: Tasks 4~5

Coverage gaps: none.

### Placeholder scan

The plan contains exact files, interfaces, enum values, report fields, commands, counts, version
targets and commit boundaries. Ellipses in Python type signatures denote callable bodies, not
unfinished plan content.

### Type consistency

`ClassifierResponseStage` is shared by contract parsing, transport parsing and runner counting.
`QuestionClassifier` remains `ClassifierDecision | None`; only the optional observer is additive.
The runner uses the same enum and does not define a second parser or a stringly-typed stage list.

## Execution Choice

The user requested immediate fast implementation and did not request subagents for this turn.
Execute inline with `superpowers:executing-plans`; do not create parallel agents.
