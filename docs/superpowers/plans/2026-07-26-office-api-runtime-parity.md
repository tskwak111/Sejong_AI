# OFFICE-API-001 Office Directory Runtime Parity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the already-declared `GET /api/v1/offices` contract in the default and local FastAPI applications, returning only server-owned OFFICIAL office metadata and failing closed when the local repository is unavailable.

**Architecture:** A strict `OfficeListResponse` reuses the existing public `Office` model, while one shared response mapper serves both chat cards and the standalone directory. A small directory service depends only on the existing typed repository protocol, a readiness guard prevents unsafe reads, and a router-level dependency keeps the route discoverable in the default app while returning a value-free 503 until a local directory is injected.

**Tech Stack:** Python 3.12.13, FastAPI, Pydantic v2, pytest, Ruff, MyPy, PostgreSQL through the existing Psycopg repository, OpenAPI 3.1, openapi-typescript 7.13.0, Node 24.12.0, pnpm 11.13.0, uv 0.11.28.

## Global Constraints

- Source baseline is private `origin/main` commit `8ebc66b65a67f106b05976112de345a8c849b631`; implement on `codex/OFFICE-API-001-design` and never merge automatically.
- Preserve required `region` and required supported `intent`; valid no-match is HTTP 200 with exact `{"items":[]}`.
- Return only records already filtered as `data_origin=OFFICIAL` by `app_api.list_offices`, preserving its deterministic `public_id` order.
- Never synthesize office identity, address, phone, map URL, source title, source URL, or verification date; map only typed `OfficeRecord` fields.
- Missing/invalid query input returns the existing value-free 422 `VALIDATION_ERROR`; closed dependency, readiness failure, and database failure return value-free 503 `SERVICE_UNAVAILABLE` with `Retry-After: 30`.
- Unexpected programming and model-validation errors must remain visible as test/500 failures; do not convert them to `items=[]`.
- Reuse the existing PostgreSQL function and repository adapter; add no migration, rollback, seed, official/mock data, pool, credential, or background task.
- Add no production dependency and do not change the lockfile.
- Do not call an LLM, use provider credentials, write chat/event/failed-question/candidate data, or process/store question text, PII, IP, or device identifiers.
- Do not change Web behavior, public/remote deployment, admin exposure, GPS, distance, or map behavior.
- Implementation completion targets are application `0.10.0-office-directory-runtime`, API `3.3.0-draft`, shared contracts `0.6.0`, and test suite `1.7.0-office-directory`; DB schema `0.4.0-local`, official data `0.1.0-initial.2`, prompt set `0.2.0-grounded-live-chat`, and Web `0.6.0-answer-mode` remain unchanged.
- Use TDD in RED→GREEN order, run focused tests per task, then one full API/contract/document/security gate at closeout.
- Use no secret-bearing output. The optional actual local smoke may print only endpoint status and item count, never DSN, environment values, query values, or returned records.

---

## File Map and Locked Interfaces

| File | Action | Single responsibility |
|---|---|---|
| `apps/api/src/sejong_ai_api/contracts/offices.py` | Create | Strict standalone office-list response only |
| `apps/api/src/sejong_ai_api/office/__init__.py` | Create | Package marker with no runtime composition |
| `apps/api/src/sejong_ai_api/office/response.py` | Create | `OfficeRecord` to public `Office` mapping shared by chat and directory |
| `apps/api/src/sejong_ai_api/office/service.py` | Create | Repository protocol, fail-closed service, readiness guard, closed default |
| `apps/api/src/sejong_ai_api/api/offices.py` | Create | HTTP query validation and 200/503 envelope assembly |
| `apps/api/src/sejong_ai_api/contracts/chat.py` | Modify | Export the existing `SupportedIntent` alias |
| `apps/api/src/sejong_ai_api/chat/response.py` | Modify | Consume the shared office mapper; remove private duplicate |
| `apps/api/src/sejong_ai_api/main.py` | Modify | Always register router and accept optional directory injection |
| `apps/api/src/sejong_ai_api/local.py` | Modify | Compose existing repository/probe into the directory |
| `apps/api/tests/office/test_contract_and_response.py` | Create | Strict model and exact metadata mapping regression |
| `apps/api/tests/office/test_service.py` | Create | Service/guard failure semantics and repository-call assertions |
| `apps/api/tests/test_offices_route.py` | Create | HTTP 200/422/503 and generated runtime OpenAPI |
| `apps/api/tests/test_local.py` | Modify | Local composition and readiness-failure integration |
| `apps/api/tests/chat/test_response.py` | Modify | Preserve existing chat office-card wire behavior |
| `contracts/openapi-v1.yaml` | Modify | Add reusable list response and explicit 422/503; bump API draft |
| `packages/shared-contracts/src/generated/api.ts` | Regenerate | Generated TypeScript for API 3.3.0-draft |
| `packages/shared-contracts/package.json` | Modify | Shared contract package `0.6.0` |
| `packages/shared-contracts/test/contract-structure.test.mjs` | Modify | Exact office-path/schema/error/version contract assertions |
| `apps/api/tests/test_health.py` | Modify | Expected runtime API version `3.3.0-draft` |
| `apps/api/README.md` | Modify | Actual endpoint and fail-closed local usage |
| `docs/05_API_AND_CONTRACTS.md` | Modify | Active office wire contract and non-goals |
| `docs/12_VERSIONING_AND_RELEASES.md` | Modify | Completed release-axis evidence |
| `TASKS.md` | Modify | OFFICE-API-001 completion/evidence |
| `CHANGELOG.md` | Modify | Runtime parity change and unchanged DB/data/provider scope |
| `versions/manifest.json` | Modify | Approved application/API/shared/test/docs version advances |
| `docs/implementation-notes/INDEX.md` | Modify | One closeout-note index row |
| `docs/implementation-notes/IMP-20260726-012-office-api-runtime-parity.md` | Create | Reproducible implementation closeout evidence |

