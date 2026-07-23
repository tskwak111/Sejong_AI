# Upstage Solar Pro 3 Synthetic Evaluation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local/private, server-allowlisted Upstage `solar-pro3` evaluator that measures
Korean answer quality, strict JSON stability and bounded token cost without connecting any citizen
or public `/api/v1/chat` request to an external provider.

**Architecture:** Add an isolated `sejong_ai_api.llm` package and a root local-only runner. The
evaluator reuses the existing redaction, deterministic classification, ACTIVE/OFFICIAL retrieval and
grounding functions before calling Upstage. The public app factory, chat route and chat service remain
provider-free; failures produce an evaluation-only deterministic template outcome and text-free
aggregate metrics.

**Tech Stack:** Python 3.12.13, existing `httpx==0.28.1`, `pydantic==2.13.4`, `pytest==9.1.1`,
existing Psycopg repository, standard-library `csv`, `decimal`, `json`, `asyncio`, `argparse`.

- Plan ID: LLM-002-PLAN
- Status: **Review — written specification approved; execution approval pending**
- Design:
  `docs/superpowers/specs/2026-07-23-upstage-solar-pro3-synthetic-evaluation-design.md`
- ADR: `docs/adr/0022-upstage-solar-pro3-synthetic-evaluation.md`
- Decision: Q-LLM-005=A / D-065 / D-066
- Base: `b318375` on `codex/LLM-002-upstage-synthetic-evaluation`

## Global Constraints

- Provider/model/base URL are exactly `upstage`, `solar-pro3`,
  `https://api.upstage.ai/v1`.
- External input is limited to server-loaded canonical `T-01` through `T-10`; client/free-form
  question input is not an evaluator interface.
- Existing redaction, deterministic classification, ACTIVE/OFFICIAL retrieval and grounding must
  pass before every provider call.
- `/api/v1/chat`, `sejong_ai_api.main`, `sejong_ai_api.local.create_local_app`, OpenAPI, Web, DB
  schema/migrations and official data do not gain a provider dependency in this plan.
- Provider is disabled by default. Actual network use requires exact local synthetic mode and an
  ignored local API key.
- Exact runtime limits: `temperature=0.1`, preflight input upper bound 4096 using canonical UTF-8
  bytes as a deliberately conservative token proxy, provider-reported input tokens at most 4096,
  max output 1024, connect timeout 5 seconds, read/write/pool timeout 15 seconds, concurrency 1,
  hidden HTTP retry 0, logical retry at most 1, process-run outbound attempt cap 30.
- No startup, health, readiness, model-list, balance, billing, auto-recharge or reset network call.
- Provider output cannot set intent, answer status, candidate eligibility, source ID/title/URL/date,
  or grounding status.
- Request/response content, reasoning and API key are never persisted or emitted by structured
  logs. Interactive PM review is local TTY-only and stores scores/reason codes, not answer text.
- No new production dependency and no lockfile regeneration.
- One task is one reviewable commit. Every behavior change follows RED → minimal GREEN → focused
  gate → diff review → commit.
- Actual Upstage execution is the final local-only gate after all offline tests pass. Codex Cloud,
  GitHub Actions and public/remote environments never receive the key.

Before the first PowerShell command block in a terminal, resolve the ignored project-local `uv`
binary from the Git common directory so the commands work in both the primary checkout and linked
worktrees:

```powershell
$commonGitDir = git rev-parse --path-format=absolute --git-common-dir
$uv = Join-Path (Split-Path $commonGitDir -Parent) ".tools\uv\uv.exe"
if (-not (Test-Path -LiteralPath $uv)) {
  throw "PROJECT_UV_NOT_FOUND"
}
```

Every `& $uv ...` command below consumes that resolved binary and never downloads a tool.

---

## File and Responsibility Map

| File | Responsibility |
|---|---|
| `apps/api/src/sejong_ai_api/llm/__init__.py` | Public exports for the internal evaluator package only |
| `apps/api/src/sejong_ai_api/llm/settings.py` | Exact fail-closed Upstage synthetic environment parsing |
| `apps/api/src/sejong_ai_api/llm/contracts.py` | Strict model output, usage, outcome and aggregate types |
| `apps/api/src/sejong_ai_api/llm/prompt.py` | Versioned prompt and source-free minimum KB payload |
| `apps/api/src/sejong_ai_api/llm/cost.py` | Decimal pricing snapshot and USD/VAT estimate |
| `apps/api/src/sejong_ai_api/llm/limits.py` | Input upper bound, atomic per-process attempt cap and concurrency-one lease |
| `apps/api/src/sejong_ai_api/llm/upstage.py` | HTTPX transport, envelope parsing and one logical retry |
| `apps/api/src/sejong_ai_api/llm/fixtures.py` | Exact canonical CSV header/ID/SUCCESS allowlist loader |
| `apps/api/src/sejong_ai_api/llm/evaluation.py` | Redact→classify→retrieve→ground→generate orchestration |
| `apps/api/src/sejong_ai_api/llm/report.py` | Text-free aggregate report and PM score validation |
| `scripts/run_upstage_synthetic_evaluation.py` | Safe local DB/client lifecycle and optional TTY review |
| `apps/api/tests/llm/**` | Unit/integration tests with no real network |
| `scripts/tests/test_run_upstage_synthetic_evaluation.py` | CLI, output and secret-safety contract |
| `apps/api/.env.example` | Disabled-by-default generic Upstage selection, no secret |
| `docs/test-reports/LLM-002-UPSTAGE-SYNTHETIC-EVALUATION.md` | Aggregate actual evidence only |

The implementation must not create `apps/api/src/sejong_ai_api/api/llm.py`, add a FastAPI router,
or import `sejong_ai_api.llm` from `main.py`, `local.py`, `api/chat.py` or `chat/service.py`.

---

### Task 1: Fail-closed synthetic provider settings

**Files:**
- Create: `apps/api/src/sejong_ai_api/llm/__init__.py`
- Create: `apps/api/src/sejong_ai_api/llm/settings.py`
- Create: `apps/api/tests/llm/__init__.py`
- Create: `apps/api/tests/llm/test_settings.py`
- Modify: `apps/api/.env.example`

**Interfaces:**
- Consumes: process environment or exact ignored `apps/api/.env`
- Produces:
  `load_upstage_synthetic_settings(*, environ: Mapping[str, str] | None = None,
  env_path: Path | None = None) -> UpstageSyntheticSettings | None`
- Produces: immutable `UpstageSyntheticSettings` with redacted `repr`

- [ ] **Step 1: Write the settings RED tests**

