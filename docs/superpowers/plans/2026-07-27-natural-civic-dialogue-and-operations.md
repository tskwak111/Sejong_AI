# Natural Civic Dialogue and Operations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** 자연스러운 한국어 질문을 privacy-first hybrid routing으로 처리하고, context v2,
별도 scope-gap 운영 queue, 일반 후보 작성, actual/local/public 검증까지 완성한다.

**Architecture:** deterministic PII·policy·high-confidence gate 뒤 안전한 ambiguous 질문만
Upstage closed classifier에 전달한다. 서버가 route, ACTIVE/OFFICIAL retrieval, persistence,
source와 fallback을 소유한다. 세 수직 slice를 독립 area gate로 닫은 뒤 clean DB, PII-free
actual provider, hardened configured remote 시민 경로를 순서대로 검증한다.

**Tech Stack:** Python 3.12.13, FastAPI 0.139.0, Pydantic 2.13.4, httpx 0.28.1,
PostgreSQL 17/Supabase CLI 2.109.1 patched runner, Node 24.12.0, pnpm 11.13.0,
Next.js 16.2.10, React 19.2.7, Vitest 4.1.10, Playwright existing harness.

## Global Constraints

- 새 production dependency는 0이다.
- 질문 원문·raw transcript·context token·secret·DSN은 DB와 로그에 저장·출력하지 않는다.
- PII redaction 성공 전 provider call은 0이다.
- citizen retrieval은 ACTIVE KB, source/office는 OFFICIAL only다.
- classifier는 3초·1 attempt·retry 0·input 1,024 chars·output 128 tokens·sub-cap 20이다.
- generator는 8초·1 attempt·retry 0·sub-cap 30이다.
- 요청당 provider 최대 2회, process combined cap 40, hard wall 12초다.
- actual run은 PII-free allowlisted fixture와 VAT 포함 USD 0.05 stop line을 사용한다.
- `[db.seed].enabled=false`를 유지하고 `.2`는 별도 `seed-cycle → verify-final`로 적용한다.
- migration 00100~00670과 immutable `.1`/`.2` release byte를 수정하지 않는다.
- remote/public에서 admin router는 비활성이고 real citizen/free-input provider outbound는 0이다.
- Web은 390px·430px·desktop, keyboard, visible focus, live-region을 검증한다.
- automatic merge는 하지 않는다.

---

## File responsibility map

| Unit | Files | Responsibility |
|---|---|---|
| PII | `privacy/redaction.py`, `tests/privacy/test_redaction.py` | provider 전 안전 문자열 |
| Classifier domain | `chat/classification.py`, new `llm/classifier_contracts.py` | closed route와 server validation |
| Classifier provider | new `llm/classifier_prompt.py`, `llm/upstage_classifier.py` | exact Upstage one-attempt adapter |
| Provider budgets | `llm/limits.py`, `llm/settings.py`, `local.py` | shared combined cap and modes |
| Chat orchestration | `chat/service.py`, `chat/response.py` | route, retrieval, fallback, persistence |
| Context | `chat/context.py` | v1 read-only, v2 issuer/reader |
| Contracts | `contracts/*`, Pydantic, generated TS | breaking public fallback reason |
| Citizen Web | `chat-screen.tsx`, `FollowupCard.tsx`, typed client | region/context/reset/loading |
| Scope DB | new 00680/rollback/pgTAP | isolated 30-day queue |
| Scope backend | repository/admin service/API/contracts | local/private list/review |
| Admin Web | existing `/admin/failures` family and candidate UI | tabs, scope review, general form |
| Public hardening | new 00700/rollback/pgTAP, DB runner | exact 22 function properties |
| Actual/remote | existing approved scripts/runbooks | clean DB, provider fixture, citizen smoke |

---

### Task 1: Correct contextual-name PII false positives

**Files:**
- Modify: `apps/api/tests/privacy/test_redaction.py`
- Modify: `apps/api/src/sejong_ai_api/privacy/redaction.py`

**Interfaces:**
- Consumes: `redact_question(str) -> RedactionResult`
- Produces: unchanged `RedactionResult`; ordinary civic/non-civic Korean remains provider-safe
- Preserves: frozen positive PII cases and `AMBIGUOUS_PERSON_NAME` fail-closed outcome

- [ ] **Step 1: Add the negative regression corpus**

Add a parameterized test with:

```python
@pytest.mark.parametrize(
    "question",
    [
        "오늘 날씨 어때요?",
        "청년 월세 지원 어떻게 해요?",
        "장학금 신청 어떻게 해요?",
        "가족관계증명서 어떻게 발급받아요?",
        "증명서 발급해야해",
    ],
)
def test_ordinary_korean_is_not_an_ambiguous_person_name(question: str) -> None:
    result = redact_question(question)
    assert result.unresolved_reason is None
    assert result.masked_text == question
    assert result.safe_for_failure_storage is True
    assert result.safe_for_synthetic_provider is True
```

- [ ] **Step 2: Run RED and capture the exact failing cases**

Run:

```powershell
apps/api/.venv/Scripts/python.exe -m pytest `
  apps/api/tests/privacy/test_redaction.py `
  -q
```

Expected: at least the previously reported ordinary phrases fail with
`AMBIGUOUS_PERSON_NAME`; existing positive tests remain collected.

- [ ] **Step 3: Tighten contextual-name evidence**

In `_looks_like_contextual_person_name`, require both:

```python
has_person_context = bool(
    _PERSON_RELATION_OR_HONORIFIC.search(left_context)
    or _SELF_INTRODUCTION_CONTEXT.search(left_context)
)
has_name_shape = _looks_like_korean_person_name(candidate)
return has_person_context and has_name_shape
```

Keep the existing explicit name/relationship positive patterns. Do not add the five sentences to
a global allowlist.

- [ ] **Step 4: Run focused positive and negative GREEN**

Run the full privacy file and record pass count:

```powershell
apps/api/.venv/Scripts/python.exe -m pytest `
  apps/api/tests/privacy/test_redaction.py `
  -q
```

Expected: zero failures; frozen positive PII tests do not decrease.

- [ ] **Step 5: Commit the PII correction**

```powershell
git add apps/api/src/sejong_ai_api/privacy/redaction.py `
  apps/api/tests/privacy/test_redaction.py
git commit -m "fix(privacy): avoid ordinary Korean name false positives"
```

---

### Task 2: Define the closed hybrid classifier domain

**Files:**
- Create: `apps/api/src/sejong_ai_api/llm/classifier_contracts.py`
- Create: `apps/api/tests/llm/test_classifier_contracts.py`
- Modify: `apps/api/src/sejong_ai_api/chat/classification.py`
- Modify: `apps/api/tests/chat/test_classification.py`

**Interfaces:**
- Produces:

```python
class ClassifierRoute(str, Enum):
    SUPPORTED = "SUPPORTED"
    CIVIC_SCOPE_GAP = "CIVIC_SCOPE_GAP"
    NON_CIVIC = "NON_CIVIC"
    NEEDS_FOLLOWUP = "NEEDS_FOLLOWUP"

