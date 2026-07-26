from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from types import TracebackType
from typing import cast
from uuid import UUID, uuid4

import psycopg
import pytest
from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import AsyncConnectionPool

from sejong_ai_api.db.errors import (
    DatabaseRuleCode,
    DatabaseRuleError,
    DatabaseUnavailableError,
)
from sejong_ai_api.db.models import (
    Actor,
    AdminRole,
    AnswerStatus,
    CandidateDraft,
    DataOrigin,
    FallbackReason,
    Intent,
    InteractionWrite,
    Region,
)
from sejong_ai_api.db.pool import create_pool
from sejong_ai_api.db.repository import PsycopgSejongRepository, SejongRepository

LIST_ACTIVE_KB_SQL = "SELECT * FROM app_api.list_active_kb(%s)"
LIST_OFFICES_SQL = "SELECT * FROM app_api.list_offices(%s, %s)"
RECORD_INTERACTION_SQL = (
    "SELECT * FROM app_api.record_interaction(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
)
CONFIRM_REASON_SQL = "SELECT app_api.confirm_failed_question_reason(%s, %s, %s, %s)"
CREATE_CANDIDATE_SQL = (
    "SELECT app_api.create_kb_candidate(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, "
    "%s, %s, %s, %s, %s, %s, %s)"
)
SUBMIT_CANDIDATE_SQL = "SELECT app_api.submit_kb_candidate(%s, %s, %s)"
APPROVE_CANDIDATE_SQL = "SELECT app_api.approve_kb_candidate(%s, %s, %s, %s)"
APPROVE_CANDIDATE_WITH_PUBLIC_ID_SQL = (
    "SELECT app_api.approve_kb_candidate_with_public_id(%s, %s, %s, %s, %s)"
)
REJECT_CANDIDATE_SQL = "SELECT app_api.reject_kb_candidate(%s, %s, %s, %s)"
PURGE_SQL = "SELECT * FROM app_api.purge_expired_failed_question_text()"
LIST_ACTIVE_KB_MIGRATION = (
    Path(__file__).resolve().parents[4]
    / "supabase"
    / "migrations"
    / "20260716000500_indexes_and_read_interfaces.sql"
)


def _database_dsn(scheme: str, authority: str) -> str:
    return f"{scheme}://{authority}"


class FakePsycopgError(psycopg.Error):
    def __init__(self, sqlstate: str, sentinel: str) -> None:
        super().__init__(sentinel)
        self.sqlstate = sqlstate


class FakeCursor:
    def __init__(
        self,
        *,
        rows: list[dict[str, object]] | None = None,
        execute_error: BaseException | None = None,
    ) -> None:
        self.rows = rows or []
        self.execute_error = execute_error
        self.executions: list[tuple[str, tuple[object, ...]]] = []
        self.enter_count = 0
        self.exit_exceptions: list[type[BaseException] | None] = []

    async def __aenter__(self) -> FakeCursor:
        self.enter_count += 1
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        self.exit_exceptions.append(exc_type)
        return False

    async def execute(self, sql: str, params: tuple[object, ...] = ()) -> None:
        self.executions.append((sql, params))
        if self.execute_error is not None:
            raise self.execute_error

    async def fetchall(self) -> list[dict[str, object]]:
        return self.rows

    async def fetchone(self) -> dict[str, object] | None:
        return self.rows[0] if self.rows else None


class FakeTransaction:
    def __init__(self) -> None:
        self.enter_count = 0
        self.exit_exceptions: list[type[BaseException] | None] = []

    async def __aenter__(self) -> FakeTransaction:
        self.enter_count += 1
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        self.exit_exceptions.append(exc_type)
        return False


class FakeConnection:
    def __init__(self, cursor: FakeCursor) -> None:
        self.fake_cursor = cursor
        self.fake_transaction = FakeTransaction()
        self.row_factories: list[object] = []

    def cursor(self, *, row_factory: object) -> FakeCursor:
        self.row_factories.append(row_factory)
        return self.fake_cursor

    def transaction(self) -> FakeTransaction:
        return self.fake_transaction


class FakeConnectionContext:
    def __init__(self, connection: FakeConnection) -> None:
        self.connection = connection
        self.exit_exceptions: list[type[BaseException] | None] = []

    async def __aenter__(self) -> FakeConnection:
        return self.connection

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        self.exit_exceptions.append(exc_type)
        return False


