# Grounded Upstage Local Chat Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an explicitly enabled local/private Upstage `solar-pro3` generation attempt to the
existing grounded `/api/v1/chat` SUCCESS path while keeping policy, official facts, sources and all
failure behavior under deterministic server control.

**Architecture:** The existing redact → classify → ACTIVE/OFFICIAL retrieve → grounding flow remains
the authority. After grounding, an optional internal generator receives only the masked current
question and a bounded list of server-issued fact IDs with official text. The model may return one
bounded summary and those IDs. Pure server code validates the summary and IDs, materializes every
administrative fact from the retrieved `KnowledgeRecord`, and binds source/office metadata. Any
disabled state, exception, timeout, cap, schema error, unknown ID or fact drift discards the complete
draft and returns the existing deterministic SUCCESS template. Durable idempotency claims happen
before generation, so concurrent/same-key replays do not start a second provider request.

**Tech Stack:** Python 3.12.13, FastAPI 0.139.0, Pydantic 2.13.4, existing
`httpx==0.28.1`, Psycopg 3.3.4, pytest 9.1.1, Node 24.12.0, pnpm 11.13.0, Next.js
16.2.10, React 19.2.7, TypeScript 5.9.3, Vitest 4.1.10.

- Plan ID: LLM-003-PLAN
- Status: **Complete for approved local/private scope: offline implementation, Task 8 closeout,
  provider-disabled final root gate and D-075 local actual PASS. Public/remote remains prohibited.**
- Design:
  `docs/superpowers/specs/2026-07-25-grounded-live-chat-generation-design.md`
- ADR: `docs/adr/0023-grounded-upstage-local-chat-generation.md`
- Decisions: Q-LLM-006~Q-LLM-012 / D-072 / D-073 / D-074
- Execution base: `de1ee096d6e27b0a326dfaa0c93f72baf0c5f1c0`
- D-074 authorizes implementation and the additive API mutation in this plan. D-075 separately
  authorizes and records the local actual call. DB migration, public/remote use, push, PR and merge
  remain separately gated as stated below.

## Global Constraints

- Scope is local/private only. Public/remote deployment, real institutional operation and remote DB
  remain prohibited.
- Provider/model/base URL are exactly `upstage`, `solar-pro3`,
  `https://api.upstage.ai/v1`.
- Grounded chat mode is disabled by default and is mutually exclusive with synthetic evaluation
  mode.
- A provider call is allowed only after safe masking, supported deterministic intent,
  ACTIVE/OFFICIAL retrieval and the existing grounding gate all pass.
- `FOLLOWUP`, `PRIVACY_UNRESOLVED`, `INSUFFICIENT_GROUNDING`, `PERSONAL_LOOKUP`,
  `LEGAL_JUDGMENT`, `OUT_OF_SCOPE` and system-unavailable paths make exactly zero provider calls.
- The provider cannot set intent, answer status, fallback reason, candidate eligibility, source,
  office, context, official fact text or KB state.
- Exact runtime limits are timeout 8 seconds, logical attempt 1, hidden transport retry 0,
  concurrency 1, max input 4096, max output 1024 and non-resettable process attempt cap 30.
- The same valid `Idempotency-Key` and request digest may initiate at most one provider call while
  its durable claim is active. A concurrent `IN_PROGRESS` replay returns a deterministic template
  without provider use or a duplicate interaction write. A completed replay uses the persisted safe
  response. Commit uncertainty returns the existing service-unavailable outcome and never triggers
  an automatic provider retry.
- No new DB migration is added. Existing `00660` durable idempotency storage may retain the strictly
  validated final safe response for its logical 24-hour TTL only when a caller supplies
  `Idempotency-Key`. Raw/masked questions, prompt, provider body, context token, request/correlation
  ID and secret remain forbidden. This is the explicit exception to the broad “generated answer is
  not persisted” wording; no other persistence is introduced.
- No new production dependency and no lockfile regeneration.
- No raw/masked question, prompt, provider request/response or generated answer is logged, traced or
  written to a file. Only content-free bounded outcome/attempt/token/latency aggregates are allowed.
- Source title, URL, verified date and office are always assembled from server-owned records and
  must remain present for `GENERATED` and `TEMPLATE`.
- Each implementation task follows RED → focused RED evidence → minimal GREEN → focused gate →
  diff/security review → one reviewable commit.
- The actual network acceptance run is a separate final local human gate after all offline tests
  pass. It must use the ignored local key, print no question/answer/provider body, and never run in
  Cloud or CI.

Before the first Python command in a Windows worktree, resolve the repository-owned `uv` binary:

```powershell
$commonGitDir = git rev-parse --path-format=absolute --git-common-dir
$uv = Join-Path (Split-Path $commonGitDir -Parent) ".tools\uv\uv.exe"
if (-not (Test-Path -LiteralPath $uv)) {
  throw "PROJECT_UV_NOT_FOUND"
}
```

Every Python command below uses this resolved binary and `--frozen`; no tool or dependency is
downloaded.

---

## File and Responsibility Map