```python
from pathlib import Path

from sejong_ai_api.llm.settings import (
    UpstageSyntheticSettings,
    load_upstage_synthetic_settings,
)


VALID = {
    "LLM_PROVIDER": "upstage",
    "LLM_MODEL": "solar-pro3",
    "LLM_API_KEY": "synthetic-test-key-not-a-real-secret",
    "LLM_BASE_URL": "https://api.upstage.ai/v1",
    "LLM_TIMEOUT_SECONDS": "15",
    "LLM_MAX_RETRIES": "1",
    "LLM_MAX_CONCURRENCY": "1",
    "LLM_MAX_INPUT_TOKENS": "4096",
    "LLM_MAX_OUTPUT_TOKENS": "1024",
    "LLM_RUN_ATTEMPT_CAP": "30",
    "UPSTAGE_SYNTHETIC_EVALUATION_MODE": "true",
}


def test_exact_synthetic_settings_load_without_exposing_key() -> None:
    settings = load_upstage_synthetic_settings(environ=VALID, env_path=Path("missing"))
    assert isinstance(settings, UpstageSyntheticSettings)
    assert settings.model == "solar-pro3"
    assert settings.base_url == "https://api.upstage.ai/v1"
    assert settings.timeout_seconds == 15.0
    assert settings.max_retries == 1
    assert settings.max_concurrency == 1
    assert settings.max_input_tokens == 4096
    assert settings.max_output_tokens == 1024
    assert settings.run_attempt_cap == 30
    assert VALID["LLM_API_KEY"] not in repr(settings)


def test_disabled_or_non_exact_values_fail_closed() -> None:
    for key, invalid in (
        ("LLM_PROVIDER", "disabled"),
        ("LLM_MODEL", "solar-pro"),
        ("LLM_BASE_URL", "https://example.invalid/v1"),
        ("LLM_TIMEOUT_SECONDS", "14"),
        ("LLM_MAX_RETRIES", "2"),
        ("LLM_MAX_CONCURRENCY", "2"),
        ("LLM_MAX_INPUT_TOKENS", "4097"),
        ("LLM_MAX_OUTPUT_TOKENS", "2048"),
        ("LLM_RUN_ATTEMPT_CAP", "31"),
        ("UPSTAGE_SYNTHETIC_EVALUATION_MODE", "false"),
    ):
        candidate = dict(VALID)
        candidate[key] = invalid
        assert load_upstage_synthetic_settings(environ=candidate, env_path=Path("missing")) is None
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```powershell
& $uv run --project apps/api --frozen pytest apps/api/tests/llm/test_settings.py -q
```

Expected: collection/import failure because `sejong_ai_api.llm.settings` does not exist.

- [ ] **Step 3: Implement exact immutable settings**

Use this public shape and constants:

```python
from dataclasses import dataclass, field
from pathlib import Path
from collections.abc import Mapping

UPSTAGE_PROVIDER = "upstage"
UPSTAGE_MODEL = "solar-pro3"
UPSTAGE_BASE_URL = "https://api.upstage.ai/v1"
UPSTAGE_TIMEOUT_SECONDS = 15.0
UPSTAGE_MAX_RETRIES = 1
UPSTAGE_MAX_CONCURRENCY = 1
UPSTAGE_MAX_INPUT_TOKENS = 4096
UPSTAGE_MAX_OUTPUT_TOKENS = 1024
UPSTAGE_RUN_ATTEMPT_CAP = 30


@dataclass(frozen=True, slots=True)
class UpstageSyntheticSettings:
    api_key: str = field(repr=False)
    provider: str = UPSTAGE_PROVIDER
    model: str = UPSTAGE_MODEL
    base_url: str = UPSTAGE_BASE_URL
    timeout_seconds: float = UPSTAGE_TIMEOUT_SECONDS
    max_retries: int = UPSTAGE_MAX_RETRIES
    max_concurrency: int = UPSTAGE_MAX_CONCURRENCY
    max_input_tokens: int = UPSTAGE_MAX_INPUT_TOKENS
    max_output_tokens: int = UPSTAGE_MAX_OUTPUT_TOKENS
    run_attempt_cap: int = UPSTAGE_RUN_ATTEMPT_CAP


def load_upstage_synthetic_settings(
    *,
    environ: Mapping[str, str] | None = None,
    env_path: Path | None = None,
) -> UpstageSyntheticSettings | None:
    """Return settings only for the exact approved local synthetic profile."""
```

The function must:

1. Read only the eleven keys used in `VALID`.
2. Prefer process values and fill only missing keys from `apps/api/.env`.
3. Reject duplicate allowlisted assignments, quotes mismatch, NUL/CR/LF, surrounding whitespace,
   empty key, extra URL slash/query/fragment and non-ASCII numeric text.
4. Require every value to equal the constants above.
5. Return `None` for all invalid/disabled states without logging a value.

Update `apps/api/.env.example` to:

```dotenv
LLM_PROVIDER=disabled
LLM_MODEL=solar-pro3
LLM_API_KEY=
LLM_BASE_URL=https://api.upstage.ai/v1
LLM_TIMEOUT_SECONDS=15
LLM_MAX_RETRIES=1
LLM_MAX_CONCURRENCY=1
LLM_MAX_INPUT_TOKENS=4096
LLM_MAX_OUTPUT_TOKENS=1024
LLM_RUN_ATTEMPT_CAP=30
UPSTAGE_SYNTHETIC_EVALUATION_MODE=false
```

Remove the two obsolete `DEEPSEEK_*` example assignments and `LLM_THINKING_ENABLED`; do not touch
the ignored real `.env`.

- [ ] **Step 4: Run focused and static gates**

Run:

```powershell
& $uv run --project apps/api --frozen pytest apps/api/tests/llm/test_settings.py -q
& $uv run --project apps/api --frozen ruff check apps/api/src/sejong_ai_api/llm apps/api/tests/llm
& $uv run --project apps/api --frozen mypy apps/api/src/sejong_ai_api/llm apps/api/tests/llm
```

Expected: all tests PASS, Ruff exit 0, Mypy exit 0.

- [ ] **Step 5: Review and commit**

Verify `git diff -- apps/api/.env.example apps/api/src/sejong_ai_api/llm apps/api/tests/llm` contains
no key value, route or dependency change.

```powershell
git add apps/api/.env.example apps/api/src/sejong_ai_api/llm apps/api/tests/llm
git commit -m "feat(llm): add fail-closed Upstage settings"
```

---

### Task 2: Strict output, prompt and cost contracts

**Files:**
- Create: `apps/api/src/sejong_ai_api/llm/contracts.py`
- Create: `apps/api/src/sejong_ai_api/llm/prompt.py`
- Create: `apps/api/src/sejong_ai_api/llm/cost.py`
- Create: `apps/api/tests/llm/test_contracts.py`
- Create: `apps/api/tests/llm/test_prompt.py`
- Create: `apps/api/tests/llm/test_cost.py`
- Create: `apps/api/tests/llm/conftest.py`

**Interfaces:**
- Consumes: `KnowledgeRecord`, masked synthetic question and deterministic `Intent`
- Produces: `GeneratedAnswer`, `TokenUsage`, `GenerationOutcome`, `OutcomeCode`
- Produces:
  `build_upstage_messages(fixture: GroundedFixture) -> tuple[dict[str, str], ...]`
- Produces:
  `estimate_input_token_upper_bound(messages: tuple[dict[str, str], ...]) -> int`
- Produces: `estimate_cost_usd(usage: TokenUsage) -> Decimal`

- [ ] **Step 1: Write strict contract RED tests**

```python
import json
from decimal import Decimal

import pytest
from pydantic import ValidationError

