# Upstage Classifier Strict Five-Key Wire Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Upstage return the exact closed five-key classifier wire, normalize exact `NONE`
sentinels at the provider boundary, and preserve existing server validation and fail-closed behavior.

**Architecture:** Add a provider-wire parsing mode beside the existing canonical JSON-null parser,
but make both paths share the same closed decision and current catalog validation. Replace
`json_object` with a fresh strict `json_schema`, rewrite the classifier system prompt with canonical
field names, and verify everything offline before requesting separate permission for one actual run.

**Tech Stack:** Python 3.12.13, FastAPI package layout, httpx 0.28.1, pytest 9.1.1,
pytest-asyncio 1.4.0, Ruff 0.15.21, Mypy 2.3.0, Upstage `solar-pro3`

## Global Constraints

- Follow `AGENTS.md`, D-112~D-115, ADR-0025/0027 and the approved written specification.
- Provider input must already be `SafeQuestion`; do not change PII redaction or policy ordering.
- Exact wire keys are `route`, `intent`, `topic_id`, `coverage_id`, `pending_slot`.
- Every wire field is required and string; nullable meaning uses exact uppercase `NONE`.
- Only `intent`, `topic_id`, `coverage_id`, `pending_slot` may normalize `NONE` to internal `None`.
- Keep canonical JSON-null parsing and public `CLASSIFIER_DECISION_INVALID` behavior unchanged.
- Keep server-owned route/intent/shape/current ACTIVE/OFFICIAL catalog validation and source binding.
- Keep model `solar-pro3`, max output 128, timeout 3 seconds, retry 0, concurrency 1 and current ledger.
- Add no production dependency; do not modify package manifests or lockfiles.
- Do not modify public API, shared contracts, DB/migrations, official/mock data or Web.
- Never store or output question, provider body, status detail, exception, key or DSN.
- Do not run the actual provider command during Tasks 1~5.
- Task 6 requires a new explicit human approval after Tasks 1~5 pass on clean committed source.
- Do not push, merge, reset DB, seed, deploy or activate public/remote provider behavior.

## File Structure

- Modify `apps/api/src/sejong_ai_api/llm/classifier_contracts.py`
  - Own canonical and provider-wire decoding paths plus one shared closed validator.
- Modify `apps/api/src/sejong_ai_api/llm/classifier_prompt.py`
  - Own canonical field-name and `NONE` output instructions.
- Modify `apps/api/src/sejong_ai_api/llm/upstage_classifier.py`
  - Own strict Upstage response-format construction and transport integration.
- Modify `apps/api/tests/llm/test_classifier_contracts.py`
  - Prove sentinel normalization, canonical regression and fixed stage mapping.
- Modify `apps/api/tests/llm/test_prompt.py`
  - Prove full-name prompt, shorthand removal, data minimization and 4,096 upper bound.
- Modify `apps/api/tests/llm/test_upstage_classifier.py`
  - Prove exact request schema, provider-wire response handling, observer isolation and retry 0.
- Modify `versions/manifest.json`, `CHANGELOG.md`, `TASKS.md`,
  `docs/12_VERSIONING_AND_RELEASES.md`, A-072 authority docs and the implementation-note INDEX
  - Record implementation and verification evidence only after GREEN.
- Do not modify `scripts/run_hybrid_rag_actual.py` or its protected fixture/data inputs unless a
  focused regression proves the existing runner cannot consume the new production parser.

---

### Task 1: Provider-Wire Parser and Shared Validation

**Files:**
- Modify: `apps/api/src/sejong_ai_api/llm/classifier_contracts.py`
- Test: `apps/api/tests/llm/test_classifier_contracts.py`

**Interfaces:**
- Consumes: `payload: bytes`, `catalog: TopicCatalog`,
  existing `ClassifierDecisionParseResult` and `ClassifierResponseStage`
- Produces:
  `parse_classifier_wire_decision_with_stage(payload: bytes, catalog: TopicCatalog) -> ClassifierDecisionParseResult`
- Preserves:
  `parse_classifier_decision_with_stage(payload, catalog)` and
  `parse_classifier_decision(payload, catalog)` canonical JSON-null behavior