| File | Responsibility |
|---|---|
| `contracts/openapi-v1.yaml` | Public `answer_mode` enum on SUCCESS and API `3.2.0-draft` |
| `contracts/chat-response.schema.json` | JSON Schema mirror of the SUCCESS discriminator contract |
| `contracts/fixtures/chat-response/*.json` | Valid/invalid contract evidence with required mode |
| `packages/shared-contracts/src/generated/api.ts` | Generated TypeScript API types |
| `packages/shared-contracts/test/type-fixtures/chat-response-types.ts` | Compile-time mode fixtures |
| `apps/api/src/sejong_ai_api/contracts/chat.py` | Strict Pydantic `AnswerMode`/SUCCESS model |
| `apps/api/src/sejong_ai_api/chat/response.py` | Server-owned template/generated response assembly |
| `apps/api/src/sejong_ai_api/llm/chat_contracts.py` | Provider-neutral grounded draft/result protocol |
| `apps/api/src/sejong_ai_api/llm/facts.py` | Fact ID issuance, summary validation and materialization |
| `apps/api/src/sejong_ai_api/llm/chat_prompt.py` | Source-free bounded prompt and input preflight |
| `apps/api/src/sejong_ai_api/llm/upstage_chat.py` | One-attempt HTTPX grounded-chat adapter/runtime |
| `apps/api/src/sejong_ai_api/llm/settings.py` | Mutually exclusive exact synthetic/chat profiles |
| `apps/api/src/sejong_ai_api/chat/service.py` | Post-grounding generation gate and idempotent fallback |
| `apps/api/src/sejong_ai_api/local.py` | Optional local runtime composition and client lifecycle |
| `apps/api/.env.example` | Disabled-by-default exact profile example without a key |
| `apps/web/src/components/citizen/AnswerCard.tsx` | Accessible answer-mode label and disclosure |
| `apps/web/src/app/chat/*.test.tsx` | Generated/template rendering and source/a11y regression |
| `docs/test-reports/LLM-003-GROUNDED-LIVE-CHAT.md` | Text-free offline/optional actual acceptance evidence |

The implementation must not add a public LLM router, expose provider details in HTTP responses,
import provider code into `sejong_ai_api.main`, modify official data, or modify DB migrations.

---

### Task 1: Freeze the additive SUCCESS `answer_mode` contract

**Files:**
- Modify: `contracts/openapi-v1.yaml`
- Modify: `contracts/chat-response.schema.json`
- Modify: `contracts/fixtures/chat-response/valid-success.json`
- Modify: `contracts/fixtures/chat-response/invalid-success-empty-sources.json`
- Modify: `contracts/fixtures/chat-response/invalid-success-fallback.json`
- Modify: `packages/shared-contracts/test/type-fixtures/chat-response-types.ts`
- Regenerate: `packages/shared-contracts/src/generated/api.ts`
- Modify: `apps/api/src/sejong_ai_api/contracts/chat.py`
- Modify: `apps/api/src/sejong_ai_api/chat/response.py`
- Modify: `apps/api/tests/chat/test_response.py`
- Modify: `apps/api/tests/chat/test_service.py`
- Modify: `apps/api/tests/test_chat_contract_fixtures.py`
- Modify: `apps/api/src/sejong_ai_api/main.py`

**Interfaces:**

```python
type AnswerMode = Literal["GENERATED", "TEMPLATE"]

class SuccessResponse(ChatResponseBase):
    answer_status: Literal["SUCCESS"]
    answer_mode: AnswerMode
    # existing fields remain unchanged

def build_success_response(
    *,
    request_id: UUID,
    record: KnowledgeRecord,
    office: OfficeRecord | None,
    confidence: float,
    context_token: str | None,
) -> SuccessResponse: ...
```

At this baseline task the response builder always sets `answer_mode="TEMPLATE"` internally. It does
not accept generated content or import the Task 2 types. Task 5 will extend this internal builder
only after `MaterializedChatAnswer` exists. In all modes source and office remain built from
`KnowledgeRecord` and `OfficeRecord`.

- [x] **Step 1: Write contract and response RED tests**

Add assertions that:

```python
response = build_success_response(
    request_id=REQUEST_ID,
    record=record,
    office=None,
    confidence=0.99,
    context_token=None,
)
assert response.answer_mode == "TEMPLATE"
assert SuccessResponse.model_validate(
    {**response.model_dump(mode="json"), "answer_mode": "GENERATED"}
).answer_mode == "GENERATED"
```

Contract fixtures must reject a missing mode and any value outside `GENERATED|TEMPLATE`. Existing
empty-source and fallback-on-SUCCESS fixtures remain invalid after receiving `answer_mode`.

- [x] **Step 2: Run RED**

```powershell
& $uv run --project apps/api --frozen pytest `
  apps/api/tests/chat/test_response.py `
  apps/api/tests/test_chat_contract_fixtures.py -q
corepack pnpm --filter @sejong-ai/shared-contracts test
```

Expected: failures for the absent Pydantic/OpenAPI/JSON Schema field and stale TypeScript fixtures.

- [x] **Step 3: Add the minimal additive contract**

Set OpenAPI info/API app version to `3.2.0-draft`; require `answer_mode` only in the SUCCESS branch.
Do not add the field to FOLLOWUP or FALLBACK. Add `answer_mode="TEMPLATE"` to all deterministic
server response construction and fixtures.

- [x] **Step 4: Generate and verify**

```powershell
corepack pnpm --filter @sejong-ai/shared-contracts generate
corepack pnpm --filter @sejong-ai/shared-contracts generate:check
corepack pnpm --filter @sejong-ai/shared-contracts test
& $uv run --project apps/api --frozen pytest `
  apps/api/tests/chat/test_response.py `
  apps/api/tests/chat/test_service.py `
  apps/api/tests/test_chat_contract_fixtures.py -q
git diff --check -- packages/shared-contracts/src/generated/api.ts
```

Expected: all PASS and a clean post-generation diff check.

- [x] **Step 5: Review and commit**

Verify every SUCCESS fixture has one mode, sources remain non-empty, non-SUCCESS schemas have no
mode, and no generated type was hand-edited.

```powershell
git add contracts packages/shared-contracts apps/api/src/sejong_ai_api/contracts/chat.py `
  apps/api/src/sejong_ai_api/chat/response.py apps/api/src/sejong_ai_api/main.py `
  apps/api/tests/chat apps/api/tests/test_chat_contract_fixtures.py
