#!/usr/bin/env python3
"""Run the one local/private 19-to-20 ACTIVE regression through actual HTTP."""

from __future__ import annotations

import asyncio
import os
import sys
import warnings
from collections.abc import Callable, Mapping, Sequence
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any, NoReturn, Protocol, cast
from uuid import UUID

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_API_SOURCE = _REPOSITORY_ROOT / "apps" / "api" / "src"
_API_ENV_PATH = _REPOSITORY_ROOT / "apps" / "api" / ".env"

_RESERVED_PUBLIC_ID = "KB-WASTE-03"
_RESERVED_QUESTION = "침대 2인용 프레임 수수료가 얼마예요?"
_PERSONAL_LOOKUP_QUESTION = "내 자동차세 체납액 알려줘."
_SOURCE_URL = "https://www.sjwaste.kr/wasteApp/appCategoryPopup.do?menuId=MENU00305"
_EXPECTED_FEE = "1인용침대 8,000원; 2인용침대 10,000원"
_PERSONAL_IDEMPOTENCY_KEY = "67000000-0000-4000-8000-000000000000"
_K1_IDEMPOTENCY_KEY = "67000000-0000-4000-8000-000000000001"
_K2_IDEMPOTENCY_KEY = "67000000-0000-4000-8000-000000000002"
_PERSISTENCE_COUNT_SQL = """
SELECT
  (SELECT count(*) FROM app_private.interaction_events) AS interaction_events,
  (SELECT count(*) FROM app_private.failed_questions) AS failed_questions
"""
_SUPPORTED_CATEGORIES = (
    "MOVE_IN_RESIDENT_REGISTRATION",
    "CERTIFICATE_ISSUANCE",
    "BULKY_WASTE",
    "LOCAL_TAX_GENERAL",
)

_OPERATOR_HEADERS = {
    "X-Demo-Actor-Id": "OPERATOR-LOCAL-001",
    "X-Demo-Role": "OPERATOR",
}
_FAKE_APPROVER_HEADERS = {
    "X-Demo-Actor-Id": "OPERATOR-LOCAL-001",
    "X-Demo-Role": "APPROVER",
}
_PM_APPROVER_HEADERS = {
    "X-Demo-Actor-Id": "PM-LOCAL-001",
    "X-Demo-Role": "APPROVER",
}


class _RegressionFailed(RuntimeError):
    """Value-free internal stop carrying only a stable step name."""


class _ConfigurationInvalid(RuntimeError):
    """The existing local-only configuration cannot run the regression."""


class _DiscardOutput:
    """Drop dependency output without retaining possible sensitive values."""

    encoding = "utf-8"

    def write(self, value: str) -> int:
        return len(value)

    def flush(self) -> None:
        return None

    def isatty(self) -> bool:
        return False


class _PoolOwner:
    """Close a manually composed async pool exactly until app lifespan owns it."""

    def __init__(self, pool: Any) -> None:
        self._pool = pool
        self._released = False

    def close(self) -> None:
        if self._released:
            return
        if getattr(self._pool, "closed", False) is True:
            self._released = True
            return
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            pass
        else:
            raise _ConfigurationInvalid
        asyncio.run(self._pool.close())
        if getattr(self._pool, "closed", False) is not True:
            raise _ConfigurationInvalid
        self._released = True

    def mark_lifespan_closed(self) -> None:
        if getattr(self._pool, "closed", False) is not True:
            self.close()
            return
        self._released = True


class _Response(Protocol):
    status_code: int

    def json(self) -> object: ...


class _RegressionRuntime(Protocol):
    def __enter__(self) -> _RegressionRuntime: ...

    def __exit__(
        self,
        exception_type: object,
        exception: object,
        traceback: object,
    ) -> None: ...

    def request(
        self,
        method: str,
        path: str,
        *,
        headers: Mapping[str, str] | None = None,
        json: Mapping[str, object] | None = None,
    ) -> _Response: ...

    def active_projection(self) -> Mapping[str, tuple[str, ...]]: ...

    def read_persistence_counts(self) -> Mapping[str, int]: ...