- [ ] **Step 1: Add RED tests for every accepted wire route**

Add an import for `parse_classifier_wire_decision_with_stage` and parameterize the exact string
wire shapes:

```python
@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        (
            b'{"route":"SUPPORTED","intent":"BULKY_WASTE",'
            b'"topic_id":"KB-WASTE-01","coverage_id":"GENERAL_BULKY_DISPOSAL",'
            b'"pending_slot":"NONE"}',
            ("SUPPORTED", "BULKY_WASTE", "KB-WASTE-01", "GENERAL_BULKY_DISPOSAL", None),
        ),
        (
            b'{"route":"NO_TOPIC_MATCH","intent":"BULKY_WASTE",'
            b'"topic_id":"NONE","coverage_id":"NONE","pending_slot":"NONE"}',
            ("NO_TOPIC_MATCH", "BULKY_WASTE", None, None, None),
        ),
        (
            b'{"route":"NON_CIVIC","intent":"NONE","topic_id":"NONE",'
            b'"coverage_id":"NONE","pending_slot":"NONE"}',
            ("NON_CIVIC", None, None, None, None),
        ),
        (
            b'{"route":"NEEDS_FOLLOWUP","intent":"BULKY_WASTE",'
            b'"topic_id":"NONE","coverage_id":"NONE","pending_slot":"WASTE_ITEM"}',
            ("NEEDS_FOLLOWUP", "BULKY_WASTE", None, None, "WASTE_ITEM"),
        ),
    ],
)
def test_provider_wire_normalizes_exact_none_and_accepts_closed_shapes(
    payload: bytes,
    expected: tuple[str, str | None, str | None, str | None, str | None],
) -> None:
    result = parse_classifier_wire_decision_with_stage(payload, _catalog())
    assert result.stage is ClassifierResponseStage.ACCEPTED
    assert result.decision is not None
    assert (
        result.decision.route.value,
        result.decision.intent.value if result.decision.intent else None,
        result.decision.topic_id,
        result.decision.coverage_id,
        result.decision.pending_slot.value if result.decision.pending_slot else None,
    ) == expected
```

- [ ] **Step 2: Add RED tests for exact type, sentinel, key and canonical isolation**

Add cases with JSON `null`, route `NONE`, lowercase `none`, `NONE `, missing/extra keys and catalog
mismatch. Assert the exact fixed stage. Add this canonical regression:

```python
def test_canonical_parser_keeps_json_null_and_rejects_provider_sentinel() -> None:
    canonical = parse_classifier_decision(
        b'{"route":"NON_CIVIC","intent":null,"topic_id":null,'
        b'"coverage_id":null,"pending_slot":null}',
        _catalog(),
    )
    assert canonical.route is ClassifierRoute.NON_CIVIC

    with pytest.raises(ValueError, match="^CLASSIFIER_DECISION_INVALID$"):
        parse_classifier_decision(
            b'{"route":"NON_CIVIC","intent":"NONE","topic_id":"NONE",'
            b'"coverage_id":"NONE","pending_slot":"NONE"}',
            _catalog(),
        )
```

Expected wire stages:

```text
JSON null/non-string → FIELD_TYPE_REJECTED
missing/extra key → KEY_SET_REJECTED
route NONE/lowercase/space/invalid route combination → ENUM_SHAPE_REJECTED
unknown topic or wrong coverage → CATALOG_REJECTED
valid normalized decision → ACCEPTED
```

- [ ] **Step 3: Run the contract tests and confirm RED**

Run from `apps/api`:

```powershell
.venv/Scripts/python.exe -m pytest `
  tests/llm/test_classifier_contracts.py `
  -q
```

Expected: FAIL because `parse_classifier_wire_decision_with_stage` is absent or wire `NONE` is not
yet normalized. Existing canonical tests must remain green inside the same run.

- [ ] **Step 4: Refactor one shared decode/validation path and add wire normalization**

Keep `_EXPECTED_KEYS` as the one exact key set. Refactor the current parser into one internal helper
with a `wire_strings` switch:

```python
_NONE_SENTINEL = "NONE"
_NULLABLE_FIELDS = ("intent", "topic_id", "coverage_id", "pending_slot")


def parse_classifier_wire_decision_with_stage(
    payload: bytes,
    catalog: TopicCatalog,
) -> ClassifierDecisionParseResult:
    return _parse_classifier_payload_with_stage(
        payload,
        catalog,
        wire_strings=True,
    )


def parse_classifier_decision_with_stage(
    payload: bytes,
    catalog: TopicCatalog,
) -> ClassifierDecisionParseResult:
    return _parse_classifier_payload_with_stage(
        payload,
        catalog,
        wire_strings=False,
    )
```

Inside `_parse_classifier_payload_with_stage`:

```python
if wire_strings:
    if any(type(raw[field]) is not str for field in _EXPECTED_KEYS):
        return ClassifierDecisionParseResult(
            None,
            ClassifierResponseStage.FIELD_TYPE_REJECTED,
        )
    normalized = dict(raw)
    for field in _NULLABLE_FIELDS:
        if normalized[field] == _NONE_SENTINEL:
            normalized[field] = None
    raw = normalized
```

Then execute the current enum/shape/catalog construction exactly once on `raw`. Do not convert
route `NONE`; it must fail `ClassifierRoute(route_raw)` and become `ENUM_SHAPE_REJECTED`.

- [ ] **Step 5: Preserve the public surface and value-free errors**

Add `parse_classifier_wire_decision_with_stage` to `__all__`. Do not change the public
`parse_classifier_decision()` signature or its exact failure string. Ensure no exception includes
payload values.

- [ ] **Step 6: Run contract tests and confirm GREEN**

```powershell
.venv/Scripts/python.exe -m pytest `
  tests/llm/test_classifier_contracts.py `
  -q
```

Expected: all tests PASS, including canonical JSON-null regression and provider-wire stage cases.

- [ ] **Step 7: Commit Task 1**

```powershell
git add apps/api/src/sejong_ai_api/llm/classifier_contracts.py `
  apps/api/tests/llm/test_classifier_contracts.py
git commit -m "feat(llm): normalize strict classifier wire"
```

---

### Task 2: Canonical Full-Name Classifier Prompt

**Files:**
- Modify: `apps/api/src/sejong_ai_api/llm/classifier_prompt.py`
- Test: `apps/api/tests/llm/test_prompt.py`
- Test: `apps/api/tests/llm/test_upstage_classifier.py`

**Interfaces:**
- Consumes: `SafeQuestion`, request-local `TopicCatalog`, `max_input_chars`
- Produces: unchanged
  `build_classifier_messages(...) -> tuple[dict[str, str], ...]`
- Preserves: masked question, six catalog columns, max 20 topics, max two approved examples,
  1,024 character input and 4,096 upper bound

- [ ] **Step 1: Replace permissive prompt tests with exact RED assertions**

Add this test to `test_prompt.py`:

```python
def test_classifier_prompt_uses_canonical_wire_names_and_exact_none() -> None:
    system = build_classifier_messages(
        _safe_question(),
        _catalog(),
        max_input_chars=1024,
    )[0]["content"]

    for field in ("route", "intent", "topic_id", "coverage_id", "pending_slot"):
        assert field in system
    assert "NONE" in system
    for forbidden in ("route/I:", "T:topic_id", "C:coverage_id", "P:pending_slot", "∅", "n³", "n⁴"):
        assert forbidden not in system
```

Update `test_prompt_defines_all_closed_pending_slots_and_route_shapes` so it requires full field
names and `NONE` instead of accepting `I`, `P` or `n`.

- [ ] **Step 2: Run prompt tests and confirm RED**

```powershell
.venv/Scripts/python.exe -m pytest `
  tests/llm/test_prompt.py `
  tests/llm/test_upstage_classifier.py::test_prompt_defines_supported_boundary_and_closed_route_meanings `
  tests/llm/test_upstage_classifier.py::test_prompt_defines_all_closed_pending_slots_and_route_shapes `
  -q
