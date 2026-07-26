from __future__ import annotations

from collections.abc import Callable
from dataclasses import FrozenInstanceError
from datetime import date, datetime
from uuid import UUID, uuid4

import pytest

from sejong_ai_api.db.models import (
    Actor,
    AdminRole,
    AnswerStatus,
    CandidateDraft,
    DataOrigin,
    FailureReasonConfirmation,
    FallbackReason,
    Intent,
    InteractionWrite,
    InteractionWriteResult,
    KnowledgeRecord,
    OfficeRecord,
    PurgeResult,
    Region,
)

SUPPORTED_INTENTS = (
    Intent.MOVE_IN_RESIDENT_REGISTRATION,
    Intent.CERTIFICATE_ISSUANCE,
    Intent.BULKY_WASTE,
    Intent.LOCAL_TAX_GENERAL,
)


def operator() -> Actor:
    return Actor("operator-1", AdminRole.OPERATOR)


def approver() -> Actor:
    return Actor("approver-1", AdminRole.APPROVER)


def interaction(**overrides: object) -> InteractionWrite:
    values: dict[str, object] = {
        "request_id": uuid4(),
        "intent": Intent.MOVE_IN_RESIDENT_REGISTRATION,
        "answer_status": AnswerStatus.SUCCESS,
        "fallback_reason": None,
        "used_source_ids": ("KB-MOVE-01",),
        "response_time_ms": 25,
        "selected_region": Region.AREUM_DONG,
        "routed_office_public_id": "OFFICE-AREUM",
        "is_test": False,
        "masked_question": None,
    }
    values.update(overrides)
    return InteractionWrite(**values)  # type: ignore[arg-type]


def candidate(**overrides: object) -> CandidateDraft:
    values: dict[str, object] = {
        "failed_question_id": uuid4(),
        "actor": operator(),
        "title": "전입신고 안내",
        "representative_question": "전입신고는 어떻게 하나요?",
        "category": Intent.MOVE_IN_RESIDENT_REGISTRATION,
        "answer_summary": "신고 절차를 안내합니다.",
        "procedure_steps": ("신청서 작성", "제출"),
        "required_documents": ("신분증",),
        "processing_time": "즉시",
        "fee": "무료",
        "department": "민원행정팀",
        "source_title": "공식 안내",
        "source_url": "https://example.invalid/official",
        "last_verified_at": date(2026, 7, 17),
        "caution": "개인 상황에 따라 다를 수 있습니다.",
        "data_origin": DataOrigin.OFFICIAL,
    }
    values.update(overrides)
    return CandidateDraft(**values)  # type: ignore[arg-type]


def knowledge(**overrides: object) -> KnowledgeRecord:
    values: dict[str, object] = {
        "public_id": "KB-MOVE-01",
        "category": Intent.MOVE_IN_RESIDENT_REGISTRATION,
        "service_name": "전입신고",
        "answer_summary": "신고 절차를 안내합니다.",
        "procedure_steps": ("신청서 작성",),
        "required_documents": ("신분증",),
        "processing_time": None,
        "fee": None,
        "department": "민원행정팀",
        "source_title": "공식 안내",
        "source_url": "https://example.invalid/official",
        "last_verified_at": date(2026, 7, 17),
        "caution": None,
        "question_examples": ("전입신고는 어떻게 하나요?",),
    }
    values.update(overrides)
    return KnowledgeRecord(**values)  # type: ignore[arg-type]


def office(**overrides: object) -> OfficeRecord:
    values: dict[str, object] = {
        "public_id": "OFFICE-AREUM",
        "region": Region.AREUM_DONG,
        "office_name": "아름동 행정복지센터",
        "address": "세종시 보람로 1",
        "phone": "044-200-0001",
        "opening_hours": None,
        "map_url": None,
        "department_label": None,
        "source_title": "공식 기관 안내",
        "source_url": "https://example.invalid/office",
        "last_verified_at": date(2026, 7, 17),
    }
    values.update(overrides)
    return OfficeRecord(**values)  # type: ignore[arg-type]


