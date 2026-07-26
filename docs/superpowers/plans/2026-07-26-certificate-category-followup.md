# Certificate Category Follow-up Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Status:** Paused pending an integrated hybrid-taxonomy written specification.
> Q-SCOPE-001=A and Q-CLASS-001=A are resolved, but the certificate slice touches the same
> classifier/service boundary and must be integrated or explicitly unpaused first.

**Goal:** Replace the repeating generic certificate category question with a server-owned five-option certificate FOLLOWUP that leads into the existing ACTIVE-only answer path.

**Architecture:** The deterministic classifier represents generic certificate language as `CERTIFICATE_ISSUANCE + followup_required`. The chat service maps that typed outcome to a bounded server option set and a certificate context token without repository reads or failure storage. The Web renders intent-specific copy and sends the selected option through the existing idempotent, memory-only context flow.

**Tech Stack:** Python 3.12.13, FastAPI/Pydantic domain core, pytest 9.1.1, TypeScript, React 19, Next.js 16.2.10, Vitest 4.1.10, pnpm 11.13.0.

## Global Constraints

- No new production dependency.
- No external LLM/provider call.
- No DB migration, seed, reset, purge or official-data mutation.
- No public deployment or remote DB work.
- Public OpenAPI response shape and generated shared types remain unchanged.
- FOLLOWUP stores no question text and creates no failed-question row.
- Unsupported compound certificates remain OUT_OF_SCOPE.
- Only ACTIVE/OFFICIAL KB may produce SUCCESS after option selection.
- Preserve the primary checkout's user-generated `apps/web/next-env.d.ts` change.
- Every production change follows RED → observed expected failure → minimal GREEN → focused regression.

---

### Task 1: Represent generic certificate ambiguity in the deterministic classifier

**Files:**
- Modify: `apps/api/tests/chat/test_classification.py:11-145`
- Modify: `apps/api/src/sejong_ai_api/chat/classification.py:152-215`

**Interfaces:**
- Consumes: privacy-proven `SafeQuestion`
- Produces: `ClassificationOutcome(Intent.CERTIFICATE_ISSUANCE, True, None)` for generic certificate language
- Preserves: specific supported intent outcomes and `Intent.OUT_OF_SCOPE` for unsupported certificate domains

- [ ] **Step 1: Write the failing classification tests**

Add literal expectations:

```python
def test_generic_certificate_request_requires_certificate_followup() -> None:
    outcome = classify_question(safe_question("증명서 발급해야해"))

    assert outcome.intent is Intent.CERTIFICATE_ISSUANCE
    assert outcome.followup_required is True
    assert outcome.fallback_reason is None


@pytest.mark.parametrize(
    ("question", "expected_intent", "expected_followup", "expected_reason"),
    [
        ("졸업증명서 발급", Intent.OUT_OF_SCOPE, False, FallbackReason.OUT_OF_SCOPE),
        ("주민등록등본 발급", Intent.CERTIFICATE_ISSUANCE, False, None),
        ("납세증명서 발급", Intent.LOCAL_TAX_GENERAL, False, None),
    ],
)
def test_certificate_followup_preserves_specific_and_unsupported_priority(
    question: str,
    expected_intent: Intent,
    expected_followup: bool,
    expected_reason: FallbackReason | None,
) -> None:
    outcome = classify_question(safe_question(question))

    assert outcome.intent is expected_intent
    assert outcome.followup_required is expected_followup
    assert outcome.fallback_reason is expected_reason
```

- [ ] **Step 2: Run the classifier RED test**

Run:

```powershell
apps/api/.venv/Scripts/python.exe -m pytest `
  apps/api/tests/chat/test_classification.py `
  -q
```

Expected: the generic certificate test fails because actual intent is `UNKNOWN`; all priority cases remain green.

- [ ] **Step 3: Implement the minimal classifier branch**

Adjust the outcome invariant:

```python
if self.followup_required:
    if self.intent not in _SUPPORTED_INTENTS | {Intent.UNKNOWN} or self.fallback_reason is not None:
        raise ValueError("CLASSIFICATION_OUTCOME_INVALID")
    return
```

After score calculation and the existing no-score OUT_OF_SCOPE check, add the bounded cue:

```python
if highest_score == 0 and "증명서" in compact:
    return ClassificationOutcome(
        Intent.CERTIFICATE_ISSUANCE,
        followup_required=True,
        fallback_reason=None,
    )
```

Keep this branch after explicit OUT_OF_SCOPE matching and do not add `증명서` to `_INTENT_TERMS`.

