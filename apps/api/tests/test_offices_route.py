from datetime import date
from uuid import UUID

import pytest
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

    async def list_offices(self, region: Region, intent: Intent) -> tuple[Office, ...]:
        self.calls.append((region, intent))
        return self.items


class UnexpectedDirectory(FakeDirectory):
    async def list_offices(self, region: Region, intent: Intent) -> tuple[Office, ...]:
        del region, intent
        raise RuntimeError("unexpected directory failure")


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


@pytest.mark.parametrize(
    "params",
    (
        {"intent": "BULKY_WASTE"},
        {"region": "아름동"},
        {"region": "지원하지않는지역", "intent": "BULKY_WASTE"},
        {"region": "아름동", "intent": "UNKNOWN"},
        {"region": "아름동", "intent": "OUT_OF_SCOPE"},
    ),
)
def test_invalid_office_filters_return_value_free_validation_error(
    params: dict[str, str],
) -> None:
    directory = FakeDirectory()
    sentinel = "DO-NOT-ECHO-OFFICE-QUERY"

    response = TestClient(create_app(office_directory=directory)).get(
        "/api/v1/offices",
        params={**params, "sentinel": sentinel},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert response.json()["error"]["message"] == "입력값을 확인해 주세요."
    assert response.json()["error"]["retryable"] is False
    UUID(response.json()["error"]["request_id"])
    assert sentinel not in response.text
    assert directory.calls == []


def test_unexpected_directory_error_is_not_converted_to_safe_unavailable() -> None:
    with pytest.raises(RuntimeError, match="unexpected directory failure"):
        TestClient(create_app(office_directory=UnexpectedDirectory())).get(
            "/api/v1/offices",
            params={"region": "아름동", "intent": "BULKY_WASTE"},
        )


def test_generated_openapi_declares_the_office_route() -> None:
    operation = create_app().openapi()["paths"]["/api/v1/offices"]["get"]

    assert operation["operationId"] == "listOffices"
    assert {item["name"] for item in operation["parameters"]} == {"region", "intent"}
    assert all(item["required"] is True for item in operation["parameters"])
    assert set(operation["responses"]) >= {"200", "422", "503"}


def test_generated_openapi_declares_the_office_retry_after_header() -> None:
    operation = create_app().openapi()["paths"]["/api/v1/offices"]["get"]

    assert operation["responses"]["503"]["headers"]["Retry-After"] == {
        "description": "Suggested retry delay in seconds.",
        "schema": {"type": "integer", "minimum": 1},
    }
