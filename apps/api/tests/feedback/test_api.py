from __future__ import annotations

from uuid import UUID

from fastapi.testclient import TestClient

from sejong_ai_api.contracts.feedback import FeedbackCreateRequest
from sejong_ai_api.feedback.service import FeedbackPrivacyUnresolvedError
from sejong_ai_api.main import create_app

REQUEST_ID = UUID("82000000-0000-4000-8000-000000000001")
RESPONSE_REQUEST_ID = UUID("81000000-0000-4000-8000-000000000001")


class RecordingFeedbackService:
    def __init__(self) -> None:
        self.payloads: list[FeedbackCreateRequest] = []
        self.raise_privacy = False

    async def record(self, payload: FeedbackCreateRequest):  # type: ignore[no-untyped-def]
        from sejong_ai_api.contracts.feedback import FeedbackCreateResponse

        self.payloads.append(payload)
        if self.raise_privacy:
            raise FeedbackPrivacyUnresolvedError()
        return FeedbackCreateResponse(
            request_id=payload.request_id,
            status="RECORDED",
            detail_status="NOT_PROVIDED",
        )


def test_feedback_route_is_closed_by_default() -> None:
    with TestClient(create_app(request_id_factory=lambda: REQUEST_ID)) as client:
        response = client.post(
            "/api/v1/feedback",
            json={
                "request_id": str(RESPONSE_REQUEST_ID),
                "rating": "SATISFIED",
                "category": None,
                "reason_code": None,
                "detail": None,
            },
        )

    assert response.status_code == 503
    assert response.json()["error"] == {
        "code": "SERVICE_UNAVAILABLE",
        "message": "잠시 후 다시 시도해 주세요.",
        "request_id": str(REQUEST_ID),
        "retryable": True,
    }


def test_injected_feedback_service_records_strict_payload() -> None:
    service = RecordingFeedbackService()
    with TestClient(
        create_app(
            feedback_service=service,
            request_id_factory=lambda: REQUEST_ID,
        )
    ) as client:
        response = client.post(
            "/api/v1/feedback",
            json={
                "request_id": str(RESPONSE_REQUEST_ID),
                "rating": "DISSATISFIED",
                "category": "OTHER",
                "reason_code": "OTHER",
                "detail": "버튼 안내가 부족해요.",
            },
        )

    assert response.status_code == 201
    assert response.json() == {
        "request_id": str(RESPONSE_REQUEST_ID),
        "status": "RECORDED",
        "detail_status": "NOT_PROVIDED",
    }
    assert service.payloads[0].detail == "버튼 안내가 부족해요."


def test_other_reason_requires_detail_before_service() -> None:
    service = RecordingFeedbackService()
    with TestClient(
        create_app(
            feedback_service=service,
            request_id_factory=lambda: REQUEST_ID,
        )
    ) as client:
        response = client.post(
            "/api/v1/feedback",
            json={
                "request_id": str(RESPONSE_REQUEST_ID),
                "rating": "DISSATISFIED",
                "category": "OTHER",
                "reason_code": "OTHER",
                "detail": None,
            },
        )

    assert response.status_code == 422
    assert service.payloads == []
    assert "input" not in response.text.casefold()


def test_privacy_unresolved_returns_value_free_422_and_no_echo() -> None:
    service = RecordingFeedbackService()
    service.raise_privacy = True
    unsafe = "010-9999-8888"
    with TestClient(
        create_app(
            feedback_service=service,
            request_id_factory=lambda: REQUEST_ID,
        )
    ) as client:
        response = client.post(
            "/api/v1/feedback",
            json={
                "request_id": str(RESPONSE_REQUEST_ID),
                "rating": "DISSATISFIED",
                "category": "OTHER",
                "reason_code": "OTHER",
                "detail": unsafe,
            },
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "FEEDBACK_PRIVACY_UNRESOLVED"
    assert unsafe not in response.text
