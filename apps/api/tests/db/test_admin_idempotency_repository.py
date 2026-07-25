from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import cast
from uuid import UUID

import pytest
from psycopg.types.json import Jsonb

from sejong_ai_api.db.errors import DatabaseUnavailableError
from sejong_ai_api.db.repository import PsycopgSejongRepository

from .test_repository import FakePool, assert_one_transaction, event, repository

FAILED_ID = UUID("10000000-0000-4000-8000-000000000001")
CANDIDATE_ID = UUID("20000000-0000-4000-8000-000000000001")
ACTIVATED_ID = UUID("30000000-0000-4000-8000-000000000001")
IDEMPOTENCY_KEY = UUID("40000000-0000-4000-8000-000000000001")
CLAIM_TOKEN = UUID("50000000-0000-4000-8000-000000000001")
NOW = datetime(2026, 7, 22, 3, 0, tzinfo=UTC)
DIGEST = "a" * 64


def safe_fallback_payload() -> dict[str, object]:
    return {
        "intent": "UNKNOWN",
        "confidence": None,
        "summary": None,
        "procedure_steps": [],
        "required_documents": [],
        "processing_time": None,
        "fee": None,
        "department": None,
        "followup_options": [],
        "fallback": {
            "reason": "PERSONAL_LOOKUP",
            "title": "개인 정보 조회는 할 수 없어요",
            "message": "이 서비스는 개인별 신청·처리·고지 상태를 조회하지 않아요.",
            "next_actions": ["정부24 또는 해당 기관의 본인 인증 조회 경로를 이용해 주세요."],
            "candidate_eligible": False,
            "office": None,
        },
        "answer_status": "FALLBACK",
        "sources": [],
    }


def failed_row() -> dict[str, object]:
    return {
        "id": FAILED_ID,
        "masked_question": "침대 프레임 수수료를 알려 주세요.",
        "intent": "BULKY_WASTE",
        "fallback_reason": "INSUFFICIENT_GROUNDING",
        "candidate_eligible": True,
        "status": "NEW",
        "created_at": NOW,
        "text_expires_at": NOW + timedelta(days=30),
        "text_purged_at": None,
    }


def candidate_row() -> dict[str, object]:
    return {
        "id": CANDIDATE_ID,
        "failed_question_id": FAILED_ID,
        "title": "침대 프레임 배출 안내",
        "representative_question": "침대 프레임은 어떻게 버리나요?",
        "data_origin": "OFFICIAL",
        "category": "BULKY_WASTE",
        "answer_summary": "신청 후 배출번호를 붙여 배출합니다.",
        "procedure_steps": ["신청합니다.", "배출합니다."],
        "required_documents": [],
        "processing_time": None,
        "fee": "10,000원",
        "department": "자원순환과",
        "source_title": "세종특별자치시 대형폐기물 배출 안내",
        "source_url": "https://www.sejong.go.kr/example",
        "last_verified_at": date(2026, 7, 19),
        "caution": None,
        "status": "APPROVED",
        "created_by": "OPERATOR-LOCAL-001",
        "reviewed_by": "PM-LOCAL-001",
        "review_comment": "공식 출처를 확인했습니다.",
        "approved_at": NOW,
        "activated_kb_id": ACTIVATED_ID,
        "created_at": NOW,
        "updated_at": NOW,
    }


@pytest.mark.asyncio
async def test_admin_reads_use_exact_capabilities_and_typed_contract_rows() -> None:
    failure_pool = FakePool(rows=[failed_row()])
    candidate_pool = FakePool(rows=[candidate_row()])

    failures = await repository(failure_pool).list_failed_questions(
        reason="INSUFFICIENT_GROUNDING", status="NEW"
    )
    candidates = await repository(candidate_pool).list_kb_candidates()

    assert failure_pool.cursor.executions == [
        (
            "SELECT * FROM app_api.list_failed_questions(%s, %s)",
            ("INSUFFICIENT_GROUNDING", "NEW"),
        )
    ]
    assert candidate_pool.cursor.executions == [("SELECT * FROM app_api.list_kb_candidates()", ())]
    assert failures[0].id == FAILED_ID
    assert failures[0].masked_question == "침대 프레임 수수료를 알려 주세요."
    assert candidates[0].id == CANDIDATE_ID
    assert str(candidates[0].source_url) == "https://www.sejong.go.kr/example"
    assert failure_pool.connection_value.fake_transaction.enter_count == 0
    assert candidate_pool.connection_value.fake_transaction.enter_count == 0