class PendingSlot(str, Enum):
    CERTIFICATE_KIND = "CERTIFICATE_KIND"
    REGION = "REGION"
    WASTE_ITEM = "WASTE_ITEM"

@dataclass(frozen=True, slots=True)
class ClassifierDecision:
    route: ClassifierRoute
    intent: Intent | None
    topic_id: str | None
    pending_slot: PendingSlot | None
```

- `ClassificationOutcome` gains route, topic and pending slot while retaining intent/fallback.

- [ ] **Step 1: Write combination-invariant RED tests**

Test exact valid combinations and reject:

```python
with pytest.raises(ValueError, match="CLASSIFIER_DECISION_INVALID"):
    ClassifierDecision(
        route=ClassifierRoute.NON_CIVIC,
        intent=Intent.LOCAL_TAX_GENERAL,
        topic_id=None,
        pending_slot=None,
    )
```

Also reject extra JSON keys, unknown enum, SUPPORTED without intent, scope/non-civic with any
intent/topic/slot and FOLLOWUP without slot.

- [ ] **Step 2: Run the contract RED test**

```powershell
apps/api/.venv/Scripts/python.exe -m pytest `
  apps/api/tests/llm/test_classifier_contracts.py `
  -q
```

Expected: import failure because the module does not exist.

- [ ] **Step 3: Implement strict parser and invariants**

Provide:

```python
def parse_classifier_decision(payload: bytes) -> ClassifierDecision:
    value = json.loads(payload.decode("utf-8"))
    if type(value) is not dict or set(value) != {
        "route", "intent", "topic_id", "pending_slot"
    }:
        raise ValueError("CLASSIFIER_DECISION_INVALID")
    return ClassifierDecision(
        route=ClassifierRoute(value["route"]),
        intent=Intent(value["intent"]) if value["intent"] is not None else None,
        topic_id=value["topic_id"],
        pending_slot=(
            PendingSlot(value["pending_slot"])
            if value["pending_slot"] is not None
            else None
        ),
    )
```

Use exact enum constructors, non-empty server ID syntax
`re.fullmatch(r"[A-Z0-9][A-Z0-9._-]{0,63}", topic_id)`, and no coercion.

- [ ] **Step 4: Add deterministic fast-path tests**

Add exact expectations:

```python
assert classify_question(safe("오늘 날씨 어때요?")).route is ClassifierRoute.NON_CIVIC
assert classify_question(safe("주민등록등본 발급")).route is ClassifierRoute.SUPPORTED
assert classify_question(safe("증명서 발급해야해")).pending_slot is PendingSlot.CERTIFICATE_KIND
assert classify_question(safe("청년 월세 지원 어떻게 해요?")).needs_provider is True
```

`needs_provider` is true only when deterministic policy, supported, explicit non-civic and bounded
certificate followup did not resolve the question.

- [ ] **Step 5: Implement minimal deterministic outcome changes**

Keep policy priority, high-score supported and explicit non-civic fast paths. Remove broad
administrative OOS terms from `NON_CIVIC`; unsupported administrative phrases remain ambiguous for
the provider.

- [ ] **Step 6: Run classifier GREEN**

```powershell
apps/api/.venv/Scripts/python.exe -m pytest `
  apps/api/tests/llm/test_classifier_contracts.py `
  apps/api/tests/chat/test_classification.py `
  -q
```

- [ ] **Step 7: Commit the domain contract**

```powershell
git add apps/api/src/sejong_ai_api/llm/classifier_contracts.py `
  apps/api/src/sejong_ai_api/chat/classification.py `
  apps/api/tests/llm/test_classifier_contracts.py `
  apps/api/tests/chat/test_classification.py
git commit -m "feat(chat): define closed hybrid classifier routes"
```

---

### Task 3: Implement bounded Upstage classifier and shared attempt ledger

**Files:**
- Create: `apps/api/src/sejong_ai_api/llm/classifier_prompt.py`
- Create: `apps/api/src/sejong_ai_api/llm/upstage_classifier.py`
- Create: `apps/api/tests/llm/test_upstage_classifier.py`
- Modify: `apps/api/src/sejong_ai_api/llm/limits.py`
- Modify: `apps/api/src/sejong_ai_api/llm/settings.py`
- Modify: `apps/api/tests/llm/test_settings.py`
- Modify: `apps/api/.env.example`

**Interfaces:**
- Produces `QuestionClassifier.classify(SafeQuestion) -> ClassifierDecision | None`
- Produces `ProviderAttemptLedger(classifier_cap=20, generator_cap=30, combined_cap=40)`
- New exact flag: `UPSTAGE_CLASSIFIER_MODE=true|false`

- [ ] **Step 1: Write RED transport tests**

Use `httpx.MockTransport` and assert:

```python
assert request.url == "https://api.upstage.ai/v1/chat/completions"
assert body["model"] == "solar-pro3"
assert body["max_tokens"] == 128
assert body["response_format"] == {"type": "json_object"}
```

Cover success, timeout, 429, 500, invalid JSON, invalid enum and attempt-cap exhaustion. Assert
each failure returns `None`, outbound count at most 1 and raw question is absent from exceptions.

- [ ] **Step 2: Run RED**

```powershell
apps/api/.venv/Scripts/python.exe -m pytest `
  apps/api/tests/llm/test_upstage_classifier.py `
  apps/api/tests/llm/test_settings.py `
  -q
```

- [ ] **Step 3: Implement the shared non-resettable ledger**

Use one object:

```python
class ProviderAttemptLedger:
    @asynccontextmanager
    async def reserve_classifier(self) -> AsyncIterator[int]:
        async with self._reserve(_ProviderLane.CLASSIFIER) as reservation:
            yield reservation

    @asynccontextmanager
    async def reserve_generator(self) -> AsyncIterator[int]:
        async with self._reserve(_ProviderLane.GENERATOR) as reservation:
            yield reservation
```

Each reservation checks its sub-cap and the combined 40 under one lock before incrementing. Keep
the existing concurrency-one semaphore. No public reset method exists.

- [ ] **Step 4: Add exact settings profile**

`UpstageClassifierSettings` must accept only:

```text
LLM_PROVIDER=upstage
LLM_MODEL=solar-pro3
LLM_BASE_URL=https://api.upstage.ai/v1
LLM_MAX_CONCURRENCY=1
UPSTAGE_SYNTHETIC_EVALUATION_MODE=false
UPSTAGE_CLASSIFIER_MODE=true
LLM_CLASSIFIER_TIMEOUT_SECONDS=3
LLM_CLASSIFIER_MAX_RETRIES=0
LLM_CLASSIFIER_MAX_INPUT_CHARS=1024
LLM_CLASSIFIER_MAX_OUTPUT_TOKENS=128
LLM_CLASSIFIER_ATTEMPT_CAP=20
LLM_GENERATOR_ATTEMPT_CAP=30
LLM_COMBINED_ATTEMPT_CAP=40
```

Classifier-only actual uses `UPSTAGE_GROUNDED_CHAT_MODE=false`; combined local demo uses
`UPSTAGE_GROUNDED_CHAT_MODE=true` with its existing generator settings. Keep duplicate/malformed
assignment fail-closed and API key `repr=False`. Preserve legacy `LLM_RUN_ATTEMPT_CAP=30` for the
published LLM-002/003 profiles; the three new lane keys own the combined runtime.

- [ ] **Step 5: Implement prompt and adapter**

The prompt lists only the four routes, four intents and three slots. The user content is
`question.text[:1024]`; no source or answer fields are requested. Configure
`httpx.Timeout(connect=3, read=3, write=3, pool=3)` and no retry loop.

- [ ] **Step 6: Run LLM area GREEN**

```powershell
apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests/llm -q
apps/api/.venv/Scripts/python.exe -m ruff check apps/api/src/sejong_ai_api/llm apps/api/tests/llm
apps/api/.venv/Scripts/python.exe -m mypy apps/api/src/sejong_ai_api/llm
```

- [ ] **Step 7: Commit provider boundary**

```powershell
git add apps/api/src/sejong_ai_api/llm apps/api/tests/llm apps/api/.env.example
git commit -m "feat(llm): add bounded Upstage question classifier"
```

---

### Task 4: Add the breaking `CIVIC_SCOPE_GAP` public response contract

**Files:**
- Modify: `contracts/openapi-v1.yaml`
- Modify: `contracts/chat-response.schema.json`
- Create: `contracts/fixtures/chat-response/valid-civic-scope-gap.json`
- Modify: `apps/api/src/sejong_ai_api/contracts/chat.py`
- Modify: `apps/api/src/sejong_ai_api/db/models.py`
- Modify: `packages/shared-contracts/package.json`
- Regenerate: `packages/shared-contracts/src/generated/api.ts`
- Modify: contract and API model tests

**Interfaces:**
- Adds `FallbackReason.CIVIC_SCOPE_GAP`
- Requires `intent=OUT_OF_SCOPE`, `candidate_eligible=false`, sources/followup/context empty
- API version target `4.0.0-draft`; shared package `1.0.0`

- [ ] **Step 1: Add RED fixture/schema tests**

Fixture fallback copy:

```json
{
  "reason": "CIVIC_SCOPE_GAP",
  "title": "아직 지원하지 않는 민원이에요",
  "message": "행정 민원으로 보이지만 현재 승인된 안내 범위에는 없어요.",
  "next_actions": ["지원 범위 확대 검토 대상으로 안전하게 접수할 수 있어요."],
  "candidate_eligible": false,
  "office": null
}
```

Run `corepack.cmd pnpm --filter @sejong-ai/shared-contracts test`; expected RED until enums and
semantics are updated.

- [ ] **Step 2: Extend OpenAPI, JSON Schema and Pydantic together**

Add the enum and a dedicated semantic branch requiring OUT_OF_SCOPE intent. Update
`FallbackResponse.validate_fallback_semantics` to treat `CIVIC_SCOPE_GAP` exactly like OOS for
intent and never as candidate eligible.

- [ ] **Step 3: Regenerate and inspect TypeScript**

```powershell
corepack.cmd pnpm contracts:generate
corepack.cmd pnpm contracts:check
corepack.cmd pnpm --filter @sejong-ai/shared-contracts test
```

Expected: generated diff contains only the new reason and approved admin additions from later
tasks are not present yet.

- [ ] **Step 4: Run Pydantic contract tests**

```powershell
apps/api/.venv/Scripts/python.exe -m pytest `
  apps/api/tests/contracts `
  apps/api/tests/db/test_models.py `
  -q
```

- [ ] **Step 5: Commit the breaking contract**

```powershell
git add contracts apps/api/src/sejong_ai_api/contracts/chat.py `
  apps/api/src/sejong_ai_api/db/models.py apps/api/tests/contracts `
  apps/api/tests/db/test_models.py packages/shared-contracts
git commit -m "feat(contract): add civic scope gap fallback reason"
```

---

### Task 5: Integrate hybrid routing, certificate FOLLOWUP and storage boundaries

**Files:**
- Modify: `apps/api/src/sejong_ai_api/chat/service.py`
- Modify: `apps/api/src/sejong_ai_api/chat/response.py`
- Modify: `apps/api/tests/chat/test_service.py`
- Modify: `apps/api/tests/chat/test_response.py`
- Modify: `apps/api/tests/chat/test_grounded_generation.py`

**Interfaces:**
- `ChatService` accepts optional `QuestionClassifier`
- `ChatRepository` gains best-effort `record_civic_scope_gap(masked_question: str) -> None`
- FOLLOWUP option IDs include five certificate IDs

- [ ] **Step 1: Write route RED tests**

Test the four reported questions, certificate five options, classifier failure, NON_CIVIC row 0,
scope gap event/failed row 0 plus queue call 1, and policy/privacy all repositories/calls 0.

For the queue spy:

```python
assert repository.interactions == []
assert repository.scope_gaps == ["청년 월세 지원 어떻게 해요?"]
assert classifier.calls == 1
assert generator.calls == 0
```

- [ ] **Step 2: Run chat RED**

```powershell
apps/api/.venv/Scripts/python.exe -m pytest `
  apps/api/tests/chat/test_service.py `
  apps/api/tests/chat/test_response.py `
  -q
```

- [ ] **Step 3: Implement route resolution**

Order:

```python
deterministic = classify_question(safe_question)
decision = deterministic.decision
if deterministic.needs_provider and self._question_classifier is not None:
    decision = await self._question_classifier.classify(safe_question)
if decision is None:
    return self._safe_domain_followup(
        request_id=selected_request_id,
        selected_region=selected_region,
    )
```

Map NON_CIVIC to fixed OUT_OF_SCOPE response without any record. Map CIVIC_SCOPE_GAP to the new
fallback and call only `record_civic_scope_gap` best-effort. Keep retrieval/generation exclusively
for SUPPORTED.

- [ ] **Step 4: Add certificate labels**