The interfaces below are locked for every task:

```python
# contracts/offices.py
class OfficeListResponse(StrictPublicModel):
    items: list[Office]

# office/response.py
@overload
def build_public_office(record: OfficeRecord) -> Office: ...

@overload
def build_public_office(record: None) -> None: ...

def build_public_office(record: OfficeRecord | None) -> Office | None: ...

# office/service.py
class OfficeRepository(Protocol):
    async def list_offices(
        self, region: Region, intent: Intent
    ) -> Sequence[OfficeRecord]: ...

class OfficeDirectory(Protocol):
    async def list_offices(
        self, region: Region, intent: Intent
    ) -> tuple[Office, ...]: ...

class OfficeReadinessProbe(Protocol):
    async def check_ready(self) -> bool: ...
    def mark_unavailable(self) -> None: ...

class OfficeDirectoryUnavailableError(Exception): ...

class ClosedOfficeDirectory:
    async def list_offices(
        self, region: Region, intent: Intent
    ) -> tuple[Office, ...]: ...

class OfficeDirectoryService:
    def __init__(self, repository: OfficeRepository) -> None: ...
    async def list_offices(
        self, region: Region, intent: Intent
    ) -> tuple[Office, ...]: ...

class GuardedOfficeDirectory:
    def __init__(
        self, probe: OfficeReadinessProbe, directory: OfficeDirectory
    ) -> None: ...
    async def list_offices(
        self, region: Region, intent: Intent
    ) -> tuple[Office, ...]: ...

# api/offices.py
def get_office_directory() -> OfficeDirectory: ...
```

`OfficeDirectoryService` catches only `DatabaseUnavailableError`. `GuardedOfficeDirectory` converts readiness false to `OfficeDirectoryUnavailableError`, and marks the probe unavailable only after its wrapped directory raises that typed unavailable error.

### Task 1: Strict List Contract and Shared Office Mapper

**Files:**
- Create: `apps/api/src/sejong_ai_api/contracts/offices.py`
- Create: `apps/api/src/sejong_ai_api/office/__init__.py`
- Create: `apps/api/src/sejong_ai_api/office/response.py`
- Create: `apps/api/tests/office/__init__.py`
- Create: `apps/api/tests/office/test_contract_and_response.py`
- Modify: `apps/api/src/sejong_ai_api/contracts/chat.py`
- Modify: `apps/api/src/sejong_ai_api/chat/response.py:1-20,130-230`
- Modify: `apps/api/tests/chat/test_response.py`

**Interfaces:**
- Consumes: `OfficeRecord` from `sejong_ai_api.db.models`, `Office` and existing `SupportedIntent` from `sejong_ai_api.contracts.chat`, `StrictPublicModel` from `sejong_ai_api.contracts.health`.
- Produces: `OfficeListResponse`; overloaded `build_public_office(OfficeRecord) -> Office` and `build_public_office(None) -> None`; exported `SupportedIntent`.

- [ ] **Step 1: Write the strict list and exact mapping tests**

Create `apps/api/tests/office/test_contract_and_response.py` with a fixed OFFICIAL record fixture and these assertions:

```python
from datetime import date

import pytest
from pydantic import ValidationError

from sejong_ai_api.contracts.offices import OfficeListResponse
from sejong_ai_api.db.models import OfficeRecord, Region
from sejong_ai_api.office.response import build_public_office


def office_record() -> OfficeRecord:
    return OfficeRecord(
        public_id="OFFICE-AREUM",
        region=Region.AREUM_DONG,
        office_name="아름동 행정복지센터",
        address="세종특별자치시 보듬3로 114",
        phone="044-301-6300",
        opening_hours="평일 09:00~18:00",
        map_url="https://www.sejong.go.kr/office/map",
        department_label="내부 담당 부서",
        source_title="세종특별자치시 공식 기관 안내",
        source_url="https://www.sejong.go.kr/office",
        last_verified_at=date(2026, 7, 19),
    )


def test_office_list_requires_explicit_items_and_accepts_empty_list() -> None:
    assert OfficeListResponse(items=[]).model_dump(mode="json") == {"items": []}
    with pytest.raises(ValidationError):
        OfficeListResponse.model_validate({})


def test_office_record_maps_only_exact_public_fields() -> None:
    public = build_public_office(office_record())
    payload = public.model_dump(mode="json")
    assert payload == {
        "id": "OFFICE-AREUM",
        "region": "아름동",
        "office_name": "아름동 행정복지센터",
        "address": "세종특별자치시 보듬3로 114",
        "phone": "044-301-6300",
        "opening_hours": "평일 09:00~18:00",
        "map_url": "https://www.sejong.go.kr/office/map",
        "source_title": "세종특별자치시 공식 기관 안내",
        "source_url": "https://www.sejong.go.kr/office",
        "last_verified_at": "2026-07-19",
    }
    assert "department_label" not in payload
    assert build_public_office(None) is None
```

Add one assertion to the existing chat success/fallback office-card tests that the JSON remains byte-for-field equivalent after the mapper move; do not change the fixture values or public keys.

- [ ] **Step 2: Run the focused tests and confirm RED**

Run:

```powershell
uv run --directory apps/api --frozen pytest `
  tests/office/test_contract_and_response.py `
  tests/chat/test_response.py -q -p no:cacheprovider
```

Expected: FAIL during collection because `contracts.offices` and `office.response` do not exist.

- [ ] **Step 3: Add the strict response and shared mapper**

Create `contracts/offices.py`:

```python
"""Public response contract for the official office directory."""

from sejong_ai_api.contracts.chat import Office
from sejong_ai_api.contracts.health import StrictPublicModel


class OfficeListResponse(StrictPublicModel):
    items: list[Office]


__all__ = ["OfficeListResponse"]
```

Create `office/response.py` with the exact existing mapping and overloads:

```python
"""Server-owned conversion from database office records to public cards."""

from typing import overload

from pydantic import AnyUrl

from sejong_ai_api.contracts.chat import Office
from sejong_ai_api.db.models import OfficeRecord


@overload
def build_public_office(record: OfficeRecord) -> Office: ...


@overload
def build_public_office(record: None) -> None: ...


def build_public_office(record: OfficeRecord | None) -> Office | None:
    if record is None:
        return None
    return Office(
        id=record.public_id,
        region=record.region.value,
        office_name=record.office_name,
        address=record.address,
        phone=record.phone,
        opening_hours=record.opening_hours,
        map_url=AnyUrl(record.map_url) if record.map_url is not None else None,
        source_title=record.source_title,
        source_url=AnyUrl(record.source_url),
        last_verified_at=record.last_verified_at,
    )


__all__ = ["build_public_office"]
```

Replace both `_public_office(...)` calls in `chat/response.py` with `build_public_office(...)`, import the helper, and delete the private function and now-unused `AnyUrl` import. Add `"SupportedIntent"` to `contracts/chat.py::__all__`. Keep both package `__init__.py` files empty.

- [ ] **Step 4: Run focused format, type, and test gates**

Run:

```powershell
uv run --directory apps/api --frozen ruff format --check `
  src/sejong_ai_api/contracts/offices.py `
  src/sejong_ai_api/office `
  src/sejong_ai_api/chat/response.py `
  tests/office tests/chat/test_response.py
uv run --directory apps/api --frozen ruff check `
  src/sejong_ai_api/contracts/offices.py `
  src/sejong_ai_api/office `
  src/sejong_ai_api/chat/response.py `
  tests/office tests/chat/test_response.py
uv run --directory apps/api --frozen mypy `
  src/sejong_ai_api/contracts/offices.py `
  src/sejong_ai_api/office `
  src/sejong_ai_api/chat/response.py
uv run --directory apps/api --frozen pytest `
  tests/office/test_contract_and_response.py `
  tests/chat/test_response.py -q -p no:cacheprovider
```

Expected: all commands PASS; existing chat JSON shape is unchanged and `department_label` is absent.

- [ ] **Step 5: Commit the contract and mapping**

```powershell
git add -- `
  apps/api/src/sejong_ai_api/contracts/chat.py `
  apps/api/src/sejong_ai_api/contracts/offices.py `
  apps/api/src/sejong_ai_api/chat/response.py `
  apps/api/src/sejong_ai_api/office/__init__.py `
  apps/api/src/sejong_ai_api/office/response.py `
  apps/api/tests/office/__init__.py `
  apps/api/tests/office/test_contract_and_response.py `
  apps/api/tests/chat/test_response.py
git commit -m "refactor(api): share official office response mapping"
```

### Task 2: Directory Service, Closed Default, and Readiness Guard

**Files:**
- Create: `apps/api/src/sejong_ai_api/office/service.py`
- Create: `apps/api/tests/office/test_service.py`

**Interfaces:**
- Consumes: Task 1 `build_public_office(OfficeRecord) -> Office`; existing `DatabaseUnavailableError`, `Region`, `Intent`, and `OfficeRecord`.
- Produces: `OfficeRepository`, `OfficeDirectory`, `OfficeReadinessProbe`, `OfficeDirectoryUnavailableError`, `ClosedOfficeDirectory`, `OfficeDirectoryService`, and `GuardedOfficeDirectory` with the locked interfaces above.

- [ ] **Step 1: Write service and guard failure tests**

Create fakes that record calls without a database:

```python
from datetime import date

import pytest

from sejong_ai_api.contracts.chat import Office
from sejong_ai_api.db.errors import DatabaseUnavailableError
from sejong_ai_api.db.models import Intent, OfficeRecord, Region
from sejong_ai_api.office.service import (
    GuardedOfficeDirectory,
    OfficeDirectoryService,
    OfficeDirectoryUnavailableError,
)


def office_record(public_id: str) -> OfficeRecord:
    return OfficeRecord(
        public_id=public_id,
        region=Region.AREUM_DONG,
        office_name=f"{public_id} 행정복지센터",
        address="세종특별자치시 보듬3로 114",
        phone="044-301-6300",
        opening_hours=None,
        map_url=None,
        department_label="내부 담당 부서",
        source_title="세종특별자치시 공식 기관 안내",
        source_url="https://www.sejong.go.kr/office",
        last_verified_at=date(2026, 7, 19),
    )


class FakeRepository:
    def __init__(
        self,
        records: tuple[OfficeRecord, ...] = (),
        error: Exception | None = None,
    ) -> None:
        self.records = records
        self.error = error
        self.calls: list[tuple[Region, Intent]] = []

    async def list_offices(
        self, region: Region, intent: Intent
    ) -> tuple[OfficeRecord, ...]:
        self.calls.append((region, intent))
        if self.error is not None:
            raise self.error
        return self.records


class FakeProbe:
    def __init__(self, ready: bool) -> None:
        self.ready = ready
        self.mark_count = 0

    async def check_ready(self) -> bool:
        return self.ready

    def mark_unavailable(self) -> None:
        self.mark_count += 1
        self.ready = False


class FakeDirectory:
    def __init__(self) -> None:
        self.calls: list[tuple[Region, Intent]] = []

    async def list_offices(
        self, region: Region, intent: Intent
    ) -> tuple[Office, ...]:
        self.calls.append((region, intent))
        return ()


class FailingDirectory:
    async def list_offices(
        self, region: Region, intent: Intent
    ) -> tuple[Office, ...]:
        del region, intent
        raise OfficeDirectoryUnavailableError
```

Add exact tests:

```python
@pytest.mark.asyncio
async def test_service_passes_typed_filters_and_preserves_record_order() -> None:
    repository = FakeRepository((office_record("OFFICE-02"), office_record("OFFICE-01")))
    directory = OfficeDirectoryService(repository)
    result = await directory.list_offices(Region.AREUM_DONG, Intent.BULKY_WASTE)
    assert repository.calls == [(Region.AREUM_DONG, Intent.BULKY_WASTE)]
    assert tuple(item.id for item in result) == ("OFFICE-02", "OFFICE-01")