git commit -m "feat(contract): expose chat answer mode"
```

---

### Task 2: Add pure fact-ID and summary validation

**Files:**
- Create: `apps/api/src/sejong_ai_api/llm/chat_contracts.py`
- Create: `apps/api/src/sejong_ai_api/llm/facts.py`
- Create: `apps/api/tests/llm/test_chat_contracts.py`
- Create: `apps/api/tests/llm/test_facts.py`
- Modify: `apps/api/src/sejong_ai_api/llm/__init__.py`

**Interfaces:**

```python
class FactKind(StrEnum):
    PROCEDURE_STEP = "PROCEDURE_STEP"
    REQUIRED_DOCUMENT = "REQUIRED_DOCUMENT"
    PROCESSING_TIME = "PROCESSING_TIME"
    FEE = "FEE"
    DEPARTMENT = "DEPARTMENT"

@dataclass(frozen=True, slots=True)
class GroundedFact:
    fact_id: str
    kind: FactKind
    text: str

@dataclass(frozen=True, slots=True)
class GroundedChatRequest:
    masked_question: str
    intent: Intent
    service_name: str
    approved_summary: str
    facts: tuple[GroundedFact, ...]

class GeneratedChatDraft(StrictPublicModel):
    summary: Annotated[str, Field(min_length=1, max_length=500)]
    procedure_step_ids: Annotated[list[str], Field(max_length=12)]
    required_document_ids: Annotated[list[str], Field(max_length=12)]
    processing_time_id: str | None
    fee_id: str | None
    department_id: str

@dataclass(frozen=True, slots=True)
class MaterializedChatAnswer:
    summary: str
    procedure_steps: tuple[str, ...]
    required_documents: tuple[str, ...]
    processing_time: str | None
    fee: str | None
    department: str

class GroundedChatOutcomeCode(StrEnum):
    SUCCESS = "SUCCESS"
    ATTEMPT_CAP = "ATTEMPT_CAP"
    TIMEOUT = "TIMEOUT"
    TRANSPORT = "TRANSPORT"
    RATE_LIMIT = "RATE_LIMIT"
    AUTH = "AUTH"
    HTTP_ERROR = "HTTP_ERROR"
    EMPTY = "EMPTY"
    TRUNCATED = "TRUNCATED"
    SCHEMA_INVALID = "SCHEMA_INVALID"
    INPUT_LIMIT = "INPUT_LIMIT"

class GroundedAnswerGenerator(Protocol):
    async def generate(self, request: GroundedChatRequest) -> GroundedChatResult: ...

def build_grounded_chat_request(
    *,
    masked_question: str,
    intent: Intent,
    record: KnowledgeRecord,
) -> GroundedChatRequest: ...

def materialize_grounded_answer(
    request: GroundedChatRequest,
    draft: GeneratedChatDraft,
) -> MaterializedChatAnswer | None: ...
```

Fact IDs are request-local and exact:

```text
STEP-01..STEP-12
DOC-01..DOC-12
TIME-01
FEE-01
DEPT-01
```

The draft must return the complete ordered set of step/document IDs, the exact optional time/fee
presence, and `DEPT-01`; unknown, missing, reordered or duplicate IDs fail the whole draft.

Summary validation is fail-closed:

1. NFKC, non-empty, maximum 500 characters and safe Unicode.
2. A second `redact_question(summary)` must return the identical safe text.
3. No URL, email, phone-shaped value, mask token or control character.
4. Every number/date/currency-shaped token must occur exactly in the canonical record corpus.
5. Significant Korean/ASCII tokens, after a fixed conservative Korean particle suffix strip, must
   occur in the canonical record corpus or the explicit non-factual presentation lexicon
   `{"공식", "안내", "정보", "쉽게", "정리", "확인", "드려요"}`.
6. At least one significant token must overlap the record corpus.

False rejection is acceptable and produces TEMPLATE; false acceptance of a new fact is not.

- [x] **Step 1: Write pure RED tests**

Cover valid complete materialization and each rejection class: extra field, unknown ID, duplicate,
missing/reordered ID, optional mismatch, PII, new URL/number/date/money, mask token, unsupported
semantic token and no record overlap. Assert official field equality byte-for-byte.

- [x] **Step 2: Run RED**

```powershell
& $uv run --project apps/api --frozen pytest `
  apps/api/tests/llm/test_chat_contracts.py `
  apps/api/tests/llm/test_facts.py -q
```

Expected: import failure for the two new modules.

- [x] **Step 3: Implement pure types and validator**

Keep these modules free of HTTP, DB, environment and logging imports. Construct facts only from the
single grounded record and never include `public_id`, question examples, caution, source or office.

- [x] **Step 4: Run focused static gates**

```powershell
& $uv run --project apps/api --frozen pytest `
  apps/api/tests/llm/test_chat_contracts.py `
  apps/api/tests/llm/test_facts.py -q
& $uv run --project apps/api --frozen ruff format --check `
  apps/api/src/sejong_ai_api/llm apps/api/tests/llm
& $uv run --project apps/api --frozen ruff check `
  apps/api/src/sejong_ai_api/llm apps/api/tests/llm
& $uv run --project apps/api --frozen mypy `
  apps/api/src/sejong_ai_api/llm apps/api/tests/llm
```

- [x] **Step 5: Review and commit**

```powershell
git add apps/api/src/sejong_ai_api/llm apps/api/tests/llm
git commit -m "feat(llm): validate server-issued chat facts"
```

---

### Task 3: Separate exact synthetic and grounded-chat settings

