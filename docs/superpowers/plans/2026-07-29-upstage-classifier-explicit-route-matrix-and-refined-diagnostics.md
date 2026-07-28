# Upstage Classifier Explicit Route Matrix and Refined Diagnostics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the approved strict five-key Upstage classifier prompt unambiguous, distinguish
enum/identifier/route-shape rejection without retaining values, and preserve fail-closed behavior.

**Architecture:** Keep the existing five required string response schema. Normalize canonical and
provider wire representations into one shared typed decision builder whose fixed first-failure
stages precede the existing `ClassifierDecision` invariant and catalog check. Replace the compact
prompt with an exact route matrix and a smaller intent-grouped catalog so the governed 20-topic
actual subset remains under the existing 4,096 transport guard without truncation or sampling.

**Tech Stack:** Python 3.12.13, FastAPI package layout, httpx 0.28.1, pytest 9.1.1,
pytest-asyncio 1.4.0, Ruff 0.15.21, Mypy 2.3.0, Upstage `solar-pro3`

## Global Constraints

- Follow `AGENTS.md`, D-118/D-119, ADR-0025/0027 and the approved A-073 written specification.
- Provider input must already be `SafeQuestion`; do not change PII redaction or policy ordering.
- Keep exact wire keys `route`, `intent`, `topic_id`, `coverage_id`, `pending_slot`.
- Keep every output field required and string; only exact uppercase ASCII `NONE` is the nullable
  provider sentinel.
- Keep the existing five-string `json_schema`; do not add provider schema enum, pattern or
  conditional keywords.
- Keep public `parse_classifier_decision()` and exact `CLASSIFIER_DECISION_INVALID`.
- Keep `ClassifierDecision` as the single route-shape invariant authority; do not duplicate its
  route matrix in a second production validator.
- Keep server-owned current ACTIVE/OFFICIAL catalog membership, facts, source and office binding.
- Keep model `solar-pro3`, max output 128, timeout 3 seconds, retry 0, concurrency 1 and current
  attempt/cost ledger.
- Keep the configured masked-question upper bound 1,024. The complete-message 4,096 guard remains
  authoritative: a long question that exceeds it fails closed before transport without truncating
  the question or catalog.
- The governed 20-topic catalog plus a 256-character safe question must remain at or below 4,096,
  matching the existing actual-eligible boundary.
- Preserve all topic IDs, coverage IDs, coverage labels and up to two approved question examples.
  The provider-only prompt may omit redundant `service_name`; public records/data remain unchanged.
- Add no production dependency and do not modify package manifests or lockfiles.
- Do not modify public API, shared contracts, Web, DB/migrations or official/mock data.
- Never store or output question, provider body, invalid field value, fixture-specific stage,
  exception/status detail, key or DSN.
- Tasks 1~5 must make zero provider/network calls and incur zero provider cost.
- During Tasks 1~5, never run `scripts/run_hybrid_rag_actual.py`,
  `scripts/run_upstage_classifier_evaluation.py`, an API server or a manual `/chat` request.
- `scripts/tests/test_run_hybrid_rag_actual.py` is allowed because it uses controlled doubles and
  makes zero provider calls.
- Do not archive, delete or replace the current D-117 report during Tasks 1~5.
- Task 6 requires a new exact human approval after Tasks 1~5 pass on clean committed source.
- Do not push, merge, reset/seed DB, deploy or activate public/remote provider behavior.

## File Structure

- Modify `apps/api/src/sejong_ai_api/llm/classifier_diagnostics.py`
  - Own the additive closed terminal-stage vocabulary.
- Modify `apps/api/src/sejong_ai_api/llm/classifier_contracts.py`
  - Own wire decoding and the one shared typed decision builder.
- Modify `apps/api/src/sejong_ai_api/llm/classifier_prompt.py`
  - Own the exact route matrix, grouped catalog and deterministic wire examples.
- Preserve `apps/api/src/sejong_ai_api/llm/upstage_classifier.py`
  - Existing five-string schema, guard and exactly-once observer require regression tests only.
- Modify `apps/api/tests/llm/test_classifier_contracts.py`
  - Prove first-failure stages, shared authority and generic public errors.
- Modify `apps/api/tests/llm/test_prompt.py`
  - Prove exact prompt semantics, data minimization and the real 19/20-topic bound.
- Modify `apps/api/tests/llm/test_upstage_classifier.py`
  - Prove refined stages reach the observer exactly once and transport/schema remain unchanged.
- Modify `scripts/tests/test_run_hybrid_rag_actual.py`
  - Prove the nine actual-subset oracle decisions round-trip through the production wire parser
    and aggregate fields stay value-free.
- Preserve `scripts/run_hybrid_rag_actual.py` during offline implementation
  - Its enum-derived report fields and recorder already consume additive stages.
- Modify authority/version documents and create one implementation note after code is GREEN.

---

### Task 1: Shared Typed Decision Builder and Refined Rejection Stages

**Files:**
- Modify: `apps/api/src/sejong_ai_api/llm/classifier_diagnostics.py`
- Modify: `apps/api/src/sejong_ai_api/llm/classifier_contracts.py`
- Test: `apps/api/tests/llm/test_classifier_contracts.py`

**Interfaces:**
- Consumes: exact decoded fields, `TopicCatalog`, existing `ClassifierDecision`
- Produces:
  `_build_classifier_decision_with_stage(...) -> ClassifierDecisionParseResult`
- Preserves:
  `parse_classifier_wire_decision_with_stage(payload, catalog)`,
  `parse_classifier_decision_with_stage(payload, catalog)` and
  `parse_classifier_decision(payload, catalog)`

- [ ] **Step 1: Add the five closed stage values in the tests first**

Import and require these exact enum values:

```python
EXPECTED_REFINED_STAGES = (
    ClassifierResponseStage.ROUTE_ENUM_REJECTED,
    ClassifierResponseStage.INTENT_ENUM_REJECTED,
    ClassifierResponseStage.PENDING_SLOT_ENUM_REJECTED,
    ClassifierResponseStage.IDENTIFIER_SHAPE_REJECTED,
    ClassifierResponseStage.ROUTE_SHAPE_REJECTED,
)
```

Add test `test_refined_classifier_response_stage_values_are_closed_and_legacy_is_retained`.
Assert all five values exist and `ClassifierResponseStage.ENUM_SHAPE_REJECTED` still exists for
historical reports.

- [ ] **Step 2: Add exact RED cases for first-failure precedence**

Add this exact parameterized test to `test_classifier_contracts.py`:

```python
@pytest.mark.parametrize(
    ("payload", "expected_stage", "forbidden_value"),
    [
        (
            b'{"route":"BAD_ROUTE","intent":"NONE","topic_id":"NONE",'
            b'"coverage_id":"NONE","pending_slot":"NONE"}',
            ClassifierResponseStage.ROUTE_ENUM_REJECTED,
            "BAD_ROUTE",
        ),
        (
            b'{"route":"NON_CIVIC","intent":"BAD_INTENT","topic_id":"NONE",'
            b'"coverage_id":"NONE","pending_slot":"NONE"}',
            ClassifierResponseStage.INTENT_ENUM_REJECTED,
            "BAD_INTENT",
        ),
        (
            b'{"route":"NON_CIVIC","intent":"OUT_OF_SCOPE","topic_id":"NONE",'
            b'"coverage_id":"NONE","pending_slot":"NONE"}',
            ClassifierResponseStage.INTENT_ENUM_REJECTED,
            "OUT_OF_SCOPE",
        ),
        (
            b'{"route":"NEEDS_FOLLOWUP","intent":"BULKY_WASTE",'
            b'"topic_id":"NONE","coverage_id":"NONE","pending_slot":"BAD_SLOT"}',
            ClassifierResponseStage.PENDING_SLOT_ENUM_REJECTED,
            "BAD_SLOT",
        ),
        (
            b'{"route":"SUPPORTED","intent":"BULKY_WASTE","topic_id":"bad topic",'
            b'"coverage_id":"GENERAL_BULKY_DISPOSAL","pending_slot":"NONE"}',
            ClassifierResponseStage.IDENTIFIER_SHAPE_REJECTED,
            "bad topic",
        ),
        (
            b'{"route":"NON_CIVIC","intent":"BULKY_WASTE","topic_id":"NONE",'
            b'"coverage_id":"NONE","pending_slot":"NONE"}',
            ClassifierResponseStage.ROUTE_SHAPE_REJECTED,
            "BULKY_WASTE",
        ),
        (
            b'{"route":"BAD_ROUTE","intent":"BAD_INTENT","topic_id":"bad topic",'
            b'"coverage_id":"bad coverage","pending_slot":"BAD_SLOT"}',
            ClassifierResponseStage.ROUTE_ENUM_REJECTED,
            "BAD_ROUTE",
        ),
    ],
)
def test_provider_wire_reports_refined_first_failure_without_reflecting_value(
    payload: bytes,
    expected_stage: ClassifierResponseStage,
    forbidden_value: str,
) -> None:
    result = parse_classifier_wire_decision_with_stage(payload, _catalog())

    assert result.decision is None
    assert result.stage is expected_stage
    assert forbidden_value not in repr(result)
```

The final row proves fixed precedence: route wins over simultaneously invalid intent, pending slot
and identifiers. The `OUT_OF_SCOPE` row proves that the public/server intent is not a provider
wire intent.

- [ ] **Step 3: Add shared-authority and public-regression RED tests**

Add:

```text
test_canonical_and_provider_parsers_share_refined_stage_mapping
test_direct_classifier_decision_keeps_route_shape_invariant
test_public_parser_keeps_generic_non_reflective_failure
test_new_parser_path_never_emits_legacy_enum_shape_stage
```

The direct-constructor test must exercise `__post_init__`, not a missing-argument `TypeError`:

```python
with pytest.raises(ValueError, match="^CLASSIFIER_DECISION_INVALID$"):
    ClassifierDecision(
        route=ClassifierRoute.CIVIC_SCOPE_GAP,
        intent=Intent.OUT_OF_SCOPE,
        topic_id=None,
        coverage_id=None,
        pending_slot=None,
    )
```

The public wrapper must continue to raise exactly
`ValueError("CLASSIFIER_DECISION_INVALID")`.

- [ ] **Step 4: Run the focused contract file and confirm RED**

Run from repository root:

```powershell
apps/api/.venv/Scripts/python.exe -B -m pytest `
  apps/api/tests/llm/test_classifier_contracts.py `
  -q -p no:cacheprovider
```

Expected: new tests fail because all enum/identifier/route-shape cases still collapse into
`ENUM_SHAPE_REJECTED`.

- [ ] **Step 5: Add the new enum members without removing the legacy member**

In `classifier_diagnostics.py`, place the additive values after `FIELD_TYPE_REJECTED` and before
legacy `ENUM_SHAPE_REJECTED`:

```python
ROUTE_ENUM_REJECTED = "ROUTE_ENUM_REJECTED"
INTENT_ENUM_REJECTED = "INTENT_ENUM_REJECTED"
PENDING_SLOT_ENUM_REJECTED = "PENDING_SLOT_ENUM_REJECTED"
IDENTIFIER_SHAPE_REJECTED = "IDENTIFIER_SHAPE_REJECTED"
ROUTE_SHAPE_REJECTED = "ROUTE_SHAPE_REJECTED"
ENUM_SHAPE_REJECTED = "ENUM_SHAPE_REJECTED"
```