- [ ] **Step 4: Run the classifier GREEN test**

Run the Step 2 command.

Expected: all tests in `test_classification.py` pass.

- [ ] **Step 5: Commit the classifier behavior**

```powershell
git add apps/api/src/sejong_ai_api/chat/classification.py apps/api/tests/chat/test_classification.py
git commit -m "fix(chat): classify generic certificate followup"
```

---

### Task 2: Add the server-owned certificate follow-up option set

**Files:**
- Modify: `apps/api/tests/chat/test_response.py:137-159`
- Modify: `apps/api/src/sejong_ai_api/chat/response.py:15-44`

**Interfaces:**
- Consumes: internal `FollowupOptionId`
- Produces: exact Korean labels in `FollowupResponse.followup_options`
- Preserves: rejection of every non-allowlisted option ID

- [ ] **Step 1: Write the failing response-builder test**

Add:

```python
def test_certificate_followup_uses_only_the_five_approved_kb_topics() -> None:
    response = build_followup_response(
        request_id=REQUEST_ID,
        intent=Intent.CERTIFICATE_ISSUANCE,
        confidence=None,
        option_ids=(
            "certificate.resident-copy",
            "certificate.resident-abstract",
            "certificate.copy-vs-abstract",
            "certificate.resident-register-inspection",
            "certificate.unmanned-kiosk",
        ),
        context_token="signed-certificate-followup",
    )

    assert response.intent == "CERTIFICATE_ISSUANCE"
    assert response.followup_options == [
        "주민등록등본 발급",
        "주민등록초본 발급",
        "등본과 초본의 차이",
        "주민등록표 열람",
        "무인민원발급기 이용",
    ]
```

- [ ] **Step 2: Run the response RED test**

Run:

```powershell
apps/api/.venv/Scripts/python.exe -m pytest `
  apps/api/tests/chat/test_response.py `
  -q
```

Expected: `FOLLOWUP_OPTION_INVALID`.

- [ ] **Step 3: Extend the closed internal option type and label map**

Extend `FollowupOptionId` and `_FOLLOWUP_LABELS` with exactly:

```python
"certificate.resident-copy": "주민등록등본 발급",
"certificate.resident-abstract": "주민등록초본 발급",
"certificate.copy-vs-abstract": "등본과 초본의 차이",
"certificate.resident-register-inspection": "주민등록표 열람",
"certificate.unmanned-kiosk": "무인민원발급기 이용",
```

Do not expose the internal IDs in OpenAPI or context-token claims.

- [ ] **Step 4: Run the response GREEN test**

Run the Step 2 command.

Expected: all response tests pass, including rejection of citizen-controlled values.

- [ ] **Step 5: Commit the response option set**

```powershell
git add apps/api/src/sejong_ai_api/chat/response.py apps/api/tests/chat/test_response.py
git commit -m "feat(chat): add certificate followup options"
```

---

### Task 3: Route typed certificate ambiguity through a text-free FOLLOWUP

**Files:**
- Modify: `apps/api/tests/chat/test_service.py:287-302`
- Modify: `apps/api/src/sejong_ai_api/chat/service.py:67-91`
- Modify: `apps/api/src/sejong_ai_api/chat/service.py:251-327`

**Interfaces:**
- Consumes: `ClassificationOutcome` from Task 1 and option IDs from Task 2
- Produces: certificate-intent `FollowupResponse`, signed certificate context and text-free FOLLOWUP interaction
- Preserves: contextual short-detail recovery, unknown four-category FOLLOWUP and failure-storage rules

- [ ] **Step 1: Write the failing service test for the initial certificate FOLLOWUP**

Add:

```python
@pytest.mark.asyncio
async def test_generic_certificate_question_returns_bounded_followup_without_reads() -> None:
    repository = FakeRepository(fail_reads=True)

    response = await service(repository).answer(ChatRequest(question="증명서 발급해야해"))

    assert response.answer_status == "FOLLOWUP"
    assert response.intent == Intent.CERTIFICATE_ISSUANCE.value
    assert response.followup_options == [
        "주민등록등본 발급",
        "주민등록초본 발급",
        "등본과 초본의 차이",
        "주민등록표 열람",
        "무인민원발급기 이용",
    ]
    assert response.context_token is not None
    decoded = ContextTokenCodec(secret=b"x" * 32, clock=lambda: 1_000).read(
        response.context_token
    )
    assert decoded is not None
    assert decoded.last_intent == Intent.CERTIFICATE_ISSUANCE.value
    assert decoded.answer_status == "FOLLOWUP"
    assert repository.active_intents == []
    assert repository.office_queries == []
    assert len(repository.events) == 1
    assert repository.events[0].intent is Intent.CERTIFICATE_ISSUANCE
    assert repository.events[0].answer_status is AnswerStatus.FOLLOWUP
    assert repository.events[0].masked_question is None
```

