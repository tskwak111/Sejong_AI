import json
from uuid import UUID

from fastapi.testclient import TestClient

from sejong_ai_api.api.health import ReadinessProbe
from sejong_ai_api.main import create_app


class FakeReadinessProbe:
    def __init__(self, ready: bool) -> None:
        self.ready = ready
        self.call_count = 0

    async def check_ready(self) -> bool:
        self.call_count += 1
        return self.ready


def test_health_is_process_only_and_has_an_exact_public_shape() -> None:
    probe = FakeReadinessProbe(ready=True)

    with TestClient(create_app(readiness_probe=probe)) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert probe.call_count == 0


def test_default_readiness_is_an_exact_retryable_service_unavailable() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/ready")

    assert response.status_code == 503
    assert response.headers["Retry-After"] == "30"

    body = response.json()
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message", "request_id", "retryable"}
    assert body["error"]["code"] == "SERVICE_UNAVAILABLE"
    assert body["error"]["message"] == "잠시 후 다시 시도해 주세요."
    assert body["error"]["retryable"] is True
    UUID(body["error"]["request_id"])

    serialized_body = json.dumps(body, ensure_ascii=False).casefold()
    for forbidden_detail in (
        "cause",
        "database",
        "deepseek",
        "provider",
        "question",
        "secret",
        "stack",
        "traceback",
    ):
        assert forbidden_detail not in serialized_body


def test_injected_readiness_probe_can_report_ready_without_database_code() -> None:
    probe = FakeReadinessProbe(ready=True)
    typed_probe: ReadinessProbe = probe

    with TestClient(create_app(readiness_probe=typed_probe)) as client:
        response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
    assert "Retry-After" not in response.headers
    assert probe.call_count == 1


def test_generated_openapi_uses_the_tracked_health_operation_ids() -> None:
    schema = create_app().openapi()

    assert schema["info"]["version"] == "3.2.0-draft"
    assert schema["paths"]["/health"]["get"]["operationId"] == "health"
    assert schema["paths"]["/ready"]["get"]["operationId"] == "readiness"


def test_generated_openapi_has_strict_required_health_and_readiness_bodies() -> None:
    schema = create_app().openapi()

    for path, component_name, expected_status in (
        ("/health", "HealthResponse", "ok"),
        ("/ready", "ReadyResponse", "ready"),
    ):
        response_schema = schema["paths"][path]["get"]["responses"]["200"]["content"][
            "application/json"
        ]["schema"]
        assert response_schema == {"$ref": f"#/components/schemas/{component_name}"}

        component = schema["components"]["schemas"][component_name]
        assert component["additionalProperties"] is False
        assert component["required"] == ["status"]
        assert component["properties"]["status"]["type"] == "string"
        assert component["properties"]["status"]["const"] == expected_status
        assert "default" not in component["properties"]["status"]


def test_generated_openapi_declares_the_wire_retry_after_header() -> None:
    schema = create_app().openapi()
    retry_after = schema["paths"]["/ready"]["get"]["responses"]["503"]["headers"]["Retry-After"]

    assert retry_after["schema"] == {"type": "integer", "minimum": 1}