Do not rename or delete any existing value.

- [ ] **Step 6: Implement one shared typed decision builder**

Add this exact internal boundary to `classifier_contracts.py`:

```python
def _build_classifier_decision_with_stage(
    *,
    route_raw: str,
    intent_raw: str | None,
    topic_id: str | None,
    coverage_id: str | None,
    slot_raw: str | None,
) -> ClassifierDecisionParseResult:
    try:
        route = ClassifierRoute(route_raw)
    except ValueError:
        return ClassifierDecisionParseResult(
            None,
            ClassifierResponseStage.ROUTE_ENUM_REJECTED,
        )

    intent: Intent | None = None
    if intent_raw is not None:
        try:
            intent = Intent(intent_raw)
        except ValueError:
            return ClassifierDecisionParseResult(
                None,
                ClassifierResponseStage.INTENT_ENUM_REJECTED,
            )
        if intent not in _SUPPORTED_INTENTS:
            return ClassifierDecisionParseResult(
                None,
                ClassifierResponseStage.INTENT_ENUM_REJECTED,
            )

    pending_slot: PendingSlot | None = None
    if slot_raw is not None:
        try:
            pending_slot = PendingSlot(slot_raw)
        except ValueError:
            return ClassifierDecisionParseResult(
                None,
                ClassifierResponseStage.PENDING_SLOT_ENUM_REJECTED,
            )

    if (
        (topic_id is not None and _IDENTIFIER_PATTERN.fullmatch(topic_id) is None)
        or (
            coverage_id is not None
            and _IDENTIFIER_PATTERN.fullmatch(coverage_id) is None
        )
    ):
        return ClassifierDecisionParseResult(
            None,
            ClassifierResponseStage.IDENTIFIER_SHAPE_REJECTED,
        )

    try:
        decision = ClassifierDecision(
            route=route,
            intent=intent,
            topic_id=topic_id,
            coverage_id=coverage_id,
            pending_slot=pending_slot,
        )
    except (TypeError, ValueError):
        return ClassifierDecisionParseResult(
            None,
            ClassifierResponseStage.ROUTE_SHAPE_REJECTED,
        )
    return ClassifierDecisionParseResult(
        decision,
        ClassifierResponseStage.ACCEPTED,
    )
```

Both canonical and provider payload paths must call this helper after their existing key/type and
provider-only `NONE` normalization. Keep the current catalog membership check after the helper;
map a mismatch only to `CATALOG_REJECTED`. Do not copy route-shape branches out of
`ClassifierDecision.__post_init__`.

- [ ] **Step 7: Run contract tests and confirm GREEN**

```powershell
apps/api/.venv/Scripts/python.exe -B -m pytest `
  apps/api/tests/llm/test_classifier_contracts.py `
  -q -p no:cacheprovider
```

Expected: all tests PASS; canonical JSON-null and provider exact-`NONE` regressions remain green.

- [ ] **Step 8: Review and commit Task 1**

```powershell
git diff --check
git diff -- apps/api/src/sejong_ai_api/llm/classifier_diagnostics.py `
  apps/api/src/sejong_ai_api/llm/classifier_contracts.py `
  apps/api/tests/llm/test_classifier_contracts.py
git add apps/api/src/sejong_ai_api/llm/classifier_diagnostics.py `
  apps/api/src/sejong_ai_api/llm/classifier_contracts.py `
  apps/api/tests/llm/test_classifier_contracts.py
git commit -m "fix(llm): refine classifier validation stages"
```

---

### Task 2: Explicit Route Matrix and Bounded Grouped Catalog Prompt

**Files:**
- Modify: `apps/api/src/sejong_ai_api/llm/classifier_prompt.py`
- Modify: `apps/api/tests/llm/test_prompt.py`
- Modify prompt assertions only: `apps/api/tests/llm/test_upstage_classifier.py`

**Interfaces:**
- Consumes: `SafeQuestion`, provider-eligible `TopicCatalog`, `max_input_chars`
- Produces unchanged:
  `build_classifier_messages(...) -> tuple[dict[str, str], ...]`
- Changes provider-only user payload:
  `cat` becomes exact-intent groups whose rows are
  `[topic_id, coverage_id, coverage_label, approved_examples]`
- Preserves: all catalog topics, exact IDs/labels, two approved examples, stable order,
  question text and existing complete-message guard

- [ ] **Step 1: Replace obsolete shorthand assertions with exact RED assertions**

Replace tests that currently require `default=NONE`, `NONE=없음`,
`NO_TOPIC_MATCH=지원` or `NEEDS_FOLLOWUP=DOMAIN?NONE:지원,,,`.

Add:

```text
test_classifier_prompt_declares_exact_closed_wire_vocabularies_without_ambiguous_defaults
test_classifier_prompt_encodes_every_complete_route_matrix_row
test_classifier_prompt_builds_supported_example_from_first_same_catalog_row
test_classifier_prompt_includes_exact_all_none_scope_gap_example
test_classifier_prompt_forbids_none_translations_null_and_explanatory_output
```

The first test must assert the system message contains every exact supported intent and every
pending slot through the complete matrix, while these strings are absent:

```python
("default=NONE", "NONE=없음", "NO_TOPIC_MATCH=지원", "DOMAIN?NONE:지원,,,")
```

- [ ] **Step 2: Add exact RED tests for the grouped catalog**

Update the governed catalog expectations to require:

```python
payload["cat"] == {
    intent.value: [
        [
            topic.record.public_id,
            topic.coverage.coverage_id,
            topic.coverage.coverage_label,
            list(topic.record.question_examples[:2]),
        ]
        for topic in catalog.topics
        if topic.record.category is intent
    ]
    for intent in (
        Intent.MOVE_IN_RESIDENT_REGISTRATION,
        Intent.CERTIFICATE_ISSUANCE,
        Intent.BULKY_WASTE,
        Intent.LOCAL_TAX_GENERAL,
    )
    if any(topic.record.category is intent for topic in catalog.topics)
}
```

Assert every original public ID, coverage ID, coverage label and first two approved examples occurs
exactly once, while `service_name`, source, answer, procedure, office, fee and caution are absent.

- [ ] **Step 3: Add deterministic wire-example and 4,096 RED tests**

Require:

```python
first = catalog.topics[0]
assert payload["ex"] == [
    [
        "SUPPORTED",
        first.record.category.value,
        first.record.public_id,
        first.coverage.coverage_id,
        "NONE",
    ],
    ["CIVIC_SCOPE_GAP", "NONE", "NONE", "NONE", "NONE"],
]
```

Add `test_real_governed_20_catalog_with_256_character_question_fits_route_matrix_guard`.
Build a safe question of 256 Korean characters and assert the complete estimate is `<= 4096`.
Retain the existing oversized 1,025-character rejection and explicit over-4,096 fail-closed tests.
Also require the system message to contain this literal provider grammar:

```text
cat={intent:[[topic_id,coverage_id,coverage_label,approved_examples]]}
SUPPORTED intent=cat group key; topic_id/coverage_id=same row
```

This assertion prevents the compact input format from becoming a new provider ambiguity.

- [ ] **Step 4: Run prompt tests and confirm RED**

```powershell
apps/api/.venv/Scripts/python.exe -B -m pytest `
  apps/api/tests/llm/test_prompt.py `
  apps/api/tests/llm/test_upstage_classifier.py::test_prompt_defines_supported_boundary_and_closed_route_meanings `
  apps/api/tests/llm/test_upstage_classifier.py::test_prompt_defines_all_closed_pending_slots_and_route_shapes `
  apps/api/tests/llm/test_upstage_classifier.py::test_real_governed_20_catalog_with_256_chars_reaches_transport_and_ledger `
  apps/api/tests/llm/test_upstage_classifier.py::test_prompt_over_4096_estimate_is_rejected_before_transport_and_reservation `
  -q -p no:cacheprovider
```

Expected: shorthand and payload-shape tests fail. The current 20-topic/256-character baseline is
4,093, so simply appending the matrix must not be accepted as GREEN.

- [ ] **Step 5: Implement the exact compact system matrix**

Replace the old system message with one bounded string that specifies:

```text
keys: route,intent,topic_id,coverage_id,pending_slot
all five values are strings
no extra key, prose or Markdown
NONE is exact uppercase ASCII; 없음/none/null/empty are forbidden
provider intents: the four supported intents or NONE
cat={intent:[[topic_id,coverage_id,coverage_label,approved_examples]]}
SUPPORTED intent=cat group key; topic_id/coverage_id=same row
valid tuples in key order:
SUPPORTED|catalog intent|same-row topic_id|same-row coverage_id|NONE
NO_TOPIC_MATCH|supported intent|NONE|NONE|NONE
CIVIC_SCOPE_GAP|NONE|NONE|NONE|NONE
NON_CIVIC|NONE|NONE|NONE|NONE
NEEDS_FOLLOWUP|NONE|NONE|NONE|DOMAIN
NEEDS_FOLLOWUP|supported intent|NONE|NONE|TOPIC_CHOICE
NEEDS_FOLLOWUP|CERTIFICATE_ISSUANCE|NONE|NONE|CERTIFICATE_KIND
NEEDS_FOLLOWUP|supported intent|NONE|NONE|REGION
NEEDS_FOLLOWUP|BULKY_WASTE|NONE|NONE|WASTE_ITEM
```

The actual string may use `|` and `;` delimiters, but it must retain every literal above and must
not reintroduce translated sentinel/default shorthand.

- [ ] **Step 6: Implement grouped catalog and deterministic examples**

Add:

```python
_PROVIDER_INTENT_ORDER = (
    Intent.MOVE_IN_RESIDENT_REGISTRATION,
    Intent.CERTIFICATE_ISSUANCE,
    Intent.BULKY_WASTE,
    Intent.LOCAL_TAX_GENERAL,
)


def _build_grouped_catalog(catalog: TopicCatalog) -> dict[str, list[list[object]]]:
    grouped: dict[str, list[list[object]]] = {}
    for intent in _PROVIDER_INTENT_ORDER:
        rows = [
            [
                topic.record.public_id,
                topic.coverage.coverage_id,
                topic.coverage.coverage_label,
                list(topic.record.question_examples[:2]),
            ]
            for topic in catalog.topics
            if topic.record.category is intent
        ]
        if rows:
            grouped[intent.value] = rows
    return grouped
```

Use `catalog.topics[0]` for the first example and include the all-`NONE` scope-gap example.
Do not sort or sample a second time; `TopicCatalog` already guarantees stable public-ID order.
Do not include `service_name` in this provider-only payload.

- [ ] **Step 7: Run prompt and transport-guard tests and confirm GREEN**

Run the Step 4 command again.

Expected: all selected tests PASS; governed 19/20 rows and approved examples are complete,
20 topics plus 256 characters is `<=4096`, and an over-bound message makes zero transport and
ledger reservations.

- [ ] **Step 8: Review and commit Task 2**

```powershell
git diff --check
git add apps/api/src/sejong_ai_api/llm/classifier_prompt.py `
  apps/api/tests/llm/test_prompt.py `
  apps/api/tests/llm/test_upstage_classifier.py
git commit -m "fix(llm): make classifier route matrix explicit"
```

---

### Task 3: Production-Wire Oracle, Exactly-Once Observer and Aggregate Report Regression