@pytest.mark.asyncio
async def test_service_maps_only_database_unavailable_to_directory_unavailable() -> None:
    directory = OfficeDirectoryService(FakeRepository(error=DatabaseUnavailableError()))
    with pytest.raises(OfficeDirectoryUnavailableError):
        await directory.list_offices(Region.AREUM_DONG, Intent.BULKY_WASTE)


@pytest.mark.asyncio
async def test_guard_skips_directory_when_readiness_is_false() -> None:
    wrapped = FakeDirectory()
    guarded = GuardedOfficeDirectory(FakeProbe(False), wrapped)
    with pytest.raises(OfficeDirectoryUnavailableError):
        await guarded.list_offices(Region.AREUM_DONG, Intent.BULKY_WASTE)
    assert wrapped.calls == []


@pytest.mark.asyncio
async def test_guard_marks_probe_unavailable_after_typed_read_failure() -> None:
    probe = FakeProbe(True)
    guarded = GuardedOfficeDirectory(probe, FailingDirectory())
    with pytest.raises(OfficeDirectoryUnavailableError):
        await guarded.list_offices(Region.AREUM_DONG, Intent.BULKY_WASTE)
    assert probe.mark_count == 1
```

Also test `ClosedOfficeDirectory` always raises and that a raw `RuntimeError` from a repository is not converted to an empty tuple or typed unavailable error.

- [ ] **Step 2: Run the service tests and confirm RED**

Run:

```powershell
uv run --directory apps/api --frozen pytest `
  tests/office/test_service.py -q -p no:cacheprovider
```

Expected: FAIL during collection because `office.service` does not exist.

- [ ] **Step 3: Implement only the typed service boundaries**

Create `office/service.py`:

```python
"""Read-only official office directory and fail-closed readiness boundary."""

from collections.abc import Sequence
from typing import Protocol

from sejong_ai_api.contracts.chat import Office
from sejong_ai_api.db.errors import DatabaseUnavailableError
from sejong_ai_api.db.models import Intent, OfficeRecord, Region
from sejong_ai_api.office.response import build_public_office


class OfficeRepository(Protocol):
    async def list_offices(
        self, region: Region, intent: Intent
    ) -> Sequence[OfficeRecord]: ...


class OfficeDirectory(Protocol):
    async def list_offices(
        self, region: Region, intent: Intent
    ) -> tuple[Office, ...]: ...


class OfficeReadinessProbe(Protocol):
    async def check_ready(self) -> bool: ...
    def mark_unavailable(self) -> None: ...


class OfficeDirectoryUnavailableError(Exception):
    """Signal that no safe official directory response can be produced."""


class ClosedOfficeDirectory:
    async def list_offices(
        self, region: Region, intent: Intent
    ) -> tuple[Office, ...]:
        del region, intent
        raise OfficeDirectoryUnavailableError


class OfficeDirectoryService:
    def __init__(self, repository: OfficeRepository) -> None:
        self._repository = repository

    async def list_offices(
        self, region: Region, intent: Intent
    ) -> tuple[Office, ...]:
        try:
            records = await self._repository.list_offices(region, intent)
        except DatabaseUnavailableError as exc:
            raise OfficeDirectoryUnavailableError from exc
        return tuple(build_public_office(record) for record in records)


class GuardedOfficeDirectory:
    def __init__(
        self, probe: OfficeReadinessProbe, directory: OfficeDirectory
    ) -> None:
        self._probe = probe
        self._directory = directory

    async def list_offices(
        self, region: Region, intent: Intent
    ) -> tuple[Office, ...]:
        if not await self._probe.check_ready():
            raise OfficeDirectoryUnavailableError
        try:
            return await self._directory.list_offices(region, intent)
        except OfficeDirectoryUnavailableError:
            self._probe.mark_unavailable()
            raise
```

Export only the seven locked public names through `__all__`. Do not catch `Exception`, `ValueError`, or Pydantic validation errors.

- [ ] **Step 4: Run focused service gates**

Run:

```powershell
uv run --directory apps/api --frozen ruff format --check `
  src/sejong_ai_api/office/service.py tests/office/test_service.py
uv run --directory apps/api --frozen ruff check `
  src/sejong_ai_api/office/service.py tests/office/test_service.py
uv run --directory apps/api --frozen mypy `
  src/sejong_ai_api/office/service.py tests/office/test_service.py
uv run --directory apps/api --frozen pytest `
  tests/office/test_service.py -q -p no:cacheprovider
```

Expected: PASS; false readiness produces zero wrapped-directory calls; DB unavailability is typed; raw programming errors remain visible.

- [ ] **Step 5: Commit the directory service**

```powershell
git add -- `
  apps/api/src/sejong_ai_api/office/service.py `
  apps/api/tests/office/test_service.py
git commit -m "feat(api): add fail-closed office directory service"
```

### Task 3: HTTP Router and Always-Registered Default Application

**Files:**
- Create: `apps/api/src/sejong_ai_api/api/offices.py`
- Create: `apps/api/tests/test_offices_route.py`
- Modify: `apps/api/src/sejong_ai_api/main.py:1-78`

**Interfaces:**
- Consumes: `OfficeListResponse`, `SupportedIntent`, `OfficeDirectory`, `ClosedOfficeDirectory`, and `OfficeDirectoryUnavailableError`.
- Produces: `get_office_directory() -> OfficeDirectory`, an `APIRouter` with `GET /api/v1/offices`, and `create_app(..., office_directory: OfficeDirectory | None = None)`.

- [ ] **Step 1: Write default, success, empty, validation, and OpenAPI route tests**

Create an injected fake directory:

```python
from datetime import date

from fastapi.testclient import TestClient
from pydantic import AnyUrl

from sejong_ai_api.contracts.chat import Office
from sejong_ai_api.db.models import Intent, Region
from sejong_ai_api.main import create_app


def public_office() -> Office:
    return Office(
        id="OFFICE-AREUM",
        region="아름동",
        office_name="아름동 행정복지센터",
        address="세종특별자치시 보듬3로 114",
        phone="044-301-6300",
        opening_hours="평일 09:00~18:00",
        map_url=AnyUrl("https://www.sejong.go.kr/office/map"),
        source_title="세종특별자치시 공식 기관 안내",
        source_url=AnyUrl("https://www.sejong.go.kr/office"),
        last_verified_at=date(2026, 7, 19),
    )


class FakeDirectory:
    def __init__(self, items: tuple[Office, ...] = ()) -> None:
        self.items = items
        self.calls: list[tuple[Region, Intent]] = []

    async def list_offices(
        self, region: Region, intent: Intent
    ) -> tuple[Office, ...]:
        self.calls.append((region, intent))
        return self.items
```

Write these test cases:

```python
def test_default_app_registers_offices_but_fails_closed() -> None:
    response = TestClient(create_app()).get(
        "/api/v1/offices",
        params={"region": "아름동", "intent": "BULKY_WASTE"},
    )
    assert response.status_code == 503
    assert response.headers["Retry-After"] == "30"
    assert response.json()["error"]["code"] == "SERVICE_UNAVAILABLE"
    assert response.json()["error"]["message"] == "잠시 후 다시 시도해 주세요."
    assert response.json()["error"]["retryable"] is True


def test_injected_directory_returns_exact_items_and_typed_filters() -> None:
    directory = FakeDirectory((public_office(),))
    response = TestClient(create_app(office_directory=directory)).get(
        "/api/v1/offices",
        params={"region": "아름동", "intent": "BULKY_WASTE"},
    )
    assert response.status_code == 200
    assert response.json() == {"items": [public_office().model_dump(mode="json")]}
    assert directory.calls == [(Region.AREUM_DONG, Intent.BULKY_WASTE)]


def test_valid_no_match_returns_explicit_empty_items() -> None:
    response = TestClient(create_app(office_directory=FakeDirectory())).get(
        "/api/v1/offices",
        params={"region": "아름동", "intent": "BULKY_WASTE"},
    )
    assert response.status_code == 200
    assert response.json() == {"items": []}
```

Parameterize missing region, missing intent, unsupported region, `UNKNOWN`, and `OUT_OF_SCOPE`; each must be exact 422 `VALIDATION_ERROR`, and a sentinel query value must not appear in the response text. Assert the fake directory has no calls. Finally inspect `create_app().openapi()` and assert:

```python
operation = create_app().openapi()["paths"]["/api/v1/offices"]["get"]
assert operation["operationId"] == "listOffices"
assert {item["name"] for item in operation["parameters"]} == {"region", "intent"}
assert all(item["required"] is True for item in operation["parameters"])
assert set(operation["responses"]) >= {"200", "422", "503"}
```

- [ ] **Step 2: Run the route tests and confirm RED**

Run:

```powershell
uv run --directory apps/api --frozen pytest `
  tests/test_offices_route.py -q -p no:cacheprovider
```

Expected: FAIL because the router is absent and `create_app` does not accept `office_directory`.

- [ ] **Step 3: Implement the route and dependency seam**

Create `api/offices.py`:

```python
"""HTTP boundary for read-only official office lookup."""

from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from sejong_ai_api.contracts.chat import SupportedIntent
from sejong_ai_api.contracts.errors import ValidationErrorEnvelope
from sejong_ai_api.contracts.health import (
    ServiceUnavailableDetail,
    ServiceUnavailableEnvelope,
)
from sejong_ai_api.contracts.offices import OfficeListResponse
from sejong_ai_api.db.models import Intent, Region
from sejong_ai_api.office.service import (
    ClosedOfficeDirectory,
    OfficeDirectory,
    OfficeDirectoryUnavailableError,
)

RETRY_AFTER_SECONDS = 30
router = APIRouter(prefix="/api/v1", tags=["offices"])
_CLOSED_DIRECTORY: OfficeDirectory = ClosedOfficeDirectory()


def get_office_directory() -> OfficeDirectory:
    return _CLOSED_DIRECTORY


@router.get(
    "/offices",
    operation_id="listOffices",
    response_model=OfficeListResponse,
    responses={
        422: {"model": ValidationErrorEnvelope, "description": "Invalid query"},
        503: {"model": ServiceUnavailableEnvelope, "description": "Dependency unavailable"},
    },
)
async def list_offices(
    request: Request,
    region: Annotated[Region, Query()],
    intent: Annotated[SupportedIntent, Query()],
    directory: Annotated[OfficeDirectory, Depends(get_office_directory)],
) -> OfficeListResponse | JSONResponse:
    try:
        items = await directory.list_offices(region, Intent(intent))
    except OfficeDirectoryUnavailableError:
        request_id = getattr(request.state, "request_id", None)
        resolved_request_id = request_id if isinstance(request_id, UUID) else uuid4()
        unavailable = ServiceUnavailableEnvelope(
            error=ServiceUnavailableDetail(
                code="SERVICE_UNAVAILABLE",
                message="잠시 후 다시 시도해 주세요.",
                request_id=resolved_request_id,
                retryable=True,
            )
        )
        return JSONResponse(
            status_code=503,
            headers={"Retry-After": str(RETRY_AFTER_SECONDS)},
            content=unavailable.model_dump(mode="json"),
        )
    return OfficeListResponse(items=list(items))


__all__ = ["get_office_directory", "router"]
```

In `main.py`, import and always include `offices_router`. Add the keyword-only seam:

```python
office_directory: OfficeDirectory | None = None,
```

When injected, override `get_office_directory` exactly as the health/chat seams do. Do not make route registration conditional and do not alter the admin route gate.

- [ ] **Step 4: Run route, health, logging, and OpenAPI-focused tests**

Run:

```powershell
uv run --directory apps/api --frozen ruff format --check `
  src/sejong_ai_api/api/offices.py src/sejong_ai_api/main.py `
  tests/test_offices_route.py