- [ ] **Step 2: Write the failing non-loop test for all five labels**

Add:

```python
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "option",
    [
        "주민등록등본 발급",
        "주민등록초본 발급",
        "등본과 초본의 차이",
        "주민등록표 열람",
        "무인민원발급기 이용",
    ],
)
async def test_certificate_option_never_returns_the_same_category_followup(option: str) -> None:
    response = await service(FakeRepository()).answer(ChatRequest(question=option))

    assert response.intent == Intent.CERTIFICATE_ISSUANCE.value
    assert response.answer_status != "FOLLOWUP"
```

With no fake ACTIVE record these options safely produce `INSUFFICIENT_GROUNDING`; the assertion
only protects against the repeated-category loop.

- [ ] **Step 3: Run the service RED tests**

Run:

```powershell
apps/api/.venv/Scripts/python.exe -m pytest `
  apps/api/tests/chat/test_service.py `
  -q
```

Expected: the initial generic certificate test fails because the service enters retrieval or
returns the old four-category response.

- [ ] **Step 4: Split general and certificate option constants**

Define:

```python
_GENERAL_FOLLOWUP_OPTIONS = (
    "intent.move-in",
    "intent.certificate",
    "intent.bulky-waste",
    "intent.local-tax",
)
_CERTIFICATE_FOLLOWUP_OPTIONS = (
    "certificate.resident-copy",
    "certificate.resident-abstract",
    "certificate.copy-vs-abstract",
    "certificate.resident-register-inspection",
    "certificate.unmanned-kiosk",
)
```

Use one closed helper:

```python
def _followup_options_for(intent: Intent) -> tuple[FollowupOptionId, ...]:
    if intent is Intent.CERTIFICATE_ISSUANCE:
        return _CERTIFICATE_FOLLOWUP_OPTIONS
    if intent is Intent.UNKNOWN:
        return _GENERAL_FOLLOWUP_OPTIONS
    raise ValueError("FOLLOWUP_INTENT_INVALID")
```

The exact local type alias must include the nine allowed IDs and must match `response.py`.

- [ ] **Step 5: Handle unresolved FOLLOWUP before retrieval**

Replace the UNKNOWN-only block with:

```python
if outcome.followup_required and not intent_from_context:
    token = self._issue_context(
        intent=intent,
        selected_region=selected_region,
        answer_status="FOLLOWUP",
    )
    followup_response = build_followup_response(
        request_id=selected_request_id,
        intent=intent,
        confidence=None,
        option_ids=_followup_options_for(intent),
        context_token=token,
    )
    interaction = self._build_interaction(
        request_id=selected_request_id,
        intent=intent,
        answer_status=AnswerStatus.FOLLOWUP,
        fallback_reason=None,
        used_source_ids=(),
        selected_region=selected_region,
        office=None,
        masked_question=None,
        started_ns=started_ns,
    )
    return _ChatExecution(response=followup_response, interaction=interaction)
```

Do not return a second FOLLOWUP when `intent_from_context` resolved a short contextual detail.

- [ ] **Step 6: Run service and combined API focused GREEN tests**

Run:

```powershell
apps/api/.venv/Scripts/python.exe -m pytest `
  apps/api/tests/chat/test_classification.py `
  apps/api/tests/chat/test_response.py `
  apps/api/tests/chat/test_service.py `
  -q
```

Expected: all focused tests pass.

- [ ] **Step 7: Commit the service orchestration**

```powershell
git add apps/api/src/sejong_ai_api/chat/service.py apps/api/tests/chat/test_service.py
git commit -m "fix(chat): route certificate ambiguity to followup"
```

---

### Task 4: Render intent-specific Web copy and preserve option context

**Files:**
- Create: `apps/web/src/components/citizen/FollowupCard.test.tsx`
- Modify: `apps/web/src/components/citizen/FollowupCard.tsx:18-113`
- Modify: `apps/web/src/app/chat/chat-screen.tsx:368-382`
- Modify: `apps/web/src/app/chat/chat-screen.test.tsx:157-227`
- Modify: `apps/web/src/app/chat/contract-fixtures.test.tsx:78-87`