RuntimeFactory = Callable[[Mapping[str, str]], _RegressionRuntime]
PolicyConfigurer = Callable[[str], None]
PersistenceCountReader = Callable[[], Mapping[str, int]]


def _fail(step: str) -> NoReturn:
    raise _RegressionFailed(step)


def _mapping_response(response: _Response, status: int, step: str) -> dict[str, object]:
    if response.status_code != status:
        _fail(step)
    try:
        payload = response.json()
    except Exception:
        _fail(step)
    if type(payload) is not dict or any(type(key) is not str for key in payload):
        _fail(step)
    return cast(dict[str, object], payload)


def _required_uuid(value: object, step: str) -> str:
    if type(value) is not str:
        _fail(step)
    try:
        parsed = UUID(value)
    except (TypeError, ValueError, AttributeError):
        _fail(step)
    text = value
    if str(parsed) != text:
        _fail(step)
    return text


def _business_payload(payload: Mapping[str, object], step: str) -> dict[str, object]:
    business = dict(payload)
    _required_uuid(business.pop("request_id", None), step)
    return business


def _require_fallback(response: _Response, step: str) -> dict[str, object]:
    payload = _mapping_response(response, 200, step)
    fallback = payload.get("fallback")
    if (
        payload.get("answer_status") != "FALLBACK"
        or payload.get("intent") != "BULKY_WASTE"
        or payload.get("sources") != []
        or type(fallback) is not dict
        or fallback.get("reason") != "INSUFFICIENT_GROUNDING"
        or fallback.get("candidate_eligible") is not True
    ):
        _fail(step)
    _required_uuid(payload.get("request_id"), step)
    return payload


def _require_personal_lookup(response: _Response, step: str) -> dict[str, object]:
    payload = _mapping_response(response, 200, step)
    fallback = payload.get("fallback")
    if (
        payload.get("answer_status") != "FALLBACK"
        or payload.get("intent") != "UNKNOWN"
        or payload.get("sources") != []
        or type(fallback) is not dict
        or fallback.get("reason") != "PERSONAL_LOOKUP"
        or fallback.get("candidate_eligible") is not False
    ):
        _fail(step)
    _required_uuid(payload.get("request_id"), step)
    return payload


def _persistence_counts(
    counts: Mapping[str, int],
    step: str,
) -> tuple[int, int]:
    expected_keys = {"interaction_events", "failed_questions"}
    if type(counts) is not dict or set(counts) != expected_keys:
        _fail(step)
    interaction_events = counts.get("interaction_events")
    failed_questions = counts.get("failed_questions")
    if (
        type(interaction_events) is not int
        or interaction_events < 0
        or type(failed_questions) is not int
        or failed_questions < 0
    ):
        _fail(step)
    return interaction_events, failed_questions


def _require_success(response: _Response, step: str) -> dict[str, object]:
    payload = _mapping_response(response, 200, step)
    sources = payload.get("sources")
    if (
        payload.get("answer_status") != "SUCCESS"
        or payload.get("intent") != "BULKY_WASTE"
        or payload.get("fee") != _EXPECTED_FEE
        or type(sources) is not list
        or len(sources) != 1
    ):
        _fail(step)
    source = cast(list[object], sources)[0]
    if type(source) is not dict:
        _fail(step)
    source_record = cast(dict[str, object], source)
    if (
        source_record.get("source_id") != _RESERVED_PUBLIC_ID
        or source_record.get("url") != _SOURCE_URL
    ):
        _fail(step)
    _required_uuid(payload.get("request_id"), step)
    return payload


def _projection_ids(
    projection: Mapping[str, tuple[str, ...]],
    step: str,
) -> tuple[str, ...]:
    if set(projection) != set(_SUPPORTED_CATEGORIES):
        _fail(step)
    flattened: list[str] = []
    for category in _SUPPORTED_CATEGORIES:
        values = projection.get(category)
        if type(values) is not tuple or any(type(value) is not str for value in values):
            _fail(step)
        flattened.extend(values)
    if len(set(flattened)) != len(flattened):
        _fail(step)
    return tuple(flattened)


