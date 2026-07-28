"""Explicit local/private dependency composition.

Use this module as an application factory. Importing ``sejong_ai_api.main``
continues to avoid environment and database access.
"""

from __future__ import annotations

import asyncio
import os
import time
from collections.abc import AsyncIterator, Callable, Mapping
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol, TextIO, cast
from urllib.parse import quote
from uuid import UUID, uuid4

from fastapi import FastAPI
from psycopg import Error as PsycopgError
from psycopg.conninfo import conninfo_to_dict

from sejong_ai_api.admin.service import AdminRepository, AdminService
from sejong_ai_api.chat.context import ContextTokenCodec
from sejong_ai_api.chat.idempotency import ChatIdempotencyRepository
from sejong_ai_api.chat.readiness import ReadinessRepository, RepositoryReadinessProbe
from sejong_ai_api.chat.service import (
    ChatRepository,
    ChatResult,
    ChatService,
    ChatUnavailableError,
)
from sejong_ai_api.contracts.chat import ChatRequest
from sejong_ai_api.db.models import PurgeResult
from sejong_ai_api.db.pool import _ambient_libpq_environment_is_clear, create_pool
from sejong_ai_api.db.repository import PsycopgSejongRepository
from sejong_ai_api.main import create_app
from sejong_ai_api.office.service import GuardedOfficeDirectory, OfficeDirectoryService

if TYPE_CHECKING:
    import httpx

    from sejong_ai_api.chat.classification import SafeQuestion
    from sejong_ai_api.chat.service import QuestionClassifierPort
    from sejong_ai_api.chat.topic_catalog import TopicCatalog
    from sejong_ai_api.llm.classifier_contracts import ClassifierDecision
    from sejong_ai_api.llm.limits import ProviderAttemptLedger
    from sejong_ai_api.llm.settings import UpstageChatSettings
    from sejong_ai_api.llm.upstage_chat import GroundedChatRuntime

    type GroundedChatRuntimeFactory = Callable[[UpstageChatSettings], GroundedChatRuntime]
    type ClassifierClientFactory = Callable[[], httpx.AsyncClient]
    type ClassifierDelegateFactory = Callable[[httpx.AsyncClient], QuestionClassifierPort]

_LOCAL_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
_TOPIC_COVERAGE_PATH = (
    Path(__file__).resolve().parents[4] / "data" / "retrieval" / "topic-coverage.v1.json"
)
_ALLOWED_ENV_KEYS = frozenset({"DATABASE_URL", "CONTEXT_TOKEN_SECRET"})
_ALLOWED_DATABASE_CONNINFO_KEYS = frozenset({"user", "password", "host", "port", "dbname"})
_EXPECTED_DATABASE_IDENTITY = ("sejong_local_login", "127.0.0.1", 54322, "postgres")
_MIN_CONTEXT_SECRET_BYTES = 32
_DEFAULT_PURGE_INTERVAL_SECONDS = 60.0


@dataclass(frozen=True, slots=True)
class LocalSettings:
    database_url: str = field(repr=False)
    context_token_secret: bytes = field(repr=False)


@dataclass(frozen=True, slots=True)
class _ClassifierRuntime:
    classifier: _LazyQuestionClassifier
    ledger: ProviderAttemptLedger

    async def aclose(self) -> None:
        await self.classifier.aclose()


class _LazyQuestionClassifier:
    """Own the classifier client only after the first eligible request."""

    __slots__ = (
        "_client",
        "_client_factory",
        "_delegate",
        "_delegate_factory",
        "_disabled",
        "_init_lock",
    )

    def __init__(
        self,
        *,
        client_factory: ClassifierClientFactory,
        delegate_factory: ClassifierDelegateFactory,
    ) -> None:
        if not callable(client_factory) or not callable(delegate_factory):
            raise ValueError("CLASSIFIER_FACTORY_INVALID")
        self._client_factory = client_factory
        self._delegate_factory = delegate_factory
        self._client: httpx.AsyncClient | None = None
        self._delegate: QuestionClassifierPort | None = None
        self._disabled = False
        self._init_lock = asyncio.Lock()

    async def classify(
        self,
        question: SafeQuestion,
        catalog: TopicCatalog,
    ) -> ClassifierDecision | None:
        delegate = await self._get_or_create()
        return None if delegate is None else await delegate.classify(question, catalog)

    async def _get_or_create(self) -> QuestionClassifierPort | None:
        if self._disabled:
            return None
        if self._delegate is not None:
            return self._delegate
        async with self._init_lock:
            if self._disabled:
                return None
            if self._delegate is not None:
                return self._delegate
            client: httpx.AsyncClient | None = None
            try:
                client = self._client_factory()
                delegate = self._delegate_factory(client)
            except Exception:
                self._disabled = True
                if client is not None:
                    with suppress(Exception):
                        await client.aclose()
                return None
            self._client = client
            self._delegate = delegate
            return delegate

    async def aclose(self) -> None:
        async with self._init_lock:
            self._disabled = True
            client = self._client
            self._client = None
            self._delegate = None
        if client is not None:
            await client.aclose()