**Files:**
- Modify: `apps/api/tests/llm/test_upstage_classifier.py`
- Modify: `scripts/tests/test_run_hybrid_rag_actual.py`
- Preserve: `apps/api/src/sejong_ai_api/llm/upstage_classifier.py`
- Preserve: `scripts/run_hybrid_rag_actual.py`

**Interfaces:**
- Consumes:
  `parse_classifier_wire_decision_with_stage(bytes, TopicCatalog)`,
  additive `ClassifierResponseStage`
- Produces: offline test evidence only
- Preserves: current five-string response schema, retry 0, observer signature and report path

- [ ] **Step 1: Expand the transport stage matrix**

In `test_upstage_classifier.py`, replace the single generic enum/shape controlled response with
five controlled responses that terminate at:

```text
ROUTE_ENUM_REJECTED
INTENT_ENUM_REJECTED
PENDING_SLOT_ENUM_REJECTED
IDENTIFIER_SHAPE_REJECTED
ROUTE_SHAPE_REJECTED
```

For each response assert:

```python
assert decision is None
assert observed == [expected_stage]
assert all(type(stage) is ClassifierResponseStage for stage in observed)
```

Keep the observer-failure isolation test and assert the captured request schema still has only
five string properties with no enum or catalog IDs.

- [ ] **Step 2: Add a test-only canonical wire serializer**

In `scripts/tests/test_run_hybrid_rag_actual.py`, add:

```python
def _oracle_wire_payload(decision: ClassifierDecision) -> bytes:
    def nullable(value: object | None) -> str:
        if value is None:
            return "NONE"
        return value.value if hasattr(value, "value") else str(value)

    return json.dumps(
        {
            "route": decision.route.value,
            "intent": nullable(decision.intent),
            "topic_id": nullable(decision.topic_id),
            "coverage_id": nullable(decision.coverage_id),
            "pending_slot": nullable(decision.pending_slot),
        },
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
```

This helper is test-only and must not write or print the payload.

- [ ] **Step 3: Round-trip all nine provider actual-subset oracles**

Add
`test_actual_provider_subset_oracles_round_trip_through_production_wire_parser`.
Select exactly the actual-subset fixtures whose `expected_provider_use` is 1:

```text
HR-001, HR-002, HR-003, HR-004, HR-007, HR-008, HR-037, HR-039, HR-040
```

For each, convert `_oracle_decision()` into wire bytes, pass it through
`parse_classifier_wire_decision_with_stage()`, and assert `ACCEPTED` plus semantic equality.

- [ ] **Step 4: Prove the scope-gap wire/public boundary**

Add `test_scope_gap_out_of_scope_fixture_uses_civic_scope_gap_all_none_provider_wire`.
For HR-037/039/040 assert the provider bytes decode to:

```json
{
  "route": "CIVIC_SCOPE_GAP",
  "intent": "NONE",
  "topic_id": "NONE",
  "coverage_id": "NONE",
  "pending_slot": "NONE"
}
```

Also assert the fixture's public expected intent remains `OUT_OF_SCOPE`; it is server
post-processing, not provider intent.

- [ ] **Step 5: Prove fixed aggregate field order and non-retention**

Extend the controlled-double report tests to require each new
`provider_stage_<name>_count` field exactly once in enum order. Require legacy
`provider_stage_enum_shape_rejected_count` to remain present and zero on new controlled responses.
Assert report/stdout contains no fixture-stage table, provider payload, question, invalid value,
status detail, exception, key or DSN.

- [ ] **Step 6: Run focused transport and runner tests**

```powershell
apps/api/.venv/Scripts/python.exe -B -m pytest `
  apps/api/tests/llm/test_upstage_classifier.py `
  -q -p no:cacheprovider

apps/api/.venv/Scripts/python.exe -B -m pytest `
  scripts/tests/test_run_hybrid_rag_actual.py `
  -q -p no:cacheprovider
```

Expected: both commands PASS with zero network/provider calls. Production
`upstage_classifier.py` and `run_hybrid_rag_actual.py` remain byte-unchanged.

- [ ] **Step 7: Review and commit Task 3**

```powershell
git diff --check
git diff --name-status
git add apps/api/tests/llm/test_upstage_classifier.py `
  scripts/tests/test_run_hybrid_rag_actual.py
git commit -m "test(llm): prove corrected classifier wire"
```

---

### Task 4: Area Regression, Version Integration and Reproducible Evidence

**Files:**
- Modify: `versions/manifest.json`
- Modify: `CHANGELOG.md`
- Modify: `TASKS.md`
- Modify: `docs/00_SOURCE_OF_TRUTH.md`
- Modify: `docs/source-of-truth/TEAM_DECISIONS.md`
- Modify: `docs/11_AMBIGUITY_REGISTER.md`
- Modify: `docs/12_VERSIONING_AND_RELEASES.md`
- Modify: `docs/decisions/DECISION_LOG.md`
- Create: A-073 offline implementation note with `scripts/new_implementation_note.py`
- Modify: `docs/implementation-notes/INDEX.md`
- Preserve: ADR-0027, public contracts, DB/data and dependency files

**Interfaces:**
- Consumes: committed Tasks 1~3
- Produces:
  application `0.12.4-classifier-wire-diagnostics`,
  prompt `0.4.3-explicit-route-matrix`,
  tests `2.1.7-classifier-wire-correction`
- Preserves: API/shared/Web/DB/data/dependency versions

- [ ] **Step 1: Run the complete classifier/Hybrid RAG area suite**

```powershell
Push-Location apps/api
.venv/Scripts/python.exe -B -m pytest `
  tests/llm/test_classifier_contracts.py `
  tests/llm/test_prompt.py `
  tests/llm/test_upstage_classifier.py `
  tests/chat/test_hybrid_rag_uat.py `
  tests/chat/test_official_examples.py `
  tests/chat/test_classification.py `
  tests/chat/test_service.py `
  tests/test_local.py `
  -q -p no:cacheprovider
Pop-Location
```