def _candidate_payload(failed_question_id: str) -> dict[str, object]:
    return {
        "failed_question_id": failed_question_id,
        "title": "침대 프레임 배출 수수료",
        "representative_question": _RESERVED_QUESTION,
        "category": "BULKY_WASTE",
        "answer_summary": (
            "공식 품목표의 침대 프레임 수수료는 1인용침대 8,000원, "
            "2인용침대 10,000원으로 표시됩니다."
        ),
        "procedure_steps": [
            "공식 품목표에서 침대 프레임의 1인용침대 또는 2인용침대 항목을 확인합니다.",
            "해당 수수료로 공식 배출 절차를 진행합니다.",
        ],
        "required_documents": [],
        "processing_time": None,
        "fee": _EXPECTED_FEE,
        "department": "세종특별자치시시설관리공단",
        "source_title": "배출항목선택",
        "source_url": _SOURCE_URL,
        "last_verified_at": "2026-07-18",
        "caution": (
            "공식 품목표의 1인용침대·2인용침대 항목을 그대로 따릅니다. "
            "매트리스 포함 가격이나 실제 규격을 단정하지 않습니다."
        ),
    }


def _chat_headers(idempotency_key: str) -> dict[str, str]:
    return {"Idempotency-Key": idempotency_key}


def run_regression(runtime: _RegressionRuntime) -> tuple[str, ...]:
    """Execute the exact HTTP workflow and return buffered, value-safe evidence."""

    with runtime as active:
        ready = _mapping_response(active.request("GET", "/ready"), 200, "READY")
        if ready != {"status": "ready"}:
            _fail("READY")

        initial_projection = active.active_projection()
        initial_ids = _projection_ids(initial_projection, "INITIAL_ACTIVE")
        if len(initial_ids) != 19 or _RESERVED_PUBLIC_ID in initial_ids:
            _fail("INITIAL_ACTIVE")

        personal_before = _persistence_counts(
            active.read_persistence_counts(),
            "PERSONAL_STORAGE",
        )
        _require_personal_lookup(
            active.request(
                "POST",
                "/api/v1/chat",
                headers=_chat_headers(_PERSONAL_IDEMPOTENCY_KEY),
                json={"question": _PERSONAL_LOOKUP_QUESTION},
            ),
            "PERSONAL_LOOKUP",
        )
        personal_after = _persistence_counts(
            active.read_persistence_counts(),
            "PERSONAL_STORAGE",
        )
        if personal_after != personal_before:
            _fail("PERSONAL_STORAGE")

        first = _require_fallback(
            active.request(
                "POST",
                "/api/v1/chat",
                headers=_chat_headers(_K1_IDEMPOTENCY_KEY),
                json={"question": _RESERVED_QUESTION},
            ),
            "INITIAL_FALLBACK",
        )
        replay = _require_fallback(
            active.request(
                "POST",
                "/api/v1/chat",
                headers=_chat_headers(_K1_IDEMPOTENCY_KEY),
                json={"question": _RESERVED_QUESTION},
            ),
            "BUSINESS_REPLAY",
        )
        if first.get("request_id") == replay.get("request_id") or _business_payload(
            first, "BUSINESS_REPLAY"
        ) != _business_payload(replay, "BUSINESS_REPLAY"):
            _fail("BUSINESS_REPLAY")

        failed_list = _mapping_response(
            active.request(
                "GET",
                "/api/v1/admin/failed-questions"
                "?reason=INSUFFICIENT_GROUNDING&status=NEW",
                headers=dict(_OPERATOR_HEADERS),
            ),
            200,
            "FAILED_NEW",
        )
        items = failed_list.get("items")
        if failed_list.get("total") != 1 or type(items) is not list or len(items) != 1:
            _fail("FAILED_NEW")
        failed_item = items[0]
        if (
            type(failed_item) is not dict
            or failed_item.get("status") != "NEW"
            or failed_item.get("fallback_reason") != "INSUFFICIENT_GROUNDING"
            or failed_item.get("candidate_eligible") is not True
        ):
            _fail("FAILED_NEW")
        failed_question_id = _required_uuid(failed_item.get("id"), "FAILED_NEW")

        confirmed = _mapping_response(
            active.request(
                "PATCH",
                f"/api/v1/admin/failed-questions/{failed_question_id}/reason",
                headers=dict(_OPERATOR_HEADERS),
                json={"reason": "INSUFFICIENT_GROUNDING"},
            ),
            200,
            "REASON_CONFIRMED",
        )
        if (
            confirmed.get("id") != failed_question_id
            or confirmed.get("status") != "REASON_CONFIRMED"
        ):
            _fail("REASON_CONFIRMED")

        candidate_payload = _candidate_payload(failed_question_id)
        if "public_id" in candidate_payload:
            _fail("CANDIDATE_CREATED")
        created = _mapping_response(
            active.request(
                "POST",
                "/api/v1/admin/kb-candidates",
                headers=dict(_OPERATOR_HEADERS),
                json=candidate_payload,
            ),
            201,
            "CANDIDATE_CREATED",
        )
        candidate_id = _required_uuid(created.get("id"), "CANDIDATE_CREATED")
        if created.get("status") != "DRAFTED":
            _fail("CANDIDATE_CREATED")

        submitted = _mapping_response(
            active.request(
                "POST",
                f"/api/v1/admin/kb-candidates/{candidate_id}/submit",
                headers=dict(_OPERATOR_HEADERS),
            ),
            200,
            "CANDIDATE_SUBMITTED",
        )
        if (
            submitted.get("id") != candidate_id
            or submitted.get("status") != "PENDING_APPROVAL"
        ):
            _fail("CANDIDATE_SUBMITTED")

        blocked = _mapping_response(
            active.request(
                "PATCH",
                f"/api/v1/admin/kb-candidates/{candidate_id}/review",
                headers=dict(_FAKE_APPROVER_HEADERS),
                json={"decision": "APPROVED", "review_comment": "공식 출처 확인"},
            ),
            403,
            "SELF_APPROVAL_BLOCKED",
        )
        blocked_error = blocked.get("error")
        if (
            type(blocked_error) is not dict
            or blocked_error.get("code") != "ADMIN_FORBIDDEN"
        ):
            _fail("SELF_APPROVAL_BLOCKED")

        approved = _mapping_response(
            active.request(
                "PATCH",
                f"/api/v1/admin/kb-candidates/{candidate_id}/review",
                headers=dict(_PM_APPROVER_HEADERS),
                json={
                    "decision": "APPROVED",
                    "review_comment": "공식 품목표 정본 확인",
                },
            ),
            200,
            "CANDIDATE_APPROVED",
        )
        if approved.get("id") != candidate_id or approved.get("status") != "APPROVED":
            _fail("CANDIDATE_APPROVED")

        _require_success(
            active.request(
                "POST",
                "/api/v1/chat",
                headers=_chat_headers(_K2_IDEMPOTENCY_KEY),
                json={"question": _RESERVED_QUESTION},
            ),
            "IMPROVED_REQUERY",
        )
        old_replay = _require_fallback(
            active.request(
                "POST",
                "/api/v1/chat",
                headers=_chat_headers(_K1_IDEMPOTENCY_KEY),
                json={"question": _RESERVED_QUESTION},
            ),
            "OLD_REPLAY",
        )
        if old_replay.get("request_id") in {
            first.get("request_id"),
            replay.get("request_id"),
        } or _business_payload(old_replay, "OLD_REPLAY") != _business_payload(
            first, "OLD_REPLAY"
        ):
            _fail("OLD_REPLAY")

        final_projection = active.active_projection()
        final_ids = _projection_ids(final_projection, "FINAL_ACTIVE")
        if (
            len(final_ids) != 20
            or any(
                len(final_projection[category]) != 5
                for category in _SUPPORTED_CATEGORIES
            )
            or final_ids.count(_RESERVED_PUBLIC_ID) != 1
        ):
            _fail("FINAL_ACTIVE")

    return (
        "PASS ready",
        "PASS initial-active count=19",
        "PASS personal-lookup no-storage",
        "PASS initial-fallback",
        "PASS business-replay",
        "PASS failed-new count=1",
        "PASS reason-confirmed",
        "PASS candidate-created",
        "PASS candidate-submitted",
        "PASS self-approval-blocked",
        "PASS candidate-approved",
        f"PASS improved-requery public_id={_RESERVED_PUBLIC_ID}",
        "PASS old-replay",
        "PASS final-active total=20 categories=4 count_each=5 "
        f"public_id={_RESERVED_PUBLIC_ID}",
    )