class LocalPool(Protocol):
    async def open(self, *, wait: bool = False) -> None: ...

    async def close(self) -> None: ...


class LocalRepository(
    ChatRepository,
    ReadinessRepository,
    AdminRepository,
    ChatIdempotencyRepository,
    Protocol,
):
    async def purge_expired_chat_idempotency(self) -> PurgeResult: ...


class GuardedChatResponder:
    """Keep chat closed until the approved local projection is ready."""

    __slots__ = ("_probe", "_service")

    def __init__(self, probe: RepositoryReadinessProbe, service: ChatService) -> None:
        self._probe = probe
        self._service = service

    async def answer(
        self,
        request: ChatRequest,
        *,
        request_id: UUID | None = None,
        idempotency_key: UUID | None = None,
    ) -> ChatResult:
        if not await self._probe.check_ready():
            raise ChatUnavailableError()
        try:
            return await self._service.answer(
                request,
                request_id=request_id,
                idempotency_key=idempotency_key,
            )
        except ChatUnavailableError:
            self._probe.mark_unavailable()
            raise ChatUnavailableError() from None


def load_local_settings(
    *,
    environ: Mapping[str, str] | None = None,
    env_path: Path | None = None,
) -> LocalSettings | None:
    """Load only the two local runtime values, preferring the process environment."""

    source = os.environ if environ is None else environ
    if not _ambient_libpq_environment_is_clear(source) or not _ambient_libpq_environment_is_clear(
        os.environ
    ):
        return None
    selected: dict[str, str] = {}
    for key in _ALLOWED_ENV_KEYS:
        if key in source:
            selected[key] = source[key]

    if len(selected) != len(_ALLOWED_ENV_KEYS):
        file_values = _read_allowlisted_env(env_path if env_path is not None else _LOCAL_ENV_PATH)
        if file_values is None:
            return None
        for key in _ALLOWED_ENV_KEYS:
            if key not in selected and key in file_values:
                selected[key] = file_values[key]

    database_dsn = selected.get("DATABASE_URL")
    secret_text = selected.get("CONTEXT_TOKEN_SECRET")
    if not _valid_database_url(database_dsn) or not _valid_env_value(secret_text):
        return None
    valid_database_url = cast(str, database_dsn)
    valid_secret_text = cast(str, secret_text)
    try:
        secret = valid_secret_text.encode("utf-8")
    except UnicodeEncodeError:
        return None
    if len(secret) < _MIN_CONTEXT_SECRET_BYTES:
        return None
    return LocalSettings(database_url=valid_database_url, context_token_secret=secret)