Expected: all tests PASS and no new skip is introduced.

- [ ] **Step 2: Run controlled-double evaluation regressions**

```powershell
apps/api/.venv/Scripts/python.exe -B -m pytest `
  scripts/tests/test_run_hybrid_rag_actual.py `
  scripts/tests/test_upstage_classifier_evaluation.py `
  -q -p no:cacheprovider
```

Expected: PASS with network/provider call count and cost both zero.

- [ ] **Step 3: Run formatter, lint and type checks**

```powershell
Push-Location apps/api
.venv/Scripts/python.exe -B -m ruff format --check src tests
.venv/Scripts/python.exe -B -m ruff check src tests
.venv/Scripts/python.exe -B -m mypy src tests
Pop-Location
apps/api/.venv/Scripts/python.exe -B -m ruff format --check `
  scripts/tests/test_run_hybrid_rag_actual.py
apps/api/.venv/Scripts/python.exe -B -m ruff check `
  scripts/tests/test_run_hybrid_rag_actual.py
```

Expected: all exit 0. The approved Mypy scope remains `apps/api/src` and `apps/api/tests`;
the controlled CLI test is explicitly covered by direct Ruff format/lint plus pytest and does not
silently expand the repository typecheck contract. If format check fails only in changed Python
files, run:

```powershell
apps/api/.venv/Scripts/python.exe -B -m ruff format `
  apps/api/src/sejong_ai_api/llm/classifier_diagnostics.py `
  apps/api/src/sejong_ai_api/llm/classifier_contracts.py `
  apps/api/src/sejong_ai_api/llm/classifier_prompt.py `
  apps/api/tests/llm/test_classifier_contracts.py `
  apps/api/tests/llm/test_prompt.py `
  apps/api/tests/llm/test_upstage_classifier.py `
  scripts/tests/test_run_hybrid_rag_actual.py
```

Then rerun all three checks and record both the initial failure and final result.
Also rerun both direct Ruff checks for `scripts/tests/test_run_hybrid_rag_actual.py`.

- [ ] **Step 4: Advance only the approved implementation versions**

Set:

```text
application: 0.12.3-structured-classifier-wire
          -> 0.12.4-classifier-wire-diagnostics
prompt_set: 0.4.2-exact-five-key-schema
         -> 0.4.3-explicit-route-matrix
test_suite: 2.1.6-structured-classifier-wire
         -> 2.1.7-classifier-wire-correction
documentation: 2.30.5
            -> 2.30.6
```

Keep product spec, repository guidance, Web, API, shared contracts, DB schema, official/mock data
and dependency axes unchanged.

- [ ] **Step 5: Synchronize authority and implementation evidence**

Record the exact test counts and commits. Set A-073 to
`Implemented offline / actual exact-one approval pending`. Add a new decision row for the offline
implementation without modifying D-117. ADR-0027 remains unchanged because server authority,
provider boundary and retention architecture do not change.

Generate and fully complete the implementation note:

```powershell
python -B scripts/new_implementation_note.py `
  --title "A-073 classifier route matrix와 refined diagnostics offline 구현" `
  --task-id A-073-CLASSIFIER-ENUM-SHAPE-CORRECTION `
  --type implementation-provider-offline
```

- [ ] **Step 6: Run documentation and security checks**

```powershell
python -B scripts/check_repository_docs.py
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File scripts/check_secret_patterns.ps1 -RepositoryRoot .
git diff --check
```

Expected: documentation PASS, secret findings 0 and whitespace errors 0.

- [ ] **Step 7: Review scope and commit Task 4**

```powershell
git diff --name-status 32344a5...HEAD
git status --short
```

Allowed product paths are only the three LLM modules and the three approved test files plus
`scripts/tests/test_run_hybrid_rag_actual.py`. There must be no `.env`, provider report, contract,
DB/migration, official/mock data, package or lockfile change.

```powershell
git add versions/manifest.json CHANGELOG.md TASKS.md `
  docs/00_SOURCE_OF_TRUTH.md docs/source-of-truth/TEAM_DECISIONS.md `
  docs/11_AMBIGUITY_REGISTER.md docs/12_VERSIONING_AND_RELEASES.md `
  docs/decisions/DECISION_LOG.md docs/implementation-notes
git commit -m "docs(llm): integrate classifier correction evidence"
```

---

### Task 5: One Offline Root Gate and Clean-Source Review

**Files:**
- Modify only when recording exact evidence:
  A-073 implementation note, `docs/implementation-notes/INDEX.md`,
  `CHANGELOG.md`, `TASKS.md`, authority/version documents
- Preserve: product code after the reviewed Tasks 1~3 commits
- Preserve: current D-117 report and all archives

**Interfaces:**
- Consumes: committed Tasks 1~4
- Produces: clean full source SHA eligible for a separate actual decision

