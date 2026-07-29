from __future__ import annotations

from uuid import UUID

import pytest

from sejong_ai_api.contracts.feedback import FeedbackCreateRequest
from sejong_ai_api.db.models import CitizenFeedbackWrite
from sejong_ai_api.feedback.service import (
    FeedbackPrivacyUnresolvedError,
    FeedbackService,
)

REQUEST_ID = UUID("81000000-0000-4000-8000-000000000001")


class RecordingRepository:
    def __init__(self) -> None:
        self.writes: list[CitizenFeedbackWrite] = []

    async def record_citizen_feedback(self, write: CitizenFeedbackWrite) -> None:
        self.writes.append(write)


@pytest.mark.asyncio
async def test_satisfied_feedback_records_only_closed_metadata() -> None:
    repository = RecordingRepository()
    service = FeedbackService(repository)

    result = await service.record(
        FeedbackCreateRequest(
            request_id=REQUEST_ID,
            rating="SATISFIED",
            category=None,
            reason_code=None,
            detail=None,
        )
    )

    assert result.model_dump(mode="json") == {
        "request_id": str(REQUEST_ID),
        "status": "RECORDED",
        "detail_status": "NOT_PROVIDED",
    }
    assert repository.writes == [
        CitizenFeedbackWrite(
            response_request_id=REQUEST_ID,
            rating="SATISFIED",
            category=None,
            reason_code=None,
            masked_detail=None,
            detail_was_masked=False,
        )
    ]


@pytest.mark.asyncio
async def test_phone_in_detail_is_masked_before_repository_boundary() -> None:
    repository = RecordingRepository()
    service = FeedbackService(repository)
    raw_detail = "연락처 010-0000-0000"

    result = await service.record(
        FeedbackCreateRequest(
            request_id=REQUEST_ID,
            rating="DISSATISFIED",
            category="OTHER",
            reason_code="OTHER",
            detail=raw_detail,
        )
    )

    assert result.detail_status == "MASKED"
    assert len(repository.writes) == 1
    assert repository.writes[0].masked_detail == ("연락처 [전화번호]")
    assert raw_detail not in repr(repository.writes)


@pytest.mark.asyncio
async def test_ordinary_feedback_sentence_is_stored_without_question_only_rejection() -> None:
    repository = RecordingRepository()
    service = FeedbackService(repository)

    result = await service.record(
        FeedbackCreateRequest(
            request_id=REQUEST_ID,
            rating="DISSATISFIED",
            category="OTHER",
            reason_code="OTHER",
            detail="설명이 부족해요.",
        )
    )

    assert result.detail_status == "STORED"
    assert repository.writes == [
        CitizenFeedbackWrite(
            response_request_id=REQUEST_ID,
            rating="DISSATISFIED",
            category="OTHER",
            reason_code="OTHER",
            masked_detail="설명이 부족해요.",
            detail_was_masked=False,
        )
    ]


@pytest.mark.asyncio
async def test_phone_and_ordinary_feedback_tail_are_masked_before_repository_boundary() -> None:
    repository = RecordingRepository()
    service = FeedbackService(repository)
    raw_detail = "테스트 연락처 010-0000-0000, 설명이 부족해요."

    result = await service.record(
        FeedbackCreateRequest(
            request_id=REQUEST_ID,
            rating="DISSATISFIED",
            category="OTHER",
            reason_code="OTHER",
            detail=raw_detail,
        )
    )

    assert result.detail_status == "MASKED"
    assert len(repository.writes) == 1
    assert repository.writes[0].masked_detail == ("테스트 연락처 [전화번호], 설명이 부족해요.")
    assert raw_detail not in repr(repository.writes)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "unsafe_detail",
    [
        "김철수라고 합니다.",
        "가상 아파트 101동 202호",
        "연락처 1234567890123456",
    ],
)
async def test_ambiguous_or_residual_pii_detail_creates_no_row(
    unsafe_detail: str,
) -> None:
    repository = RecordingRepository()
    service = FeedbackService(repository)

    with pytest.raises(
        FeedbackPrivacyUnresolvedError,
        match="^FEEDBACK_PRIVACY_UNRESOLVED$",
    ) as captured:
        await service.record(
            FeedbackCreateRequest(
                request_id=REQUEST_ID,
                rating="DISSATISFIED",
                category="OTHER",
                reason_code="OTHER",
                detail=unsafe_detail,
            )
        )

    assert repository.writes == []
    assert unsafe_detail not in str(captured.value)


@pytest.mark.asyncio
async def test_unresolved_detail_creates_no_row_and_never_echoes_value() -> None:
    repository = RecordingRepository()
    service = FeedbackService(repository)
    unsafe = "\u202e개인정보"

    with pytest.raises(
        FeedbackPrivacyUnresolvedError,
        match="^FEEDBACK_PRIVACY_UNRESOLVED$",
    ) as captured:
        await service.record(
            FeedbackCreateRequest(
                request_id=REQUEST_ID,
                rating="DISSATISFIED",
                category="LOCAL_TAX_GENERAL",
                reason_code="OTHER",
                detail=unsafe,
            )
        )

    assert repository.writes == []
    assert unsafe not in str(captured.value)