def test_enum_values_exactly_match_database_contract() -> None:
    assert [item.value for item in AdminRole] == ["OPERATOR", "APPROVER"]
    assert [item.value for item in Intent] == [
        "MOVE_IN_RESIDENT_REGISTRATION",
        "CERTIFICATE_ISSUANCE",
        "BULKY_WASTE",
        "LOCAL_TAX_GENERAL",
        "OUT_OF_SCOPE",
        "UNKNOWN",
    ]
    assert [item.value for item in AnswerStatus] == [
        "SUCCESS",
        "FOLLOWUP",
        "FALLBACK",
        "SYSTEM_ERROR",
    ]
    assert [item.value for item in FallbackReason] == [
        "INSUFFICIENT_GROUNDING",
        "PERSONAL_LOOKUP",
        "LEGAL_JUDGMENT",
        "CIVIC_SCOPE_GAP",
        "OUT_OF_SCOPE",
    ]
    assert [item.value for item in Region] == ["아름동", "도담동", "조치원읍"]
    assert [item.value for item in DataOrigin] == ["OFFICIAL", "MOCK"]


def test_models_are_frozen_slotted_and_keep_immutable_tuples() -> None:
    event = interaction()
    draft = candidate()
    record = knowledge()

    with pytest.raises(FrozenInstanceError):
        event.response_time_ms = 30  # type: ignore[misc]
    assert not hasattr(event, "__dict__")
    assert type(draft.procedure_steps) is tuple
    assert type(record.question_examples) is tuple


@pytest.mark.parametrize(
    "url", ["javascript:alert(1)", "data:text/html,test", "http://example.invalid"]
)
def test_db_boundary_rejects_non_https_official_urls(url: str) -> None:
    with pytest.raises(ValueError, match="SOURCE_URL_INVALID"):
        candidate(source_url=url)
    with pytest.raises(ValueError, match="SOURCE_URL_INVALID"):
        knowledge(source_url=url)
    with pytest.raises(ValueError, match="SOURCE_URL_INVALID"):
        office(source_url=url)
    with pytest.raises(ValueError, match="MAP_URL_INVALID"):
        office(map_url=url)


@pytest.mark.parametrize("actor_id", ["", " ", " operator", "operator ", 1, None])
def test_actor_requires_an_exact_trimmed_nonempty_string(actor_id: object) -> None:
    with pytest.raises(ValueError, match="^ACTOR_ID_INVALID$"):
        Actor(actor_id, AdminRole.OPERATOR)  # type: ignore[arg-type]


def test_actor_requires_an_exact_admin_role() -> None:
    with pytest.raises(ValueError, match="^ACTOR_ROLE_INVALID$"):
        Actor("operator-1", "OPERATOR")  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("answer_status", "intent", "fallback_reason", "sources", "masked_question"),
    [
        (AnswerStatus.SUCCESS, Intent.OUT_OF_SCOPE, None, ("KB-1",), None),
        (AnswerStatus.SUCCESS, SUPPORTED_INTENTS[0], None, (), None),
        (
            AnswerStatus.SUCCESS,
            SUPPORTED_INTENTS[0],
            FallbackReason.INSUFFICIENT_GROUNDING,
            ("KB-1",),
            None,
        ),
        (AnswerStatus.SUCCESS, SUPPORTED_INTENTS[0], None, ("KB-1",), "masked"),
        (AnswerStatus.FOLLOWUP, Intent.OUT_OF_SCOPE, None, (), None),
        (AnswerStatus.FOLLOWUP, SUPPORTED_INTENTS[0], None, ("KB-1",), None),
        (
            AnswerStatus.FOLLOWUP,
            SUPPORTED_INTENTS[0],
            FallbackReason.PERSONAL_LOOKUP,
            (),
            None,
        ),
        (AnswerStatus.FOLLOWUP, Intent.UNKNOWN, None, (), "masked"),
        (
            AnswerStatus.FALLBACK,
            SUPPORTED_INTENTS[0],
            FallbackReason.OUT_OF_SCOPE,
            (),
            None,
        ),
        (
            AnswerStatus.FALLBACK,
            Intent.OUT_OF_SCOPE,
            FallbackReason.OUT_OF_SCOPE,
            (),
            "must-not-persist",
        ),
        (
            AnswerStatus.FALLBACK,
            Intent.OUT_OF_SCOPE,
            FallbackReason.PERSONAL_LOOKUP,
            (),
            None,
        ),
        (AnswerStatus.FALLBACK, SUPPORTED_INTENTS[0], None, (), None),
        (
            AnswerStatus.FALLBACK,
            SUPPORTED_INTENTS[0],
            FallbackReason.LEGAL_JUDGMENT,
            ("KB-1",),
            None,
        ),
        (
            AnswerStatus.SYSTEM_ERROR,
            SUPPORTED_INTENTS[0],
            FallbackReason.PERSONAL_LOOKUP,
            (),
            None,
        ),
        (AnswerStatus.SYSTEM_ERROR, Intent.UNKNOWN, None, ("KB-1",), None),
        (AnswerStatus.SYSTEM_ERROR, Intent.UNKNOWN, None, (), "masked"),
    ],
)
def test_interaction_matrix_rejects_unsafe_combinations(
    answer_status: AnswerStatus,
    intent: Intent,
    fallback_reason: FallbackReason | None,
    sources: tuple[str, ...],
    masked_question: str | None,
) -> None:
    with pytest.raises(ValueError, match="^INTERACTION_COMBINATION_INVALID$"):
        interaction(
            answer_status=answer_status,
            intent=intent,
            fallback_reason=fallback_reason,
            used_source_ids=sources,
            masked_question=masked_question,
        )