- [ ] **Step 1: Run the offline root gate exactly once**

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File scripts/verify.ps1 -Offline
```

Expected: every executed stage PASS. If the wrapper stops on an environment-only stage, record the
exact stage/reason and wrapper as FAIL; do not relabel constituent checks as an aggregate PASS and
do not rerun merely to obtain a green label.

- [ ] **Step 2: Run final immutable-scope checks**

```powershell
python -B scripts/check_repository_docs.py
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File scripts/check_secret_patterns.ps1 -RepositoryRoot .
git diff --check
git status --short
```

Expected: docs PASS, secret findings 0, diff errors 0. Record any explicitly documented
environment-only gate accurately.

- [ ] **Step 3: Request independent scope and code review**

Use `superpowers:requesting-code-review` against `32344a5...HEAD`. The review must confirm:

```text
shared decision authority is not duplicated
five-stage first-failure precedence is exact
no provider value can cross the observer/report boundary
prompt preserves all topic/coverage/approved-example semantics
20-topic + 256-character guard is <=4096
five-string response schema is unchanged
API/DB/data/dependency and D-117 evidence are unchanged
```

Resolve every Critical/Important finding with focused RED/GREEN and one bounded re-review.

- [ ] **Step 4: Commit evidence-only corrections and recover a clean tree**

When Task 5 evidence changes tracked documents:

```powershell
git add CHANGELOG.md TASKS.md versions/manifest.json `
  docs/00_SOURCE_OF_TRUTH.md docs/source-of-truth/TEAM_DECISIONS.md `
  docs/11_AMBIGUITY_REGISTER.md docs/12_VERSIONING_AND_RELEASES.md `
  docs/decisions/DECISION_LOG.md docs/implementation-notes
git commit -m "docs(llm): close classifier correction offline gate"
python -B scripts/check_repository_docs.py
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File scripts/check_secret_patterns.ps1 -RepositoryRoot .
git diff --check
git status --short
```

Expected: all three checks exit 0 and `git status --short` prints nothing.

- [ ] **Step 5: Record the clean SHA and stop**

```powershell
git rev-parse HEAD
```

Report the full SHA, exact area/root evidence and provider calls/cost 0. Do not continue to Task 6
without this exact new user approval:

```text
A-073 corrective actual 1회 실행 승인
```

General plan or implementation approval does not authorize Task 6.

---

### Task 6: Separately Human-Gated Corrective Actual

**Files:**
- Archive:
  `docs/test-reports/CHAT-HYBRID-RAG-001-UPSTAGE-ACTUAL.md`
  to
  `docs/test-reports/archive/CHAT-HYBRID-RAG-001-UPSTAGE-ACTUAL-20260729-D117-ENUM-SHAPE-REJECTED-FAIL.md`
- Create via runner:
  `docs/test-reports/CHAT-HYBRID-RAG-001-UPSTAGE-ACTUAL.md`
- Modify after the run: authority, task, version, changelog and implementation-note evidence

**Interfaces:**
- Consumes: clean Task 5 SHA and exact Task 6 human approval
- Produces: one aggregate PASS/FAIL report; never provider/question content

- [ ] **Step 1: Verify approval, clean source and D-117 hash**

Require the exact Task 6 approval. Verify:

```powershell
git status --short
Get-FileHash -Algorithm SHA256 `
  -LiteralPath docs/test-reports/CHAT-HYBRID-RAG-001-UPSTAGE-ACTUAL.md
```

Expected D-117 SHA-256:

```text
1749F83ADF52FB4BEB5970272204C424CB8F13545A548CAF141C998861C9F8BD
```

- [ ] **Step 2: Archive D-117 byte-for-byte and commit the absent-current baseline**

```powershell
$source = "docs/test-reports/CHAT-HYBRID-RAG-001-UPSTAGE-ACTUAL.md"
$archive = "docs/test-reports/archive/CHAT-HYBRID-RAG-001-UPSTAGE-ACTUAL-20260729-D117-ENUM-SHAPE-REJECTED-FAIL.md"
Copy-Item -LiteralPath $source -Destination $archive
$sourceHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $source).Hash
$archiveHash = (Get-FileHash -Algorithm SHA256 -LiteralPath $archive).Hash
if ($sourceHash -ne $archiveHash) { throw "D117_ARCHIVE_HASH_MISMATCH" }
Remove-Item -LiteralPath $source
if (Test-Path -LiteralPath $source) { throw "CURRENT_REPORT_MUST_BE_ABSENT" }
if (Test-Path -LiteralPath "$source.run.lock") { throw "ACTUAL_RUN_LOCK_PRESENT" }
git add docs/test-reports
git commit -m "docs(llm): archive D-117 enum-shape evidence"
git status --short
```

Expected: archive hash equals the source hash and the tree is clean with the standard current
report absent.

- [ ] **Step 3: Run a value-free readiness check, then execute exactly once in one restoration block**

Use one PowerShell session and this complete block. It temporarily overrides only the three
process-level mode flags, never edits or prints `.env`, and restores the prior process values in
`finally`. The readiness process calls the same pinned-input and exact-settings validators as the
runner but never acquires the report lease, writes evidence, constructs a client or calls a
provider. Therefore an invalid local profile cannot consume the one-shot report path.

```powershell
$priorClassifierMode = [Environment]::GetEnvironmentVariable(
  "UPSTAGE_CLASSIFIER_MODE", "Process"
)
$priorGroundedMode = [Environment]::GetEnvironmentVariable(
  "UPSTAGE_GROUNDED_CHAT_MODE", "Process"
)
$priorSyntheticMode = [Environment]::GetEnvironmentVariable(
  "UPSTAGE_SYNTHETIC_EVALUATION_MODE", "Process"
)

function Assert-LastExit([string]$stage) {
  if ($LASTEXITCODE -ne 0) { throw $stage }
}