class _ActualRuntime:
    def __init__(
        self,
        application: Any,
        repository: Any,
        client_type: Any,
        intent_type: Any,
        pool_owner: _PoolOwner,
        persistence_count_reader: PersistenceCountReader | None = None,
    ) -> None:
        self._repository = repository
        self._intent_type = intent_type
        self._client = client_type(application)
        self._pool_owner = pool_owner
        self._persistence_count_reader = persistence_count_reader
        self._active_client: Any | None = None

    def __enter__(self) -> _ActualRuntime:
        try:
            self._active_client = self._client.__enter__()
        except Exception:
            self._pool_owner.close()
            raise
        return self

    def __exit__(
        self,
        exception_type: object,
        exception: object,
        traceback: object,
    ) -> None:
        try:
            self._client.__exit__(exception_type, exception, traceback)
        except Exception:
            self._pool_owner.close()
            raise
        else:
            self._pool_owner.mark_lifespan_closed()
        finally:
            self._active_client = None

    def request(
        self,
        method: str,
        path: str,
        *,
        headers: Mapping[str, str] | None = None,
        json: Mapping[str, object] | None = None,
    ) -> _Response:
        active_client = self._active_client
        if active_client is None:
            _fail("RUNTIME")
        return cast(
            _Response,
            active_client.request(method, path, headers=headers, json=json),
        )

    def active_projection(self) -> Mapping[str, tuple[str, ...]]:
        portal = getattr(self._client, "portal", None)
        if portal is None:
            _fail("RUNTIME")
        active_portal = cast(Any, portal)
        projection: dict[str, tuple[str, ...]] = {}
        for category in _SUPPORTED_CATEGORIES:
            records = active_portal.call(
                self._repository.list_active_kb,
                self._intent_type(category),
            )
            projection[category] = tuple(record.public_id for record in records)
        return projection

    def read_persistence_counts(self) -> Mapping[str, int]:
        if self._active_client is None or self._persistence_count_reader is None:
            _fail("RUNTIME")
        try:
            return self._persistence_count_reader()
        except _RegressionFailed:
            raise
        except Exception:
            raise _ConfigurationInvalid from None