from sejong_ai_api.llm.contracts import GeneratedAnswer, TokenUsage
from sejong_ai_api.llm.cost import estimate_cost_usd
from sejong_ai_api.llm.prompt import (
    build_upstage_messages,
    estimate_input_token_upper_bound,
)


def test_generated_answer_rejects_provider_owned_source_and_status() -> None:
    payload = {
        "summary": "공식 KB 범위에서 정리한 안내입니다.",
        "procedure_steps": ["첫 번째 절차를 확인합니다."],
        "required_documents": [],
        "processing_time": None,
        "fee": None,
        "department": "민원 담당 부서",
        "source_url": "https://example.invalid",
    }
    with pytest.raises(ValidationError):
        GeneratedAnswer.model_validate_json(json.dumps(payload, ensure_ascii=False))


def test_cost_uses_decimal_snapshot_and_vat() -> None:
    usage = TokenUsage(input_tokens=4096, cached_input_tokens=0, output_tokens=1024)
    assert estimate_cost_usd(usage) == Decimal("0.0405504")


def test_canonical_prompt_stays_within_conservative_input_upper_bound(
    grounded_fixture,
) -> None:
    messages = build_upstage_messages(grounded_fixture)
    assert estimate_input_token_upper_bound(messages) <= 4096
```

Create `apps/api/tests/llm/conftest.py` with reusable exact typed values so every later snippet has a
defined fixture:

```python
from datetime import date

import pytest

from sejong_ai_api.db.models import Intent, KnowledgeRecord
from sejong_ai_api.llm.contracts import GroundedFixture
from sejong_ai_api.llm.settings import UpstageSyntheticSettings


@pytest.fixture
def exact_settings() -> UpstageSyntheticSettings:
    return UpstageSyntheticSettings(api_key="synthetic-test-key-not-a-real-secret")


@pytest.fixture
def grounded_fixture() -> GroundedFixture:
    record = KnowledgeRecord(
        public_id="KB-BULKY-001",
        category=Intent.BULKY_WASTE,
        service_name="대형폐기물 배출",
        answer_summary="신고 후 배출번호를 표시해 지정한 날짜와 장소에 배출합니다.",
        procedure_steps=("배출 품목을 확인합니다.", "신고 후 배출번호를 표시합니다."),
        required_documents=(),
        processing_time="신고 즉시",
        fee="품목별 수수료",
        department="자원순환 담당부서",
        source_title="세종특별자치시 대형폐기물 안내",
        source_url="https://www.sejong.go.kr/",
        last_verified_at=date(2026, 7, 20),
        caution=None,
        question_examples=("소파를 버리려면 어떻게 하나요?",),
    )
    return GroundedFixture(
        fixture_id="T-09",
        masked_question="소파를 버리려면 어떻게 하나요?",
        intent=Intent.BULKY_WASTE,
        record=record,
    )
```

- [ ] **Step 2: Run RED**

Run:

```powershell
& $uv run --project apps/api --frozen pytest `
  apps/api/tests/llm/test_contracts.py `
  apps/api/tests/llm/test_prompt.py `
  apps/api/tests/llm/test_cost.py -q
```

Expected: import failure for the three new modules.

- [ ] **Step 3: Implement the closed types**

Use these exact public fields:

```python
from dataclasses import dataclass
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field
from sejong_ai_api.db.models import Intent, KnowledgeRecord


class GeneratedAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    summary: Annotated[str, Field(min_length=1, max_length=500)]
    procedure_steps: Annotated[list[str], Field(max_length=12)]
    required_documents: Annotated[list[str], Field(max_length=12)]
    processing_time: Annotated[str, Field(min_length=1, max_length=200)] | None
    fee: Annotated[str, Field(min_length=1, max_length=200)] | None
    department: Annotated[str, Field(min_length=1, max_length=200)] | None


@dataclass(frozen=True, slots=True)
class GroundedFixture:
    fixture_id: str
    masked_question: str
    intent: Intent
    record: KnowledgeRecord


@dataclass(frozen=True, slots=True)
class TokenUsage:
    input_tokens: int
    cached_input_tokens: int
    output_tokens: int


class OutcomeCode(str, Enum):
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


@dataclass(frozen=True, slots=True)
class GenerationOutcome:
    code: OutcomeCode
    answer: GeneratedAnswer | None
    usage: TokenUsage
    attempts_used: int
```

Each dataclass must reject negative tokens/attempts and invalid success/failure combinations in
`__post_init__`.

- [ ] **Step 4: Implement source-free prompt and Decimal cost**

Use `PROMPT_VERSION = "0.1.0-upstage-solar-pro3-synthetic"` and serialize only:

```python
{
    "question": fixture.masked_question,
    "intent": fixture.intent.value,
    "official_kb": {
        "service_name": fixture.record.service_name,
        "answer_summary": fixture.record.answer_summary,
        "procedure_steps": list(fixture.record.procedure_steps),
        "required_documents": list(fixture.record.required_documents),
        "processing_time": fixture.record.processing_time,
        "fee": fixture.record.fee,
        "department": fixture.record.department,
        "caution": fixture.record.caution,
    },
    "output_schema": {
        "summary": "string, 1..500",
        "procedure_steps": "list[string], max 12",
        "required_documents": "list[string], max 12",
        "processing_time": "string 1..200 or null",
        "fee": "string 1..200 or null",
        "department": "string 1..200 or null",
    },
}
```

The system message must say in Korean that no fact may be added, JSON only is required, null must be
preserved, and source/intent/status fields are forbidden. Assert the serialized prompt does not
contain `source_title`, `source_url`, `last_verified_at`, `question_examples`, `public_id`.

`estimate_input_token_upper_bound()` must canonicalize the complete messages with
`json.dumps(..., ensure_ascii=False, separators=(",", ":"))` and return the UTF-8 byte length. This
intentionally over-budgets Korean input without adding a tokenizer dependency. Task 3 must block the
transport when this value exceeds 4096 and must independently reject any response whose
provider-reported `prompt_tokens` exceeds 4096.

Implement cost with exact `Decimal` constants:

```python
INPUT_PER_MILLION = Decimal("0.15")
CACHED_INPUT_PER_MILLION = Decimal("0.015")
OUTPUT_PER_MILLION = Decimal("0.60")
VAT_RATE = Decimal("0.10")
ONE_MILLION = Decimal("1000000")
RUN_COST_CAP_USD = Decimal("0.05")
```

- [ ] **Step 5: Run focused tests and commit**

Run:

```powershell
& $uv run --project apps/api --frozen pytest apps/api/tests/llm/test_contracts.py apps/api/tests/llm/test_prompt.py apps/api/tests/llm/test_cost.py -q
& $uv run --project apps/api --frozen ruff check apps/api/src/sejong_ai_api/llm apps/api/tests/llm
& $uv run --project apps/api --frozen mypy apps/api/src/sejong_ai_api/llm apps/api/tests/llm
git add apps/api/src/sejong_ai_api/llm apps/api/tests/llm
git commit -m "feat(llm): define synthetic prompt and cost contracts"
```

Expected: PASS and no dependency/lockfile diff.

---

### Task 3: Atomic attempt budget and Upstage HTTPX transport