Define exact IDs:

```python
"certificate.resident-copy"
"certificate.resident-abstract"
"certificate.copy-vs-abstract"
"certificate.resident-register-inspection"
"certificate.unmanned-kiosk"
```

Initial generic certificate FOLLOWUP must read zero KB/office rows and record zero failure/scope
rows.

- [ ] **Step 5: Enforce request hard wall**

Compute one monotonic 12-second provider deadline and pass the remaining budget to classifier and
generator waits. On deadline, if grounded record exists return full template; otherwise return the
safe domain FOLLOWUP. Apply the deadline only to provider stages; route-specific DB persistence
starts after the provider deadline block and is never cancelled by it.

- [ ] **Step 6: Run chat GREEN and privacy architecture tests**

```powershell
apps/api/.venv/Scripts/python.exe -m pytest `
  apps/api/tests/chat `
  apps/api/tests/privacy `
  apps/api/tests/test_architecture.py `
  apps/api/tests/llm/test_architecture.py `
  -q
```

- [ ] **Step 7: Commit Slice 1 service integration**

```powershell
git add apps/api/src/sejong_ai_api/chat `
  apps/api/tests/chat
git commit -m "feat(chat): route ambiguous questions through bounded classifier"
```

---

### Task 6: Upgrade the signed context issuer to v2

**Files:**
- Modify: `apps/api/src/sejong_ai_api/chat/context.py`
- Modify: `apps/api/tests/chat/test_context.py`
- Modify: `apps/api/src/sejong_ai_api/chat/service.py`
- Modify: `apps/api/tests/chat/test_service.py`

**Interfaces:**
- `CONTEXT_TOKEN_SCHEMA_VERSION = 2`
- `ChatContext` gains `topic_id`, `pending_slot`, `dialog_act`
- `ContextTokenCodec.read()` accepts v1 and v2; `issue()` emits v2 only

- [ ] **Step 1: Add v1 compatibility and v2 claim RED tests**

Freeze one valid v1 token using injected clock/secret. Assert it reads before expiry and fails at
expiry. Assert issued token has:

```python
{
    "schema_version": 2,
    "topic_id": "KB-CERT-01",
    "pending_slot": "CERTIFICATE_KIND",
    "dialog_act": "ASKING_SLOT",
}
```

Reject unknown claims, raw text claims, invalid topic syntax and invalid slot/act.

- [ ] **Step 2: Run context RED**

```powershell
apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests/chat/test_context.py -q
```

- [ ] **Step 3: Implement dual reader and v2-only issuer**

Split `_validate_v1_claims` and `_validate_v2_claims`; never translate a v1 token into stored
state. Add exact enums:

```python
PendingSlot = Literal["CERTIFICATE_KIND", "REGION", "WASTE_ITEM"]
DialogAct = Literal["ANSWERED", "ASKING_SLOT", "CHANGING_REGION", "CHANGING_TOPIC"]
```

- [ ] **Step 4: Bind topics only after current ACTIVE retrieval**

`topic_id` may be reused as a lookup hint, but service calls `list_active_kb(intent)` and accepts it
only when a current record public ID matches and data origin is OFFICIAL.

- [ ] **Step 5: Run context/service GREEN**

```powershell
apps/api/.venv/Scripts/python.exe -m pytest `
  apps/api/tests/chat/test_context.py `
  apps/api/tests/chat/test_service.py `
  -q
```

- [ ] **Step 6: Commit context v2**

```powershell
git add apps/api/src/sejong_ai_api/chat/context.py `
  apps/api/src/sejong_ai_api/chat/service.py `
  apps/api/tests/chat/test_context.py apps/api/tests/chat/test_service.py
git commit -m "feat(chat): issue structured context v2"
```

---

### Task 7: Implement five contextual followups and region transitions

**Files:**
- Modify: `apps/api/src/sejong_ai_api/chat/service.py`
- Modify: `apps/api/tests/chat/test_service.py`
- Modify: `apps/api/src/sejong_ai_api/chat/grounding.py`
- Modify: `apps/api/tests/chat/test_grounding.py`

**Interfaces:**
- Context detail intents: fee, documents, online procedure, office, region/topic change
- No new public response fields

- [ ] **Step 1: Add RED transition matrix**

For one ACTIVE record, parameterize:

```python
[
    ("비용은요?", "fee"),
    ("준비물은요?", "required_documents"),
    ("온라인도 돼요?", "procedure_steps"),
    ("어디로 가요?", "REGION"),
    ("도담동으로 바꿔줘", "CHANGING_REGION"),
]
```

Assert no generic four-category loop, sources remain server-bound and selected region changes only
to the three allowed values.

- [ ] **Step 2: Run RED**

```powershell
apps/api/.venv/Scripts/python.exe -m pytest `
  apps/api/tests/chat/test_service.py `
  apps/api/tests/chat/test_grounding.py `
  -q
```

- [ ] **Step 3: Implement closed dialog-act resolver**

Use exact compact-term maps only after a valid v2 or still-valid v1 supported context. Explicit new
intent terms take precedence over contextual terms. Office questions without a region return
`pending_slot=REGION`; with a region they bind current OFFICIAL office.

- [ ] **Step 4: Run Slice 2 backend GREEN**

```powershell
apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests/chat -q
```

- [ ] **Step 5: Commit followup transitions**

```powershell
git add apps/api/src/sejong_ai_api/chat apps/api/tests/chat
git commit -m "feat(chat): support structured contextual followups"
```

---

### Task 8: Add citizen Web region, reset, prompt and staged waiting UI

**Files:**
- Modify: `apps/web/src/components/citizen/FollowupCard.tsx`
- Create: `apps/web/src/components/citizen/FollowupCard.test.tsx`
- Modify: `apps/web/src/app/chat/chat-screen.tsx`
- Modify: `apps/web/src/app/chat/chat-screen.test.tsx`
- Modify: `apps/web/src/lib/chat-api.ts`
- Modify: `apps/web/src/lib/chat-api.test.ts`
- Modify: `tools/web-e2e/e2e/home-chat-shell.spec.ts`

**Interfaces:**
- Uses existing `selected_region` request and context token
- Adds Web-only region selector for `아름동|도담동|조치원읍`
- New conversation clears transcript, context token, region and idempotency key

- [ ] **Step 1: Add component/integration RED tests**

Assert certificate prompt `어떤 증명서를 발급하려고 하시나요?`, region selector label
`거주 지역`, and reset:

```tsx
fireEvent.click(screen.getByRole("button", { name: "새 대화" }));
expect(screen.queryByText(previousAnswer)).not.toBeInTheDocument();
expect(transport.send).not.toHaveBeenCalled();
```