**Files:**
- Modify: `apps/api/src/sejong_ai_api/llm/settings.py`
- Modify: `apps/api/tests/llm/test_settings.py`
- Modify: `apps/api/.env.example`
- Modify: `scripts/run_upstage_synthetic_evaluation.py`
- Modify: `scripts/tests/test_run_upstage_synthetic_evaluation.py`

**Interfaces:**

```python
@dataclass(frozen=True, slots=True)
class UpstageChatSettings:
    api_key: str = field(repr=False)
    provider: str = "upstage"
    model: str = "solar-pro3"
    base_url: str = "https://api.upstage.ai/v1"
    timeout_seconds: float = 8.0
    max_retries: int = 0
    max_concurrency: int = 1
    max_input_tokens: int = 4096
    max_output_tokens: int = 1024
    run_attempt_cap: int = 30

def load_upstage_chat_settings(
    *,
    environ: Mapping[str, str] | None = None,
    env_path: Path | None = None,
) -> UpstageChatSettings | None: ...
```

Exact chat profile:

```dotenv
LLM_PROVIDER=upstage
LLM_MODEL=solar-pro3
LLM_BASE_URL=https://api.upstage.ai/v1
LLM_TIMEOUT_SECONDS=8
LLM_MAX_RETRIES=0
LLM_MAX_CONCURRENCY=1
LLM_MAX_INPUT_TOKENS=4096
LLM_MAX_OUTPUT_TOKENS=1024
LLM_RUN_ATTEMPT_CAP=30
UPSTAGE_SYNTHETIC_EVALUATION_MODE=false
UPSTAGE_GROUNDED_CHAT_MODE=true
```

The key must be non-empty and is never represented. The synthetic profile keeps its existing
15-second/one-retry exact values and requires synthetic true/chat false. Chat requires chat
true/synthetic false. Both true, both provider modes active, non-exact values, malformed `.env` or
missing key return `None`. `.env.example` remains disabled and keyless, with grounded-chat values
8/0 documented as the citizen profile; the synthetic runbook retains its explicit 15/1 override.

- [x] **Step 1: Write settings RED tests**

Test exact chat load, disabled default, exclusivity, every exact field, redacted repr, duplicate
assignment, process-over-file precedence and preservation of the synthetic loader.

- [x] **Step 2: Run RED**

```powershell
& $uv run --project apps/api --frozen pytest `
  apps/api/tests/llm/test_settings.py `
  scripts/tests/test_run_upstage_synthetic_evaluation.py -q
```

- [x] **Step 3: Implement one shared safe parser and two exact profile validators**

Do not read the key unless the selected mode and all non-secret exact values pass. Do not log or
raise a value-bearing configuration error. Do not alter the ignored real `.env`.

- [x] **Step 4: Run focused gates**

```powershell
& $uv run --project apps/api --frozen pytest `
  apps/api/tests/llm/test_settings.py `
  scripts/tests/test_run_upstage_synthetic_evaluation.py -q
& $uv run --project apps/api --frozen ruff check `
  apps/api/src/sejong_ai_api/llm/settings.py `
  apps/api/tests/llm/test_settings.py `
  scripts/run_upstage_synthetic_evaluation.py `
  scripts/tests/test_run_upstage_synthetic_evaluation.py
& $uv run --project apps/api --frozen mypy `
  apps/api/src/sejong_ai_api/llm/settings.py `
  apps/api/tests/llm/test_settings.py
```

- [x] **Step 5: Review and commit**

Verify no key value, dependency or lockfile changed.

```powershell
git add apps/api/.env.example apps/api/src/sejong_ai_api/llm/settings.py `
  apps/api/tests/llm/test_settings.py scripts/run_upstage_synthetic_evaluation.py `
  scripts/tests/test_run_upstage_synthetic_evaluation.py
git commit -m "feat(llm): add fail-closed grounded chat profile"
```

---

### Task 4: Build the source-free one-attempt Upstage adapter

**Files:**
- Create: `apps/api/src/sejong_ai_api/llm/chat_prompt.py`
- Create: `apps/api/src/sejong_ai_api/llm/upstage_chat.py`
- Create: `apps/api/tests/llm/test_chat_prompt.py`
- Create: `apps/api/tests/llm/test_upstage_chat.py`
- Modify: `apps/api/src/sejong_ai_api/llm/__init__.py`

**Interfaces:**

```python
def build_grounded_chat_messages(
    request: GroundedChatRequest,
) -> tuple[dict[str, str], ...]: ...

def estimate_grounded_input_upper_bound(
    messages: tuple[dict[str, str], ...],
) -> int: ...

def create_upstage_chat_client(settings: UpstageChatSettings) -> httpx.AsyncClient: ...

class UpstageChatGenerator:
    def __init__(
        self,
        *,
        settings: UpstageChatSettings,
        client: httpx.AsyncClient,
        budget: AttemptBudget,
    ) -> None: ...

    async def generate(self, request: GroundedChatRequest) -> GroundedChatResult: ...

@dataclass(frozen=True, slots=True)
class GroundedChatRuntime:
    generator: GroundedAnswerGenerator
    client: httpx.AsyncClient

    async def aclose(self) -> None: ...

def build_upstage_chat_runtime(settings: UpstageChatSettings) -> GroundedChatRuntime: ...
```

The prompt payload contains only:

```json
{
  "masked_question": "...",
  "intent": "SUPPORTED_ENUM",
  "service_name": "...",
  "approved_summary": "...",
  "facts": [{"id": "STEP-01", "kind": "PROCEDURE_STEP", "text": "..."}],
  "output_schema": {
    "summary": "string<=500",
    "procedure_step_ids": ["STEP-.."],
    "required_document_ids": ["DOC-.."],
    "processing_time_id": "TIME-01|null",
    "fee_id": "FEE-01|null",
    "department_id": "DEPT-01"
  }
}
```