```

Expected: FAIL because the old system message contains shorthand and lacks the exact `NONE` rule.

- [ ] **Step 3: Replace `_SYSTEM_MESSAGE` with full canonical rules**

Use this bounded message, preserving every route and pending-slot rule:

```python
_SYSTEM_MESSAGE = (
    "JSON 객체만 출력. 필드는 route,intent,topic_id,coverage_id,pending_slot 정확히 5개이며 "
    "모두 문자열. 값 없음은 NONE, 추가 필드 금지. "
    "SUPPORTED: intent/topic_id/coverage_id는 catalog row 값, pending_slot=NONE. "
    "NO_TOPIC_MATCH: intent는 지원 intent, topic_id/coverage_id/pending_slot=NONE. "
    "CIVIC_SCOPE_GAP 또는 NON_CIVIC: intent/topic_id/coverage_id/pending_slot=NONE. "
    "NEEDS_FOLLOWUP: topic_id/coverage_id=NONE, pending_slot은 "
    "DOMAIN|TOPIC_CHOICE|CERTIFICATE_KIND|REGION|WASTE_ITEM. "
    "pending_slot=DOMAIN이면 intent=NONE, 그 외 intent는 지원 intent."
)
```

Do not add answer, source, office, confidence, reasoning or free-text fields.

- [ ] **Step 4: Run prompt tests, governed 20-topic bound and source-free checks**

```powershell
.venv/Scripts/python.exe -m pytest `
  tests/llm/test_prompt.py `
  tests/llm/test_upstage_classifier.py::test_prompt_defines_supported_boundary_and_closed_route_meanings `
  tests/llm/test_upstage_classifier.py::test_prompt_defines_all_closed_pending_slots_and_route_shapes `
  -q
```

Expected: PASS, with governed 19/20 catalogs at or below the existing 4,096 estimate.

- [ ] **Step 5: Commit Task 2**

```powershell
git add apps/api/src/sejong_ai_api/llm/classifier_prompt.py `
  apps/api/tests/llm/test_prompt.py `
  apps/api/tests/llm/test_upstage_classifier.py
git commit -m "fix(llm): require canonical classifier fields"
```

---

### Task 3: Strict Upstage Schema and Production Wire Integration

**Files:**
- Modify: `apps/api/src/sejong_ai_api/llm/upstage_classifier.py`
- Modify: `apps/api/tests/llm/test_upstage_classifier.py`

**Interfaces:**
- Consumes:
  `parse_classifier_wire_decision_with_stage(payload, catalog)` from Task 1
- Produces: unchanged `QuestionClassifier.classify(...) -> ClassifierDecision | None`
- Preserves: `_parse_response` value-free stage result, observer exactly once, retry 0 and ledger

- [ ] **Step 1: Make the provider test helper emit the approved string wire**

Change `_provider_response` default content in `test_upstage_classifier.py`:

```python
content: str = (
    '{"route":"CIVIC_SCOPE_GAP","intent":"NONE","topic_id":"NONE",'
    '"coverage_id":"NONE","pending_slot":"NONE"}'
)
```

Update every controlled accepted response in the file to use `NONE` for nullable wire values.
Retain an explicit JSON-null response in the stage matrix and expect `FIELD_TYPE_REJECTED`.

- [ ] **Step 2: Change the captured-request assertion to the exact strict schema**

Replace the expected `response_format` with:

```python
"response_format": {
    "type": "json_schema",
    "json_schema": {
        "name": "sejong_classifier_decision",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "route": {"type": "string"},
                "intent": {"type": "string"},
                "topic_id": {"type": "string"},
                "coverage_id": {"type": "string"},
                "pending_slot": {"type": "string"},
            },
            "required": [
                "route",
                "intent",
                "topic_id",
                "coverage_id",
                "pending_slot",
            ],
            "additionalProperties": False,
        },
    },
},
```

Also assert serialized request content excludes `answer`, source fields, fact sentinels, key and
dynamic schema enums.

- [ ] **Step 3: Run transport tests and confirm RED**

```powershell
.venv/Scripts/python.exe -m pytest `
  tests/llm/test_upstage_classifier.py `
  -q