def _compose_actual_runtime(
    *,
    dsn: str,
    selected_environment: Mapping[str, str],
    create_pool_fn: Callable[[str], Any],
    repository_type: Callable[[Any], Any],
    create_local_app_fn: Callable[..., Any],
    client_loader: Callable[[], Any],
    intent_type: Any,
    persistence_count_reader: PersistenceCountReader | None = None,
) -> _RegressionRuntime:
    owner: _PoolOwner | None = None
    try:
        pool = create_pool_fn(dsn)
        owner = _PoolOwner(pool)
        repository = repository_type(pool)

        def pool_factory(selected_database_url: str) -> Any:
            if selected_database_url != dsn:
                raise _ConfigurationInvalid
            return pool

        def repository_factory(selected_pool: object) -> Any:
            if selected_pool is not pool:
                raise _ConfigurationInvalid
            return repository

        application = create_local_app_fn(
            environ=selected_environment,
            env_path=_API_ENV_PATH,
            pool_factory=pool_factory,
            repository_factory=repository_factory,
        )
        client_type = client_loader()
        return _ActualRuntime(
            application,
            repository,
            client_type,
            intent_type,
            owner,
            persistence_count_reader,
        )
    except Exception:
        if owner is not None:
            try:
                owner.close()
            except Exception:
                pass
        raise _ConfigurationInvalid from None