No source, URL, verified date, office, `public_id`, context, question examples, caution or internal
identifier is present. The transport uses `httpx.AsyncHTTPTransport(retries=0)`,
`httpx.Timeout(8.0, connect=5.0, read=8.0, write=8.0, pool=8.0)`, one budget reservation and no loop.
The request sets exact model, `stream=false`, `temperature=0.1`, `max_tokens=1024`. Every provider
response is reduced to a typed content-free outcome; body/error text is never raised or logged.

- [x] **Step 1: Write prompt and transport RED tests**

Use `httpx.MockTransport`. Assert source/internal fields and sentinel secrets are absent from the
serialized request. Cover success, timeout, transport, 401/403, 429, 5xx, other HTTP, empty,
truncated, invalid JSON, strict schema invalid, input limit and cap. Assert request count is 0 or 1
and never 2.

- [x] **Step 2: Run RED**

```powershell
& $uv run --project apps/api --frozen pytest `
  apps/api/tests/llm/test_chat_prompt.py `
  apps/api/tests/llm/test_upstage_chat.py -q
```

- [x] **Step 3: Implement prompt, parser, adapter and runtime**

Reuse `AttemptBudget`; do not change the synthetic `UpstageProvider`. The new adapter must not
import FastAPI, repository or Web modules.

- [x] **Step 4: Run focused gates**

```powershell
& $uv run --project apps/api --frozen pytest `
  apps/api/tests/llm/test_chat_prompt.py `
  apps/api/tests/llm/test_upstage_chat.py `
  apps/api/tests/llm/test_upstage.py `
  apps/api/tests/llm/test_limits.py -q
& $uv run --project apps/api --frozen ruff format --check `
  apps/api/src/sejong_ai_api/llm apps/api/tests/llm
& $uv run --project apps/api --frozen ruff check `
  apps/api/src/sejong_ai_api/llm apps/api/tests/llm
& $uv run --project apps/api --frozen mypy `
  apps/api/src/sejong_ai_api/llm apps/api/tests/llm
```

- [x] **Step 5: Review and commit**

```powershell
git add apps/api/src/sejong_ai_api/llm apps/api/tests/llm
git commit -m "feat(llm): add bounded grounded chat adapter"
```

---

### Task 5: Integrate post-grounding generation with durable idempotency

**Files:**
- Modify: `apps/api/src/sejong_ai_api/chat/service.py`
- Modify: `apps/api/src/sejong_ai_api/chat/response.py`
- Modify: `apps/api/src/sejong_ai_api/chat/idempotency.py`
- Modify: `apps/api/tests/chat/test_service.py`
- Modify: `apps/api/tests/chat/test_idempotency.py`
- Create: `apps/api/tests/chat/test_grounded_generation.py`
- Modify: `apps/api/tests/chat/test_sample_questions_20.py`

**Interfaces:**

```python
def build_success_response(
    *,
    request_id: UUID,
    record: KnowledgeRecord,
    office: OfficeRecord | None,
    confidence: float,
    context_token: str | None,
    answer_mode: AnswerMode = "TEMPLATE",
    answer: MaterializedChatAnswer | None = None,
) -> SuccessResponse: ...

class ChatService:
    def __init__(
        ...,
        answer_generator: GroundedAnswerGenerator | None = None,
    ) -> None: ...

    async def _execute_once(
        self,
        request: ChatRequest,
        *,
        request_id: UUID | None = None,
        allow_generation: bool = True,
    ) -> _ChatExecution: ...
```

`answer=None` is valid only with `TEMPLATE`; `GENERATED` requires one already validated
`MaterializedChatAnswer`. The builder still derives source and office exclusively from the trusted
record arguments.

After `evaluate_grounding` succeeds:

```python
answer_mode: AnswerMode = "TEMPLATE"
materialized: MaterializedChatAnswer | None = None
if allow_generation and self._answer_generator is not None:
    grounded_request = build_grounded_chat_request(
        masked_question=safe_question.text,
        intent=intent,
        record=grounding.record,
    )
    try:
        result = await self._answer_generator.generate(grounded_request)
    except Exception:
        result = None
    if result is not None and result.code is GroundedChatOutcomeCode.SUCCESS:
        materialized = materialize_grounded_answer(grounded_request, result.draft)
        if materialized is not None:
            answer_mode = "GENERATED"
```

The response builder receives `answer_mode` and `materialized`. All failures use `TEMPLATE`.
Provider result/error data is not added to the interaction record.

Idempotency behavior:

- claim before `_execute_once`
- `COMPLETED`: replay the stored strictly validated safe response, no provider call
- `IN_PROGRESS`: call `_execute_once(..., allow_generation=False)`, return TEMPLATE, do not write a
  second interaction and do not abandon/complete the other claim
- `CONFLICT`: preserve the existing conflict response
- `ACQUIRED`: at most one generator call, then atomically commit safe response + interaction
- DB/commit uncertainty: preserve fail-closed service unavailable; no automatic provider retry

The safe response validator allows `answer_mode` but continues to reject question, prompt,
provider body, context token, request/correlation ID and related keys recursively.

- [x] **Step 1: Write integration RED tests**

Create a counting fake generator and assert:

1. grounded supported request → one call → GENERATED
2. generator disabled → TEMPLATE
3. every policy/followup/IG path → zero calls
4. all typed provider failures/exceptions → TEMPLATE HTTP-success model
5. invalid summary/IDs → TEMPLATE with complete official fields
6. generated source/office/intent/status equal the template response
7. completed same-key replay → call count 1
8. concurrent/in-progress replay → deterministic TEMPLATE and call count at most 1
9. cap path → zero transport after cap and TEMPLATE
10. sample 20/20 remains pass with generator disabled

- [x] **Step 2: Run RED**

```powershell
& $uv run --project apps/api --frozen pytest `
  apps/api/tests/chat/test_grounded_generation.py `
  apps/api/tests/chat/test_idempotency.py `
  apps/api/tests/chat/test_sample_questions_20.py -q
```