```

Expected: exact request test FAIL because production still sends `json_object`; accepted response
tests also fail until `_parse_response` uses the provider-wire parser.

- [ ] **Step 4: Add a fresh strict response-format builder**

In `upstage_classifier.py` add:

```python
_CLASSIFIER_FIELDS = (
    "route",
    "intent",
    "topic_id",
    "coverage_id",
    "pending_slot",
)


def _build_classifier_response_format() -> dict[str, object]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "sejong_classifier_decision",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": {
                    field: {"type": "string"} for field in _CLASSIFIER_FIELDS
                },
                "required": list(_CLASSIFIER_FIELDS),
                "additionalProperties": False,
            },
        },
    }
```

Use `_build_classifier_response_format()` when constructing every request. Do not store one mutable
schema object globally.

- [ ] **Step 5: Route response content through the wire parser**

Import `parse_classifier_wire_decision_with_stage` and change only the final parser call:

```python
parsed = parse_classifier_wire_decision_with_stage(payload, catalog)
```

Do not change envelope, usage, choice, finish reason, content, observer or cost handling.

- [ ] **Step 6: Run transport and observer tests and confirm GREEN**

```powershell
.venv/Scripts/python.exe -m pytest `
  tests/llm/test_upstage_classifier.py `
  tests/llm/test_classifier_contracts.py `
  -q
```

Expected: PASS for exact schema, valid wire decisions, JSON-null rejection, all 13 terminal stages,
observer isolation, no retry, usage/cost accounting and current catalog mismatch.

- [ ] **Step 7: Commit Task 3**

```powershell
git add apps/api/src/sejong_ai_api/llm/upstage_classifier.py `
  apps/api/tests/llm/test_upstage_classifier.py
git commit -m "fix(llm): enforce strict classifier response schema"
```

---

### Task 4: Offline Area Regression and Version Integration

**Files:**
- Modify: `versions/manifest.json`
- Modify: `CHANGELOG.md`
- Modify: `TASKS.md`
- Modify: `docs/00_SOURCE_OF_TRUTH.md`
- Modify: `docs/source-of-truth/TEAM_DECISIONS.md`
- Modify: `docs/11_AMBIGUITY_REGISTER.md`
- Modify: `docs/12_VERSIONING_AND_RELEASES.md`
- Modify: `docs/decisions/DECISION_LOG.md`
- Modify: `docs/adr/0027-active-topic-catalog-and-coverage-grounding.md`
- Create: A-072 implementation note with `scripts/new_implementation_note.py`
- Modify: `docs/implementation-notes/INDEX.md`

**Interfaces:**
- Consumes: Tasks 1~3 committed code and focused GREEN evidence
- Produces: application `0.12.3-structured-classifier-wire`,
  prompt `0.4.2-exact-five-key-schema`, tests `2.1.6-structured-classifier-wire`
- Preserves: API, shared contracts, DB/data and dependency versions

- [ ] **Step 1: Run the complete classifier/Hybrid RAG area suite**

From `apps/api`:

```powershell
.venv/Scripts/python.exe -m pytest `
  tests/llm/test_classifier_contracts.py `
  tests/llm/test_prompt.py `
  tests/llm/test_upstage_classifier.py `
  tests/chat/test_hybrid_rag_uat.py `
  tests/chat/test_service.py `
  tests/test_local.py `
  -q
```

Expected: PASS with no skip introduced by this change.

- [ ] **Step 2: Run actual-runner offline regression without network**

From repository root:

```powershell
apps/api/.venv/Scripts/python.exe -m pytest `
  scripts/tests/test_run_hybrid_rag_actual.py `
  -q
```

Expected: PASS. This command uses controlled doubles and must make zero provider calls.

- [ ] **Step 3: Run formatter, lint and type checks**

From `apps/api`:

```powershell
.venv/Scripts/python.exe -m ruff format --check src tests
.venv/Scripts/python.exe -m ruff check src tests
.venv/Scripts/python.exe -m mypy src tests
```

Expected: all exit 0. If formatter check fails, run
`.venv/Scripts/python.exe -m ruff format <changed-files>` once, inspect the diff, then rerun all
three commands.