**Files:**
- Create: `apps/api/src/sejong_ai_api/llm/limits.py`
- Create: `apps/api/src/sejong_ai_api/llm/upstage.py`
- Create: `apps/api/tests/llm/test_limits.py`
- Create: `apps/api/tests/llm/test_upstage.py`

**Interfaces:**
- Consumes: settings, `GroundedFixture`, injected `httpx.AsyncClient`
- Produces: `AttemptBudget(cap: int, concurrency: int)`
- Produces:
  `UpstageProvider.generate(fixture: GroundedFixture) -> GenerationOutcome`

- [ ] **Step 1: Write RED cap and transport tests**

```python
import httpx
import pytest

from sejong_ai_api.llm.limits import AttemptBudget, AttemptCapReached
from sejong_ai_api.llm.upstage import UpstageProvider


@pytest.mark.asyncio
async def test_attempt_31_is_blocked_before_transport() -> None:
    budget = AttemptBudget(cap=30, concurrency=1)
    for expected in range(1, 31):
        async with budget.reserve() as actual:
            assert actual == expected
    with pytest.raises(AttemptCapReached):
        async with budget.reserve():
            raise AssertionError("reservation must not succeed")


@pytest.mark.asyncio
async def test_rate_limit_retries_once_and_never_uses_hidden_retry(
    grounded_fixture,
    exact_settings,
) -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if len(seen) == 1:
            return httpx.Response(429, json={"error": {"message": "bounded"}})
        return httpx.Response(
            200,
            json={
                "choices": [{
                    "finish_reason": "stop",
                    "message": {"content": (
                        '{"summary":"안내","procedure_steps":[],"required_documents":[],'
                        '"processing_time":null,"fee":null,"department":null}'
                    )},
                }],
                "usage": {"prompt_tokens": 20, "completion_tokens": 10},
            },
        )

    async with httpx.AsyncClient(
        base_url=exact_settings.base_url,
        transport=httpx.MockTransport(handler),
    ) as client:
        outcome = await UpstageProvider(
            settings=exact_settings,
            client=client,
            budget=AttemptBudget(cap=30, concurrency=1),
        ).generate(grounded_fixture)

    assert outcome.code.value == "SUCCESS"
    assert outcome.attempts_used == 2
    assert len(seen) == 2
```

- [ ] **Step 2: Run RED**

Run:

```powershell
& $uv run --project apps/api --frozen pytest apps/api/tests/llm/test_limits.py apps/api/tests/llm/test_upstage.py -q
```

Expected: imports fail for `limits` and `upstage`.

- [ ] **Step 3: Implement atomic reservation**

`AttemptBudget.reserve()` must be an `@asynccontextmanager` that acquires an
`asyncio.Semaphore(1)`, increments the counter under `asyncio.Lock`, raises `AttemptCapReached`
before a network attempt when the count is already 30, and releases the semaphore in `finally`.
Expose read-only `attempts_used`.

- [ ] **Step 4: Implement exact HTTPX call and parsing**

The provider request body is exactly:

```python
payload = {
    "model": "solar-pro3",
    "messages": list(build_upstage_messages(fixture)),
    "stream": False,
    "temperature": 0.1,
    "max_tokens": 1024,
}
```

The production client factory uses:

```python
timeout = httpx.Timeout(15.0, connect=5.0, read=15.0, write=15.0, pool=15.0)
transport = httpx.AsyncHTTPTransport(retries=0)
client = httpx.AsyncClient(
    base_url="https://api.upstage.ai/v1",
    headers={
        "Authorization": f"Bearer {settings.api_key}",
        "Content-Type": "application/json",
    },
    timeout=timeout,
    transport=transport,
)
```

`generate()` posts to `/chat/completions`, parses only
`choices[0].message.content`, `choices[0].finish_reason`, and integer
`usage.prompt_tokens`/`usage.completion_tokens`. It then validates content with
`GeneratedAnswer.model_validate_json()`.

Retry exactly once only for timeout, transport error, 429, 5xx, empty, non-`stop` finish reason and
schema-invalid content. Do not retry 401/403 or other 4xx. Never include response text or exception
text in an error, return value, log or assertion failure. Sum usage only from valid integer fields.
Before reserving an attempt, return `INPUT_LIMIT` without transport if
`estimate_input_token_upper_bound(messages) > settings.max_input_tokens`. If a successful provider
envelope reports `prompt_tokens > settings.max_input_tokens`, discard the generated answer, return
`INPUT_LIMIT`, do not retry it, and make the evaluator stop before any later fixture call.

- [ ] **Step 5: Complete the failure matrix**

Add exact parameterized cases for 401→AUTH/no retry, 400→HTTP_ERROR/no retry, timeout twice→TIMEOUT,
500 twice→HTTP_ERROR, empty twice→EMPTY, `length` twice→TRUNCATED, invalid JSON twice→SCHEMA_INVALID,
extra `source_url` twice→SCHEMA_INVALID, conservative input overflow→INPUT_LIMIT/no request,
provider usage 4097→INPUT_LIMIT/no retry and cap reached→ATTEMPT_CAP/no request.

Run:

```powershell
& $uv run --project apps/api --frozen pytest apps/api/tests/llm/test_limits.py apps/api/tests/llm/test_upstage.py -q
& $uv run --project apps/api --frozen ruff check apps/api/src/sejong_ai_api/llm apps/api/tests/llm
& $uv run --project apps/api --frozen mypy apps/api/src/sejong_ai_api/llm apps/api/tests/llm
```

Expected: full failure matrix PASS, no real DNS/network request.

- [ ] **Step 6: Review and commit**

```powershell
git add apps/api/src/sejong_ai_api/llm apps/api/tests/llm
git commit -m "feat(llm): add bounded Upstage transport"
```

---

### Task 4: Canonical fixture gate and grounded evaluator

**Files:**
- Create: `apps/api/src/sejong_ai_api/llm/fixtures.py`
- Create: `apps/api/src/sejong_ai_api/llm/evaluation.py`
- Create: `apps/api/tests/llm/test_fixtures.py`
- Create: `apps/api/tests/llm/test_evaluation.py`

**Interfaces:**
- Consumes: exact `data/evaluation/sample_questions_20.csv`, repository `list_active_kb`, provider
- Produces:
  `load_allowed_fixtures(path: Path) -> tuple[SyntheticFixture, ...]`
- Produces:
  `SyntheticEvaluationService.run(*, repetitions: int = 3) -> EvaluationRun`

Define the exact preparation types in `fixtures.py`/`evaluation.py`:

```python
from dataclasses import dataclass
from enum import Enum

from sejong_ai_api.db.models import AnswerStatus, Intent


class PreparationCode(str, Enum):
    PRIVACY_UNRESOLVED = "PRIVACY_UNRESOLVED"
    NOT_DETERMINISTIC_SUCCESS = "NOT_DETERMINISTIC_SUCCESS"
    INSUFFICIENT_GROUNDING = "INSUFFICIENT_GROUNDING"


@dataclass(frozen=True, slots=True)
class SyntheticFixture:
    fixture_id: str
    question: str
    expected_intent: Intent
    expected_status: AnswerStatus
    contains_pii: bool


@dataclass(frozen=True, slots=True)
class PreparedCaseFailure:
    code: PreparationCode
```