def create_local_app(
    *,
    environ: Mapping[str, str] | None = None,
    env_path: Path | None = None,
    pool_factory: Callable[[str], LocalPool] | None = None,
    repository_factory: Callable[[object], LocalRepository] | None = None,
    grounded_chat_runtime_factory: GroundedChatRuntimeFactory | None = None,
    purge_interval_seconds: float = _DEFAULT_PURGE_INTERVAL_SECONDS,
) -> FastAPI:
    """Build one fail-closed local application without eager network access."""

    settings = load_local_settings(environ=environ, env_path=env_path)
    if settings is None or type(purge_interval_seconds) is not float or purge_interval_seconds <= 0:
        return create_app()

    selected_pool_factory = pool_factory if pool_factory is not None else _default_pool_factory
    selected_repository_factory = (
        repository_factory if repository_factory is not None else _default_repository_factory
    )
    try:
        pool = selected_pool_factory(settings.database_url)
        repository = selected_repository_factory(pool)
        probe = RepositoryReadinessProbe(repository)
        upstage_chat_settings = _load_optional_upstage_chat_settings(
            environ=environ,
            env_path=env_path,
        )
        classifier_runtime = _compose_optional_classifier_runtime(
            environ=environ,
            env_path=env_path,
            upstage_chat_settings=upstage_chat_settings,
        )
        grounded_chat_runtime = _compose_optional_grounded_chat_runtime(
            chat_settings=upstage_chat_settings,
            runtime_factory=grounded_chat_runtime_factory,
            ledger=(classifier_runtime.ledger if classifier_runtime is not None else None),
        )
        from sejong_ai_api.chat.topic_catalog import load_topic_coverage

        topic_coverage = load_topic_coverage(_TOPIC_COVERAGE_PATH)
        service = ChatService(
            repository=repository,
            context_codec=ContextTokenCodec(
                secret=settings.context_token_secret,
                clock=lambda: int(time.time()),
            ),
            request_id_factory=uuid4,
            monotonic_ns=time.monotonic_ns,
            is_test=False,
            idempotency_repository=repository,
            idempotency_secret=settings.context_token_secret,
            idempotency_claim_factory=uuid4,
            answer_generator=(
                grounded_chat_runtime.generator if grounded_chat_runtime is not None else None
            ),
            question_classifier=(
                classifier_runtime.classifier if classifier_runtime is not None else None
            ),
            topic_coverage=topic_coverage,
        )
        responder = GuardedChatResponder(probe, service)
        office_directory = GuardedOfficeDirectory(
            probe,
            OfficeDirectoryService(repository),
        )
    except Exception:
        return create_app()

    application = create_app(
        readiness_probe=probe,
        chat_responder=responder,
        office_directory=office_directory,
        admin_enabled=True,
        admin_service=AdminService(repository),
    )

    @asynccontextmanager
    async def local_lifespan(_application: FastAPI) -> AsyncIterator[None]:
        stop_purge = asyncio.Event()
        purge_task: asyncio.Task[None] | None = None
        try:
            await pool.open(wait=True)
            await _purge_expired_private_records(repository)
            await probe.refresh()
            purge_task = asyncio.create_task(
                _run_periodic_purge(
                    repository,
                    probe,
                    stop_purge,
                    purge_interval_seconds,
                )
            )
        except Exception:
            probe.disable()
        try:
            yield
        finally:
            stop_purge.set()
            if purge_task is not None:
                with suppress(Exception):
                    await purge_task
            if grounded_chat_runtime is not None:
                with suppress(Exception):
                    await grounded_chat_runtime.aclose()
            if classifier_runtime is not None:
                with suppress(Exception):
                    await classifier_runtime.aclose()
            with suppress(Exception):
                await pool.close()
            probe.disable()

    application.router.lifespan_context = local_lifespan
    return application


def _compose_optional_grounded_chat_runtime(
    *,
    chat_settings: UpstageChatSettings | None,
    runtime_factory: GroundedChatRuntimeFactory | None,
    ledger: ProviderAttemptLedger | None,
) -> GroundedChatRuntime | None:
    """Lazily compose the exact local profile without making an outbound request."""

    try:
        if chat_settings is None:
            return None
        if runtime_factory is not None:
            if ledger is not None:
                return None
            return runtime_factory(chat_settings)
        from sejong_ai_api.llm.upstage_chat import build_upstage_chat_runtime

        return build_upstage_chat_runtime(chat_settings, ledger=ledger)
    except Exception:
        return None


def _load_optional_upstage_chat_settings(
    *,
    environ: Mapping[str, str] | None,
    env_path: Path | None,
) -> UpstageChatSettings | None:
    """Load the optional validated generator capability exactly once per app composition."""

    try:
        from sejong_ai_api.llm.settings import load_upstage_chat_settings

        return load_upstage_chat_settings(environ=environ, env_path=env_path)
    except Exception:
        return None