- [ ] **Step 4: Review the implementation diff against the immutable scope**

Run from repository root:

```powershell
git diff --name-status dc69b68...HEAD
git diff --check
git status --short
```

The name list may contain only the approved LLM source/tests and authority/version/note documents.
It must contain no `.env`, contract, DB/migration, official/mock data, package or lockfile.

- [ ] **Step 5: Advance only approved versions and write the implementation note**

Set:

```text
application = 0.12.3-structured-classifier-wire
prompt_set = 0.4.2-exact-five-key-schema
test_suite = 2.1.6-structured-classifier-wire
```

Keep API/shared/DB/official/mock axes unchanged. Record exact commands, counts, code files,
provider call 0, cost USD 0, security impact, rollback and next actual gate in the note.

- [ ] **Step 6: Run docs, secret and diff gates**

```powershell
python -B scripts/check_repository_docs.py
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File scripts/check_secret_patterns.ps1 -RepositoryRoot .
git diff --check
```

Expected: documentation PASS, secret findings 0 and whitespace errors 0.

- [ ] **Step 7: Commit Task 4**

```powershell
git add versions/manifest.json CHANGELOG.md TASKS.md `
  docs/00_SOURCE_OF_TRUTH.md docs/source-of-truth/TEAM_DECISIONS.md `
  docs/11_AMBIGUITY_REGISTER.md docs/12_VERSIONING_AND_RELEASES.md `
  docs/decisions/DECISION_LOG.md `
  docs/adr/0027-active-topic-catalog-and-coverage-grounding.md `
  docs/implementation-notes
git commit -m "docs(llm): integrate strict classifier wire evidence"
```

---

### Task 5: Repository Gate, Clean-Source Review and Actual Decision Gate

**Files:**
- Modify only if evidence requires correction:
  A-072 implementation note, INDEX and authority/version documents
- Do not create or modify the current actual report in this task.

**Interfaces:**
- Consumes: committed Tasks 1~4
- Produces: clean source SHA and exact offline acceptance evidence for the human actual decision

- [ ] **Step 1: Run the repository gate once**

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/verify.ps1
```

Expected: every stage PASS. If an unrelated environment-only stage cannot run, record its exact
bounded reason and run the remaining constituent commands; do not label the wrapper PASS.

- [ ] **Step 2: Run final security and scope checks**

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File scripts/check_secret_patterns.ps1 -RepositoryRoot .
git diff --check
git status --short
git log -4 --oneline
```

Expected: secret finding 0, diff errors 0 and clean worktree.

- [ ] **Step 3: Review code against the spec**

Confirm:

```text
strict five-key schema present
exact NONE only at provider boundary
canonical JSON-null parser unchanged
server enum/shape/catalog validation shared
observer fixed-stage and exactly-once unchanged
retry/cost/model/profile unchanged
question/body/status/key/DSN retention 0
API/DB/data/dependency changes 0
```

- [ ] **Step 4: Record the clean source SHA**

```powershell
git rev-parse HEAD
git status --short
```

Write the full SHA and final test counts to the implementation note. If the note changes, rerun
docs/secret/diff checks and commit only the evidence update:

```powershell
git add docs/implementation-notes docs/implementation-notes/INDEX.md `
  docs/00_SOURCE_OF_TRUTH.md docs/source-of-truth/TEAM_DECISIONS.md `
  docs/11_AMBIGUITY_REGISTER.md TASKS.md versions/manifest.json CHANGELOG.md