class FakePool:
    def __init__(
        self,
        *,
        rows: list[dict[str, object]] | None = None,
        execute_error: BaseException | None = None,
    ) -> None:
        self.cursor = FakeCursor(rows=rows, execute_error=execute_error)
        self.connection_value = FakeConnection(self.cursor)
        self.connection_context = FakeConnectionContext(self.connection_value)
        self.connection_calls = 0

    def connection(self) -> FakeConnectionContext:
        self.connection_calls += 1
        return self.connection_context


def repository(pool: FakePool) -> PsycopgSejongRepository:
    typed_pool = cast(
        AsyncConnectionPool[AsyncConnection[dict[str, object]]],
        pool,
    )
    return PsycopgSejongRepository(typed_pool)


def operator() -> Actor:
    return Actor("operator-1", AdminRole.OPERATOR)


def approver() -> Actor:
    return Actor("approver-1", AdminRole.APPROVER)


def event() -> InteractionWrite:
    return InteractionWrite(
        request_id=UUID("11111111-1111-4111-8111-111111111111"),
        intent=Intent.MOVE_IN_RESIDENT_REGISTRATION,
        answer_status=AnswerStatus.SUCCESS,
        fallback_reason=None,
        used_source_ids=("KB-MOVE-01", "KB-MOVE-02"),
        response_time_ms=42,
        selected_region=Region.AREUM_DONG,
        routed_office_public_id="OFFICE-AREUM",
        is_test=False,
        masked_question=None,
    )


def draft() -> CandidateDraft:
    return CandidateDraft(
        failed_question_id=UUID("22222222-2222-4222-8222-222222222222"),
        actor=operator(),
        title="전입신고 안내",
        representative_question="전입신고는 어떻게 하나요?",
        category=Intent.MOVE_IN_RESIDENT_REGISTRATION,
        answer_summary="신고 절차를 안내합니다.",
        procedure_steps=("신청서 작성", "제출"),
        required_documents=("신분증",),
        processing_time="즉시",
        fee="무료",
        department="민원행정팀",
        source_title="공식 안내",
        source_url="https://example.invalid/official",
        last_verified_at=date(2026, 7, 17),
        caution=None,
        data_origin=DataOrigin.OFFICIAL,
    )


def kb_row() -> dict[str, object]:
    return {
        "public_id": "KB-MOVE-01",
        "category": "MOVE_IN_RESIDENT_REGISTRATION",
        "service_name": "전입신고",
        "answer_summary": "신고 절차를 안내합니다.",
        "procedure_steps": ["신청서 작성", "제출"],
        "required_documents": ["신분증"],
        "processing_time": None,
        "fee": None,
        "department": "민원행정팀",
        "source_title": "공식 안내",
        "source_url": "https://example.invalid/official",
        "last_verified_at": date(2026, 7, 17),
        "caution": None,
        "question_examples": ["전입신고는 어떻게 하나요?"],
    }


def office_row() -> dict[str, object]:
    return {
        "public_id": "OFFICE-AREUM",
        "region": "아름동",
        "office_name": "아름동 행정복지센터",
        "address": "세종시 보람로 1",
        "phone": "044-200-0001",
        "opening_hours": None,
        "map_url": None,
        "department_label": "민원행정팀",
        "source_title": "공식 기관 안내",
        "source_url": "https://example.invalid/office",
        "last_verified_at": date(2026, 7, 17),
    }


def assert_one_transaction(pool: FakePool, expected_exception: type[BaseException] | None) -> None:
    transaction = pool.connection_value.fake_transaction
    assert transaction.enter_count == 1
    assert transaction.exit_exceptions == [expected_exception]


def test_repository_satisfies_the_exact_nine_method_protocol() -> None:
    concrete: SejongRepository = repository(FakePool())

    assert isinstance(concrete, PsycopgSejongRepository)