- [x] **Step 3: Implement the minimal post-grounding gate**

Do not call the generator before grounding and do not add generation to fallback builders. Preserve
`PERSONAL_LOOKUP`/`LEGAL_JUDGMENT` complete non-persistence.

- [x] **Step 4: Run the chat area gate**

```powershell
& $uv run --project apps/api --frozen pytest apps/api/tests/chat -q
& $uv run --project apps/api --frozen ruff check `
  apps/api/src/sejong_ai_api/chat apps/api/tests/chat
& $uv run --project apps/api --frozen mypy `
  apps/api/src/sejong_ai_api/chat apps/api/tests/chat
```

- [x] **Step 5: Review and commit**

Review specifically for pre-grounding imports/calls, content logging, source mutation, interaction
payload changes and exception leakage.

```powershell
git add apps/api/src/sejong_ai_api/chat apps/api/tests/chat
git commit -m "feat(chat): add grounded generation fallback"
```

---

### Task 6: Compose and close the optional local runtime

**Files:**
- Modify: `apps/api/src/sejong_ai_api/local.py`
- Modify: `apps/api/tests/test_local.py`
- Modify: `apps/api/tests/test_architecture.py`
- Modify: `apps/api/tests/llm/test_architecture.py`
- Modify: `apps/api/.env.example`
- Modify: `apps/api/README.md`
- Modify: `README.md`
- Create: `docs/runbooks/LLM-003-LOCAL-GROUNDED-CHAT.md`

**Interfaces:**

```python
type GroundedChatRuntimeFactory = Callable[[UpstageChatSettings], GroundedChatRuntime]

def create_local_app(
    *,
    environ: Mapping[str, str] | None = None,
    env_path: Path | None = None,
    pool_factory: Callable[[str], LocalPool] | None = None,
    repository_factory: Callable[[object], LocalRepository] | None = None,
    grounded_chat_runtime_factory: GroundedChatRuntimeFactory | None = None,
    purge_interval_seconds: float = 60.0,
) -> FastAPI: ...
```

`load_local_settings` remains responsible only for DB/context settings. The separate chat loader may
return `None`; this must still build the real local DB app with deterministic TEMPLATE responses.
Creating an HTTPX client is allowed during composition but makes no network request. The local
lifespan closes the optional client and pool independently in `finally`. Startup, `/health` and
`/ready` must not call Upstage.

- [x] **Step 1: Write local composition RED tests**

Use a fake runtime/client and assert exact valid chat profile injects the generator, disabled or
invalid profile injects `None`, app/ready still works in template mode, startup makes zero provider
calls, shutdown closes the client once, pool shutdown still occurs when client close fails, and
importing `sejong_ai_api.main` never imports provider modules.

- [x] **Step 2: Run RED**

```powershell
& $uv run --project apps/api --frozen pytest `
  apps/api/tests/test_local.py `
  apps/api/tests/test_architecture.py `
  apps/api/tests/llm/test_architecture.py -q
```

- [x] **Step 3: Implement optional composition and the exact runbook**

Runbook order:

1. keep `[db.seed].enabled=false`
2. start patched local Supabase
3. run immutable `.2` `seed-cycle`
4. run `verify-final`
5. set the ignored local DB/context values
6. select exactly one provider mode
7. set the ignored key
8. start API on loopback
9. verify `/ready=200`
10. run provider-disabled regression before optional grounded actual
11. disable mode/remove key for rollback

Never include an example real-looking key, DSN password or answer text.

- [x] **Step 4: Run local/API focused gates**

```powershell
& $uv run --project apps/api --frozen pytest `
  apps/api/tests/test_local.py `
  apps/api/tests/test_chat_route.py `
  apps/api/tests/test_architecture.py `
  apps/api/tests/llm/test_architecture.py -q
& $uv run --project apps/api --frozen ruff check apps/api/src apps/api/tests
& $uv run --project apps/api --frozen mypy apps/api/src apps/api/tests
python -B scripts/check_repository_docs.py
```

- [x] **Step 5: Review and commit**

```powershell
git add apps/api/src/sejong_ai_api/local.py apps/api/tests/test_local.py `
  apps/api/tests/test_architecture.py apps/api/tests/llm/test_architecture.py `
  apps/api/.env.example apps/api/README.md README.md `
  docs/runbooks/LLM-003-LOCAL-GROUNDED-CHAT.md
git commit -m "feat(local): compose optional grounded chat runtime"
```

---

### Task 7: Render an accessible answer-mode label without weakening sources

**Files:**
- Modify: `apps/web/src/components/citizen/AnswerCard.tsx`
- Modify: `apps/web/src/app/chat/chat-screen.test.tsx`
- Modify: `apps/web/src/app/chat/contract-fixtures.test.tsx`
- Modify: `apps/web/src/lib/chat-api.test.ts`
- Modify: `apps/web/src/lib/demo-fixtures.ts`
- Modify: `apps/web/README.md`
- Modify: `tools/web-e2e/e2e/home-chat-shell.spec.ts`

**Citizen copy:**