Use fake timers to assert 2-second and 6-second messages, and no stale timer after response.

- [ ] **Step 2: Run Web RED**

```powershell
corepack.cmd pnpm --filter @sejong-ai/web exec vitest run `
  src/components/citizen/FollowupCard.test.tsx `
  src/app/chat/chat-screen.test.tsx `
  src/lib/chat-api.test.ts
```

- [ ] **Step 3: Implement intent-aware prompt and direct region selection**

Prompt priority: all-region options → certificate intent → generic. Region change sends the next
request with `selected_region` and current context token. Do not store region in cookie or
localStorage.

- [ ] **Step 4: Implement new conversation and live status**

One function clears all React state and focuses the textarea. Status container uses
`role="status" aria-live="polite"` and replaces text rather than appending duplicate nodes.

- [ ] **Step 5: Run Web area GREEN**

```powershell
corepack.cmd pnpm --filter @sejong-ai/web lint
corepack.cmd pnpm --filter @sejong-ai/web typecheck
corepack.cmd pnpm --filter @sejong-ai/web test
corepack.cmd pnpm --filter @sejong-ai/web build
```

- [ ] **Step 6: Run 390/430/desktop E2E**

Run:

```powershell
corepack.cmd pnpm --dir tools/web-e2e test -- `
  --config=playwright.config.ts `
  e2e/home-chat-shell.spec.ts
```

Assert no horizontal overflow, keyboard selection, focus return and reset in the existing
`mobile-390`, `mobile-430` and desktop projects.

- [ ] **Step 7: Commit citizen Web Slice 2**

```powershell
git add apps/web/src tools/web-e2e
git commit -m "feat(web): add contextual chat controls"
```

---

### Task 9: Add isolated scope-gap queue migration 00680

**Files:**
- Create: `supabase/migrations/20260727000680_civic_scope_gap_queue.sql`
- Create: `database/rollbacks/20260727000680_civic_scope_gap_queue.rollback.sql`
- Create: `supabase/tests/database/010_civic_scope_gap_queue_test.sql`
- Modify: `scripts/verify_database.ps1`
- Modify: `scripts/tests/test_supabase_tooling.py`
- Modify: `database/schema-v1.draft.sql`

**Interfaces:**
- SQL capabilities exactly match spec section 9
- Rollback order begins `00680 → 00670`

- [ ] **Step 1: Add runner and pgTAP RED expectations**

Static runner test requires 00680 first and test count increases to 10 files. pgTAP asserts table
columns/checks, owner, ACL, SECURITY DEFINER search path, state transitions, row separation and
purge.

- [ ] **Step 2: Run static RED**

```powershell
apps/api/.venv/Scripts/python.exe -m pytest `
  scripts/tests/test_supabase_tooling.py `
  -q
```

- [ ] **Step 3: Create forward migration**

Create `app_private.civic_scope_gaps` with status check:

```sql
CHECK (status IN ('NEW', 'PLANNED', 'DISMISSED'))
```

Add a terminal-state consistency check requiring actor/time/comment together. `record` accepts one
non-empty masked string; `review` requires `APPROVER`, distinct closed decision and non-empty
comment; `purge` nulls only expired text and sets `text_purged_at`.

All functions use qualified names, owner `sejong_schema_owner`,
`SET search_path = pg_catalog, pg_temp`, and exact grants only to `sejong_backend`.

- [ ] **Step 4: Create reverse rollback**

Revoke/drop four exact functions by signature, then drop the private table. Never delete unrelated
tables or roles.

- [ ] **Step 5: Run actual DB full gate**

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File scripts/verify_database.ps1
```

Expected: exact loopback, 10 pgTAP files, 10-stage rollback/replay and API integration all PASS.

- [ ] **Step 6: Commit 00680**

```powershell
git add supabase/migrations/20260727000680_civic_scope_gap_queue.sql `
  database/rollbacks/20260727000680_civic_scope_gap_queue.rollback.sql `
  supabase/tests/database/010_civic_scope_gap_queue_test.sql `
  scripts/verify_database.ps1 scripts/tests/test_supabase_tooling.py `
  database/schema-v1.draft.sql
git commit -m "feat(db): add isolated civic scope gap queue"
```

---

### Task 10: Connect scope-gap repository, API contract and admin service

**Files:**
- Modify: `apps/api/src/sejong_ai_api/db/repository.py`
- Modify: `apps/api/tests/db/test_repository.py`
- Modify: `apps/api/src/sejong_ai_api/contracts/admin.py`
- Modify: `apps/api/src/sejong_ai_api/admin/service.py`
- Modify: `apps/api/src/sejong_ai_api/api/admin.py`
- Modify: `apps/api/tests/admin/test_service.py`
- Modify: `apps/api/tests/test_admin_route.py`
- Modify: `contracts/openapi-v1.yaml`
- Regenerate: `packages/shared-contracts/src/generated/api.ts`

**Interfaces:**
- `CivicScopeGapSummary`
- `CivicScopeGapListResponse`
- `CivicScopeGapReviewRequest(decision, review_comment)`
- GET/PATCH endpoints from spec

- [ ] **Step 1: Write repository/service/route RED tests**

Assert safe row parsing rejects unknown status, unexpected columns and non-null expired text.
Assert OPERATOR cannot review, APPROVER can, invalid UUID/decision/comment returns typed 422/409,
and disabled app has no admin route.

- [ ] **Step 2: Run RED**

```powershell
apps/api/.venv/Scripts/python.exe -m pytest `
  apps/api/tests/db/test_repository.py `
  apps/api/tests/admin/test_service.py `
  apps/api/tests/test_admin_route.py `
  -q
```

- [ ] **Step 3: Implement typed repository methods**

Use exact SQL constants:

```python
RECORD_CIVIC_SCOPE_GAP_SQL = "SELECT app_api.record_civic_scope_gap(%s)"
LIST_CIVIC_SCOPE_GAPS_SQL = "SELECT * FROM app_api.list_civic_scope_gaps(%s)"
REVIEW_CIVIC_SCOPE_GAP_SQL = (
    "SELECT app_api.review_civic_scope_gap(%s, %s, %s, %s, %s)"
)
```

No query value appears in error text.

- [ ] **Step 4: Add service and HTTP routes**

Read permits both demo roles; review requires APPROVER and uses the existing allowlisted actor
headers. Map DB rules to existing typed admin error codes.

- [ ] **Step 5: Update OpenAPI and regenerate**

```powershell
corepack.cmd pnpm contracts:generate
corepack.cmd pnpm contracts:check
corepack.cmd pnpm --filter @sejong-ai/shared-contracts test
```

- [ ] **Step 6: Run API area GREEN**