@pytest.mark.parametrize(
    ("answer_status", "intent", "fallback_reason", "sources", "masked_question"),
    [
        (AnswerStatus.SUCCESS, SUPPORTED_INTENTS[0], None, ("KB-1",), None),
        (AnswerStatus.FOLLOWUP, SUPPORTED_INTENTS[1], None, (), None),
        (AnswerStatus.FOLLOWUP, Intent.UNKNOWN, None, (), None),
        (
            AnswerStatus.FALLBACK,
            Intent.OUT_OF_SCOPE,
            FallbackReason.OUT_OF_SCOPE,
            (),
            None,
        ),
        (
            AnswerStatus.FALLBACK,
            SUPPORTED_INTENTS[2],
            FallbackReason.INSUFFICIENT_GROUNDING,
            (),
            None,
        ),
        (
            AnswerStatus.FALLBACK,
            SUPPORTED_INTENTS[3],
            FallbackReason.PERSONAL_LOOKUP,
            (),
            "[이름] 자동차세",
        ),
        (AnswerStatus.SYSTEM_ERROR, Intent.OUT_OF_SCOPE, None, (), None),
    ],
)
def test_interaction_matrix_accepts_database_permitted_combinations(
    answer_status: AnswerStatus,
    intent: Intent,
    fallback_reason: FallbackReason | None,
    sources: tuple[str, ...],
    masked_question: str | None,
) -> None:
    event = interaction(
        answer_status=answer_status,
        intent=intent,
        fallback_reason=fallback_reason,
        used_source_ids=sources,
        masked_question=masked_question,
    )

    assert event.answer_status is answer_status


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("request_id", "not-a-uuid", "REQUEST_ID_INVALID"),
        ("intent", "UNKNOWN", "INTENT_INVALID"),
        ("answer_status", "SUCCESS", "ANSWER_STATUS_INVALID"),
        ("fallback_reason", "OUT_OF_SCOPE", "FALLBACK_REASON_INVALID"),
        ("used_source_ids", ["KB-1"], "USED_SOURCE_IDS_INVALID"),
        ("used_source_ids", ("KB-1", "KB-1"), "USED_SOURCE_IDS_INVALID"),
        ("used_source_ids", (" KB-1",), "USED_SOURCE_IDS_INVALID"),
        ("response_time_ms", True, "RESPONSE_TIME_MS_INVALID"),
        ("response_time_ms", -1, "RESPONSE_TIME_MS_INVALID"),
        ("selected_region", "아름동", "REGION_INVALID"),
        ("routed_office_public_id", " OFFICE-1", "ROUTED_OFFICE_ID_INVALID"),
        ("is_test", 1, "IS_TEST_INVALID"),
        ("masked_question", " ", "MASKED_QUESTION_INVALID"),
    ],
)
def test_interaction_rejects_wrong_structural_types_and_padded_values(
    field: str, value: object, message: str
) -> None:
    with pytest.raises(ValueError, match=f"^{message}$"):
        interaction(**{field: value})