- `GENERATED`: `AI로 정리한 공식 안내`
- `TEMPLATE`: `공식 안내`
- Static disclosure:
  `AI가 표현을 정리할 수 있지만 행정 사실과 출처는 승인된 공식 자료에서 확인하며, 오류가 있으면 공식 안내 형식을 사용합니다.`

The mode is text, not color-only; it is not a trust score. Existing source title/link/verified date
remains visible in both modes.

- [x] **Step 1: Write Web RED tests**

Add generated/template SUCCESS fixtures and assert exact labels, disclosure, non-empty source strip,
external source link safety and no provider/model name. Run axe-equivalent existing semantic checks,
keyboard navigation and 390/430/desktop viewport expectations.

- [x] **Step 2: Run RED**

```powershell
corepack pnpm --filter @sejong-ai/web test -- `
  src/app/chat/chat-screen.test.tsx `
  src/app/chat/contract-fixtures.test.tsx `
  src/lib/chat-api.test.ts
```

Expected: stale fixtures/types or missing label assertions fail.

- [x] **Step 3: Implement the minimal label/disclosure**

Place the text label in the answer card header near the existing intent badge. Keep the disclosure
static and concise; do not add loading animation, provider error copy or a new dependency.

- [x] **Step 4: Run the Web area once**

```powershell
corepack pnpm --filter @sejong-ai/web lint
corepack pnpm --filter @sejong-ai/web typecheck
corepack pnpm --filter @sejong-ai/web test
corepack pnpm --filter @sejong-ai/web build
corepack pnpm --dir tools/web-e2e exec playwright test e2e/home-chat-shell.spec.ts
```

- [x] **Step 5: Review and commit**

```powershell
git add apps/web tools/web-e2e/e2e/home-chat-shell.spec.ts
git commit -m "feat(web): explain generated official answers"
```

---

### Task 8: Close security, regression, versions and optional local actual evidence

- [x] **Preparation: synchronize task-scoped evidence, source-of-truth status and closeout report/note** — see [LLM-003 report](../../test-reports/LLM-003-GROUNDED-LIVE-CHAT.md) and [implementation note](../../implementation-notes/IMP-20260725-005-llm-003-grounded-live-chat-implementation.md).

**Files:**
- Create: `docs/test-reports/LLM-003-GROUNDED-LIVE-CHAT.md`
- Create: `docs/implementation-notes/IMP-20260725-005-llm-003-grounded-live-chat-implementation.md`
- Modify: `docs/implementation-notes/INDEX.md`
- Modify: `docs/superpowers/plans/2026-07-25-grounded-live-chat-generation.md`
- Modify: `docs/superpowers/specs/2026-07-25-grounded-live-chat-generation-design.md`
- Modify: `docs/decisions/DECISION_LOG.md`
- Modify: `docs/11_AMBIGUITY_REGISTER.md`
- Modify: `TASKS.md`
- Modify: `CHANGELOG.md`
- Modify: `versions/manifest.json`
- Modify: `docs/12_VERSIONING_AND_RELEASES.md`
- Modify: `docs/05_API_AND_CONTRACTS.md`
- Modify: `docs/07_SECURITY_PRIVACY.md`
- Modify: `docs/08_TEST_STRATEGY.md`
- Modify: `CODEX_FILE_INDEX.md`
- Modify only if assertions require it:
  `scripts/tests/test_security_boundaries.py`,
  `scripts/tests/test_repository_scaffold.py`

**Target version axes after offline implementation:**

```text
product_spec: 2.5.0
application: 0.9.0-grounded-local-chat
web: 0.6.0-answer-mode
api: 3.2.0-draft
shared_contracts: 0.5.0
database_schema: 0.4.0-local
official_data: 0.1.0-initial.2
mock_data: 0.0.0-not-populated
prompt_set: 0.2.0-grounded-live-chat
test_suite: 1.6.0-grounded-live-chat
documentation: 2.20.0
```

- [x] **Step 1: Add offline security/regression assertions**

Assert:

- raw/masked question, prompt/provider body and key are absent from logs, stored interaction,
  idempotency payload and exception text
- a validated final safe response may exist only in existing idempotency storage
- generated response facts and source equal the retrieved ACTIVE/OFFICIAL record
- CANDIDATE/mock/non-official data never reaches the prompt
- policy/IG/followup make zero provider calls
- provider-disabled sample T-01~T-20 is 20/20 with skip 0
- no provider import/use in default app, startup, health or readiness

- [x] **Step 2: Run the final offline repository gate once** — provider-disabled/unset-key run started `2026-07-26T02:39:05+09:00`, completed `2026-07-26T02:49:42+09:00` (637.7s; stdout 2006 bytes; stderr 0); every listed root/data/seed/Web/API/contracts/secrets/bundle/package/diff step PASSed. After final review fix commit `aaf67fe`, the controller reran the same full gate at the exact publication HEAD: exit `0` after `728.7s`, with every listed step PASS. Current actual-evidence final review then added runner/provision fail-closed guards. Its first controller attempt exposed only a missing Git-ignored pinned patched Supabase binary in the worktree; manifest SHA-256 verification and ignored-path restoration made both focused runtime tests pass. A fresh current-slice controller run exited `0` after `749.9s`, with all listed steps PASS and provider actual calls `0`.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/verify.ps1 -Offline
python -B scripts/check_repository_docs.py
powershell -NoProfile -ExecutionPolicy Bypass `
  -File scripts/check_secret_patterns.ps1 -RepositoryRoot .