The internal preparation interface is
`prepare_case(fixture: SyntheticFixture) -> GroundedFixture | PreparedCaseFailure`.

- [ ] **Step 1: Write RED fixture allowlist tests**

```python
from pathlib import Path

import pytest

from sejong_ai_api.db.models import AnswerStatus
from sejong_ai_api.llm.fixtures import load_allowed_fixtures


def test_canonical_loader_returns_only_exact_success_ids() -> None:
    fixtures = load_allowed_fixtures(Path("data/evaluation/sample_questions_20.csv"))
    assert tuple(item.fixture_id for item in fixtures) == tuple(
        f"T-{number:02d}" for number in range(1, 11)
    )
    assert all(item.expected_status is AnswerStatus.SUCCESS for item in fixtures)
    assert all(item.contains_pii is False for item in fixtures)


def test_noncanonical_header_or_changed_allowed_row_fails_closed(tmp_path: Path) -> None:
    candidate = tmp_path / "sample.csv"
    candidate.write_text(
        "test_id,질문,유형,기대 intent,기대 상태,기대 폴백 사유,KB 후보 적격,기대 행동,PII 포함,비고\n"
        "T-01,임의 자유 입력,정상 답변,전입·주민등록,SUCCESS,,아니오,절차,아니오,\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="SYNTHETIC_FIXTURE_SET_INVALID"):
        load_allowed_fixtures(candidate)
```

The implementation must pin the SHA-256 of the exact approved `T-01`~`T-10` projection, not only IDs.
The hash constant is computed during implementation from base commit `b318375` and reviewed as a
literal. Later CSV wording drift must fail before provider construction.

- [ ] **Step 2: Write RED evaluation boundary tests**

Use spies to prove:

```python
assert provider.calls == 0                 # redaction unresolved
assert provider.calls == 0                 # non-SUCCESS classification
assert provider.calls == 0                 # no ACTIVE/OFFICIAL record
assert provider.calls == 0                 # grounding false
assert provider.calls == 1                 # exact grounded T-01
assert result.source_id == official_record.public_id
assert result.used_template_fallback is True  # provider failure
```

The fake repository must expose only `list_active_kb(intent)` and the fake provider must accept
`GroundedFixture`; neither may receive the raw pre-redaction question from an external caller.

- [ ] **Step 3: Run RED**

Run:

```powershell
& $uv run --project apps/api --frozen pytest apps/api/tests/llm/test_fixtures.py apps/api/tests/llm/test_evaluation.py -q
```

Expected: imports fail for `fixtures` and `evaluation`.

- [ ] **Step 4: Implement the existing deterministic gate**

For each server-loaded `SyntheticFixture`:

```python
redaction = redact_question(fixture.question)
if redaction.masked_text is None or not redaction.safe_for_synthetic_provider:
    return PreparedCaseFailure(PreparationCode.PRIVACY_UNRESOLVED)

safe_question = SafeQuestion(redaction)
classification = classify_question(safe_question)
if (
    classification.followup_required
    or classification.fallback_reason is not None
    or classification.intent is Intent.UNKNOWN
):
    return PreparedCaseFailure(PreparationCode.NOT_DETERMINISTIC_SUCCESS)

records = await repository.list_active_kb(classification.intent)
ranked = rank_active_knowledge(safe_question, classification.intent, records)
top = ranked[0] if ranked else None
grounding = evaluate_grounding(
    safe_question,
    classification.intent,
    top.record if top is not None else None,
)
if not grounding.is_grounded or grounding.record is None:
    return PreparedCaseFailure(PreparationCode.INSUFFICIENT_GROUNDING)
```

Only then create `GroundedFixture` and call the provider. On provider failure, call the existing
`build_success_response()` with the original official `KnowledgeRecord`, a generated local UUID,
`office=None`, `confidence=1.0`, `context_token=None`; mark the evaluation result as template fallback.
Do not call `record_interaction`.

- [ ] **Step 5: Enforce run semantics**

Define these exact immutable result shapes in `evaluation.py` before implementing the loop:

```python
@dataclass(frozen=True, slots=True)
class ReviewSample:
    fixture_id: str
    question: str
    answer: GeneratedAnswer


@dataclass(frozen=True, slots=True)
class EvaluationCaseResult:
    fixture_id: str
    repetition: int
    outcome_code: OutcomeCode
    attempts_used: int
    usage: TokenUsage
    latency_ms: int
    source_id: str | None
    used_template_fallback: bool


@dataclass(frozen=True, slots=True)
class EvaluationRun:
    planned_generations: int
    cases: tuple[EvaluationCaseResult, ...]
    review_samples: tuple[ReviewSample, ...]
```

Run fixtures in ID order with repetitions 1→3 and concurrency one. Stop the loop when the budget
returns ATTEMPT_CAP or INPUT_LIMIT; do not start a new process or reset the counter. Keep generated
answers and canonical synthetic questions in the returned in-memory review samples only. The
serializable aggregate contains fixture ID, repetition, outcome code, attempt count, token counts,
latency, server source ID and fallback boolean, never question/answer text.

- [ ] **Step 6: Run focused gates and commit**

```powershell
& $uv run --project apps/api --frozen pytest apps/api/tests/llm/test_fixtures.py apps/api/tests/llm/test_evaluation.py -q
& $uv run --project apps/api --frozen ruff check apps/api/src/sejong_ai_api/llm apps/api/tests/llm
& $uv run --project apps/api --frozen mypy apps/api/src/sejong_ai_api/llm apps/api/tests/llm
git add apps/api/src/sejong_ai_api/llm apps/api/tests/llm
git commit -m "feat(llm): gate canonical grounded evaluation"
```

---

### Task 5: Text-free report and safe local runner

**Files:**
- Create: `apps/api/src/sejong_ai_api/llm/report.py`
- Create: `apps/api/tests/llm/test_report.py`
- Create: `scripts/run_upstage_synthetic_evaluation.py`
- Create: `scripts/tests/test_run_upstage_synthetic_evaluation.py`
- Modify: `scripts/README.md`

**Interfaces:**
- Consumes: local DB settings, exact provider settings, canonical fixture path
- Produces:
  `build_aggregate_report(run: EvaluationRun, scores: tuple[HumanFixtureScore, ...]) -> dict[str, object]`
- Produces: fixed ignored file `artifacts/llm-002/upstage-synthetic-evaluation.json`
- CLI: `python scripts/run_upstage_synthetic_evaluation.py [--review]`

- [ ] **Step 1: Write RED report-safety tests**