git commit -m "docs(llm): close strict classifier wire offline gate"
```

- [ ] **Step 5: Stop and request the separate actual approval**

Report offline results, source SHA, provider call 0 and cost USD 0. Ask for exact approval:

```text
A-072 corrective actual 1회 실행 승인
```

Do not continue to Task 6 from a general implementation-plan approval.

---

### Task 6: Human-Gated Corrective Actual and Evidence Closeout

**Files:**
- Move the current report to
  `docs/test-reports/archive/CHAT-HYBRID-RAG-001-UPSTAGE-ACTUAL-20260728-D111-KEY-SET-REJECTED-FAIL.md`
- Create via runner: `docs/test-reports/CHAT-HYBRID-RAG-001-UPSTAGE-ACTUAL.md`
- Modify: A-072 implementation note, INDEX, decisions/SOT/ambiguity/TASKS/version/CHANGELOG

**Interfaces:**
- Consumes: clean source from Task 5 and a new explicit human approval for exactly one run
- Produces: aggregate PASS/FAIL evidence; never per-question provider content

- [ ] **Step 1: Verify the distinct human approval and runbook prerequisites**

Require the exact new approval after Task 5, clean source, valid ignored local profile, key presence
boolean, current report archived, lock absent, protected hashes unchanged and secret scan PASS.
Do not print environment values.

- [ ] **Step 2: Execute exactly once**

```powershell
apps/api/.venv/Scripts/python.exe -B `
  scripts/run_hybrid_rag_actual.py `
  --fixture apps/api/tests/chat/fixtures/hybrid-rag-uat.v1.json `
  --report docs/test-reports/CHAT-HYBRID-RAG-001-UPSTAGE-ACTUAL.md
```

Do not execute this command a second time for any result.

- [ ] **Step 3: Inspect aggregate evidence only**

Expected PASS:

```text
selected 20
skip 0
provider-free 11
outbound 9
HTTP 2xx / usage / terminal-stage total 9
ACCEPTED 9
provider route/topic match 9
retry 0
cost below USD 0.20
```

If any acceptance condition fails, record FAIL and stop. Do not inspect/recover provider body or
change prompt/schema for an immediate rerun.

- [ ] **Step 4: Restore modes and run closeout checks**

Restore ignored local provider modes to false/false unless the human immediately starts an approved
foreground demo. Verify lock/report status, secret finding 0, DB/data diff 0 and run:

```powershell
python -B scripts/check_repository_docs.py
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File scripts/check_secret_patterns.ps1 -RepositoryRoot .
git diff --check
```

- [ ] **Step 5: Record and commit aggregate evidence**

Update D-117 with the exact aggregate result and preserve all historical reports. Then:

```powershell
git add docs/test-reports docs/implementation-notes `
  docs/decisions/DECISION_LOG.md docs/00_SOURCE_OF_TRUTH.md `
  docs/source-of-truth/TEAM_DECISIONS.md docs/11_AMBIGUITY_REGISTER.md `
  TASKS.md versions/manifest.json CHANGELOG.md
git commit -m "docs(llm): record strict classifier corrective actual"
```

Do not push or merge without a separate user instruction.

---

## Plan Self-Review

### Specification coverage

- exact strict schema and fresh request object: Task 3
- canonical field-name prompt and 4,096 bound: Task 2
- provider-only exact `NONE` normalization: Task 1
- canonical JSON-null regression and shared server validation: Task 1
- fixed stage, observer isolation, retry/cost preservation: Tasks 1 and 3
- focused/area/root offline gates: Tasks 1~5
- versions, authority and implementation note: Task 4
- actual remains separately human-gated and one-shot: Tasks 5~6
- public API/DB/data/dependency non-change: Global Constraints and Tasks 4~5

### Placeholder scan

The plan contains exact files, signatures, commands, expected failures, expected passes, target
versions and stop conditions. It contains no unspecified implementation step.

### Type consistency

- Task 1 produces
  `parse_classifier_wire_decision_with_stage(bytes, TopicCatalog) -> ClassifierDecisionParseResult`.
- Task 3 imports that exact name and preserves
  `QuestionClassifier.classify(...) -> ClassifierDecision | None`.
- Both canonical and provider paths return the existing fixed `ClassifierResponseStage`.
- Tasks 4~6 consume the exact version and gate names defined above.

## Execution Handoff

Plan complete and saved to
`docs/superpowers/plans/2026-07-28-upstage-classifier-strict-five-key-wire.md`.

1. **Subagent-Driven (recommended):** fresh implementation worker per Task 1~4 with specification
   and code-quality review between tasks; main agent owns shared integration, Task 5 and all commits.
2. **Inline Execution:** execute Tasks 1~5 in this session with plan checkpoints.

Task 6 is excluded from both choices until the separate post-verification human approval.