@pytest.mark.asyncio
async def test_admin_gets_return_one_typed_row_or_none() -> None:
    failure_pool = FakePool(rows=[failed_row()])
    candidate_pool = FakePool(rows=[candidate_row()])
    missing_pool = FakePool()

    failure = await repository(failure_pool).get_failed_question(FAILED_ID)
    candidate = await repository(candidate_pool).get_kb_candidate(CANDIDATE_ID)
    missing = await repository(missing_pool).get_failed_question(FAILED_ID)

    assert failure is not None and failure.id == FAILED_ID
    assert candidate is not None and candidate.activated_kb_id == ACTIVATED_ID
    assert missing is None
    assert failure_pool.cursor.executions == [
        ("SELECT * FROM app_api.get_failed_question(%s)", (FAILED_ID,))
    ]
    assert candidate_pool.cursor.executions == [
        ("SELECT * FROM app_api.get_kb_candidate(%s)", (CANDIDATE_ID,))
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("reason", "status"),
    [
        ("OUT_OF_SCOPE", None),
        (None, "APPROVED"),
        (" padded", "NEW"),
    ],
)
async def test_admin_read_filters_fail_before_pool_access(
    reason: str | None, status: str | None
) -> None:
    pool = FakePool()

    with pytest.raises(ValueError, match="^ADMIN_READ_FILTER_INVALID$"):
        await repository(pool).list_failed_questions(reason=reason, status=status)

    assert pool.connection_calls == 0


@pytest.mark.asyncio
async def test_malformed_admin_rows_fail_with_value_free_unavailable_error() -> None:
    pool = FakePool(rows=[{"id": FAILED_ID, "masked_question": "private-sentinel"}])

    with pytest.raises(DatabaseUnavailableError, match="^DATABASE_OPERATION_FAILED$") as caught:
        await repository(pool).list_failed_questions(reason=None, status=None)

    assert "private-sentinel" not in str(caught.value)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("disposition", "response_json"),
    [
        ("ACQUIRED", None),
        ("IN_PROGRESS", None),
        ("CONFLICT", None),
        ("COMPLETED", safe_fallback_payload()),
    ],
)
async def test_idempotency_claim_maps_all_atomic_dispositions(
    disposition: str, response_json: dict[str, object] | None
) -> None:
    pool = FakePool(rows=[{"disposition": disposition, "response_json": response_json}])

    result = await repository(pool).claim_chat_idempotency(
        idempotency_key=IDEMPOTENCY_KEY,
        request_fingerprint=DIGEST,
        claim_token=CLAIM_TOKEN,
    )

    assert result.status.value == disposition
    assert result.response_payload == response_json
    assert pool.cursor.executions == [
        (
            "SELECT * FROM app_api.claim_chat_idempotency(%s, %s, %s)",
            (IDEMPOTENCY_KEY, DIGEST, CLAIM_TOKEN),
        )
    ]
    assert_one_transaction(pool, None)


@pytest.mark.asyncio
async def test_idempotency_complete_abandon_and_purge_use_exact_capabilities() -> None:
    response = safe_fallback_payload()
    complete_pool = FakePool()
    abandon_pool = FakePool()
    purge_pool = FakePool(rows=[{"purged_count": 1, "purged_ids": [IDEMPOTENCY_KEY]}])

    await repository(complete_pool).complete_chat_idempotency(
        idempotency_key=IDEMPOTENCY_KEY,
        request_fingerprint=DIGEST,
        claim_token=CLAIM_TOKEN,
        response_payload=response,
    )
    await repository(abandon_pool).abandon_chat_idempotency(
        idempotency_key=IDEMPOTENCY_KEY,
        request_fingerprint=DIGEST,
        claim_token=CLAIM_TOKEN,
    )
    purged = await repository(purge_pool).purge_expired_chat_idempotency()

    complete_sql, complete_parameters = complete_pool.cursor.executions[0]
    assert complete_sql == "SELECT app_api.complete_chat_idempotency(%s, %s, %s, %s)"
    assert complete_parameters[:3] == (IDEMPOTENCY_KEY, DIGEST, CLAIM_TOKEN)
    assert type(complete_parameters[3]) is Jsonb
    assert complete_parameters[3].obj == response
    assert abandon_pool.cursor.executions == [
        (
            "SELECT app_api.abandon_chat_idempotency(%s, %s, %s)",
            (IDEMPOTENCY_KEY, DIGEST, CLAIM_TOKEN),
        )
    ]
    assert purge_pool.cursor.executions == [
        ("SELECT * FROM app_api.purge_expired_chat_idempotency()", ())
    ]
    assert purged.purged_count == 1
    assert purged.purged_ids == (IDEMPOTENCY_KEY,)
    for pool in (complete_pool, abandon_pool, purge_pool):
        assert_one_transaction(pool, None)