def test_executable_list_active_kb_authority_pins_active_official_projection() -> None:
    migration = LIST_ACTIVE_KB_MIGRATION.read_text(encoding="utf-8")
    bodies = re.findall(
        r"AS \$list_active_kb\$\r?\n(?P<body>.*?)\r?\n\$list_active_kb\$;",
        migration,
        flags=re.DOTALL,
    )

    assert len(bodies) == 1
    body = bodies[0]
    projection = re.search(
        r"RETURN QUERY\s+SELECT(?P<projection>.*?)"
        r"\n  FROM app_private\.kb_documents AS kb",
        body,
        flags=re.DOTALL,
    )
    assert projection is not None
    for trusted_column in (
        "kb.public_id",
        "kb.category::text",
        "kb.service_name",
        "kb.answer_summary",
        "kb.procedure_steps",
        "kb.required_documents",
        "kb.processing_time",
        "kb.fee",
        "kb.department",
        "kb.source_title",
        "kb.source_url",
        "kb.last_verified_at",
        "kb.caution",
        "questions.question_example",
    ):
        assert trusted_column in projection.group("projection")

    predicate = re.search(
        r"\n  FROM app_private\.kb_documents AS kb\r?\n"
        r"  WHERE (?P<predicate>.*?)\r?\n"
        r"  ORDER BY kb\.public_id COLLATE pg_catalog\.\"C\" ASC;",
        body,
        flags=re.DOTALL,
    )
    assert predicate is not None
    assert tuple(line.strip() for line in predicate.group("predicate").splitlines()) == (
        "kb.category = p_intent::app_private.intent_code",
        "AND kb.status = 'ACTIVE'",
        "AND kb.data_origin = 'OFFICIAL'",
    )
    assert "app_private.kb_candidates" not in body
    assert "'CANDIDATE'" not in predicate.group("predicate")
    assert "'MOCK'" not in predicate.group("predicate")


def test_create_pool_is_explicit_lazy_and_preserves_nonblank_dsn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from sejong_ai_api.db import pool as pool_module

    sentinel_pool = object()
    calls: list[dict[str, object]] = []

    def fake_pool(**kwargs: object) -> object:
        calls.append(kwargs)
        return sentinel_pool

    monkeypatch.setattr(pool_module, "AsyncConnectionPool", fake_pool)
    dsn = "  postgresql://localhost/synthetic-db  "

    created = create_pool(dsn)

    assert created is sentinel_pool
    assert calls == [
        {
            "conninfo": dsn,
            "min_size": 1,
            "max_size": 4,
            "open": False,
            "kwargs": {"autocommit": False, "hostaddr": "127.0.0.1"},
        }
    ]