```python
import json

from sejong_ai_api.llm.contracts import GeneratedAnswer, OutcomeCode, TokenUsage
from sejong_ai_api.llm.evaluation import (
    EvaluationCaseResult,
    EvaluationRun,
    ReviewSample,
)
from sejong_ai_api.llm.report import HumanFixtureScore, build_aggregate_report


def _completed_evaluation_run() -> EvaluationRun:
    answer = GeneratedAnswer(
        summary="안내",
        procedure_steps=[],
        required_documents=[],
        processing_time=None,
        fee=None,
        department=None,
    )
    return EvaluationRun(
        planned_generations=1,
        cases=(
            EvaluationCaseResult(
                fixture_id="T-09",
                repetition=1,
                outcome_code=OutcomeCode.SUCCESS,
                attempts_used=1,
                usage=TokenUsage(20, 0, 10),
                latency_ms=10,
                source_id="KB-BULKY-001",
                used_template_fallback=False,
            ),
        ),
        review_samples=(
            ReviewSample(
                fixture_id="T-09",
                question="소파를 버리려면 어떻게 하나요?",
                answer=answer,
            ),
        ),
    )


def _approved_scores() -> tuple[HumanFixtureScore, ...]:
    return (
        HumanFixtureScore(
            fixture_id="T-09",
            natural_korean=5,
            directness=5,
            official_fact_preservation=5,
            unsupported_claim_absence=5,
            next_action_clarity=5,
            decision="PASS",
            reason_code="OK",
        ),
    )


def test_serialized_report_contains_no_question_answer_or_secret() -> None:
    completed_evaluation_run = _completed_evaluation_run()
    approved_scores = _approved_scores()
    report = build_aggregate_report(completed_evaluation_run, approved_scores)
    serialized = json.dumps(report, ensure_ascii=False, allow_nan=False)
    for forbidden in (
        completed_evaluation_run.review_samples[0].question,
        completed_evaluation_run.review_samples[0].answer.summary,
        "Authorization",
        "api_key",
        "provider_body",
    ):
        assert forbidden not in serialized
```

`HumanFixtureScore` fields are exactly `fixture_id`, `natural_korean`, `directness`,
`official_fact_preservation`, `unsupported_claim_absence`, `next_action_clarity` (the five scores are
integers 1..5), `decision` in `PASS|FAIL`, and `reason_code` in:
`OK|UNNATURAL_KOREAN|INDIRECT|MISSING_OFFICIAL_FACT|UNSUPPORTED_CLAIM|OFFICIAL_FACT_CONTRADICTION|UNCLEAR_NEXT_ACTION`.

- [ ] **Step 2: Write RED CLI tests**

Patch all factories and assert:

- missing/disabled provider settings exits 2 and prints only `LLM_EVALUATION_CONFIGURATION_INVALID`
- non-TTY `--review` exits 2 before DB/provider construction
- DB readiness failure exits 3 with `LLM_EVALUATION_DATABASE_UNAVAILABLE`
- successful non-review run writes only the fixed ignored aggregate path
- stdout/stderr contain no synthetic key, DSN, question, answer or exception text
- no command-line option accepts a key, URL, model, fixture path, output path, cap or arbitrary question

- [ ] **Step 3: Run RED**

```powershell
& $uv run --project apps/api --frozen pytest apps/api/tests/llm/test_report.py -q
python -B -m unittest scripts.tests.test_run_upstage_synthetic_evaluation -v
```

Expected: import/script failures.

- [ ] **Step 4: Implement report validation**

The report root keys are exactly:

```python
{
    "schema_version": "1.0.0",
    "provider": "upstage",
    "model": "solar-pro3",
    "prompt_version": "0.1.0-upstage-solar-pro3-synthetic",
    "fixture_set": "sample_questions_20:T-01..T-10",
    "planned_generations": 30,
    "completed_generations": int,
    "outbound_attempts": int,
    "outcome_counts": dict[str, int],
    "schema_valid_count": int,
    "template_fallback_count": int,
    "input_tokens": int,
    "cached_input_tokens": int,
    "output_tokens": int,
    "estimated_cost_usd_including_vat": str,
    "cost_cap_usd_including_vat": "0.05",
    "human_review": {
        "reviewed_fixture_count": int,
        "mean_score": str,
        "minimum_dimension_score": int | None,
        "critical_fact_error_count": int,
        "decision_counts": dict[str, int],
        "reason_counts": dict[str, int],
        "scores": list[dict[str, int | str]],
    },
    "acceptance": {
        "json_schema_100_percent": bool,
        "critical_fact_errors_zero": bool,
        "mean_at_least_4": bool,
        "minimum_dimension_at_least_3": bool,
        "cost_within_cap": bool,
        "overall_pass": bool,
    },
}
```

No timestamp, hostname, username, IP, path, request ID or account identifier is needed.

- [ ] **Step 5: Implement the runner lifecycle**

The root script adds only `apps/api/src` to `sys.path`, uses a value-free argument parser, calls
`load_local_settings()` and `load_upstage_synthetic_settings()`, opens the existing local pool,
creates `PsycopgSejongRepository`, `AttemptBudget`, explicit HTTPX client and evaluator, then closes
client and pool in `finally`.

`--review` requires both stdin and stdout TTY. It displays only the first valid generated answer per
fixture for deliberate human review, prompts for five 1..5 integers and one closed reason code, and
keeps answer content out of the report. Without `--review`, scores are empty and `overall_pass=false`.
Write aggregate JSON atomically to the fixed ignored path and print only:

```text
LLM_EVALUATION_COMPLETE
REPORT=artifacts/llm-002/upstage-synthetic-evaluation.json
OVERALL_PASS=true|false
```

- [ ] **Step 6: Run focused gates and commit**

```powershell
& $uv run --project apps/api --frozen pytest apps/api/tests/llm/test_report.py -q
python -B -m unittest scripts.tests.test_run_upstage_synthetic_evaluation -v
& $uv run --project apps/api --frozen ruff check apps/api/src/sejong_ai_api/llm apps/api/tests/llm
& $uv run --project apps/api --frozen mypy apps/api/src/sejong_ai_api/llm apps/api/tests/llm
git add apps/api/src/sejong_ai_api/llm apps/api/tests/llm scripts/run_upstage_synthetic_evaluation.py scripts/tests/test_run_upstage_synthetic_evaluation.py scripts/README.md
git commit -m "feat(llm): add safe synthetic evaluation runner"
```

---

### Task 6: Offline security, architecture and regression gates

**Files:**
- Create: `apps/api/tests/llm/test_architecture.py`
- Create: `apps/api/tests/llm/test_security.py`
- Modify: `apps/api/tests/test_architecture.py`
- Modify: `versions/manifest.json`
- Modify: `CHANGELOG.md`
- Modify: `README.md`
- Modify: `apps/api/README.md`
- Modify: `TASKS.md`
- Modify: related source-of-truth/policy only where implementation status changes

**Interfaces:**
- Consumes: Tasks 1–5
- Produces: offline-verified evaluator with provider disabled by default

- [ ] **Step 1: Add architecture RED assertions**

```python
from pathlib import Path


def test_public_app_and_chat_do_not_import_llm_package() -> None:
    for relative in (
        "apps/api/src/sejong_ai_api/main.py",
        "apps/api/src/sejong_ai_api/local.py",
        "apps/api/src/sejong_ai_api/api/chat.py",
        "apps/api/src/sejong_ai_api/chat/service.py",
    ):
        content = Path(relative).read_text(encoding="utf-8")
        assert "sejong_ai_api.llm" not in content


def test_no_llm_http_router_exists() -> None:
    assert not Path("apps/api/src/sejong_ai_api/api/llm.py").exists()
```

