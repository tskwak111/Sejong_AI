import json
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from sejong_ai_api.contracts.chat import (
    CHAT_RESPONSE_ADAPTER,
    ChatRequest,
    Office,
)
from sejong_ai_api.contracts.chat import (
    ServiceUnavailableEnvelope as ChatServiceUnavailableEnvelope,
)
from sejong_ai_api.contracts.health import ServiceUnavailableEnvelope

FIXTURE_ROOT = Path(__file__).parents[3] / "contracts" / "fixtures"


def read_fixture_text(relative_path: str) -> str:
    payload = (FIXTURE_ROOT / relative_path).read_text(encoding="utf-8")
    assert "시연용 샘플" in payload or "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa" in payload
    return payload


def read_fixture(relative_path: str) -> dict[str, Any]:
    payload: dict[str, Any] = json.loads(read_fixture_text(relative_path))
    return payload


@pytest.mark.parametrize(
    ("fixture", "valid"),
    [
        ("valid-first-request.json", True),
        ("valid-null-context.json", True),
        ("invalid-session-id.json", False),
    ],
)
def test_chat_request_consumes_shared_fixtures(fixture: str, valid: bool) -> None:
    payload = read_fixture_text(f"chat-request/{fixture}")

    if valid:
        ChatRequest.model_validate_json(payload)
    else:
        with pytest.raises(ValidationError):
            ChatRequest.model_validate_json(payload)


@pytest.mark.parametrize(
    ("fixture", "valid"),
    [
        ("valid-success.json", True),
        ("invalid-success-empty-sources.json", False),
        ("valid-followup.json", True),
        ("valid-fallback-no-office.json", True),
        ("valid-fallback-office.json", True),
        ("valid-civic-scope-gap.json", True),
        ("valid-privacy-unresolved.json", True),
        ("invalid-privacy-copy.json", False),
        ("invalid-privacy-confidence.json", False),
        ("invalid-privacy-answer-payload.json", False),
        ("invalid-privacy-candidate.json", False),
        ("invalid-privacy-office.json", False),
        ("invalid-success-fallback.json", False),
        ("invalid-followup-source.json", False),
        ("invalid-fallback-missing-fallback.json", False),
        ("invalid-insufficient-candidate.json", False),
        ("invalid-out-of-scope-intent.json", False),
        ("invalid-civic-scope-gap-intent.json", False),
        ("invalid-fallback-context.json", False),
        ("invalid-missing-context.json", False),
        ("invalid-session-id.json", False),
        ("invalid-office-missing-id.json", False),
        ("invalid-fallback-extra-property.json", False),
    ],
)
def test_chat_response_consumes_shared_fixtures(fixture: str, valid: bool) -> None:
    payload = read_fixture_text(f"chat-response/{fixture}")

    if valid:
        CHAT_RESPONSE_ADAPTER.validate_json(payload, strict=True)
    else:
        with pytest.raises(ValidationError):
            CHAT_RESPONSE_ADAPTER.validate_json(payload, strict=True)


def test_followup_fixture_uses_approved_current_tax_topic_labels() -> None:
    response = read_fixture("chat-response/valid-followup.json")

    assert response["intent"] == "LOCAL_TAX_GENERAL"
    assert response["followup_options"] == [
        "지방세 온라인 납부 공식 경로 안내",
        "자동차세 개인 고지 확인·납부의 공식 로그인 경로",
        "지방세 납세증명서 발급 안내",
        "지방세 세목별 과세증명서 발급 안내",
        "지방세 납부확인서 발급 안내",
    ]


@pytest.mark.parametrize(
    ("fixture", "valid"),
    [
        ("valid-service-unavailable.json", True),
        ("invalid-code.json", False),
        ("invalid-extra-property.json", False),
        ("invalid-request-id.json", False),
    ],
)
def test_service_unavailable_consumes_shared_fixtures(fixture: str, valid: bool) -> None:
    payload = read_fixture_text(f"errors/{fixture}")

    if valid:
        ServiceUnavailableEnvelope.model_validate_json(payload)
    else:
        with pytest.raises(ValidationError):
            ServiceUnavailableEnvelope.model_validate_json(payload)


def test_chat_contract_reuses_the_existing_service_unavailable_model() -> None:
    assert ChatServiceUnavailableEnvelope is ServiceUnavailableEnvelope


def test_chat_request_rejects_integer_boolean_coercion() -> None:
    request = read_fixture("chat-request/valid-null-context.json")
    request["simple_language"] = 1
    with pytest.raises(ValidationError):
        ChatRequest.model_validate_json(json.dumps(request, ensure_ascii=False))


def test_chat_response_rejects_string_number_coercion() -> None:
    response = read_fixture("chat-response/valid-success.json")
    response["confidence"] = "0.5"
    with pytest.raises(ValidationError):
        CHAT_RESPONSE_ADAPTER.validate_json(json.dumps(response, ensure_ascii=False), strict=True)


def test_success_answer_mode_is_required_and_closed() -> None:
    response = read_fixture("chat-response/valid-success.json")
    response.pop("answer_mode", None)
    with pytest.raises(ValidationError):
        CHAT_RESPONSE_ADAPTER.validate_python(response, strict=True)

    response["answer_mode"] = "UNAPPROVED"
    with pytest.raises(ValidationError):
        CHAT_RESPONSE_ADAPTER.validate_python(response, strict=True)


def test_service_unavailable_rejects_integer_literal_coercion() -> None:
    unavailable = read_fixture("errors/valid-service-unavailable.json")
    unavailable["error"]["retryable"] = 1
    with pytest.raises(ValidationError):
        ServiceUnavailableEnvelope.model_validate_json(json.dumps(unavailable, ensure_ascii=False))


def test_office_allows_future_fields_but_rejects_explicit_null_source_url() -> None:
    payload = read_fixture("chat-response/valid-fallback-office.json")
    office_payload = deepcopy(payload["fallback"]["office"])
    office_payload["future_office_field"] = "시연용 샘플 확장 필드"

    office = Office.model_validate_json(json.dumps(office_payload, ensure_ascii=False))
    assert office.__pydantic_extra__ == {"future_office_field": "시연용 샘플 확장 필드"}

    office_payload["source_url"] = None
    with pytest.raises(ValidationError):
        Office.model_validate_json(json.dumps(office_payload, ensure_ascii=False))


def test_office_omits_an_absent_source_url_in_json_serialization() -> None:
    payload = read_fixture("chat-response/valid-success.json")
    office_payload = deepcopy(payload["office"])
    office_payload.pop("source_url", None)

    serialized = Office.model_validate_json(
        json.dumps(office_payload, ensure_ascii=False)
    ).model_dump(mode="json")

    assert "source_url" not in serialized


@pytest.mark.parametrize(
    "url", ["javascript:alert(1)", "data:text/html,test", "http://example.invalid"]
)
def test_chat_contract_rejects_non_https_links(url: str) -> None:
    response = read_fixture("chat-response/valid-success.json")
    response["sources"][0]["url"] = url
    with pytest.raises(ValidationError):
        CHAT_RESPONSE_ADAPTER.validate_python(response, strict=True)

    office_payload = deepcopy(response["office"])
    office_payload["source_url"] = url
    with pytest.raises(ValidationError):
        Office.model_validate(office_payload, strict=True)