```powershell
apps/api/.venv/Scripts/python.exe -m pytest `
  apps/api/tests/db `
  apps/api/tests/admin `
  apps/api/tests/test_admin_route.py `
  -q
```

- [ ] **Step 7: Commit backend scope queue**

```powershell
git add apps/api contracts packages/shared-contracts
git commit -m "feat(admin): expose civic scope review queue"
```

---

### Task 11: Add local admin scope review and general candidate authoring

**Files:**
- Modify: `apps/web/src/lib/admin-api.ts`
- Modify: `apps/web/src/lib/admin-api.test.ts`
- Modify: `apps/web/src/app/admin/failures/page.tsx`
- Modify: `apps/web/src/app/admin/admin-flow.test.tsx`
- Modify: existing candidate form/components under `apps/web/src`
- Modify: `apps/web/src/app/admin/kb-candidates/page.tsx`

**Interfaces:**
- No new route; scope queue is a tab/card within existing `/admin/failures`
- Candidate form sends existing typed `KBCandidateCreateRequest`

- [ ] **Step 1: Add admin RED tests**

Test NEW/PLANNED/DISMISSED counts, review modal comment, actor role enforcement, empty/error states.
For candidates, construct an eligible non-WASTE failure and assert submitted fields come from form,
not reserved constants.

- [ ] **Step 2: Run RED**

```powershell
corepack.cmd pnpm --filter @sejong-ai/web exec vitest run `
  src/lib/admin-api.test.ts `
  src/app/admin/admin-flow.test.tsx
```

- [ ] **Step 3: Implement typed scope methods**

Add:

```ts
listCivicScopeGaps(status?: CivicScopeGapStatus)
reviewCivicScopeGap(id: string, body: CivicScopeGapReviewRequest)
```

Reuse demo headers and value-free error messages.

- [ ] **Step 4: Replace reserved candidate builder with form state**

Required official fields use labels and inline errors. `source_url` input requires HTTPS;
`last_verified_at` uses a date input; procedure/documents are bounded line lists. Never accept a
client public ID.

- [ ] **Step 5: Render state history and truthful copy**

Show DRAFTED/PENDING_APPROVAL/APPROVED/REJECTED tabs and counts. Replace “AI가 작성한 초안” with
`운영자가 작성한 공식 KB 후보`.

- [ ] **Step 6: Run Web GREEN and E2E**

```powershell
corepack.cmd pnpm --filter @sejong-ai/web lint
corepack.cmd pnpm --filter @sejong-ai/web typecheck
corepack.cmd pnpm --filter @sejong-ai/web test
corepack.cmd pnpm --filter @sejong-ai/web build
```

Run:

```powershell
corepack.cmd pnpm --dir tools/web-e2e test -- `
  --config=playwright.config.ts `
  e2e/admin-core-loop.spec.ts
```

Expected: keyboard modal, counts and general form pass in `mobile-390`, `mobile-430` and desktop.

- [ ] **Step 7: Commit admin Web Slice 3**

```powershell
git add apps/web/src tools/web-e2e
git commit -m "feat(web): generalize civic knowledge operations"
```

---

### Task 12: Implement public function-property hardening 00700

**Files:**
- Create: `supabase/migrations/20260727000700_privileged_function_search_path.sql`
- Create: `database/rollbacks/20260727000700_privileged_function_search_path.rollback.sql`
- Create: `supabase/tests/database/011_privileged_function_search_path_test.sql`
- Modify: `scripts/verify_database.ps1`
- Modify: `scripts/tests/test_supabase_tooling.py`

**Interfaces:**
- Exact 22 function signatures from ADR-0018 audit
- Changes only `proconfig` search_path property

- [ ] **Step 1: Freeze exact body/owner/ACL fingerprints in RED pgTAP**

Capture functions by `pg_proc.oid::regprocedure`. Assert count 22 and every search path exactly
`pg_catalog, pg_temp`; assert owner, ACL and body fingerprints match pre-migration fixtures.

- [ ] **Step 2: Add runner RED**

Require rollback order
`00700 → 00680 → 00670 → 00660 → 00650 → 00600 → 00500 → 00400 → 00300 → 00200 → 00100`
and 11 pgTAP files.

- [ ] **Step 3: Create property-only forward and rollback**

Each statement is:

```sql
ALTER FUNCTION schema.name(exact_types)
  SET search_path = pg_catalog, pg_temp;
```

Rollback sets the exact historical `pg_catalog` or the one existing `pg_catalog, pg_temp` property
per signature. Do not use dynamic discovery SQL.

- [ ] **Step 4: Run full local DB regression**

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File scripts/verify_database.ps1
```

Expected: 11 pgTAP files, 11-stage rollback absence/reapply, integration and cleanup PASS.

- [ ] **Step 5: Commit public hardening**

```powershell
git add supabase/migrations/20260727000700_privileged_function_search_path.sql `
  database/rollbacks/20260727000700_privileged_function_search_path.rollback.sql `
  supabase/tests/database/011_privileged_function_search_path_test.sql `
  scripts/verify_database.ps1 scripts/tests/test_supabase_tooling.py
git commit -m "fix(db): harden privileged function search paths"
```

---

### Task 13: Freeze versions, governance and vertical-flow implementation notes

**Files:**
- Modify: `versions/manifest.json`
- Modify: `CHANGELOG.md`
- Modify: `TASKS.md`
- Modify: `docs/11_AMBIGUITY_REGISTER.md`
- Modify: `docs/12_VERSIONING_AND_RELEASES.md`
- Modify: `docs/decisions/DECISION_LOG.md`
- Create via script: implementation notes for completed Slice 1, 2, 3
- Modify: `docs/implementation-notes/INDEX.md`

**Interfaces:**
- Version targets from specification section 12
- Every note records exact test counts, no claimed actual result before execution

- [ ] **Step 1: Update semantic versions**

Set:

```json
{
  "application": "0.11.0-natural-dialogue",
  "web": "0.7.0-natural-dialogue",
  "api": "4.0.0-draft",
  "shared_contracts": "1.0.0",
  "database_schema": "0.5.0-local",
  "prompt_set": "0.3.0-hybrid-classifier",
  "test_suite": "1.9.0-natural-dialogue"
}
```

Keep official data `.2` and mock data unchanged.

- [ ] **Step 2: Create grouped vertical notes**

Use `scripts/new_implementation_note.py` once per completed slice. Fill 6W1H, RED/GREEN commands,
contract/DB/data/security/accessibility/performance, rollback and human/AI separation.

- [ ] **Step 3: Close resolved ambiguity/task states**

Mark A-053~A-060 implemented only when their acceptance tests have passed. Keep actual/public
status pending until Tasks 15~17 produce evidence.