@pytest.mark.parametrize("database_url", ["", " ", "\t\r\n"])
def test_create_pool_rejects_blank_dsn_before_pool_construction(
    database_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    from sejong_ai_api.db import pool as pool_module

    calls = 0

    def fake_pool(**kwargs: object) -> object:
        nonlocal calls
        calls += 1
        return object()

    monkeypatch.setattr(pool_module, "AsyncConnectionPool", fake_pool)

    with pytest.raises(ValueError, match="^DATABASE_URL_REQUIRED$"):
        create_pool(database_url)
    assert calls == 0


@pytest.mark.parametrize(
    "variable",
    ["PGHOSTADDR", "PGSERVICE", "PGSERVICEFILE", "PGOPTIONS", "pgpassword"],
)
def test_create_pool_rejects_ambient_libpq_environment_before_construction(
    variable: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from sejong_ai_api.db import pool as pool_module

    calls = 0

    def fake_pool(**kwargs: object) -> object:
        nonlocal calls
        calls += 1
        return object()

    monkeypatch.setattr(pool_module, "AsyncConnectionPool", fake_pool)
    monkeypatch.setenv(variable, "synthetic-ambient-value")

    with pytest.raises(ValueError, match="^AMBIENT_LIBPQ_ENVIRONMENT_INVALID$"):
        create_pool(
            _database_dsn("postgresql", "sejong_local_login:secret@127.0.0.1:54322/postgres")
        )
    assert calls == 0


@pytest.mark.asyncio
async def test_reads_use_exact_sql_named_rows_and_return_immutable_typed_tuples() -> None:
    kb_pool = FakePool(rows=[kb_row()])
    office_pool = FakePool(rows=[office_row()])

    knowledge_records = await repository(kb_pool).list_active_kb(
        Intent.MOVE_IN_RESIDENT_REGISTRATION
    )
    office_records = await repository(office_pool).list_offices(
        Region.AREUM_DONG, Intent.MOVE_IN_RESIDENT_REGISTRATION
    )

    assert kb_pool.cursor.executions == [(LIST_ACTIVE_KB_SQL, ("MOVE_IN_RESIDENT_REGISTRATION",))]
    assert office_pool.cursor.executions == [
        (LIST_OFFICES_SQL, ("아름동", "MOVE_IN_RESIDENT_REGISTRATION"))
    ]
    assert kb_pool.connection_value.row_factories == [dict_row]
    assert office_pool.connection_value.row_factories == [dict_row]
    assert type(knowledge_records) is tuple
    assert type(office_records) is tuple
    assert knowledge_records[0].procedure_steps == ("신청서 작성", "제출")
    assert knowledge_records[0].question_examples == ("전입신고는 어떻게 하나요?",)
    assert office_records[0].region is Region.AREUM_DONG
    assert kb_pool.connection_value.fake_transaction.enter_count == 0
    assert office_pool.connection_value.fake_transaction.enter_count == 0


@pytest.mark.asyncio
async def test_reads_return_empty_tuples_for_zero_rows() -> None:
    kb_pool = FakePool()
    office_pool = FakePool()

    assert await repository(kb_pool).list_active_kb(Intent.BULKY_WASTE) == ()
    assert await repository(office_pool).list_offices(Region.DODAM_DONG, Intent.BULKY_WASTE) == ()


@pytest.mark.asyncio
async def test_record_interaction_uses_exact_native_parameters_and_transaction() -> None:
    interaction_id = uuid4()
    pool = FakePool(rows=[{"interaction_id": interaction_id, "failed_question_id": None}])
    write = event()

    result = await repository(pool).record_interaction(write)

    assert result.interaction_id == interaction_id
    assert result.failed_question_id is None
    assert pool.cursor.executions == [
        (
            RECORD_INTERACTION_SQL,
            (
                write.request_id,
                "MOVE_IN_RESIDENT_REGISTRATION",
                "SUCCESS",
                None,
                ["KB-MOVE-01", "KB-MOVE-02"],
                42,
                "아름동",
                "OFFICE-AREUM",
                False,
                None,
            ),
        )
    ]
    assert pool.cursor.executions[0][1][4] is not write.used_source_ids
    assert_one_transaction(pool, None)


@pytest.mark.asyncio
async def test_confirmation_submission_and_reviews_use_exact_sql_parameters() -> None:
    failure_id = UUID("33333333-3333-4333-8333-333333333333")
    candidate_id = UUID("44444444-4444-4444-8444-444444444444")

    confirm_pool = FakePool()
    await repository(confirm_pool).confirm_failed_question_reason(
        failure_id, operator(), FallbackReason.INSUFFICIENT_GROUNDING
    )
    assert confirm_pool.cursor.executions == [
        (
            CONFIRM_REASON_SQL,
            (failure_id, "operator-1", "OPERATOR", "INSUFFICIENT_GROUNDING"),
        )
    ]

    submit_pool = FakePool()
    await repository(submit_pool).submit_kb_candidate(candidate_id, operator())
    assert submit_pool.cursor.executions == [
        (SUBMIT_CANDIDATE_SQL, (candidate_id, "operator-1", "OPERATOR"))
    ]

    approve_pool = FakePool(rows=[{"approve_kb_candidate": "KB-ACTIVE-01"}])
    assert (
        await repository(approve_pool).approve_kb_candidate(
            candidate_id, approver(), "공식 출처 확인 완료"
        )
        == "KB-ACTIVE-01"
    )
    assert approve_pool.cursor.executions == [
        (
            APPROVE_CANDIDATE_SQL,
            (candidate_id, "approver-1", "APPROVER", "공식 출처 확인 완료"),
        )
    ]

    reject_pool = FakePool()
    await repository(reject_pool).reject_kb_candidate(candidate_id, approver(), "출처 보완 필요")
    assert reject_pool.cursor.executions == [
        (
            REJECT_CANDIDATE_SQL,
            (candidate_id, "approver-1", "APPROVER", "출처 보완 필요"),
        )
    ]

    for pool in (confirm_pool, submit_pool, approve_pool, reject_pool):
        assert_one_transaction(pool, None)


@pytest.mark.asyncio
async def test_reserved_approval_uses_fixed_explicit_public_id_sql_and_transaction() -> None:
    candidate_id = UUID("44444444-4444-4444-8444-444444444444")
    pool = FakePool(rows=[{"approve_kb_candidate_with_public_id": "KB-WASTE-03"}])

    result = await repository(pool).approve_kb_candidate_with_public_id(
        candidate_id,
        approver(),
        "공식 품목표와 canonical 값을 확인했습니다.",
        "KB-WASTE-03",
    )

    assert result == "KB-WASTE-03"
    assert pool.cursor.executions == [
        (
            APPROVE_CANDIDATE_WITH_PUBLIC_ID_SQL,
            (
                candidate_id,
                "approver-1",
                "APPROVER",
                "공식 품목표와 canonical 값을 확인했습니다.",
                "KB-WASTE-03",
            ),
        )
    ]
    assert_one_transaction(pool, None)


@pytest.mark.asyncio
async def test_reserved_approval_rejects_non_exact_server_public_id_before_pool_access() -> None:
    class CallerDefinedPublicId(str):
        pass

    pool = FakePool()

    with pytest.raises(ValueError, match="^PUBLIC_ID_INVALID$"):
        await repository(pool).approve_kb_candidate_with_public_id(
            uuid4(),
            approver(),
            "공식 품목표를 확인했습니다.",
            CallerDefinedPublicId("KB-WASTE-03"),
        )

    assert pool.connection_calls == 0


@pytest.mark.asyncio
async def test_create_candidate_uses_exact_sql_and_jsonb_list_adapters() -> None:
    candidate_id = uuid4()
    pool = FakePool(rows=[{"create_kb_candidate": candidate_id}])
    value = draft()

    result = await repository(pool).create_kb_candidate(value)

    assert result == candidate_id
    assert len(pool.cursor.executions) == 1
    sql, params = pool.cursor.executions[0]
    assert sql == CREATE_CANDIDATE_SQL
    assert params[:7] == (
        value.failed_question_id,
        "operator-1",
        "OPERATOR",
        "전입신고 안내",
        "전입신고는 어떻게 하나요?",
        "MOVE_IN_RESIDENT_REGISTRATION",
        "신고 절차를 안내합니다.",
    )
    assert type(params[7]) is Jsonb
    assert params[7].obj == ["신청서 작성", "제출"]
    assert type(params[8]) is Jsonb
    assert params[8].obj == ["신분증"]
    assert params[9:] == (
        "즉시",
        "무료",
        "민원행정팀",
        "공식 안내",
        "https://example.invalid/official",
        date(2026, 7, 17),
        None,
        "OFFICIAL",
    )
    assert_one_transaction(pool, None)


@pytest.mark.asyncio
async def test_purge_uses_exact_sql_and_maps_uuid_array_to_tuple() -> None:
    purged_ids = (uuid4(), uuid4())
    pool = FakePool(rows=[{"purged_count": 2, "purged_ids": list(purged_ids)}])

    result = await repository(pool).purge_expired_failed_question_text()

    assert result.purged_count == 2
    assert result.purged_ids == purged_ids
    assert pool.cursor.executions == [(PURGE_SQL, ())]
    assert_one_transaction(pool, None)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("operation", "expected_message"),
    [
        ("list_kb", "CATEGORY_INVALID"),
        ("list_offices", "CATEGORY_INVALID"),
        ("confirm", "ACTOR_ROLE_FORBIDDEN"),
        ("submit", "ACTOR_ROLE_FORBIDDEN"),
        ("approve", "ACTOR_ROLE_FORBIDDEN"),
        ("reject", "ACTOR_ROLE_FORBIDDEN"),
        ("approve_comment", "REVIEW_COMMENT_INVALID"),
        ("reject_comment", "REVIEW_COMMENT_INVALID"),
    ],
)
async def test_repository_validates_roles_filters_and_comments_before_pool_access(
    operation: str, expected_message: str
) -> None:
    pool = FakePool()
    adapter = repository(pool)
    candidate_id = uuid4()

    with pytest.raises(ValueError, match=f"^{expected_message}$"):
        if operation == "list_kb":
            await adapter.list_active_kb(Intent.OUT_OF_SCOPE)
        elif operation == "list_offices":
            await adapter.list_offices(Region.AREUM_DONG, Intent.UNKNOWN)
        elif operation == "confirm":
            await adapter.confirm_failed_question_reason(
                uuid4(), approver(), FallbackReason.PERSONAL_LOOKUP
            )
        elif operation == "submit":
            await adapter.submit_kb_candidate(candidate_id, approver())
        elif operation == "approve":
            await adapter.approve_kb_candidate(candidate_id, operator(), "valid")
        elif operation == "reject":
            await adapter.reject_kb_candidate(candidate_id, operator(), "valid")
        elif operation == "approve_comment":
            await adapter.approve_kb_candidate(candidate_id, approver(), " padded")
        else:
            await adapter.reject_kb_candidate(candidate_id, approver(), "x" * 1001)

    assert pool.connection_calls == 0


@pytest.mark.asyncio
async def test_psycopg_sqlstate_maps_safely_and_transaction_rolls_back(
    capsys: pytest.CaptureFixture[str],
) -> None:
    sentinel = "synthetic-private-question-answer-dsn"
    pool = FakePool(execute_error=FakePsycopgError("P1002", sentinel))

    with pytest.raises(DatabaseRuleError) as captured:
        await repository(pool).approve_kb_candidate(uuid4(), approver(), "valid")

    assert captured.value.code is DatabaseRuleCode.SELF_APPROVAL
    assert sentinel not in str(captured.value)
    assert_one_transaction(pool, FakePsycopgError)
    output = capsys.readouterr()
    assert sentinel not in output.out
    assert sentinel not in output.err


@pytest.mark.asyncio
async def test_native_database_error_maps_to_unavailable_without_sentinel_leak() -> None:
    sentinel = "synthetic-native-private-detail"
    pool = FakePool(execute_error=FakePsycopgError("23505", sentinel))

    with pytest.raises(DatabaseUnavailableError, match="^DATABASE_OPERATION_FAILED$") as captured:
        await repository(pool).record_interaction(event())

    assert sentinel not in str(captured.value)
    assert_one_transaction(pool, FakePsycopgError)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("operation", "rows"),
    [
        ("record", []),
        ("record", [{"interaction_id": "not-a-uuid", "private": "sentinel"}]),
        ("create", []),
        ("approve", [{"approve_kb_candidate": 1, "private": "sentinel"}]),
        ("purge", [{"purged_count": 1, "purged_ids": [], "private": "sentinel"}]),
        ("read", [{"public_id": "sentinel"}]),
    ],
)
async def test_missing_or_malformed_rows_fail_with_only_the_safe_unavailable_message(
    operation: str, rows: list[dict[str, object]]
) -> None:
    pool = FakePool(rows=rows)
    adapter = repository(pool)

    with pytest.raises(DatabaseUnavailableError) as captured:
        if operation == "record":
            await adapter.record_interaction(event())
        elif operation == "create":
            await adapter.create_kb_candidate(draft())
        elif operation == "approve":
            await adapter.approve_kb_candidate(uuid4(), approver(), "valid")
        elif operation == "purge":
            await adapter.purge_expired_failed_question_text()
        else:
            await adapter.list_active_kb(Intent.MOVE_IN_RESIDENT_REGISTRATION)

    assert str(captured.value) == "DATABASE_OPERATION_FAILED"
    assert "sentinel" not in str(captured.value)


@pytest.mark.asyncio
async def test_active_kb_row_with_no_question_examples_fails_safely() -> None:
    row = kb_row()
    row["question_examples"] = []

    with pytest.raises(DatabaseUnavailableError, match="^DATABASE_OPERATION_FAILED$"):
        await repository(FakePool(rows=[row])).list_active_kb(Intent.MOVE_IN_RESIDENT_REGISTRATION)


@pytest.mark.asyncio
async def test_non_psycopg_programming_error_is_not_misclassified() -> None:
    pool = FakePool(execute_error=RuntimeError("synthetic-programming-error"))

    with pytest.raises(RuntimeError, match="^synthetic-programming-error$"):
        await repository(pool).record_interaction(event())
