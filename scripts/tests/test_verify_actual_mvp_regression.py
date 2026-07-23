from __future__ import annotations

import importlib.util
import sys
from collections.abc import Mapping
from pathlib import Path
from types import ModuleType

import pytest


_MODULE_NAME = "_sejong_verify_actual_mvp_regression_test"
_RUNNER_PATH = Path(__file__).resolve().parents[1] / "verify_actual_mvp_regression.py"
_FAILURE_ID = "10000000-0000-4000-8000-000000000001"
_CANDIDATE_ID = "20000000-0000-4000-8000-000000000001"
_SOURCE_URL = "https://www.sjwaste.kr/wasteApp/appCategoryPopup.do?menuId=MENU00305"
_SECRET = "synthetic-context-secret-value-000000"
_DSN = "postgresql://sejong_local_login:" + "synthetic@127.0.0.1:54322/postgres"
_PERSONAL_QUESTION = "내 자동차세 체납액 알려줘."
_PERSONAL_IDEMPOTENCY_KEY = "67000000-0000-4000-8000-000000000000"


def _runner() -> ModuleType:
    cached = sys.modules.get(_MODULE_NAME)
    if cached is not None:
        return cached
    if not _RUNNER_PATH.is_file():
        pytest.fail("the dedicated actual MVP regression runner is missing")
    spec = importlib.util.spec_from_file_location(_MODULE_NAME, _RUNNER_PATH)
    if spec is None or spec.loader is None:
        pytest.fail("the dedicated actual MVP regression runner cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[_MODULE_NAME] = module
    spec.loader.exec_module(module)
    return module


class FakeResponse:
    def __init__(self, status_code: int, payload: Mapping[str, object]) -> None:
        self.status_code = status_code
        self._payload = dict(payload)

    def json(self) -> object:
        return self._payload.copy()


class FakeRuntime:
    def __init__(
        self,
        responses: list[FakeResponse],
        projections: list[Mapping[str, tuple[str, ...]]],
        persistence_counts: list[Mapping[str, int]] | None = None,
        events: list[str] | None = None,
    ) -> None:
        self.responses = list(responses)
        self.projections = list(projections)
        self.persistence_counts = list(persistence_counts or [])
        self.events = events if events is not None else []
        self.requests: list[
            tuple[str, str, Mapping[str, str] | None, Mapping[str, object] | None]
        ] = []
        self.persistence_count_request_positions: list[int] = []

    def __enter__(self) -> FakeRuntime:
        self.events.append("enter")
        return self

    def __exit__(
        self,
        _exception_type: object,
        _exception: object,
        _traceback: object,
    ) -> None:
        self.events.append("exit")

    def request(
        self,
        method: str,
        path: str,
        *,
        headers: Mapping[str, str] | None = None,
        json: Mapping[str, object] | None = None,
    ) -> FakeResponse:
        self.requests.append((method, path, headers, json))
        if not self.responses:
            raise AssertionError("unexpected HTTP request")
        return self.responses.pop(0)

    def active_projection(self) -> Mapping[str, tuple[str, ...]]:
        if not self.projections:
            raise AssertionError("unexpected ACTIVE projection read")
        return self.projections.pop(0)

    def read_persistence_counts(self) -> Mapping[str, int]:
        self.persistence_count_request_positions.append(len(self.requests))
        if not self.persistence_counts:
            raise AssertionError("unexpected persistence count read")
        return self.persistence_counts.pop(0)


def _fallback(request_id: str) -> FakeResponse:
    return FakeResponse(
        200,
        {
            "request_id": request_id,
            "answer_status": "FALLBACK",
            "intent": "BULKY_WASTE",
            "fallback": {
                "reason": "INSUFFICIENT_GROUNDING",
                "candidate_eligible": True,
            },
            "sources": [],
        },
    )


def _personal_fallback(
    *,
    status_code: int = 200,
    answer_status: str = "FALLBACK",
    intent: str = "UNKNOWN",
    reason: str = "PERSONAL_LOOKUP",
    candidate_eligible: bool = False,
) -> FakeResponse:
    return FakeResponse(
        status_code,
        {
            "request_id": "10000000-0000-4000-8000-000000000010",
            "answer_status": answer_status,
            "intent": intent,
            "fallback": {
                "reason": reason,
                "candidate_eligible": candidate_eligible,
            },
            "sources": [],
        },
    )


def _success(request_id: str) -> FakeResponse:
    return FakeResponse(
        200,
        {
            "request_id": request_id,
            "answer_status": "SUCCESS",
            "intent": "BULKY_WASTE",
            "fee": "1인용침대 8,000원; 2인용침대 10,000원",
            "sources": [
                {
                    "source_id": "KB-WASTE-03",
                    "url": _SOURCE_URL,
                }
            ],
        },
    )


def _initial_projection(*, include_target: bool = False) -> dict[str, tuple[str, ...]]:
    waste = tuple(f"KB-WASTE-{index:02d}" for index in range(10, 14))
    if include_target:
        waste = ("KB-WASTE-03", *waste[1:])
    return {
        "MOVE_IN_RESIDENT_REGISTRATION": tuple(
            f"KB-MOVE-{index}" for index in range(5)
        ),
        "CERTIFICATE_ISSUANCE": tuple(f"KB-CERT-{index}" for index in range(5)),
        "BULKY_WASTE": waste,
        "LOCAL_TAX_GENERAL": tuple(f"KB-TAX-{index}" for index in range(5)),
    }


def _final_projection() -> dict[str, tuple[str, ...]]:
    projection = _initial_projection()
    projection["BULKY_WASTE"] = (*projection["BULKY_WASTE"], "KB-WASTE-03")
    return projection


def _success_runtime(
    events: list[str] | None = None,
    *,
    personal_response: FakeResponse | None = None,
    persistence_counts: list[Mapping[str, int]] | None = None,
) -> FakeRuntime:
    return FakeRuntime(
        responses=[
            FakeResponse(200, {"status": "ready"}),
            personal_response or _personal_fallback(),
            _fallback("10000000-0000-4000-8000-000000000011"),
            _fallback("10000000-0000-4000-8000-000000000012"),
            FakeResponse(
                200,
                {
                    "items": [
                        {
                            "id": _FAILURE_ID,
                            "status": "NEW",
                            "fallback_reason": "INSUFFICIENT_GROUNDING",
                            "candidate_eligible": True,
                        }
                    ],
                    "total": 1,
                },
            ),
            FakeResponse(200, {"id": _FAILURE_ID, "status": "REASON_CONFIRMED"}),
            FakeResponse(201, {"id": _CANDIDATE_ID, "status": "DRAFTED"}),
            FakeResponse(200, {"id": _CANDIDATE_ID, "status": "PENDING_APPROVAL"}),
            FakeResponse(403, {"error": {"code": "ADMIN_FORBIDDEN"}}),
            FakeResponse(200, {"id": _CANDIDATE_ID, "status": "APPROVED"}),
            _success("10000000-0000-4000-8000-000000000021"),
            _fallback("10000000-0000-4000-8000-000000000013"),
        ],
        projections=[_initial_projection(), _final_projection()],
        persistence_counts=persistence_counts
        or [
            {"interaction_events": 8, "failed_questions": 3},
            {"interaction_events": 8, "failed_questions": 3},
            {"interaction_events": 9, "failed_questions": 4},
        ],
        events=events,
    )


def test_full_actual_http_workflow_is_exact_and_outputs_only_stable_evidence() -> None:
    runner = _runner()
    runtime = _success_runtime()

    lines = runner.run_regression(runtime)

    assert lines == (
        "PASS ready",
        "PASS initial-active count=19",
        "PASS personal-lookup persistence event_delta=0 failed_delta=0",
        "PASS initial-fallback",
        "PASS business-replay",
        "PASS insufficient-grounding event_delta=1 failed_delta=1",
        "PASS failed-new count=1",
        "PASS reason-confirmed",
        "PASS candidate-created",
        "PASS candidate-submitted",
        "PASS self-approval-blocked",
        "PASS candidate-approved",
        "PASS improved-requery public_id=KB-WASTE-03",
        "PASS old-replay",
        "PASS final-active total=20 categories=4 count_each=5 public_id=KB-WASTE-03",
    )
    assert runtime.events == ["enter", "exit"]
    assert runtime.responses == []
    assert runtime.projections == []
    assert runtime.persistence_counts == []
    assert runtime.persistence_count_request_positions == [1, 2, 4]

    calls = runtime.requests
    assert [(method, path) for method, path, _headers, _json in calls] == [
        ("GET", "/ready"),
        ("POST", "/api/v1/chat"),
        ("POST", "/api/v1/chat"),
        ("POST", "/api/v1/chat"),
        (
            "GET",
            "/api/v1/admin/failed-questions?reason=INSUFFICIENT_GROUNDING&status=NEW",
        ),
        ("PATCH", f"/api/v1/admin/failed-questions/{_FAILURE_ID}/reason"),
        ("POST", "/api/v1/admin/kb-candidates"),
        ("POST", f"/api/v1/admin/kb-candidates/{_CANDIDATE_ID}/submit"),
        ("PATCH", f"/api/v1/admin/kb-candidates/{_CANDIDATE_ID}/review"),
        ("PATCH", f"/api/v1/admin/kb-candidates/{_CANDIDATE_ID}/review"),
        ("POST", "/api/v1/chat"),
        ("POST", "/api/v1/chat"),
    ]
    expected_candidate = {
        "failed_question_id": _FAILURE_ID,
        "title": "침대 프레임 배출 수수료",
        "representative_question": "침대 2인용 프레임 수수료가 얼마예요?",
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
        "fee": "1인용침대 8,000원; 2인용침대 10,000원",
        "department": "세종특별자치시시설관리공단",
        "source_title": "배출항목선택",
        "source_url": _SOURCE_URL,
        "last_verified_at": "2026-07-18",
        "caution": (
            "공식 품목표의 1인용침대·2인용침대 항목을 그대로 따릅니다. "
            "매트리스 포함 가격이나 실제 규격을 단정하지 않습니다."
        ),
    }
    assert calls[6][3] == expected_candidate
    assert "public_id" not in calls[6][3]
    assert calls[8][2] == {
        "X-Demo-Actor-Id": "OPERATOR-LOCAL-001",
        "X-Demo-Role": "APPROVER",
    }
    assert calls[9][2] == {
        "X-Demo-Actor-Id": "PM-LOCAL-001",
        "X-Demo-Role": "APPROVER",
    }
    assert calls[1][2] == {"Idempotency-Key": _PERSONAL_IDEMPOTENCY_KEY}
    assert calls[2][2] == calls[3][2] == calls[11][2]
    assert calls[10][2] != calls[2][2]
    assert calls[1][3] == {"question": _PERSONAL_QUESTION}
    expected_chat_body = {"question": "침대 2인용 프레임 수수료가 얼마예요?"}
    for index in (2, 3, 10, 11):
        assert calls[index][3] == expected_chat_body

    output = "\n".join(lines)
    for forbidden in (
        runner._RESERVED_QUESTION,
        _PERSONAL_QUESTION,
        _PERSONAL_IDEMPOTENCY_KEY,
        "10000000-0000-4000-8000-000000000010",
        _SOURCE_URL,
        _FAILURE_ID,
        _CANDIDATE_ID,
        _SECRET,
        _DSN,
    ):
        assert forbidden not in output


@pytest.mark.parametrize(
    ("personal_response", "expected_step"),
    [
        (_personal_fallback(status_code=503), "PERSONAL_LOOKUP"),
        (_personal_fallback(answer_status="SUCCESS"), "PERSONAL_LOOKUP"),
        (_personal_fallback(intent="LOCAL_TAX_GENERAL"), "PERSONAL_LOOKUP"),
        (_personal_fallback(reason="INSUFFICIENT_GROUNDING"), "PERSONAL_LOOKUP"),
        (_personal_fallback(candidate_eligible=True), "PERSONAL_LOOKUP"),
    ],
)
def test_personal_lookup_contract_is_checked_before_insufficient_grounding(
    personal_response: FakeResponse,
    expected_step: str,
) -> None:
    runner = _runner()
    runtime = _success_runtime(personal_response=personal_response)

    with pytest.raises(runner._RegressionFailed, match=f"^{expected_step}$"):
        runner.run_regression(runtime)

    assert runtime.persistence_count_request_positions == [1]
    assert [(method, path) for method, path, _headers, _json in runtime.requests] == [
        ("GET", "/ready"),
        ("POST", "/api/v1/chat"),
    ]


@pytest.mark.parametrize(
    "after_counts",
    [
        {"interaction_events": 9, "failed_questions": 3},
        {"interaction_events": 8, "failed_questions": 4},
    ],
)
def test_personal_lookup_persistence_delta_stops_before_improvement_workflow(
    after_counts: Mapping[str, int],
) -> None:
    runner = _runner()
    runtime = _success_runtime(
        persistence_counts=[
            {"interaction_events": 8, "failed_questions": 3},
            after_counts,
        ]
    )

    with pytest.raises(runner._RegressionFailed, match="^PERSONAL_STORAGE$"):
        runner.run_regression(runtime)

    assert runtime.persistence_counts == []
    assert runtime.persistence_count_request_positions == [1, 2]
    assert [(method, path) for method, path, _headers, _json in runtime.requests] == [
        ("GET", "/ready"),
        ("POST", "/api/v1/chat"),
    ]


@pytest.mark.parametrize(
    "after_insufficient_counts",
    [
        {"interaction_events": 8, "failed_questions": 3},
        {"interaction_events": 9, "failed_questions": 3},
        {"interaction_events": 8, "failed_questions": 4},
        {"interaction_events": 10, "failed_questions": 4},
        {"interaction_events": 9, "failed_questions": 5},
    ],
)
def test_insufficient_grounding_requires_exact_single_event_and_failure_delta(
    after_insufficient_counts: Mapping[str, int],
) -> None:
    runner = _runner()
    runtime = _success_runtime(
        persistence_counts=[
            {"interaction_events": 8, "failed_questions": 3},
            {"interaction_events": 8, "failed_questions": 3},
            after_insufficient_counts,
        ]
    )

    with pytest.raises(runner._RegressionFailed, match="^IG_STORAGE$"):
        runner.run_regression(runtime)

    assert runtime.persistence_counts == []
    assert runtime.persistence_count_request_positions == [1, 2, 4]
    assert [(method, path) for method, path, _headers, _json in runtime.requests] == [
        ("GET", "/ready"),
        ("POST", "/api/v1/chat"),
        ("POST", "/api/v1/chat"),
        ("POST", "/api/v1/chat"),
    ]


@pytest.mark.parametrize(
    "projection",
    [
        {
            **_initial_projection(),
            "BULKY_WASTE": (*_initial_projection()["BULKY_WASTE"], "KB-WASTE-20"),
        },
        _initial_projection(include_target=True),
    ],
)
def test_start_is_refused_unmodified_unless_exactly_19_and_target_absent(
    projection: Mapping[str, tuple[str, ...]],
) -> None:
    runner = _runner()
    runtime = FakeRuntime(
        responses=[FakeResponse(200, {"status": "ready"})],
        projections=[projection],
    )

    with pytest.raises(runner._RegressionFailed, match="^INITIAL_ACTIVE$"):
        runner.run_regression(runtime)

    assert [(method, path) for method, path, _headers, _json in runtime.requests] == [
        ("GET", "/ready")
    ]
    assert runtime.responses == []


def test_windows_selector_policy_precedes_actual_runtime_and_testclient_loading() -> (
    None
):
    runner = _runner()
    events: list[str] = []
    runtime = _success_runtime(events)

    def configure(platform: str) -> None:
        events.append(f"policy:{platform}")

    def runtime_factory(environment: Mapping[str, str]) -> FakeRuntime:
        assert environment["CONTEXT_TOKEN_SECRET"] == _SECRET
        events.append("factory")
        return runtime

    lines = runner._run_with_dependencies(
        environment={"CONTEXT_TOKEN_SECRET": _SECRET},
        platform="win32",
        configure_policy=configure,
        runtime_factory=runtime_factory,
    )

    assert lines[-1].startswith("PASS final-active")
    assert events[:3] == ["policy:win32", "factory", "enter"]


def test_main_bounds_unexpected_failures_without_echoing_values(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = _runner()
    sentinel = f"{_SECRET} {_DSN} {runner._RESERVED_QUESTION} {_FAILURE_ID}"
    monkeypatch.setattr(runner, "_configure_event_loop_policy", lambda _platform: None)
    monkeypatch.setattr(
        runner,
        "_build_actual_runtime",
        lambda _environment: (_ for _ in ()).throw(RuntimeError(sentinel)),
    )

    assert runner.main([]) == 1

    output = capsys.readouterr()
    assert output.out == ""
    assert output.err == "ACTUAL_MVP_REGRESSION_FAILED\n"
    assert sentinel not in output.out + output.err


def test_main_discards_dependency_output_before_emitting_buffered_pass_lines(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = _runner()

    def noisy_dependencies(**_kwargs: object) -> tuple[str, ...]:
        print(f"dependency {_SECRET} {runner._RESERVED_QUESTION}")
        print(f"dependency {_DSN} {_FAILURE_ID}", file=sys.stderr)
        return ("PASS ready", "PASS final-active total=20 public_id=KB-WASTE-03")

    monkeypatch.setattr(runner, "_run_with_dependencies", noisy_dependencies)

    assert runner.main([]) == 0

    output = capsys.readouterr()
    assert output.out == (
        "PASS ready\nPASS final-active total=20 public_id=KB-WASTE-03\n"
    )
    assert output.err == ""
    for forbidden in (_SECRET, runner._RESERVED_QUESTION, _DSN, _FAILURE_ID):
        assert forbidden not in output.out + output.err


def test_main_rejects_all_arguments_before_configuration_without_echo(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = _runner()
    configured: list[str] = []
    monkeypatch.setattr(
        runner,
        "_configure_event_loop_policy",
        lambda platform: configured.append(platform),
    )

    assert runner.main([_SECRET]) == 2

    output = capsys.readouterr()
    assert output.out == ""
    assert output.err == "ACTUAL_MVP_REGRESSION_FAILED\n"
    assert _SECRET not in output.out + output.err
    assert configured == []


class FakeAsyncPool:
    def __init__(self) -> None:
        self.closed = False
        self.close_calls = 0

    async def close(self) -> None:
        if self.closed:
            return
        self.close_calls += 1
        self.closed = True


@pytest.mark.parametrize("failure_point", ["application", "testclient-import"])
def test_composition_failure_after_pool_creation_closes_pool_once(
    failure_point: str,
) -> None:
    runner = _runner()
    pool = FakeAsyncPool()

    def application_factory(**_kwargs: object) -> object:
        if failure_point == "application":
            raise RuntimeError("synthetic application failure")
        return object()

    def client_loader() -> object:
        if failure_point == "testclient-import":
            raise RuntimeError("synthetic import failure")
        return object()

    with pytest.raises(runner._ConfigurationInvalid):
        runner._compose_actual_runtime(
            dsn=_DSN,
            selected_environment={"CONTEXT_TOKEN_SECRET": _SECRET},
            create_pool_fn=lambda _database_url: pool,
            repository_type=lambda _pool: object(),
            create_local_app_fn=application_factory,
            client_loader=client_loader,
            intent_type=object(),
        )

    assert pool.closed is True
    assert pool.close_calls == 1


def test_testclient_enter_failure_closes_owned_pool_idempotently() -> None:
    runner = _runner()
    pool = FakeAsyncPool()
    owner = runner._PoolOwner(pool)

    class FailingClient:
        def __enter__(self) -> object:
            raise RuntimeError("synthetic enter failure")

        def __exit__(self, *_args: object) -> None:
            raise AssertionError("exit is unavailable when enter fails")

    runtime = runner._ActualRuntime(
        object(),
        object(),
        lambda _application: FailingClient(),
        object(),
        owner,
    )

    with pytest.raises(RuntimeError, match="^synthetic enter failure$"):
        runtime.__enter__()

    owner.close()
    assert pool.closed is True
    assert pool.close_calls == 1


def test_successful_testclient_lifespan_does_not_double_close_pool() -> None:
    runner = _runner()
    pool = FakeAsyncPool()
    owner = runner._PoolOwner(pool)

    class LifespanClient:
        def __enter__(self) -> LifespanClient:
            return self

        def __exit__(self, *_args: object) -> None:
            pool.close_calls += 1
            pool.closed = True

    runtime = runner._ActualRuntime(
        object(),
        object(),
        lambda _application: LifespanClient(),
        object(),
        owner,
    )

    with runtime:
        pass
    owner.close()

    assert pool.closed is True
    assert pool.close_calls == 1


def test_returned_testclient_exit_that_leaves_pool_open_is_recovered_by_owner() -> None:
    runner = _runner()
    pool = FakeAsyncPool()
    owner = runner._PoolOwner(pool)

    class IncompleteLifespanClient:
        def __enter__(self) -> IncompleteLifespanClient:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

    runtime = runner._ActualRuntime(
        object(),
        object(),
        lambda _application: IncompleteLifespanClient(),
        object(),
        owner,
    )

    with runtime:
        pass

    assert pool.closed is True
    assert pool.close_calls == 1