- [ ] **Step 4: Run documentation/version checks**

```powershell
python -B scripts/check_repository_docs.py
python -B scripts/validate_codex_package.py
git diff --check
```

- [ ] **Step 5: Commit integration documentation**

```powershell
git add versions/manifest.json CHANGELOG.md TASKS.md docs
git commit -m "docs(chat): record natural dialogue implementation"
```

---

### Task 14: Run area and repository integration gates

**Files:**
- Modify only test fixes proven necessary by a failing gate
- Create: `docs/test-reports/CHAT-NATURAL-001-INTEGRATION.md`

- [ ] **Step 1: Run API full gate**

```powershell
apps/api/.venv/Scripts/python.exe -m pytest apps/api/tests -q
apps/api/.venv/Scripts/python.exe -m ruff check apps/api/src apps/api/tests
apps/api/.venv/Scripts/python.exe -m mypy apps/api/src
```

- [ ] **Step 2: Run Web and contract full gate**

```powershell
corepack.cmd pnpm --filter @sejong-ai/shared-contracts generate:check
corepack.cmd pnpm --filter @sejong-ai/shared-contracts test
corepack.cmd pnpm --filter @sejong-ai/web lint
corepack.cmd pnpm --filter @sejong-ai/web typecheck
corepack.cmd pnpm --filter @sejong-ai/web test
corepack.cmd pnpm --filter @sejong-ai/web build
```

- [ ] **Step 3: Run DB and root gates**

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/verify_database.ps1
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/verify.ps1
```

- [ ] **Step 4: Run security/repository checks**

```powershell
python -B scripts/check_repository_docs.py
python -B scripts/validate_codex_package.py
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File scripts/check_secret_patterns.ps1 -RepositoryRoot .
git diff --check
```

- [ ] **Step 5: Record exact evidence**

Write pass/fail/skip counts, command exit codes, environment versions and any bounded non-pass.
Do not paste payloads, DSNs or questions beyond approved synthetic fixture labels.

- [ ] **Step 6: Commit integration evidence**

```powershell
git add docs/test-reports/CHAT-NATURAL-001-INTEGRATION.md `
  docs/implementation-notes docs/implementation-notes/INDEX.md
git commit -m "test(chat): verify natural dialogue integration"
```

---

### Task 15: Run clean local DB reset, formal `.2` seed and 19→20 approval regression

**Files:**
- Create: `docs/test-reports/CHAT-NATURAL-001-LOCAL-DB-ACTUAL.md`
- Modify: current implementation note and INDEX

- [ ] **Step 1: Confirm destructive scope without printing values**

Verify Docker running, target loopback `127.0.0.1:54322`, current branch clean and
`supabase/config.toml` seed disabled. Do not use bare `supabase db reset`.

- [ ] **Step 2: Run supported clean schema gate**

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File scripts/verify_database.ps1
```

- [ ] **Step 3: Run formal immutable `.2` cycle**

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File scripts/verify_data_seed.ps1 `
  -ReleaseVersion 0.1.0-initial.2
```

Expected final projection: ACTIVE 19, official office 3, mapping 10.

- [ ] **Step 4: Provision local application login without output**

```powershell
apps/api/.venv/Scripts/python.exe -B `
  scripts/provision_local_database_login.py
```

- [ ] **Step 5: Reproduce the approved 19→20 workflow**

Run:

```powershell
apps/api/.venv/Scripts/python.exe -B scripts/verify_actual_mvp_regression.py
```

The harness creates one PII-free INSUFFICIENT_GROUNDING failure, confirms reason, creates a
candidate, proves same-writer block, approves with PM-LOCAL-001, then requeries. Assert ACTIVE 20,
source bound, `/ready=200`. Never print the raw DB row or credential.

- [ ] **Step 6: Record bounded result**

Report phase names, counts, status codes and source ID only. On any failure, keep official data
version `.2`, do not claim readiness, and record the exact phase plus bounded error code.

- [ ] **Step 7: Commit local actual evidence**

```powershell
git add docs/test-reports/CHAT-NATURAL-001-LOCAL-DB-ACTUAL.md `
  docs/implementation-notes docs/implementation-notes/INDEX.md
git commit -m "test(db): record natural dialogue local actual"
```

---

### Task 16: Run the actual PII-free Upstage classifier acceptance

**Files:**
- Create: `apps/api/tests/fixtures/classifier-60.json`
- Create: `scripts/run_upstage_classifier_evaluation.py`
- Create: `scripts/tests/test_upstage_classifier_evaluation.py`
- Create: `docs/runbooks/UPSTAGE-CLASSIFIER-ACTUAL.md`
- Create: `docs/test-reports/CHAT-NATURAL-001-UPSTAGE-ACTUAL.md`
- Create via `scripts/new_implementation_note.py`: `CHAT-NATURAL-001 actual classifier 실행`
- Modify: `docs/implementation-notes/INDEX.md`

**Interfaces:**
- 60 fixtures: supported 20, non-civic 10, scope gap 10, followup 10, policy/privacy 10
- Policy/privacy cases prove outbound 0

- [ ] **Step 1: Build and validate the frozen fixture offline**

Fixture includes only synthetic PII-free Korean and expected closed route. Validate exact group
counts, unique IDs, no secret patterns and no real person/contact/address identifiers.

- [ ] **Step 2: Run offline adapter and report tests**

```powershell
apps/api/.venv/Scripts/python.exe -m pytest `
  apps/api/tests/llm/test_upstage_classifier.py `
  scripts/tests/test_upstage_classifier_evaluation.py `
  -q
```

- [ ] **Step 3: Preflight settings by presence only**

Load classifier settings through the fail-closed loader. Output only mode/model/caps, never the key.
Abort before network if exact profile or USD 0.05 stop configuration is invalid.

- [ ] **Step 4: Run actual evaluation once**

```powershell
apps/api/.venv/Scripts/python.exe -B `
  scripts/run_upstage_classifier_evaluation.py `
  --fixture apps/api/tests/fixtures/classifier-60.json `
  --report docs/test-reports/CHAT-NATURAL-001-UPSTAGE-ACTUAL.md
```

The 60-case fixture must contain exactly 20 ambiguous provider cases and 40 deterministic cases.
The runner sends only those 20 safe ambiguous cases, keeps deterministic policy/privacy outbound
0, enforces sub-cap/combined cap and stops before an attempt that could exceed USD 0.05.

- [ ] **Step 5: Restore provider modes**

Restore `UPSTAGE_CLASSIFIER_MODE=false` and `UPSTAGE_GROUNDED_CHAT_MODE=false` in local environment
unless the explicit demo command is running. Verify no mode/key entered tracked files.

- [ ] **Step 6: Commit report without payload**

```powershell
git add apps/api/tests/fixtures/classifier-60.json `
  scripts/run_upstage_classifier_evaluation.py `
  scripts/tests/test_upstage_classifier_evaluation.py `
  docs/test-reports/CHAT-NATURAL-001-UPSTAGE-ACTUAL.md `
  docs/implementation-notes docs/implementation-notes/INDEX.md