uv run --directory apps/api --frozen ruff check `
  src/sejong_ai_api/api/offices.py src/sejong_ai_api/main.py `
  tests/test_offices_route.py
uv run --directory apps/api --frozen mypy `
  src/sejong_ai_api/api/offices.py src/sejong_ai_api/main.py `
  tests/test_offices_route.py
uv run --directory apps/api --frozen pytest `
  tests/test_offices_route.py tests/test_health.py tests/test_logging.py `
  -q -p no:cacheprovider
```

Expected: PASS. The route exists in default OpenAPI, default reads are 503 rather than 404, invalid input is value-free 422, and safe request logging remains method/path/status/request-ID only.

- [ ] **Step 5: Commit the public runtime route**

```powershell
git add -- `
  apps/api/src/sejong_ai_api/api/offices.py `
  apps/api/src/sejong_ai_api/main.py `
  apps/api/tests/test_offices_route.py
git commit -m "feat(api): expose official office directory route"
```

### Task 4: Local Repository and Readiness Composition

**Files:**
- Modify: `apps/api/src/sejong_ai_api/local.py:24-40,164-205`
- Modify: `apps/api/tests/test_local.py:148-172,690-820`

**Interfaces:**
- Consumes: existing `RepositoryReadinessProbe`, `PsycopgSejongRepository`, Task 2 `OfficeDirectoryService` and `GuardedOfficeDirectory`, Task 3 `create_app(..., office_directory=...)`.
- Produces: ready local 200 office lookup and local fail-closed 503 with no second pool or background task.

- [ ] **Step 1: Add local composition integration tests**

Use the existing `FakePool`, `_config()`, `FakeRepository`, and official `_office(...)` fixtures. Add:

```python
def test_local_app_injects_ready_official_office_directory(tmp_path: Path) -> None:
    pool = FakePool()
    repositories: list[FakeRepository] = []

    def repository_factory(value: object) -> FakeRepository:
        repository = FakeRepository(value)
        repositories.append(repository)
        return repository

    app = create_local_app(
        environ=_config(),
        env_path=tmp_path / "missing",
        pool_factory=lambda _value: pool,
        repository_factory=repository_factory,
    )
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/offices",
            params={"region": "아름동", "intent": "BULKY_WASTE"},
        )
    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == ["OFFICE-AREUM"]
    assert all("department_label" not in item for item in response.json()["items"])


def test_local_office_directory_fails_closed_when_projection_is_not_ready(
    tmp_path: Path,
) -> None:
    pool = FakePool()
    app = create_local_app(
        environ=_config(),
        env_path=tmp_path / "missing",
        pool_factory=lambda _value: pool,
        repository_factory=lambda value: FakeRepository(value, ready=False),
    )
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/offices",
            params={"region": "아름동", "intent": "BULKY_WASTE"},
        )
    assert response.status_code == 503
    assert response.headers["Retry-After"] == "30"
    assert response.json()["error"]["code"] == "SERVICE_UNAVAILABLE"
```

Extend `FakeRepository` only with a call counter needed to prove its standalone directory read is not attempted after a false fake readiness result. Do not change production repository behavior.

- [ ] **Step 2: Run the local tests and confirm RED**

Run:

```powershell
uv run --directory apps/api --frozen pytest `
  tests/test_local.py -q -p no:cacheprovider
```

Expected: the new happy-path test FAILS with 503 because no office directory is injected yet; existing local tests remain green.

- [ ] **Step 3: Compose the existing repository and shared probe**

In `local.py`, add:

```python
from sejong_ai_api.office.service import GuardedOfficeDirectory, OfficeDirectoryService
```

After `responder = GuardedChatResponder(probe, service)`, construct:

```python
office_directory = GuardedOfficeDirectory(
    probe,
    OfficeDirectoryService(repository),
)
```

Pass `office_directory=office_directory` to the existing `create_app(...)` call. Do not create a second repository, pool, probe, lifespan operation, purge job, or credential loader. Leave every `return create_app()` construction-failure path unchanged so the always-registered route returns 503.

- [ ] **Step 4: Run local composition and affected area tests**

Run:

```powershell
uv run --directory apps/api --frozen ruff format --check `
  src/sejong_ai_api/local.py tests/test_local.py
uv run --directory apps/api --frozen ruff check `
  src/sejong_ai_api/local.py tests/test_local.py
uv run --directory apps/api --frozen mypy `
  src/sejong_ai_api/local.py tests/test_local.py
uv run --directory apps/api --frozen pytest `
  tests/test_local.py tests/test_offices_route.py tests/office `
  tests/chat/test_readiness.py -q -p no:cacheprovider
```

Expected: PASS. Ready local returns the exact official card, invalid configuration still yields the closed default route, and existing `/ready` and chat behavior do not regress.

- [ ] **Step 5: Commit local composition**

```powershell
git add -- apps/api/src/sejong_ai_api/local.py apps/api/tests/test_local.py
git commit -m "feat(api): compose local office directory"
```

### Task 5: Tracked OpenAPI, Generated TypeScript, and Contract Versions

**Files:**
- Modify: `contracts/openapi-v1.yaml:1-85` and `components.schemas`
- Modify: `packages/shared-contracts/package.json`
- Regenerate: `packages/shared-contracts/src/generated/api.ts`
- Modify: `packages/shared-contracts/test/contract-structure.test.mjs`
- Modify: `apps/api/src/sejong_ai_api/main.py:38`
- Modify: `apps/api/tests/test_health.py:76`

**Interfaces:**
- Consumes: runtime operation `listOffices`, `OfficeListResponse`, existing `ValidationError` and `ServiceUnavailable` reusable responses.
- Produces: tracked API `3.3.0-draft`, shared package `0.6.0`, generated TypeScript with required `region`/`intent` and 200/422/503.

- [ ] **Step 1: Tighten the tracked contract tests before editing YAML**