@pytest.mark.asyncio
async def test_interaction_and_idempotency_completion_share_one_transaction() -> None:
    interaction_id = UUID("60000000-0000-4000-8000-000000000001")
    pool = FakePool(rows=[{"interaction_id": interaction_id, "failed_question_id": FAILED_ID}])
    response = safe_fallback_payload()
    interaction = event()

    await repository(pool).commit_chat_idempotency(
        idempotency_key=IDEMPOTENCY_KEY,
        request_fingerprint=DIGEST,
        claim_token=CLAIM_TOKEN,
        response_payload=response,
        interaction=interaction,
    )

    assert len(pool.cursor.executions) == 2
    record_sql, record_parameters = pool.cursor.executions[0]
    complete_sql, complete_parameters = pool.cursor.executions[1]
    assert record_sql == (
        "SELECT * FROM app_api.record_interaction(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    )
    assert record_parameters[0] == interaction.request_id
    assert complete_sql == "SELECT app_api.complete_chat_idempotency(%s, %s, %s, %s)"
    assert complete_parameters[:3] == (IDEMPOTENCY_KEY, DIGEST, CLAIM_TOKEN)
    assert type(complete_parameters[3]) is Jsonb
    assert complete_parameters[3].obj == response
    assert_one_transaction(pool, None)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("operation", "digest", "response"),
    [
        ("claim", "A" * 64, None),
        ("claim", "a" * 63, None),
        ("complete", "not-a-digest", {"answer_status": "SUCCESS"}),
        ("complete", DIGEST, {"question": "must-not-persist"}),
        ("complete", DIGEST, {"context_token": "must-not-persist"}),
        ("complete", DIGEST, {"nested": {"correlation_id": "must-not-persist"}}),
        ("complete", DIGEST, {"nested": {"provider_response": "must-not-persist"}}),
        ("complete", DIGEST, {"nested": {"provider_error": "must-not-persist"}}),
        ("complete", DIGEST, {"nested": {"draft": "must-not-persist"}}),
    ],
)
async def test_idempotency_rejects_invalid_digest_and_unsafe_response_before_db(
    operation: str, digest: str, response: dict[str, object] | None
) -> None:
    pool = FakePool()
    adapter: PsycopgSejongRepository = repository(pool)

    with pytest.raises(
        ValueError, match="^(IDEMPOTENCY_DIGEST_INVALID|IDEMPOTENCY_RESPONSE_UNSAFE)$"
    ):
        if operation == "claim":
            await adapter.claim_chat_idempotency(
                idempotency_key=IDEMPOTENCY_KEY,
                request_fingerprint=digest,
                claim_token=CLAIM_TOKEN,
            )
        else:
            assert response is not None
            await adapter.complete_chat_idempotency(
                idempotency_key=IDEMPOTENCY_KEY,
                request_fingerprint=digest,
                claim_token=CLAIM_TOKEN,
                response_payload=response,
            )

    assert pool.connection_calls == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["complete", "commit"])
@pytest.mark.parametrize(
    "credential_key",
    [
        "access_token",
        "Api_Key",
        "api_secret",
        "Authorization",
        "bearer_token",
        "client_secret",
        "LLM_API_KEY",
        "provider_api_key",
        "provider_secret",
        "secret",
        "secret_access_key",
    ],
)
async def test_idempotency_writes_reject_nested_provider_credential_keys_before_db(
    operation: str,
    credential_key: str,
) -> None:
    pool = FakePool()
    adapter: PsycopgSejongRepository = repository(pool)
    response = safe_fallback_payload()
    fallback = cast(dict[str, object], response["fallback"])
    fallback["office"] = {
        "id": "OFFICE-TEST-01",
        "region": "아름동",
        "office_name": "아름동 행정복지센터",
        "address": "세종특별자치시 시연용 주소",
        "phone": "044-000-0000",
        "opening_hours": "평일 09:00~18:00",
        "map_url": None,
        "source_title": "승인된 기관 출처",
        "source_url": "https://example.invalid/official/office",
        "last_verified_at": "2026-07-20",
        credential_key: "provider-credential-must-not-persist",
    }

    with pytest.raises(ValueError, match="^IDEMPOTENCY_RESPONSE_UNSAFE$"):
        if operation == "complete":
            await adapter.complete_chat_idempotency(
                idempotency_key=IDEMPOTENCY_KEY,
                request_fingerprint=DIGEST,
                claim_token=CLAIM_TOKEN,
                response_payload=response,
            )
        else:
            await adapter.commit_chat_idempotency(
                idempotency_key=IDEMPOTENCY_KEY,
                request_fingerprint=DIGEST,
                claim_token=CLAIM_TOKEN,
                response_payload=response,
                interaction=None,
            )

    assert pool.connection_calls == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["complete", "commit"])
@pytest.mark.parametrize(
    "response",
    [
        {"answer_status": "FALLBACK"},
        {"arbitrary": {"nested": "json"}},
    ],
)
async def test_idempotency_writes_reject_incomplete_or_arbitrary_json_before_db(
    operation: str,
    response: dict[str, object],
) -> None:
    pool = FakePool()
    adapter: PsycopgSejongRepository = repository(pool)

    with pytest.raises(ValueError, match="^IDEMPOTENCY_RESPONSE_UNSAFE$"):
        if operation == "complete":
            await adapter.complete_chat_idempotency(
                idempotency_key=IDEMPOTENCY_KEY,
                request_fingerprint=DIGEST,
                claim_token=CLAIM_TOKEN,
                response_payload=response,
            )
        else:
            await adapter.commit_chat_idempotency(
                idempotency_key=IDEMPOTENCY_KEY,
                request_fingerprint=DIGEST,
                claim_token=CLAIM_TOKEN,
                response_payload=response,
                interaction=None,
            )

    assert pool.connection_calls == 0