def _build_actual_runtime(environment: Mapping[str, str]) -> _RegressionRuntime:
    """Compose the existing local app; TestClient is intentionally imported lazily."""

    secret = environment.get("CONTEXT_TOKEN_SECRET")
    admin_dsn = environment.get("SEJONG_ADMIN_DATABASE_URL")
    if type(secret) is not str or not secret:
        raise _ConfigurationInvalid
    if type(admin_dsn) is not str or not admin_dsn:
        raise _ConfigurationInvalid
    if not _API_SOURCE.is_dir() or not _API_ENV_PATH.is_file():
        raise _ConfigurationInvalid
    source_path = str(_API_SOURCE)
    if source_path not in sys.path:
        sys.path.insert(0, source_path)

    from sejong_ai_api.db.models import Intent
    from sejong_ai_api.db.pool import create_pool
    from sejong_ai_api.db.repository import PsycopgSejongRepository
    from sejong_ai_api.local import create_local_app, load_local_settings
    import psycopg

    selected_environment = {"CONTEXT_TOKEN_SECRET": secret}
    settings = load_local_settings(
        environ=selected_environment,
        env_path=_API_ENV_PATH,
    )
    if settings is None:
        raise _ConfigurationInvalid

    def load_test_client() -> Any:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            from fastapi.testclient import TestClient

        return TestClient

    def read_persistence_counts() -> Mapping[str, int]:
        try:
            with (
                psycopg.connect(admin_dsn, autocommit=True) as connection,
                connection.cursor() as cursor,
            ):
                cursor.execute(_PERSISTENCE_COUNT_SQL)
                row = cursor.fetchone()
        except psycopg.Error:
            raise _ConfigurationInvalid from None
        if (
            type(row) is not tuple
            or len(row) != 2
            or type(row[0]) is not int
            or type(row[1]) is not int
        ):
            raise _ConfigurationInvalid
        return {
            "interaction_events": row[0],
            "failed_questions": row[1],
        }

    return _compose_actual_runtime(
        dsn=settings.database_url,
        selected_environment=selected_environment,
        create_pool_fn=create_pool,
        repository_type=PsycopgSejongRepository,
        create_local_app_fn=create_local_app,
        client_loader=load_test_client,
        intent_type=Intent,
        persistence_count_reader=read_persistence_counts,
    )


def _configure_event_loop_policy(platform: str) -> None:
    if platform != "win32":
        return
    policy_factory = getattr(asyncio, "WindowsSelectorEventLoopPolicy", None)
    if not callable(policy_factory):
        raise _ConfigurationInvalid
    asyncio.set_event_loop_policy(policy_factory())


def _run_with_dependencies(
    *,
    environment: Mapping[str, str],
    platform: str,
    configure_policy: PolicyConfigurer,
    runtime_factory: RuntimeFactory,
) -> tuple[str, ...]:
    configure_policy(platform)
    runtime = runtime_factory(environment)
    return run_regression(runtime)


def main(argv: Sequence[str] | None = None) -> int:
    arguments = tuple(sys.argv[1:] if argv is None else argv)
    if arguments:
        print("ACTUAL_MVP_REGRESSION_FAILED", file=sys.stderr)
        return 2
    try:
        sink = _DiscardOutput()
        with redirect_stdout(sink), redirect_stderr(sink):
            lines = _run_with_dependencies(
                environment=os.environ,
                platform=sys.platform,
                configure_policy=_configure_event_loop_policy,
                runtime_factory=_build_actual_runtime,
            )
    except Exception:
        print("ACTUAL_MVP_REGRESSION_FAILED", file=sys.stderr)
        return 1
    for line in lines:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