Update `contract-structure.test.mjs`:

```javascript
assert.equal(openApi.info.version, "3.3.0-draft");
const officeOperation = openApi.paths["/api/v1/offices"].get;
assert.equal(officeOperation.operationId, "listOffices");
assert.deepEqual(
  officeOperation.parameters.map(({ name, required }) => ({ name, required })),
  [
    { name: "region", required: true },
    { name: "intent", required: true },
  ],
);
assert.deepEqual(
  officeOperation.responses["200"].content["application/json"].schema,
  { $ref: "#/components/schemas/OfficeListResponse" },
);
assert.deepEqual(officeOperation.responses["422"], {
  $ref: "#/components/responses/ValidationError",
});
assert.deepEqual(officeOperation.responses["503"], {
  $ref: "#/components/responses/ServiceUnavailable",
});
assert.deepEqual(openApi.components.schemas.OfficeListResponse, {
  type: "object",
  additionalProperties: false,
  required: ["items"],
  properties: {
    items: {
      type: "array",
      items: { $ref: "#/components/schemas/Office" },
    },
  },
});
```

Update the API runtime version expectation in `test_health.py` to `3.3.0-draft`.

- [ ] **Step 2: Run contract and API version tests and confirm RED**

Run:

```powershell
corepack pnpm --filter @sejong-ai/shared-contracts test
uv run --directory apps/api --frozen pytest `
  tests/test_health.py tests/test_offices_route.py -q -p no:cacheprovider
```

Expected: contract test FAILS on `3.2.0-draft` and inline 200 schema; API test FAILS on runtime version `3.2.0-draft`.

- [ ] **Step 3: Update tracked/runtime contracts and package metadata**

Change:

```yaml
info:
  version: 3.3.0-draft
```

Replace the office responses with:

```yaml
responses:
  '200':
    description: Official office matches
    content:
      application/json:
        schema: { $ref: '#/components/schemas/OfficeListResponse' }
  '422': { $ref: '#/components/responses/ValidationError' }
  '503': { $ref: '#/components/responses/ServiceUnavailable' }
```

Add:

```yaml
OfficeListResponse:
  type: object
  additionalProperties: false
  required: [items]
  properties:
    items:
      type: array
      items: { $ref: '#/components/schemas/Office' }
```

Set `FastAPI(..., version="3.3.0-draft")` and shared package `"version": "0.6.0"`. Do not edit dependencies or `pnpm-lock.yaml`.

- [ ] **Step 4: Regenerate and prove zero generated drift**

Run:

```powershell
corepack pnpm --filter @sejong-ai/shared-contracts generate
corepack pnpm --filter @sejong-ai/shared-contracts generate:check
git diff --exit-code -- `
  pnpm-lock.yaml apps/api/pyproject.toml apps/api/uv.lock `
  database supabase data
corepack pnpm --filter @sejong-ai/shared-contracts test
uv run --directory apps/api --frozen pytest `
  tests/test_health.py tests/test_offices_route.py -q -p no:cacheprovider
```

Expected: generated check, contract tests, and API tests PASS; forbidden dependency/DB/data paths have zero diff.

- [ ] **Step 5: Commit the public contract minor release**

```powershell
git add -- `
  contracts/openapi-v1.yaml `
  packages/shared-contracts/package.json `
  packages/shared-contracts/src/generated/api.ts `
  packages/shared-contracts/test/contract-structure.test.mjs `
  apps/api/src/sejong_ai_api/main.py `
  apps/api/tests/test_health.py
git commit -m "feat(contract): publish office directory runtime schema"
```

### Task 6: Documentation, Version Closeout, Full Gate, and Draft PR

**Files:**
- Modify: `apps/api/README.md`
- Modify: `docs/05_API_AND_CONTRACTS.md`
- Modify: `docs/12_VERSIONING_AND_RELEASES.md`
- Modify: `TASKS.md`
- Modify: `CHANGELOG.md`
- Modify: `versions/manifest.json`
- Create: `docs/implementation-notes/IMP-20260726-012-office-api-runtime-parity.md`
- Modify: `docs/implementation-notes/INDEX.md`

**Interfaces:**
- Consumes: all Tasks 1–5 code and evidence.
- Produces: reproducible closeout, exact version axes, clean full gate, pushed owner branch, and a human-review Draft PR.

- [ ] **Step 1: Run changed-area review before closeout claims**

Run:

```powershell
git diff --check
git diff --stat origin/main...HEAD
git diff --name-status origin/main...HEAD
git diff --exit-code origin/main...HEAD -- `
  database supabase data apps/web pnpm-lock.yaml apps/api/uv.lock
rg -n "department_label|DATABASE_URL|LLM_API_KEY|UPSTAGE_API_KEY" `
  apps/api/src/sejong_ai_api/api/offices.py `
  apps/api/src/sejong_ai_api/office `
  apps/api/src/sejong_ai_api/contracts/offices.py
```

Expected: no whitespace errors; only planned Python/contract/test/docs/version files changed; forbidden paths have zero diff; office public modules contain no internal department field, DSN, or provider-key names.

- [ ] **Step 2: Perform the bounded actual local smoke when local prerequisites are available**

Start the existing local application through the repository’s documented command without printing environment values. Request one supported pair and one valid no-match pair, recording only:

```text
ready_status=200
office_match_status=200
office_match_count=1
office_empty_status=200
office_empty_count=0
```

If Docker/Supabase or the already-provisioned local environment is unavailable, record `Pending — local prerequisite unavailable` in the implementation note and rely on the injected local integration test. Do not start a remote DB, reseed, reset, migrate, call an LLM, or print records/DSN.

- [ ] **Step 3: Run one full implementation gate**