def test_failure_confirmation_requires_operator_and_supported_failure_reason() -> None:
    confirmation = FailureReasonConfirmation(
        uuid4(), operator(), FallbackReason.INSUFFICIENT_GROUNDING
    )
    assert confirmation.actor.role is AdminRole.OPERATOR

    with pytest.raises(ValueError, match="^ACTOR_ROLE_FORBIDDEN$"):
        FailureReasonConfirmation(uuid4(), approver(), FallbackReason.PERSONAL_LOOKUP)
    with pytest.raises(ValueError, match="^FALLBACK_REASON_INVALID$"):
        FailureReasonConfirmation(uuid4(), operator(), FallbackReason.OUT_OF_SCOPE)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("failed_question_id", "uuid", "FAILED_QUESTION_ID_INVALID"),
        ("actor", None, "ACTOR_INVALID"),
        ("title", " title", "TITLE_INVALID"),
        ("representative_question", "", "REPRESENTATIVE_QUESTION_INVALID"),
        ("category", Intent.UNKNOWN, "CATEGORY_INVALID"),
        ("answer_summary", " ", "ANSWER_SUMMARY_INVALID"),
        ("procedure_steps", ["step"], "PROCEDURE_STEPS_INVALID"),
        ("required_documents", (" doc",), "REQUIRED_DOCUMENTS_INVALID"),
        ("processing_time", " ", "PROCESSING_TIME_INVALID"),
        ("fee", 0, "FEE_INVALID"),
        ("department", "department ", "DEPARTMENT_INVALID"),
        ("source_title", "", "SOURCE_TITLE_INVALID"),
        ("source_url", " url", "SOURCE_URL_INVALID"),
        ("last_verified_at", datetime(2026, 7, 17), "LAST_VERIFIED_AT_INVALID"),
        ("caution", " ", "CAUTION_INVALID"),
        ("data_origin", "OFFICIAL", "DATA_ORIGIN_INVALID"),
    ],
)
def test_candidate_rejects_invalid_fields_before_database_io(
    field: str, value: object, message: str
) -> None:
    with pytest.raises(ValueError, match=f"^{message}$"):
        candidate(**{field: value})


def test_candidate_requires_operator_role() -> None:
    with pytest.raises(ValueError, match="^ACTOR_ROLE_FORBIDDEN$"):
        candidate(actor=approver())


@pytest.mark.parametrize(
    ("factory", "field", "value", "message"),
    [
        (knowledge, "public_id", " KB-1", "PUBLIC_ID_INVALID"),
        (knowledge, "category", Intent.OUT_OF_SCOPE, "CATEGORY_INVALID"),
        (knowledge, "service_name", "", "SERVICE_NAME_INVALID"),
        (knowledge, "answer_summary", " ", "ANSWER_SUMMARY_INVALID"),
        (knowledge, "procedure_steps", ["step"], "PROCEDURE_STEPS_INVALID"),
        (knowledge, "required_documents", ("",), "REQUIRED_DOCUMENTS_INVALID"),
        (knowledge, "last_verified_at", "2026-07-17", "LAST_VERIFIED_AT_INVALID"),
        (knowledge, "question_examples", ["question"], "QUESTION_EXAMPLES_INVALID"),
        (office, "region", "아름동", "REGION_INVALID"),
        (office, "office_name", " office", "OFFICE_NAME_INVALID"),
        (office, "opening_hours", " ", "OPENING_HOURS_INVALID"),
        (office, "department_label", 1, "DEPARTMENT_LABEL_INVALID"),
    ],
)
def test_read_models_reject_malformed_database_shapes(
    factory: Callable[..., object], field: str, value: object, message: str
) -> None:
    with pytest.raises(ValueError, match=f"^{message}$"):
        factory(**{field: value})


def test_active_knowledge_requires_at_least_one_question_example() -> None:
    with pytest.raises(ValueError, match="^QUESTION_EXAMPLES_INVALID$"):
        knowledge(question_examples=())


def test_result_models_require_exact_uuid_and_nonnegative_count_types() -> None:
    interaction_id = uuid4()
    failed_question_id = uuid4()
    result = InteractionWriteResult(interaction_id, failed_question_id)
    purge = PurgeResult(1, (failed_question_id,))

    assert result.interaction_id == interaction_id
    assert purge.purged_ids == (failed_question_id,)

    with pytest.raises(ValueError, match="^INTERACTION_ID_INVALID$"):
        InteractionWriteResult("uuid", None)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="^FAILED_QUESTION_ID_INVALID$"):
        InteractionWriteResult(interaction_id, "uuid")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="^PURGED_COUNT_INVALID$"):
        PurgeResult(True, ())
    with pytest.raises(ValueError, match="^PURGED_IDS_INVALID$"):
        PurgeResult(0, [failed_question_id])  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="^PURGED_IDS_INVALID$"):
        PurgeResult(2, (failed_question_id,))


def test_uuid_fields_keep_uuid_values_without_coercion() -> None:
    identifier = UUID("12345678-1234-5678-9234-567812345678")

    assert (
        FailureReasonConfirmation(
            identifier, operator(), FallbackReason.LEGAL_JUDGMENT
        ).failed_question_id
        is identifier
    )