def _compose_optional_classifier_runtime(
    *,
    environ: Mapping[str, str] | None,
    env_path: Path | None,
    upstage_chat_settings: UpstageChatSettings | None,
) -> _ClassifierRuntime | None:
    """Lazily compose the exact classifier profile without an eager request."""

    try:
        from sejong_ai_api.llm.classifier_provider import (
            ClassifierProvider,
            load_classifier_provider,
        )
        from sejong_ai_api.llm.contracts import TokenUsage
        from sejong_ai_api.llm.cost import estimate_cost_usd
        from sejong_ai_api.llm.limits import ProviderAttemptLedger
        from sejong_ai_api.llm.settings import (
            UPSTAGE_MAX_INPUT_TOKENS,
            UPSTAGE_MAX_OUTPUT_TOKENS,
        )

        provider = load_classifier_provider(
            environ=environ,
            env_path=env_path,
        )
        if provider is ClassifierProvider.DISABLED:
            return None

        if provider is ClassifierProvider.UPSTAGE:
            from sejong_ai_api.llm.settings import load_upstage_classifier_settings
            from sejong_ai_api.llm.upstage_classifier import (
                QuestionClassifier,
                create_upstage_classifier_client,
            )

            classifier_settings = load_upstage_classifier_settings(
                environ=environ,
                env_path=env_path,
            )
            if classifier_settings is None:
                return None
            ledger = ProviderAttemptLedger(
                classifier_cap=classifier_settings.classifier_attempt_cap,
                generator_cap=classifier_settings.generator_attempt_cap,
                combined_cap=classifier_settings.combined_attempt_cap,
                cost_cap_usd=classifier_settings.session_cost_cap_usd,
                classifier_worst_case_usd=estimate_cost_usd(
                    TokenUsage(
                        input_tokens=UPSTAGE_MAX_INPUT_TOKENS,
                        cached_input_tokens=0,
                        output_tokens=classifier_settings.max_output_tokens,
                    )
                ),
                generator_worst_case_usd=estimate_cost_usd(
                    TokenUsage(
                        input_tokens=UPSTAGE_MAX_INPUT_TOKENS,
                        cached_input_tokens=0,
                        output_tokens=UPSTAGE_MAX_OUTPUT_TOKENS,
                    )
                ),
            )

            def upstage_client_factory() -> httpx.AsyncClient:
                return create_upstage_classifier_client(classifier_settings)

            def upstage_delegate_factory(
                client: httpx.AsyncClient,
            ) -> QuestionClassifierPort:
                return QuestionClassifier(
                    settings=classifier_settings,
                    client=client,
                    ledger=ledger,
                )

            return _ClassifierRuntime(
                classifier=_LazyQuestionClassifier(
                    client_factory=upstage_client_factory,
                    delegate_factory=upstage_delegate_factory,
                ),
                ledger=ledger,
            )

        if provider is not ClassifierProvider.DEEPSEEK:
            return None

        from sejong_ai_api.llm.deepseek_classifier import (
            DeepSeekQuestionClassifier,
            create_deepseek_classifier_client,
        )
        from sejong_ai_api.llm.deepseek_settings import (
            load_deepseek_classifier_settings,
        )
        from sejong_ai_api.llm.deepseek_usage import estimate_deepseek_cost_usd

        deepseek_settings = load_deepseek_classifier_settings(
            environ=environ,
            env_path=env_path,
            upstage_chat_settings=upstage_chat_settings,
        )
        if deepseek_settings is None:
            return None
        ledger = ProviderAttemptLedger(
            classifier_cap=deepseek_settings.classifier_attempt_cap,
            generator_cap=deepseek_settings.generator_attempt_cap,
            combined_cap=deepseek_settings.combined_attempt_cap,
            cost_cap_usd=deepseek_settings.session_cost_cap_usd,
            classifier_worst_case_usd=estimate_deepseek_cost_usd(
                TokenUsage(
                    input_tokens=deepseek_settings.max_input_usage_tokens,
                    cached_input_tokens=0,
                    output_tokens=deepseek_settings.max_output_tokens,
                )
            ),
            generator_worst_case_usd=estimate_cost_usd(
                TokenUsage(
                    input_tokens=UPSTAGE_MAX_INPUT_TOKENS,
                    cached_input_tokens=0,
                    output_tokens=UPSTAGE_MAX_OUTPUT_TOKENS,
                )
            ),
            classifier_cost_estimator=estimate_deepseek_cost_usd,
            generator_cost_estimator=estimate_cost_usd,
        )

        def deepseek_client_factory() -> httpx.AsyncClient:
            return create_deepseek_classifier_client(deepseek_settings)

        def deepseek_delegate_factory(
            client: httpx.AsyncClient,
        ) -> QuestionClassifierPort:
            return DeepSeekQuestionClassifier(
                settings=deepseek_settings,
                client=client,
                ledger=ledger,
            )

        return _ClassifierRuntime(
            classifier=_LazyQuestionClassifier(
                client_factory=deepseek_client_factory,
                delegate_factory=deepseek_delegate_factory,
            ),
            ledger=ledger,
        )
    except Exception:
        return None