git commit -m "test(llm): record bounded classifier actual"
```

---

### Task 17: Verify configured remote citizen deployment safely

**Files:**
- Create: `docs/runbooks/CONTROLLED-PUBLIC-CITIZEN-DEPLOYMENT.md`
- Create: `docs/test-reports/CHAT-NATURAL-001-REMOTE-VERIFICATION.md`
- Modify: final implementation note and INDEX

**Interfaces:**
- Citizen paths: `/health`, `/ready`, `/api/v1/chat`, `/api/v1/offices`
- Negative paths: `/admin`, `/api/v1/admin/*`

- [ ] **Step 1: Discover tracked deployment configuration and secret presence**

Run:

```powershell
rg --files -g "vercel.json" -g "render.yaml" -g ".openai/hosting.json" `
  -g "supabase/config.toml" -g ".github/workflows/*.yml"
Get-ChildItem Env: | Where-Object {
  $_.Name -match '^(VERCEL|RENDER|SUPABASE|DATABASE|NEXT_PUBLIC)_'
} | Select-Object -ExpandProperty Name
```

Record provider/project/region names only when already configured. Do not display values. If no
target/project ID exists, set outcome exactly `Not executed: target not configured` and continue
to Step 6. Plan-author discovery found only local `supabase/config.toml` and no matching remote
environment variable names, so `Not executed` is the expected current result.

- [ ] **Step 2: Preflight public hardening**

Require Task 12 full DB PASS, CORS exact citizen origin, request-body logging off, admin disabled,
provider disabled, secret scan PASS and a rollback version identifier.

- [ ] **Step 3: Apply reviewed remote migrations**

This step is conditional on a future discovery result that identifies a tracked, reviewed remote
mechanism and dedicated demo target. Apply 00680 then 00700 only through that exact mechanism. Do
not use bare Supabase commands and do not seed automatically. Run immutable `.2` formal remote
import only if the supported importer validates remote identity. With the current discovery result,
record this step as not executed.

- [ ] **Step 4: Deploy saved version and smoke**

Deploy the exact committed source. Verify health/ready/offices and one synthetic supported chat.
Assert server-bound official source and provider outbound 0.

- [ ] **Step 5: Prove admin negative and rollback readiness**

Assert `/admin` is unavailable/disabled and `/api/v1/admin/failed-questions` cannot execute.
Record rollback version and command without secret values.

- [ ] **Step 6: Write remote report**

Record source SHA, target label, migration/version label, status codes, admin negative result,
provider calls 0 and any non-execution reason. Never record URL query secrets or credentials.

- [ ] **Step 7: Commit remote evidence**

```powershell
git add docs/test-reports/CHAT-NATURAL-001-REMOTE-VERIFICATION.md `
  docs/implementation-notes docs/implementation-notes/INDEX.md
git commit -m "docs(deploy): record controlled citizen verification"
```

---

### Task 18: Final verification, self-review and Draft PR

**Files:**
- Modify: final implementation note, `TASKS.md`, `CHANGELOG.md`, `versions/manifest.json`
- No product change unless a verified defect is fixed with a focused RED/GREEN cycle

- [ ] **Step 1: Run the final repository gate once**

Repeat Task 14 after actual/remote evidence. Every command must use the final tracked source.

- [ ] **Step 2: Scan for leaks and forbidden scope**

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File scripts/check_secret_patterns.ps1 -RepositoryRoot .
rg -n \"LLM_API_KEY=.+|postgres(ql)?://|masked_question.*실제\" .
git diff origin/main...HEAD --check
```

Expected: findings 0; any matches are safe examples explicitly reviewed.

- [ ] **Step 3: Review contract/DB/source authority**

Confirm generated diff 0, migrations/rollbacks 11 each, pgTAP files 11, old migrations and `.2`
release unchanged, public source cards server-bound, admin remote off.

- [ ] **Step 4: Review user-visible acceptance**

Run reported 4 questions, 5 followups, new conversation, region change, scope admin and general
candidate E2E. Record exact pass/skip counts.

- [ ] **Step 5: Complete final implementation note**

Separate:

- 인간이 알아야 하는 actual cost, DB reset, remote status, public limitation and residual risks
- AI internal helpers, fixture and refactoring details

- [ ] **Step 6: Commit final closeout**

```powershell
git add CHANGELOG.md TASKS.md versions/manifest.json docs
git commit -m "docs(chat): close natural dialogue delivery"
```

- [ ] **Step 7: Push branch and create Draft PR**

```powershell
git push -u origin codex/ACTUAL-P0-UX-GAPS-001
```

Create a Draft PR to `main` with spec, migrations, breaking contract, test counts, actual cost,
remote status and rollback. Do not merge it.

---

## Plan self-review

### 1. Spec coverage

- PII false positive: Task 1
- hybrid closed classifier and caps: Tasks 2~5
- breaking civic scope response: Task 4
- certificate and five contextual followups: Tasks 5~8
- context v2 and new conversation/region: Tasks 6~8
- scope queue DB/API/admin: Tasks 9~11
- general candidate form/state: Task 11
- 00700 public hardening: Task 12
- versions/docs/full gates: Tasks 13~14
- clean DB/19→20, actual provider, remote: Tasks 15~17
- final security/diff/PR: Task 18

Coverage gaps: none.

### 2. Placeholder scan

The plan contains exact file names, type names, enum values, commands, expected outcomes and
rollback boundaries. The only triple-dot token is Git's literal `origin/main...HEAD` symmetric
difference syntax, not an implementation marker.

### 3. Type consistency

- `ClassifierRoute`, `PendingSlot`, `ClassifierDecision` names are consistent across Tasks 2~5.
- `CIVIC_SCOPE_GAP` maps to public OUT_OF_SCOPE and never to candidate eligibility.
- context uses `pending_slot`; Web only sends existing `selected_region` and `context_token`.
- SQL review capability has five arguments matching repository SQL.
- rollback order is 00700→00680→00670 and current migration byte remains immutable.
- current remote discovery has no target/project credential names, so Task 17 has an exact
  non-execution result instead of an invented deployment.

## Execution handoff

The user already authorized immediate continuation after plan review. Use
`superpowers:executing-plans` in this session, implement in task order, run focused tests at each
RED/GREEN boundary, area gates after each slice and the full gate only at Tasks 14 and 18.