- [ ] **Step 2: Add security matrix**

Use `httpx.MockTransport` and sentinel strings to prove:

- API key is only in the Authorization header received by the mock and absent from repr/outcome/report
- raw pre-redaction PII never reaches provider
- provider body/content never reaches Python logging records
- client-supplied `is_test`, question, model, base URL and cap are not accepted
- T-11 through T-20 and modified T-01 projection call count is zero
- source metadata is absent from prompt and model schema
- provider output with source/status/intent is schema-invalid and triggers template fallback
- 30th attempt may execute and 31st cannot reach transport
- calling health/readiness and constructing/importing the default app causes zero transport calls

- [ ] **Step 3: Run the entire API and root focused suite offline**

Run with provider environment explicitly disabled:

```powershell
$env:LLM_PROVIDER = "disabled"
$env:UPSTAGE_SYNTHETIC_EVALUATION_MODE = "false"
try {
  & $uv run --project apps/api --frozen pytest apps/api/tests -q
  & $uv run --project apps/api --frozen ruff format --check apps/api/src apps/api/tests
  & $uv run --project apps/api --frozen ruff check apps/api/src apps/api/tests
  & $uv run --project apps/api --frozen mypy apps/api/src apps/api/tests
  python -B -m unittest discover -s scripts/tests -p "test_*.py" -v
} finally {
  Remove-Item Env:LLM_PROVIDER -ErrorAction SilentlyContinue
  Remove-Item Env:UPSTAGE_SYNTHETIC_EVALUATION_MODE -ErrorAction SilentlyContinue
}
```

Expected: all relevant tests PASS; approved environment-specific skips are counted and recorded.

- [ ] **Step 4: Run secret/dependency/contract drift gates**

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/check_secret_patterns.ps1 -RepositoryRoot .
python -B scripts/check_repository_docs.py
node scripts/check_web_prod_dependency_boundary.mjs
git diff -- pnpm-lock.yaml apps/api/uv.lock contracts database supabase data
git diff --check
```

Expected: secret clean, docs PASS, dependency boundary PASS, protected diff empty, whitespace error 0.

- [ ] **Step 5: Update implementation versions**

Set:

- `application`: `0.7.0-local-synthetic-evaluator`
- `prompt_set`: `0.1.0-upstage-solar-pro3-synthetic`
- `test_suite`: `1.3.0-upstage-synthetic-evaluator`
- `documentation`: `2.14.0`

Keep the internal API package `0.4.0`, public `api=3.1.0-draft`, shared contracts, DB, official/mock
data and Web unchanged. Do not modify `apps/api/pyproject.toml` or regenerate `uv.lock`; the isolated
evaluator is versioned through the application/prompt/test/documentation axes in the manifest.

- [ ] **Step 6: Review and commit**

```powershell
git add apps/api/tests versions/manifest.json CHANGELOG.md README.md apps/api/README.md TASKS.md docs
git commit -m "test(llm): lock synthetic provider boundaries"
```

Do not include an actual provider result in this commit.

---

### Task 7: Local-only actual evaluation and PM scoring

**Files:**
- Read ignored: `apps/api/.env`
- Read ignored: `artifacts/llm-002/upstage-synthetic-evaluation.json`
- Create after PASS/FAIL is known:
  `docs/test-reports/LLM-002-UPSTAGE-SYNTHETIC-EVALUATION.md`
- Modify: `TASKS.md`
- Modify: current LLM-002 implementation note and INDEX

**Interfaces:**
- Consumes: local DB containing final ACTIVE/OFFICIAL 20, ignored Upstage key, Tasks 1–6
- Produces: aggregate actual evidence and human decision, never answer text

- [ ] **Step 1: Human prepares the ignored local environment**

The user edits `apps/api/.env` locally:

```dotenv
LLM_PROVIDER=upstage
LLM_MODEL=solar-pro3
LLM_API_KEY=
LLM_BASE_URL=https://api.upstage.ai/v1
LLM_TIMEOUT_SECONDS=15
LLM_MAX_RETRIES=1
LLM_MAX_CONCURRENCY=1
LLM_MAX_INPUT_TOKENS=4096
LLM_MAX_OUTPUT_TOKENS=1024
LLM_RUN_ATTEMPT_CAP=30
UPSTAGE_SYNTHETIC_EVALUATION_MODE=true
```

The user pastes the key only after the final `=` in the ignored local file. The key is not pasted into
chat, GitHub, Codex Cloud, PowerShell history, a command argument or a tracked file.

- [ ] **Step 2: Reconfirm official mutable facts**

Before the call, verify from Upstage official pages:

- exact model remains `solar-pro3`
- base URL remains `https://api.upstage.ai/v1`
- price remains input USD 0.15/M, cached input USD 0.015/M, output USD 0.60/M, VAT excluded
- privacy policy/account setting does not justify widening beyond synthetic input