try {
  $env:UPSTAGE_CLASSIFIER_MODE = "true"
  $env:UPSTAGE_GROUNDED_CHAT_MODE = "true"
  $env:UPSTAGE_SYNTHETIC_EVALUATION_MODE = "false"

  python -B scripts/check_repository_docs.py
  Assert-LastExit "DOCS_PREFLIGHT_FAILED"
  powershell.exe -NoProfile -ExecutionPolicy Bypass `
    -File scripts/check_secret_patterns.ps1 -RepositoryRoot .
  Assert-LastExit "SECRET_PREFLIGHT_FAILED"
  git diff --check
  Assert-LastExit "DIFF_PREFLIGHT_FAILED"

  apps/api/.venv/Scripts/python.exe -B -c @'
import scripts.run_hybrid_rag_actual as runner

runner._require_offline_gate()
runner._require_clean_secret_scan()
runner._require_protected_inputs_clean()
settings = runner.load_upstage_classifier_settings()
if settings is None:
    raise SystemExit("HYBRID_RAG_ACTUAL_READINESS_INVALID")
runner._validate_settings(settings)
runner._load_pinned_inputs()
print("HYBRID_RAG_ACTUAL_READINESS_OK")
'@
  Assert-LastExit "VALUE_FREE_READINESS_FAILED"

  apps/api/.venv/Scripts/python.exe -B `
    scripts/run_hybrid_rag_actual.py `
    --fixture apps/api/tests/chat/fixtures/hybrid-rag-uat.v1.json `
    --report docs/test-reports/CHAT-HYBRID-RAG-001-UPSTAGE-ACTUAL.md
  $actualExit = $LASTEXITCODE
} finally {
  if ($null -eq $priorClassifierMode) {
    Remove-Item Env:UPSTAGE_CLASSIFIER_MODE -ErrorAction SilentlyContinue
  } else {
    $env:UPSTAGE_CLASSIFIER_MODE = $priorClassifierMode
  }
  if ($null -eq $priorGroundedMode) {
    Remove-Item Env:UPSTAGE_GROUNDED_CHAT_MODE -ErrorAction SilentlyContinue
  } else {
    $env:UPSTAGE_GROUNDED_CHAT_MODE = $priorGroundedMode
  }
  if ($null -eq $priorSyntheticMode) {
    Remove-Item Env:UPSTAGE_SYNTHETIC_EVALUATION_MODE -ErrorAction SilentlyContinue
  } else {
    $env:UPSTAGE_SYNTHETIC_EVALUATION_MODE = $priorSyntheticMode
  }
}

if ($actualExit -ne 0) { throw "ACTUAL_FAILED_WITH_EVIDENCE" }
```

Expected readiness stdout is the constant
`HYBRID_RAG_ACTUAL_READINESS_OK`; it prints no setting or secret. Never execute the runner command
a second time, regardless of exit code or result. If readiness fails, stop with the canonical
report still absent and do not create or delete evidence.

- [ ] **Step 4: Inspect aggregate evidence only**

Expected PASS:

```text
selected 20
skip 0
provider-free 11
outbound 9
HTTP 2xx / usage / terminal-stage total 9
ACCEPTED 9
provider route/topic match 9
all refined rejection stages 0
retry 0
cost below VAT-inclusive USD 0.20
```

If any condition fails, record FAIL and stop. Do not inspect provider body, alter prompt/schema or
run a corrective second call.

- [ ] **Step 5: Verify restoration, record evidence and commit**

Verify the process mode values were restored by `finally`; the tracked/ignored defaults remain
false/false. Verify lock absent, run docs/secret/diff checks, then update
authority/version/task/note documents with aggregate facts only.

```powershell
git add docs/test-reports docs/implementation-notes `
  docs/decisions/DECISION_LOG.md docs/00_SOURCE_OF_TRUTH.md `
  docs/source-of-truth/TEAM_DECISIONS.md docs/11_AMBIGUITY_REGISTER.md `
  docs/12_VERSIONING_AND_RELEASES.md TASKS.md versions/manifest.json CHANGELOG.md
git commit -m "docs(llm): record A-073 corrective actual"
```

Do not push or merge without a separate user instruction.

---

## Plan Self-Review

### Specification coverage

- exact route/intents/pending matrix and literal `NONE`: Task 2
- request-local dynamic same-row example and all-`NONE` example: Task 2
- no topic/catalog truncation or sampling: Task 2
- 4,096 guard without changing public input contract: Task 2
- five refined value-free first-failure stages: Task 1
- one shared typed builder and `ClassifierDecision` authority: Task 1
- canonical/public parser and legacy report compatibility: Task 1
- observer exactly-once and value-free aggregate-only evidence: Task 3
- nine actual-subset production wire round trips: Task 3
- `OUT_OF_SCOPE` public versus provider `NONE` boundary: Task 3
- focused/area/root offline gates and independent review: Tasks 1~5
- version, authority and implementation-note integration: Task 4
- D-117 immutable preservation and report-absence preflight: Task 6
- actual separately human-gated and one-shot: Tasks 5~6

### Placeholder scan

Every task contains exact paths, names, code or data shapes, commands, expected RED/GREEN behavior,
version values and stop conditions. The plan has no deferred implementation instruction.

### Type consistency

- Task 1 produces the shared
  `_build_classifier_decision_with_stage(...) -> ClassifierDecisionParseResult`.
- Both parser entry points consume that helper and keep their current public signatures.
- Task 2 keeps
  `build_classifier_messages(...) -> tuple[dict[str, str], ...]`.
- Task 3 consumes existing
  `parse_classifier_wire_decision_with_stage(bytes, TopicCatalog)`.
- The observer continues to receive one `ClassifierResponseStage`; the runner continues to derive
  aggregate fields from that enum.

## Execution Handoff

Plan complete and saved to
`docs/superpowers/plans/2026-07-29-upstage-classifier-explicit-route-matrix-and-refined-diagnostics.md`.

1. **Subagent-Driven (recommended):** fresh implementation worker per Tasks 1~3 with
   specification and quality review; main agent owns Tasks 4~5 and shared documents.
2. **Inline Execution:** execute Tasks 1~5 in this session with plan checkpoints.

Task 6 is excluded from both choices until the separate exact-one human approval.