git diff --check
git status --short
```

Expected: full root verification PASS, docs PASS, secret scan exit 0, diff check exit 0. If a
pre-existing environment-only DB/Browser gate cannot run, record the exact bounded reason and run
its approved focused substitute; do not claim it passed.

- [x] **Step 3: Perform independent reviews** — task security re-review C0/I0/M0; whole-branch review later found C0/I2/M1. Commit `aaf67fe` closed replay-key canonicalization, stale SOT/ADR status and duplicate note text; scoped re-review verdicted all three ADDRESSED with no new Critical/Important breakage. Final focused results were claim/repository 139, chat 220, repository 120, security 19 plus one existing environment-only skip and 8 subtests; Ruff and Mypy passed.

Review the complete diff against:

1. design/contract semantics
2. privacy/provider boundary
3. idempotency and failure behavior
4. Web accessibility/source visibility
5. versions/docs/implementation-note reproducibility

Resolve every Critical/Important finding and rerun only affected focused tests, followed by the
single final gate if code changed after it.

- [x] **Step 4: Execute the human-approved local actual gate and record bounded evidence**

After offline PASS, the human may enable the ignored local grounded profile. The runner/test harness
must execute 10 supported, non-personal questions plus one forced timeout and output only:

```text
cases_total
generated_count
template_count
source_present_count
official_fact_mismatch_count
pii_or_secret_persistence_count
outbound_attempt_count
input_token_total
output_token_total
estimated_cost_usd
```

Acceptance is source 10/10, official mismatch 0, typed write-boundary forbidden-value violations
0 for the PII-free fixtures, outbound at most 10,
forced failure TEMPLATE, and no question/answer/provider body in output. This evidence is local demo
quality only, not public deployment approval.

- [x] **Step 5: Finalize note, versions and commit** — manifest/package metadata `0.5.0`, INDEX and closeout documents are integrated; this plan's commit is prepared after the documented checks.

Record actual commands and results, not expected results. Keep actual status `Pending` if the human
does not run it.

D-075 authorized the gate on 2026-07-26. The final publication run wrote exactly one aggregate JSON
object to stdout and passed: `cases_total=10`, `generated_count=4`, `template_count=6`,
`source_present_count=10`, `official_fact_mismatch_count=0`,
`pii_or_secret_persistence_count=0` (typed `InteractionWrite` boundary only; PII-free fixtures,
not a post-read DB forensic scan), `outbound_attempt_count=10`, `input_token_total=4183`,
`output_token_total=954`, `estimated_cost_usd=0.001319835` (10% VAT included). These token/cost
values are a legacy-reported lower bound because that revision did not require usage on all 10
responses. The configured upper bound is USD 0.0135168, below the USD 0.05 cap. The historical
forced probe observed TEMPLATE and no eleventh provider call; injection-consumption verification
was added afterward for future runs. An earlier semantically passing run
had safe dependency metadata after the aggregate; output suppression was fixed and the clean run
was repeated. Across those two successful bounded runs, provider calls totaled 20 and estimated
cost lower-bound totaled USD 0.002635710; the configured 20-call upper bound is USD 0.0270336.
No question, answer, provider body, key or DSN was printed.

```powershell
git add docs TASKS.md CHANGELOG.md versions/manifest.json CODEX_FILE_INDEX.md `
  scripts/tests
git commit -m "docs(llm): close grounded local chat implementation"
```

- [x] **Step 6: Push and create a Draft PR only after the human has approved this plan** —
  branch `codex/LLM-003-grounded-live-chat-design` was pushed at `0c3830b` and
  [Draft PR #12](https://github.com/tskwak111/Sejong_AI/pull/12) was created against current
  private `main`. Automatic merge was not enabled; human review/merge remains Pending.

```powershell
git push -u origin codex/LLM-003-grounded-live-chat-design
```

Create a Draft PR against current private `main`; do not merge or auto-merge. Before publishing,
fetch and integrate the latest `origin/main`, resolve `INDEX.md`/manifest conflicts by preserving
both lineages, rerun the final docs/secret/diff gates, and report the PR URL.

---

## Self-review completed before plan approval

- Specification coverage: provider gate, full-draft fallback, fact IDs, source authority, exact
  timeout/retry/concurrency/cap, idempotency, Web label, actual acceptance and rollback are mapped.
- Exact file/interface coverage: current ChatService, response builder, local factory, contracts,
  generated TypeScript and Web component paths were inspected at execution base `de1ee09`.
- Completion-marker check: no unresolved implementation marker, undecided interface or unassigned
  owner is left in the plan.
- Type consistency: SUCCESS alone gains `answer_mode`; provider-neutral types are separate from the
  historical synthetic `GeneratedAnswer`/`OutcomeCode`; DB schema and official data stay unchanged.
- Security consistency: no source metadata is sent, no question/provider content is newly stored or
  logged, and the existing 24-hour safe-response idempotency exception is explicit.
- Dependency consistency: existing HTTPX/Pydantic/pytest/Next/React toolchain only; lockfiles are
  unchanged.
- Human boundary: local actual network use was separately approved and passed under D-075.
  Public/remote operation and merge remain separately gated.

## Rollback

1. Runtime rollback: set `UPSTAGE_GROUNDED_CHAT_MODE=false`, set
   `LLM_PROVIDER=disabled`, remove the ignored local key and restart. The deterministic TEMPLATE
   route remains.
2. Code rollback before any external release: revert Task 8 through Task 1 commits in reverse order.
3. No DB schema/official-data rollback is needed. The two pre-review successful actual runs wrote
   22 metadata-only rows with the wrong `is_test=false` label; exclude them from KPI evidence and
   reset/delete only with separate human DB-data approval.
4. If a key may have appeared in output or tracked content, stop immediately, revoke/replace it,
   run current-tree and reachable-history scans, and do not push.
5. The additive `answer_mode` contract must be reverted together across OpenAPI, JSON Schema,
   Pydantic, generated TypeScript, fixtures and Web; partial rollback is prohibited.