**Interfaces:**
- Consumes: typed `Intent`, server-provided option labels and context token
- Produces: intent-aware visible prompt and unchanged `ChatRequest` retry/context behavior
- Preserves: region prompt, unknown generic prompt and accessible button behavior

- [ ] **Step 1: Create failing component prompt tests**

Create `FollowupCard.test.tsx`:

```tsx
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import FollowupCard from "./FollowupCard";

const CERTIFICATE_OPTIONS = [
  "주민등록등본 발급",
  "주민등록초본 발급",
  "등본과 초본의 차이",
  "주민등록표 열람",
  "무인민원발급기 이용",
] as const;

describe("FollowupCard prompt", () => {
  it("asks which certificate before and after a certificate option is selected", () => {
    render(
      <FollowupCard
        intent="CERTIFICATE_ISSUANCE"
        options={CERTIFICATE_OPTIONS}
        onSelect={vi.fn()}
      />,
    );

    expect(screen.getByText("어떤 증명서를 발급하려고 하시나요?")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "주민등록등본 발급" }));
    expect(screen.getByText("어떤 증명서를 발급하려고 하시나요?")).toBeInTheDocument();
  });

  it("keeps the generic prompt for UNKNOWN", () => {
    render(
      <FollowupCard
        intent="UNKNOWN"
        options={["전입·주민등록", "증명서 발급"]}
        onSelect={vi.fn()}
      />,
    );

    expect(screen.getByText("어떤 것부터 안내해 드릴까요?")).toBeInTheDocument();
  });

  it("keeps the region prompt for region options", () => {
    render(
      <FollowupCard
        intent="BULKY_WASTE"
        options={["아름동", "도담동", "조치원읍"]}
        onSelect={vi.fn()}
      />,
    );

    expect(
      screen.getByText("안내는 사시는 동에 따라 달라요. 어느 동에 거주하시나요?"),
    ).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run the component RED test**

Run:

```powershell
corepack.cmd pnpm --filter @sejong-ai/web exec vitest run `
  src/components/citizen/FollowupCard.test.tsx
```

Expected: TypeScript/test failure because `intent` is not a component prop and the certificate copy
does not exist.

- [ ] **Step 3: Add the typed prompt selector**

Import the generated `Intent` display type through `@/lib/labels`, add `intent: Intent` to
`FollowupCard`, and define:

```tsx
const prompt =
  options.every(isRegion)
    ? "안내는 사시는 동에 따라 달라요. 어느 동에 거주하시나요?"
    : intent === "CERTIFICATE_ISSUANCE"
      ? "어떤 증명서를 발급하려고 하시나요?"
      : "어떤 것부터 안내해 드릴까요?";
```

Use `prompt` in both pre-selection and selected-summary branches.

- [ ] **Step 4: Pass intent from every consumer**

In `ChatScreen`:

```tsx
<FollowupCard
  intent={response.intent}
  options={response.followup_options}
  disabled={disabled}
  onSelect={(option) => onSelectFollowup(message, option)}
/>
```

In `contract-fixtures.test.tsx`, pass the fixture's typed intent:

```tsx
intent={(validFollowup as { intent: "UNKNOWN" }).intent}
```

- [ ] **Step 5: Add the failing ChatScreen integration test**

Add:

```tsx
it("sends a certificate option with the certificate followup context", async () => {
  const followup = {
    request_id: "77777777-7777-4777-8777-777777777777",
    answer_status: "FOLLOWUP",
    intent: "CERTIFICATE_ISSUANCE",
    sources: [],
    followup_options: ["주민등록등본 발급", "주민등록초본 발급"],
    office: null,
    context_token: "signed-certificate-context",
  } satisfies ChatResponse;
  const send = vi.fn().mockResolvedValueOnce(followup).mockResolvedValueOnce(SUCCESS_RESPONSE);
  render(<ChatScreen transport={transportWith(send)} />);

  ask("증명서 발급해야해");
  fireEvent.click(await screen.findByRole("button", { name: "주민등록등본 발급" }));

  await waitFor(() => expect(send).toHaveBeenCalledTimes(2));
  expect(send.mock.calls[1][0]).toEqual({
    question: "주민등록등본 발급",
    selected_region: null,
    simple_language: true,
    context_token: "signed-certificate-context",
  } satisfies ChatRequest);
});
```

- [ ] **Step 6: Run Web focused GREEN tests**

Run:

```powershell
corepack.cmd pnpm --filter @sejong-ai/web exec vitest run `
  src/components/citizen/FollowupCard.test.tsx `
  src/app/chat/chat-screen.test.tsx `
  src/app/chat/contract-fixtures.test.tsx
```

Expected: all three test files pass.

- [ ] **Step 7: Run Web static gates**

```powershell
corepack.cmd pnpm --filter @sejong-ai/web lint
corepack.cmd pnpm --filter @sejong-ai/web typecheck
```

Expected: both exit 0.

- [ ] **Step 8: Commit the Web behavior**

```powershell
git add apps/web/src/components/citizen/FollowupCard.tsx `
  apps/web/src/components/citizen/FollowupCard.test.tsx `
  apps/web/src/app/chat/chat-screen.tsx `
  apps/web/src/app/chat/chat-screen.test.tsx `
  apps/web/src/app/chat/contract-fixtures.test.tsx
git commit -m "fix(web): ask certificate-specific followup"
```

---

### Task 5: Integrate versions, evidence and final gates

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `versions/manifest.json`
- Modify: `docs/11_AMBIGUITY_REGISTER.md`
- Modify: `docs/12_VERSIONING_AND_RELEASES.md`
- Modify: `docs/decisions/DECISION_LOG.md`
- Create via `scripts/new_implementation_note.py`: the next available
  `증명서 분야별 FOLLOWUP 구현` implementation note
- Modify: `docs/implementation-notes/INDEX.md`

**Interfaces:**
- Consumes: completed Tasks 1-4 and their RED/GREEN evidence
- Produces: reproducible completion note and review-ready commit series
- Version target: application `0.10.0-office-directory-runtime→0.11.0-certificate-followup`,
  Web `0.6.0-answer-mode→0.7.0-certificate-followup`,
  test `1.8.0-local-demo-readiness→1.9.0-certificate-followup`,
  docs `2.22.2→2.23.0`

- [ ] **Step 1: Run the complete API area gate**

```powershell
apps/api/.venv/Scripts/python.exe -m pytest `
  apps/api/tests `
  -q
```

Expected: zero failures; local DB-gated skips must be reported by exact count.

- [ ] **Step 2: Run the complete Web area gate**

```powershell
corepack.cmd pnpm --filter @sejong-ai/web lint
corepack.cmd pnpm --filter @sejong-ai/web typecheck
corepack.cmd pnpm --filter @sejong-ai/web test
corepack.cmd pnpm --filter @sejong-ai/web build
```

Expected: every command exits 0.

- [ ] **Step 3: Run contract and repository gates**

```powershell
corepack.cmd pnpm --filter @sejong-ai/shared-contracts generate:check
corepack.cmd pnpm --filter @sejong-ai/shared-contracts test
python -B scripts/check_repository_docs.py
python -B scripts/validate_codex_package.py
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/check_secret_patterns.ps1 `
  -RepositoryRoot .
git diff --check
```

Expected: every command exits 0 and generated contract diff remains zero.

- [ ] **Step 4: Run the original symptom regression through the service**

Use the focused service test command from Task 3 and record:

- generic request returns certificate FOLLOWUP
- exact five options
- repository read 0
- failed question 0
- each option does not repeat FOLLOWUP

- [ ] **Step 5: Update version and governance documents**

Record implementation completion in D-085 and mark A-053
`Resolved / implemented and verified`. Keep A-054/A-055 as the next P0 gaps.

Create the implementation note using:

```powershell
python scripts/new_implementation_note.py `
  --title "증명서 분야별 FOLLOWUP 구현" `
  --task-id CHAT-CERTIFICATE-FOLLOWUP-001 `
  --type implementation
```

Fill exact files, commands, pass counts, security/privacy/accessibility impact and rollback.

- [ ] **Step 6: Verify the final diff scope**

```powershell
git status --short
git diff --stat
git diff --check
git diff --name-only
```

Expected changed scope:

- API classifier/service/response and their tests
- Web FollowupCard/chat tests and consumers
- version/governance/completion docs

Expected absent scope:

- DB/migrations/official data
- package manifests/lockfile
- provider config/env
- OpenAPI/generated types

- [ ] **Step 7: Commit integration evidence**

```powershell
git add CHANGELOG.md versions/manifest.json docs `
  apps/api/src/sejong_ai_api/chat apps/api/tests/chat `
  apps/web/src/components/citizen apps/web/src/app/chat
git commit -m "docs(chat): close certificate followup implementation"
```

- [ ] **Step 8: Stop before external publication**

Do not push, create a PR or merge unless the user explicitly requests the Git publication step.