async def _purge_expired_private_records(repository: LocalRepository) -> None:
    await repository.purge_expired_failed_question_text()
    await repository.purge_expired_chat_idempotency()
    await repository.purge_expired_civic_scope_gap_text()


async def _run_periodic_purge(
    repository: LocalRepository,
    probe: RepositoryReadinessProbe,
    stop: asyncio.Event,
    interval_seconds: float,
) -> None:
    while not stop.is_set():
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval_seconds)
        except TimeoutError:
            try:
                await _purge_expired_private_records(repository)
            except Exception:
                probe.disable()
                return


def _read_allowlisted_env(path: Path) -> dict[str, str] | None:
    values: dict[str, str] = {}
    try:
        with path.open("r", encoding="utf-8", newline=None) as stream:
            while (assignment := _read_env_assignment_name(stream)) is not None:
                raw_key, has_separator = assignment
                key = raw_key.strip()
                if not key or key.startswith("#"):
                    if has_separator:
                        _discard_env_line(stream)
                    continue
                if key.startswith("export "):
                    key = key.removeprefix("export ").lstrip()
                if key not in _ALLOWED_ENV_KEYS:
                    if has_separator:
                        _discard_env_line(stream)
                    continue
                if not has_separator or key in values:
                    return None
                value = _read_env_line_value(stream).strip()
                if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                    value = value[1:-1]
                values[key] = value
    except (OSError, UnicodeDecodeError):
        return None
    return values


def _read_env_assignment_name(stream: TextIO) -> tuple[str, bool] | None:
    characters: list[str] = []
    while True:
        character = stream.read(1)
        if character == "":
            return ("".join(characters), False) if characters else None
        if character == "\n":
            return ("".join(characters), False)
        if character == "=":
            return ("".join(characters), True)
        characters.append(character)


def _read_env_line_value(stream: TextIO) -> str:
    characters: list[str] = []
    while True:
        character = stream.read(1)
        if character in ("", "\n"):
            return "".join(characters)
        characters.append(character)


def _discard_env_line(stream: TextIO) -> None:
    while stream.read(1) not in ("", "\n"):
        pass


def _valid_env_value(value: object) -> bool:
    return (
        type(value) is str
        and bool(value)
        and value == value.strip()
        and "\x00" not in value
        and "\r" not in value
        and "\n" not in value
    )


def _valid_database_url(value: object) -> bool:
    if not _valid_env_value(value):
        return False
    candidate_dsn = cast(str, value)
    if not candidate_dsn.startswith("postgresql://"):
        return False
    try:
        values = conninfo_to_dict(candidate_dsn)
        password = values.get("password")
        port_text = values.get("port")
        if (
            set(values) != _ALLOWED_DATABASE_CONNINFO_KEYS
            or not isinstance(password, str)
            or not password
            or any(character in password for character in "\x00\r\n")
            or not isinstance(port_text, str)
            or not port_text.isascii()
            or not port_text.isdecimal()
        ):
            return False
        identity = (
            values.get("user", ""),
            values.get("host", ""),
            int(port_text),
            values.get("dbname", ""),
        )
        if identity != _EXPECTED_DATABASE_IDENTITY:
            return False
        canonical_url = (
            f"postgresql://{quote(identity[0], safe='')}:{quote(password, safe='')}"
            f"@{identity[1]}:{identity[2]}/{quote(identity[3], safe='')}"
        )
    except (TypeError, UnicodeError, ValueError, PsycopgError):
        return False
    return candidate_dsn == canonical_url


def _default_pool_factory(database_url: str) -> LocalPool:
    return cast(LocalPool, create_pool(database_url))


def _default_repository_factory(pool: object) -> LocalRepository:
    return cast(LocalRepository, PsycopgSejongRepository(cast(Any, pool)))


__all__ = [
    "GuardedChatResponder",
    "LocalSettings",
    "create_local_app",
    "load_local_settings",
]