Run:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File scripts/verify.ps1
```

If a known environment bootstrap constraint prevents the aggregate script, run and record the exact constituent gates without changing dependency policy:

```powershell
uv run --directory apps/api --frozen ruff format --check src tests
uv run --directory apps/api --frozen ruff check src tests
uv run --directory apps/api --frozen mypy src tests
uv run --directory apps/api --frozen pytest -q -p no:cacheprovider
corepack pnpm --filter @sejong-ai/shared-contracts generate:check
corepack pnpm --filter @sejong-ai/shared-contracts test
python -B scripts/check_repository_docs.py
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File scripts/check_secret_patterns.ps1 -RepositoryRoot .
git diff --check
```

Expected: every executable gate PASS. Do not claim the aggregate gate passed if only constituent gates ran; record both the blocker and the substitute evidence.

- [ ] **Step 4: Update active documentation, task state, and exact versions**

Document:

- request/response examples, valid-empty 200, invalid 422, and closed 503;
- default route discovery versus local injected behavior;
- OFFICIAL-only server mapping and no `department_label`;
- no DB/data/Web/LLM/dependency/public/remote change;
- actual or Pending bounded local smoke;
- rollback by reverting route/service/model/OpenAPI/generated TypeScript together.

Set the manifest axes exactly:

```json
{
  "application": "0.10.0-office-directory-runtime",
  "api": "3.3.0-draft",
  "shared_contracts": "0.6.0",
  "test_suite": "1.7.0-office-directory"
}
```

Set `documentation` to `2.20.8`, the exact patch after this plan publication’s `2.20.7`, consistently in `versions/manifest.json` and `docs/12_VERSIONING_AND_RELEASES.md`. Leave product, repo guidance, Web, DB schema, official/mock data, and prompt axes exact and unchanged.

Mark OFFICE-API-001 `Done — Draft PR pending human merge` only after all executable gates pass. If a required gate fails, keep it `In Progress` and record the failure.

- [ ] **Step 5: Generate and complete one implementation note**

Run:

```powershell
python scripts/new_implementation_note.py `
  --title "OFFICE API runtime parity 구현" `
  --task-id "OFFICE-API-001" `
  --type "implementation"
```

Fill every applicable section with actual commits, exact commands/results, source baseline, before/after versions, security/privacy/data assessment, actual/Pending smoke, changed files, rejected alternatives, rollback, reproduction, handoff, and separate “인간이 반드시 알아야 하는 내용” / “AI 내부 구현 세부” sections. Confirm the generator appended exactly one INDEX row.

- [ ] **Step 6: Re-run document/version/diff gates after documentation edits**

Run:

```powershell
python -B -m json.tool versions/manifest.json > $null
python -B scripts/check_repository_docs.py
powershell.exe -NoProfile -ExecutionPolicy Bypass `
  -File scripts/check_secret_patterns.ps1 -RepositoryRoot .
corepack pnpm --filter @sejong-ai/shared-contracts generate:check
git diff --check
git status --short
```

Expected: all commands PASS; generated types are unchanged by closeout edits; only planned files remain.

- [ ] **Step 7: Commit, push, and create a Draft PR without merging**

```powershell
git add -- `
  apps/api CHANGELOG.md TASKS.md `
  contracts/openapi-v1.yaml packages/shared-contracts `
  docs/05_API_AND_CONTRACTS.md `
  docs/12_VERSIONING_AND_RELEASES.md `
  docs/implementation-notes `
  versions/manifest.json
git diff --cached --check
git diff --cached --stat
git commit -m "docs(api): close out office directory runtime parity"
git push -u origin codex/OFFICE-API-001-design
$body = @'
## Scope
- Implements the already-declared GET /api/v1/offices runtime in default/local FastAPI.
- Returns required region+supported intent OFFICIAL matches, deterministic order, and valid empty items.
- Adds safe 422/503 contracts; unavailable responses include Retry-After: 30.

## Unchanged boundaries
- No DB migration, seed, official/mock data, Web, LLM/provider, dependency, lockfile, public/remote deployment, or admin exposure change.

## Verification
- API Ruff/MyPy/pytest: PASS
- OpenAPI generation/shared contract tests: PASS
- Repository docs/secret/diff checks: PASS

## Rollback
- Revert the router/service/model/OpenAPI/generated TypeScript commits together; no data rollback is required.

## Evidence
- docs/implementation-notes/IMP-20260726-012-office-api-runtime-parity.md
'@
gh pr create --draft `
  --base main `
  --head codex/OFFICE-API-001-design `
  --title "feat(api): implement official office directory runtime" `
  --body $body
```

If the bounded actual smoke passed, insert this exact line under `## Verification` before creating the PR:

```text
- Bounded actual local smoke: PASS (`ready=200`, office match `200/count=1`, valid empty `200/count=0`)
```

If local prerequisites were unavailable, insert this exact alternative instead:

```text
- Bounded actual local smoke: Pending — local Docker/Supabase prerequisite unavailable; injected local integration PASS
```

Report the PR URL and stop; do not mark ready, merge, delete the branch, deploy, or run remote/public infrastructure.

---

## Self-Review Checklist

- [x] Every approved public case maps to a task: match 200, empty 200, missing/invalid 422, default/readiness/DB 503.
- [x] Every safety invariant maps to an assertion or diff gate: OFFICIAL-only existing DB function, server-owned metadata, internal field absence, no query echo, no write/LLM/provider path.
- [x] The runtime route and tracked OpenAPI both use `listOffices`, required region/intent, supported intent only, and 200/422/503.
- [x] The default app always exposes the route but never fabricates data; local composition reuses one repository/pool/probe.
- [x] Chat consumes the same mapper and its existing office-card wire tests remain green.
- [x] No migration, seed, official/mock data, Web, lockfile, production dependency, public/remote, or LLM change appears in the file map or commits.
- [x] Version updates are consistent across FastAPI, tracked OpenAPI, generated header, shared package, manifest, release docs, and tests.
- [x] There are no placeholder instructions, undefined interface names, or mismatched parameter/return types.
- [x] Implementation completion includes one reproducible implementation note, one INDEX append, and a human-review Draft PR with no automatic merge.