Use only the official [Chat API](https://console.upstage.ai/api-keys?api=chat),
[pricing](https://www.upstage.ai/pricing/api) and
[privacy policy](https://www.upstage.ai/privacy-policy) pages for this mutable-fact snapshot.

If any value changed, stop without calling and return the plan to Review.

- [ ] **Step 3: Run preflight without revealing values**

```powershell
git status --short
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/check_secret_patterns.ps1 -RepositoryRoot .
python -B scripts/check_git_history_secrets.py --repo . --local-secret-file apps/api/.env --local-secret-name LLM_API_KEY
```

Expected: tracked tree clean except planned report/note work, current/history secret matches 0. The scanner
prints counts/rule IDs only.

- [ ] **Step 4: Run interactive actual evaluation once**

The human runs in a personal local interactive terminal, not Codex Cloud:

```powershell
& $uv run --project apps/api --frozen python scripts/run_upstage_synthetic_evaluation.py --review
```

Review the first valid result for each T-01..T-10 and enter five scores. Do not rerun automatically
to improve results. If the process fails, retain the aggregate failure counts, keep provider disabled
and do not claim 30 completed generations.

- [ ] **Step 5: Apply the acceptance gate**

Overall PASS requires all:

- all completed provider outputs strict-schema valid; planned 30 valid generations if no retry consumed cap
- conservative preflight and every provider-reported input usage are at most 4096 tokens
- source/additional fields, PII/secret persistence and critical official-fact contradiction all zero
- human five-dimension mean at least 4.0 and no individual dimension below 3
- concurrency 1, hidden retry 0, outbound attempts at most 30
- every provider failure produced the deterministic template result
- actual estimated cost including VAT at most USD 0.05

Any failure keeps actual citizen/free-input option B unapproved.

- [ ] **Step 6: Publish aggregate evidence and remove/retain the local key deliberately**

Create the Markdown report from the ignored aggregate JSON. Include counts, scores, reason codes,
token totals, price snapshot, cost and PASS/FAIL; do not include question or answer text, key, DSN,
request/response body, account data or raw error.

After the run, the user either removes `LLM_API_KEY` and returns provider to disabled, or deliberately
keeps the key in ignored local `.env`. In both cases Git/history scans must remain clean.

- [ ] **Step 7: Commit actual evidence**

```powershell
git add docs/test-reports/LLM-002-UPSTAGE-SYNTHETIC-EVALUATION.md TASKS.md docs/implementation-notes
git commit -m "docs(llm): record Upstage synthetic evaluation"
```

This commit does not authorize option B.

---

### Task 8: Final full regression, review and handoff

**Files:**
- Modify: LLM-002 implementation note/INDEX
- Modify: source-of-truth/TASKS/CHANGELOG/version only for actual final status
- No product/API/DB/data changes

**Interfaces:**
- Consumes: Tasks 1–7
- Produces: reviewable owner branch and explicit actual status

- [ ] **Step 1: Disable provider for the full regression**

Set process overrides to `LLM_PROVIDER=disabled` and
`UPSTAGE_SYNTHETIC_EVALUATION_MODE=false`; do not delete or print the ignored file.

- [ ] **Step 2: Run final repository gate**

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/verify.ps1 -Offline
python -B scripts/check_repository_docs.py
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/check_secret_patterns.ps1 -RepositoryRoot .
git diff --check
```

Expected: root offline PASS, docs PASS, secret clean, diff clean. If the root gate has an
environment-specific skip/failure, record the exact bounded stage and run the approved focused
replacement; never rewrite it as a full PASS.

- [ ] **Step 3: Perform requirement-by-requirement diff review**

Verify:

- public route/import/provider call count remains zero
- API/OpenAPI/shared/Web/DB/migration/official data/dependencies unchanged
- default/import/startup/health/readiness network count zero
- allowlist is exact and hash-bound
- provider bodies and human-visible content are absent from tracked files/log records
- report math reconciles attempts, outcomes, tokens and USD cost
- input upper-bound and provider-reported prompt-token limits both reconcile at or below 4096
- actual status does not imply option B approval

- [ ] **Step 4: Finalize documentation**

Mark LLM-002:

- `Done — synthetic evaluation PASS` only if all automated and PM gates passed, or
- `Review/Blocked — synthetic evaluation failed` with exact aggregate reason codes.

Record every command, count, duration, version, privacy/cost impact and rollback in the implementation
note. Keep actual citizen/public provider use Pending in A-044/D-065/D-066.

- [ ] **Step 5: Commit closeout**

```powershell
git add CHANGELOG.md README.md TASKS.md versions/manifest.json docs
git commit -m "docs(llm): close synthetic evaluator"
git status --short
```

Expected: commit succeeds and status is clean. Do not push or create/merge a PR unless the user
explicitly asks.

---

## Test Matrix

| Layer | Evidence |
|---|---|
| Unit | settings, strict types, prompt omission, Decimal cost, attempt cap, response parsing |
| Integration-offline | HTTPX MockTransport retry/failure matrix, repository grounding, report safety |
| Architecture | public app/chat imports and route 0, startup/health/readiness network 0 |
| Privacy/security | raw PII/provider body/key log/persistence 0, exact fixture projection |
| Actual local | Upstage T-01..T-10, up to 30 attempts, aggregate tokens/cost |
| Human quality | ten first-valid fixture results, five dimensions, closed reason codes |
| Regression | full API/root offline with provider disabled |
| Contract/DB/Web | no diff; existing gates remain green |

## Version Change Plan

| Axis | Before plan execution | After successful implementation |
|---|---|---|
| Product spec | 2.4.0 | 2.4.0 |
| Application | 0.6.0-local-core-loop | 0.7.0-local-synthetic-evaluator |
| Internal API package | 0.4.0 | unchanged |
| Public API | 3.1.0-draft | unchanged |
| Web | 0.4.0-chat-admin-local-integration | unchanged |
| DB schema | 0.4.0-local | unchanged |
| Official data | 0.1.0-initial.2 | unchanged |
| Prompt set | 0.0.3-upstage-solar-pro3-synthetic-selected | 0.1.0-upstage-solar-pro3-synthetic |
| Test suite | 1.2.1-core-loop-closeout | 1.3.0-upstage-synthetic-evaluator |
| Documentation | 2.13.1 | 2.14.0 |

## Risks and Rollback

| Risk | Early signal | Required response |
|---|---|---|
| key/body leak | secret scanner or log sentinel match | stop, revoke key, scan current/history, no actual claim |
| provider policy/price drift | official values differ at Task 7 | stop before call, update spec/plan with approval |
| input limit drift/overflow | preflight bytes or actual usage >4096 | call count 0 or stop after bounded attempt; keep provider disabled |
| attempt/cost overrun | attempt >30 or estimate >USD 0.05 | stop, keep disabled, investigate without rerun |
| unstable JSON/Korean | invalid outcome or PM gate failure | retain deterministic MVP, option B remains blocked |
| source hallucination | source/status extra field | schema reject, template fallback, tracked count only |
| public route coupling | llm import in app/chat files | revert offending task before actual call |
| canonical data drift | allowlist projection hash mismatch | call count 0, review data change separately |

Rollback is one or more small task commits in reverse order. Set provider disabled and remove the local
key first. Because no public API/DB/data path changes, rollback never requires migration, data restore
or Web deployment.

## Human Approval Boundary

Already approved:

- Q-LLM-005=A and the written specification
- Upstage direct `solar-pro3` synthetic-first boundary
- no new production dependency

Required before implementation:

- this execution plan

Required during execution:

- user enters the ignored local key
- PM performs ten-result Korean quality review

Still not approved:

- actual citizen/free-input/public/remote provider connection
- higher attempt/cost/model limit, another model, auto-recharge
- Cloud secret or Cloud actual call
- new dependency, public route, DB/API contract change

## Plan Self-Review

- Spec coverage: all design sections map to Tasks 1–8; no public/citizen integration task exists.
- Placeholder scan: no implementation placeholder or open code decision remains; the local secret
  line is intentionally blank and accompanied by a human-only entry instruction.
- Type consistency: reusable `exact_settings` and `grounded_fixture` fixtures plus
  `UpstageSyntheticSettings`, `GroundedFixture`, `TokenUsage`, `GenerationOutcome`, `AttemptBudget`,
  `UpstageProvider`, `PreparationCode`, `SyntheticFixture`, `PreparedCaseFailure`, `ReviewSample`,
  `EvaluationCaseResult`, `EvaluationRun`, `HumanFixtureScore` and report names are introduced before
  use.
- Dependency consistency: only existing `httpx`, Pydantic and repository interfaces are used.
- Input consistency: canonical-message UTF-8 bytes are a fail-closed preflight upper bound and actual
  provider prompt usage above 4096 stops the run.
- Cost consistency: 4096/1024 worst-case ×30 with VAT is USD 0.0405504, below USD 0.05.
- Safety consistency: actual network occurs only in Task 7 after offline tests and human plan approval.

## Progress Record

- 2026-07-23: PR #6 merge `c3fd2ee` verified.
- 2026-07-23: Q-LLM-005=A recorded as D-065; written design committed at `b318375`.
- 2026-07-23: user approved the written specification; D-066 and this Review plan created.

## Result and Retrospective

- Actual result: not executed; product code/key/network call remain zero at plan publication.
- Plan deviation: none at publication.
- Next step: user reviews and approves this plan, then implementation starts with Task 1 RED tests.
