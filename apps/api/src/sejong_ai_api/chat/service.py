"""Privacy-first deterministic chat orchestration."""

from __future__ import annotations

import asyncio
import json
import re
import unicodedata
from collections.abc import Callable, Sequence
from contextlib import suppress
from dataclasses import dataclass
from typing import Literal, Protocol, cast
from uuid import UUID, uuid4

from sejong_ai_api.chat.classification import (
    ClassificationOutcome,
    SafeQuestion,
    classify_question,
)
from sejong_ai_api.chat.context import ChatContext, ContextTokenCodec
from sejong_ai_api.chat.grounding import evaluate_grounding
from sejong_ai_api.chat.idempotency import (
    ChatIdempotencyRepository,
    IdempotencyClaimStatus,
    IdempotencyConflictError,
    fingerprint_chat_request,
)
from sejong_ai_api.chat.response import (
    FollowupOptionId,
    build_fallback_response,
    build_followup_response,
    build_success_response,
)
from sejong_ai_api.chat.retrieval import (
    GroundingEvidence,
    GroundingEvidenceKind,
    TopicSelection,
    select_deterministic_topic,
    validate_semantic_selection,
)
from sejong_ai_api.chat.topic_catalog import (
    TopicCatalog,
    TopicCoverage,
    build_topic_catalog,
)
from sejong_ai_api.contracts.chat import (
    CHAT_RESPONSE_ADAPTER,
    AnswerMode,
    ChatRequest,
    FallbackResponse,
    FollowupResponse,
    SuccessResponse,
)
from sejong_ai_api.db.errors import DatabaseRuleError, DatabaseUnavailableError
from sejong_ai_api.db.models import (
    AnswerStatus,
    FallbackReason,
    Intent,
    InteractionWrite,
    InteractionWriteResult,
    KnowledgeRecord,
    OfficeRecord,
    Region,
)
from sejong_ai_api.llm.chat_contracts import (
    GroundedAnswerGenerator,
    GroundedChatOutcomeCode,
    GroundedChatResult,
    MaterializedChatAnswer,
)
from sejong_ai_api.llm.classifier_contracts import (
    ClassifierDecision,
    ClassifierRoute,
    PendingSlot,
)
from sejong_ai_api.llm.facts import (
    build_grounded_chat_request,
    materialize_grounded_answer,
)
from sejong_ai_api.privacy.redaction import redact_question

type ChatResult = SuccessResponse | FollowupResponse | FallbackResponse
type SupportedIntentValue = Literal[
    "MOVE_IN_RESIDENT_REGISTRATION",
    "CERTIFICATE_ISSUANCE",
    "BULKY_WASTE",
    "LOCAL_TAX_GENERAL",
]
type ContextualAction = Literal[
    "FEE",
    "REQUIRED_DOCUMENTS",
    "PROCESSING_TIME",
    "OFFICE",
    "ONLINE",
    "CHANGING_REGION",
]
_SUPPORTED_INTENT_ORDER = (
    Intent.MOVE_IN_RESIDENT_REGISTRATION,
    Intent.CERTIFICATE_ISSUANCE,
    Intent.BULKY_WASTE,
    Intent.LOCAL_TAX_GENERAL,
)
_SUPPORTED_INTENTS = frozenset(_SUPPORTED_INTENT_ORDER)
_FOLLOWUP_OPTIONS: tuple[
    Literal[
        "intent.move-in",
        "intent.certificate",
        "intent.bulky-waste",
        "intent.local-tax",
    ],
    ...,
] = (
    "intent.move-in",
    "intent.certificate",
    "intent.bulky-waste",
    "intent.local-tax",
)
_CERTIFICATE_FOLLOWUP_OPTIONS: tuple[FollowupOptionId, ...] = (
    "certificate.resident-copy",
    "certificate.resident-abstract",
    "certificate.copy-vs-abstract",
    "certificate.resident-register-inspection",
    "certificate.unmanned-kiosk",
)
_REGION_FOLLOWUP_OPTIONS: tuple[FollowupOptionId, ...] = (
    "region.areum",
    "region.dodam",
    "region.jochiwon",
)
_WASTE_ITEM_FOLLOWUP_OPTIONS: tuple[FollowupOptionId, ...] = ("waste.item.describe",)
_PROVIDER_HARD_WALL_SECONDS = 12.0
_CONTEXT_FACET_ROOTS: tuple[tuple[str, ContextualAction], ...] = (
    ("수수료", "FEE"),
    ("준비물", "REQUIRED_DOCUMENTS"),
    ("처리기간", "PROCESSING_TIME"),
    ("어디", "OFFICE"),
    ("온라인", "ONLINE"),
)
_CONTEXT_FACET_UTTERANCE_PATTERN = re.compile(
    r"(?P<facet>수수료|준비물|처리기간|어디|온라인)"
    r"(?:으로는|로는|에서는|에서|으로|로|은|는|이|가|서|도)?"
    r"(?:가능한가요|가능해요|인가요|하나요|되나요|돼요|가요|예요|요)?\Z"
)
_EXPLICIT_INTENT_TERMS = (
    "전입",
    "주민등록",
    "등본",
    "초본",
    "증명서",
    "대형폐기물",
    "폐기물",
    "지방세",
    "자동차세",
    "재산세",
    "주민세",
    "취득세",
)
_CONTEXT_REGION_CHANGE_TERMS = ("바꿔", "변경", "옮겨")
_APPROVED_OFFICE_CONTENT_TERMS = (
    "행정복지센터",
    "주민센터",
    "행정안전부",
    "정부24",
    "위택스",
    "국가법령정보센터",
    "담당기관",
    "출장소",
    "공단",
    "시청",
    "군청",
    "구청",
    "주민과",
    "정책과",
    "읍",
    "면",
    "동",
)
_APPROVED_ONLINE_CONTENT_TERMS = ("온라인", "인터넷")


class ChatRepository(Protocol):
    async def list_active_kb(self, intent: Intent) -> Sequence[KnowledgeRecord]: ...

    async def list_offices(self, region: Region, intent: Intent) -> Sequence[OfficeRecord]: ...

    async def record_interaction(self, event: InteractionWrite) -> InteractionWriteResult: ...

    async def record_civic_scope_gap(self, masked_question: str) -> None: ...


class QuestionClassifierPort(Protocol):
    async def classify(
        self,
        question: SafeQuestion,
        catalog: TopicCatalog,
    ) -> ClassifierDecision | None: ...


class ChatUnavailableError(Exception):
    """A value-free signal that no safe grounded response can be produced."""

    def __init__(self) -> None:
        super().__init__("CHAT_UNAVAILABLE")


@dataclass(frozen=True, slots=True)
class _ChatExecution:
    response: ChatResult
    interaction: InteractionWrite | None
    scope_gap_question: str | None = None


@dataclass(frozen=True, slots=True)
class FollowupPlan:
    intent: Intent
    pending_slot: PendingSlot
    options: tuple[str, ...]


@dataclass(slots=True)
class _GenerationAttemptState:
    started: bool = False

    def begin(self) -> bool:
        """Atomically mark this request-local attempt before the generator await."""

        if self.started:
            return False
        self.started = True
        return True


class ChatService:
    """Compose redaction, policy, retrieval, grounding, response and event gates."""

    def __init__(
        self,
        *,
        repository: ChatRepository,
        context_codec: ContextTokenCodec,
        request_id_factory: Callable[[], UUID],
        monotonic_ns: Callable[[], int],
        is_test: bool,
        idempotency_repository: ChatIdempotencyRepository | None = None,
        idempotency_secret: bytes | None = None,
        idempotency_claim_factory: Callable[[], UUID] = uuid4,
        answer_generator: GroundedAnswerGenerator | None = None,
        question_classifier: QuestionClassifierPort | None = None,
        topic_coverage: Sequence[TopicCoverage] = (),
    ) -> None:
        if not callable(request_id_factory) or not callable(monotonic_ns):
            raise TypeError("CHAT_SERVICE_DEPENDENCY_INVALID")
        if type(is_test) is not bool:
            raise TypeError("CHAT_SERVICE_DEPENDENCY_INVALID")
        if (idempotency_repository is None) is not (idempotency_secret is None):
            raise ValueError("IDEMPOTENCY_CONFIGURATION_INVALID")
        if idempotency_secret is not None and (
            type(idempotency_secret) is not bytes or len(idempotency_secret) < 32
        ):
            raise ValueError("IDEMPOTENCY_CONFIGURATION_INVALID")
        if not callable(idempotency_claim_factory):
            raise TypeError("CHAT_SERVICE_DEPENDENCY_INVALID")
        if not isinstance(topic_coverage, Sequence) or isinstance(
            topic_coverage, (str, bytes)
        ):
            raise TypeError("CHAT_SERVICE_DEPENDENCY_INVALID")
        if any(type(item) is not TopicCoverage for item in topic_coverage):
            raise TypeError("CHAT_SERVICE_DEPENDENCY_INVALID")
        self._repository = repository
        self._context_codec = context_codec
        self._request_id_factory = request_id_factory
        self._monotonic_ns = monotonic_ns
        self._is_test = is_test
        self._idempotency_repository = idempotency_repository
        self._idempotency_secret = idempotency_secret
        self._idempotency_claim_factory = idempotency_claim_factory
        self._answer_generator = answer_generator
        self._question_classifier = question_classifier
        self._topic_coverage = tuple(topic_coverage)

    async def answer(
        self,
        request: ChatRequest,
        *,
        request_id: UUID | None = None,
        idempotency_key: UUID | None = None,
    ) -> ChatResult:
        """Return one result, using the durable identity only when supplied."""

        if type(request) is not ChatRequest:
            raise TypeError("CHAT_REQUEST_REQUIRED")
        selected_request_id = request_id if request_id is not None else self._request_id_factory()
        if type(selected_request_id) is not UUID:
            raise TypeError("REQUEST_ID_FACTORY_INVALID")
        if idempotency_key is None:
            execution = await self._execute_once(request, request_id=selected_request_id)
            if execution.interaction is not None:
                await self._record_best_effort(execution.interaction)
            if execution.scope_gap_question is not None:
                await self._record_scope_gap_best_effort(execution.scope_gap_question)
            return execution.response
        if type(idempotency_key) is not UUID:
            raise TypeError("IDEMPOTENCY_KEY_INVALID")
        return await self._answer_idempotent(
            request,
            request_id=selected_request_id,
            idempotency_key=idempotency_key,
        )

    async def _execute_once(
        self,
        request: ChatRequest,
        *,
        request_id: UUID | None = None,
        allow_generation: bool = True,
        generation_attempt_state: _GenerationAttemptState | None = None,
    ) -> _ChatExecution:
        """Build one safe response and its optional persistence command."""

        if type(request) is not ChatRequest:
            raise TypeError("CHAT_REQUEST_REQUIRED")
        selected_request_id = request_id if request_id is not None else self._request_id_factory()
        if type(selected_request_id) is not UUID:
            raise TypeError("REQUEST_ID_FACTORY_INVALID")
        started_ns = self._read_monotonic_ns()
        provider_deadline = asyncio.get_running_loop().time() + _PROVIDER_HARD_WALL_SECONDS

        redaction = redact_question(request.question)
        if redaction.masked_text is None:
            return _ChatExecution(
                response=build_fallback_response(
                    request_id=selected_request_id,
                    intent=Intent.UNKNOWN,
                    reason="PRIVACY_UNRESOLVED",
                    office=None,
                ),
                interaction=None,
            )

        safe_question = SafeQuestion(redaction)
        prior_context = self._context_codec.read(request.context_token)
        selected_region = _selected_region(request.selected_region, prior_context)
        outcome = classify_question(safe_question)
        intent = outcome.intent
        intent_from_context = False
        contextual_action = _resolve_contextual_action(safe_question.text, prior_context)
        contextual_region = _contextual_region(safe_question.text, prior_context)
        region_changed_by_request = (
            prior_context is not None
            and request.selected_region is not None
            and request.selected_region != prior_context.selected_region
        )
        if contextual_region is not None:
            selected_region = contextual_region
            contextual_action = "CHANGING_REGION"
        elif region_changed_by_request:
            contextual_action = "CHANGING_REGION"
        if (
            outcome.followup_required
            and prior_context is not None
            and contextual_action is not None
        ):
            prior_intent = Intent(prior_context.last_intent)
            if prior_intent in _SUPPORTED_INTENTS:
                intent = prior_intent
                intent_from_context = True
        topic_changed = (
            prior_context is not None
            and intent in _SUPPORTED_INTENTS
            and Intent(prior_context.last_intent) in _SUPPORTED_INTENTS
            and Intent(prior_context.last_intent) is not intent
            and not intent_from_context
        )

        if outcome.fallback_reason is FallbackReason.OUT_OF_SCOPE:
            fallback_response = build_fallback_response(
                request_id=selected_request_id,
                intent=Intent.OUT_OF_SCOPE,
                reason="OUT_OF_SCOPE",
                office=None,
            )
            return _ChatExecution(response=fallback_response, interaction=None)

        if outcome.fallback_reason in {
            FallbackReason.PERSONAL_LOOKUP,
            FallbackReason.LEGAL_JUDGMENT,
        }:
            reason = cast(FallbackReason, outcome.fallback_reason)
            fallback_response = build_fallback_response(
                request_id=selected_request_id,
                intent=Intent.UNKNOWN,
                reason=cast(
                    Literal["PERSONAL_LOOKUP", "LEGAL_JUDGMENT"],
                    reason.value,
                ),
                office=None,
            )
            return _ChatExecution(response=fallback_response, interaction=None)

        if outcome.route is ClassifierRoute.NEEDS_FOLLOWUP and not intent_from_context:
            return self._build_followup_execution(
                request_id=selected_request_id,
                intent=intent,
                pending_slot=outcome.pending_slot,
                selected_region=selected_region,
                started_ns=started_ns,
                persist_event=True,
            )

        selection_outcome = outcome
        if intent_from_context:
            selection_outcome = ClassificationOutcome(
                intent=intent,
                followup_required=False,
                fallback_reason=None,
                route=ClassifierRoute.SUPPORTED,
            )
        selection_result = await self._select_topic(
            safe_question,
            outcome=selection_outcome,
            prior_context=prior_context,
            deadline=provider_deadline,
        )
        if selection_result is None:
            return self._build_followup_execution(
                request_id=selected_request_id,
                intent=Intent.UNKNOWN,
                selected_region=selected_region,
                pending_slot=None,
                started_ns=started_ns,
                persist_event=False,
            )

        selected_topic: TopicSelection | None = None
        if type(selection_result) is ClassifierDecision:
            decision = selection_result
            if decision.route is ClassifierRoute.NON_CIVIC:
                return _ChatExecution(
                    response=build_fallback_response(
                        request_id=selected_request_id,
                        intent=Intent.OUT_OF_SCOPE,
                        reason="OUT_OF_SCOPE",
                        office=None,
                    ),
                    interaction=None,
                )
            if decision.route is ClassifierRoute.CIVIC_SCOPE_GAP:
                return _ChatExecution(
                    response=build_fallback_response(
                        request_id=selected_request_id,
                        intent=Intent.OUT_OF_SCOPE,
                        reason="CIVIC_SCOPE_GAP",
                        office=None,
                    ),
                    interaction=None,
                    scope_gap_question=safe_question.text,
                )
            if decision.route is ClassifierRoute.NEEDS_FOLLOWUP:
                return self._build_followup_execution(
                    request_id=selected_request_id,
                    intent=decision.intent or Intent.UNKNOWN,
                    pending_slot=decision.pending_slot,
                    selected_region=selected_region,
                    started_ns=started_ns,
                    persist_event=True,
                )
            if decision.route is ClassifierRoute.NO_TOPIC_MATCH and decision.intent is not None:
                intent = decision.intent
                grounding = evaluate_grounding(safe_question, intent, None)
            else:
                return self._build_followup_execution(
                    request_id=selected_request_id,
                    intent=Intent.UNKNOWN,
                    pending_slot=None,
                    selected_region=selected_region,
                    started_ns=started_ns,
                    persist_event=False,
                )
        elif type(selection_result) is TopicSelection:
            selected_topic = selection_result
            intent = selection_result.topic.record.category
            grounding = evaluate_grounding(
                safe_question,
                intent,
                selection_result,
            )
        else:
            return self._build_followup_execution(
                request_id=selected_request_id,
                intent=Intent.UNKNOWN,
                pending_slot=None,
                selected_region=selected_region,
                started_ns=started_ns,
                persist_event=False,
            )
        if not grounding.is_grounded or grounding.record is None:
            office = await self._load_optional_office(selected_region, intent)
            fallback_response = build_fallback_response(
                request_id=selected_request_id,
                intent=intent,
                reason="INSUFFICIENT_GROUNDING",
                office=office,
            )
            interaction = self._build_interaction(
                request_id=selected_request_id,
                intent=intent,
                answer_status=AnswerStatus.FALLBACK,
                fallback_reason=FallbackReason.INSUFFICIENT_GROUNDING,
                used_source_ids=(),
                selected_region=selected_region,
                office=office,
                masked_question=safe_question.text,
                started_ns=started_ns,
            )
            return _ChatExecution(response=fallback_response, interaction=interaction)

        if contextual_action == "OFFICE" and selected_region is None:
            return self._build_followup_execution(
                request_id=selected_request_id,
                intent=intent,
                pending_slot=PendingSlot.REGION,
                selected_region=None,
                started_ns=started_ns,
                persist_event=True,
                topic_id=grounding.record.public_id,
            )

        office = await self._load_optional_office(selected_region, intent)
        token = self._issue_context(
            intent=intent,
            selected_region=selected_region,
            answer_status="SUCCESS",
            topic_id=grounding.record.public_id,
            dialog_act=(
                "CHANGING_TOPIC"
                if topic_changed
                else ("CHANGING_REGION" if contextual_action == "CHANGING_REGION" else "ANSWERED")
            ),
        )
        answer_mode: AnswerMode = "TEMPLATE"
        materialized: MaterializedChatAnswer | None = None
        if allow_generation and self._answer_generator is not None:
            try:
                grounded_request = build_grounded_chat_request(
                    masked_question=safe_question.text,
                    intent=intent,
                    record=grounding.record,
                )
                if generation_attempt_state is None or generation_attempt_state.begin():
                    async with asyncio.timeout_at(provider_deadline):
                        result = await self._answer_generator.generate(grounded_request)
                else:
                    result = None
                if (
                    type(result) is GroundedChatResult
                    and result.code is GroundedChatOutcomeCode.SUCCESS
                    and result.draft is not None
                ):
                    materialized = materialize_grounded_answer(
                        grounded_request,
                        result.draft,
                    )
                    if materialized is not None:
                        answer_mode = "GENERATED"
            except Exception:
                materialized = None
                answer_mode = "TEMPLATE"
        success_response = build_success_response(
            request_id=selected_request_id,
            record=grounding.record,
            office=office,
            confidence=_confidence(selected_topic),
            context_token=token,
            answer_mode=answer_mode,
            answer=materialized,
        )
        interaction = self._build_interaction(
            request_id=selected_request_id,
            intent=intent,
            answer_status=AnswerStatus.SUCCESS,
            fallback_reason=None,
            used_source_ids=(grounding.record.public_id,),
            selected_region=selected_region,
            office=office,
            masked_question=None,
            started_ns=started_ns,
        )
        return _ChatExecution(response=success_response, interaction=interaction)

    async def _answer_idempotent(
        self,
        request: ChatRequest,
        *,
        request_id: UUID,
        idempotency_key: UUID,
    ) -> ChatResult:
        repository = self._idempotency_repository
        secret = self._idempotency_secret
        if repository is None or secret is None:
            raise ChatUnavailableError()
        claim_token = self._idempotency_claim_factory()
        if type(claim_token) is not UUID or claim_token == request_id:
            raise ChatUnavailableError()
        request_fingerprint = fingerprint_chat_request(request, secret=secret)
        try:
            claim = await repository.claim_chat_idempotency(
                idempotency_key=idempotency_key,
                request_fingerprint=request_fingerprint,
                claim_token=claim_token,
            )
        except (DatabaseRuleError, DatabaseUnavailableError):
            raise ChatUnavailableError() from None

        if claim.status is IdempotencyClaimStatus.CONFLICT:
            raise IdempotencyConflictError()
        if claim.status is IdempotencyClaimStatus.IN_PROGRESS:
            return (
                await self._execute_once(
                    request,
                    request_id=request_id,
                    allow_generation=False,
                )
            ).response
        if claim.status is IdempotencyClaimStatus.COMPLETED:
            payload = dict(cast(dict[str, object], claim.response_payload))
            payload["request_id"] = str(request_id)
            payload["context_token"] = None
            try:
                replay = CHAT_RESPONSE_ADAPTER.validate_json(
                    json.dumps(
                        payload,
                        ensure_ascii=False,
                        allow_nan=False,
                        separators=(",", ":"),
                    )
                )
            except (TypeError, ValueError):
                raise ChatUnavailableError() from None
            if replay.answer_status in {"SUCCESS", "FOLLOWUP"}:
                prior_context = self._context_codec.read(request.context_token)
                selected_region = _selected_region(request.selected_region, prior_context)
                payload["context_token"] = self._issue_context(
                    intent=Intent(replay.intent),
                    selected_region=selected_region,
                    answer_status=replay.answer_status,
                    dialog_act=("ANSWERED" if replay.answer_status == "SUCCESS" else "ASKING_SLOT"),
                )
                try:
                    return CHAT_RESPONSE_ADAPTER.validate_json(
                        json.dumps(
                            payload,
                            ensure_ascii=False,
                            allow_nan=False,
                            separators=(",", ":"),
                        )
                    )
                except (TypeError, ValueError):
                    raise ChatUnavailableError() from None
            return replay
        if claim.status is not IdempotencyClaimStatus.ACQUIRED:
            raise ChatUnavailableError()

        generation_attempt_state = _GenerationAttemptState()
        try:
            execution = await self._execute_once(
                request,
                request_id=request_id,
                generation_attempt_state=generation_attempt_state,
            )
        except Exception:
            if generation_attempt_state.started:
                raise ChatUnavailableError() from None
            with suppress(Exception):
                await repository.abandon_chat_idempotency(
                    idempotency_key=idempotency_key,
                    request_fingerprint=request_fingerprint,
                    claim_token=claim_token,
                )
            raise

        safe_payload = cast(
            dict[str, object],
            execution.response.model_dump(
                mode="json",
                exclude={"request_id", "context_token"},
            ),
        )
        try:
            await repository.commit_chat_idempotency(
                idempotency_key=idempotency_key,
                request_fingerprint=request_fingerprint,
                claim_token=claim_token,
                response_payload=safe_payload,
                interaction=execution.interaction,
            )
        except (DatabaseRuleError, DatabaseUnavailableError):
            raise ChatUnavailableError() from None
        if execution.scope_gap_question is not None:
            await self._record_scope_gap_best_effort(execution.scope_gap_question)
        return execution.response

    async def _load_active_snapshot(
        self,
        intents: Sequence[Intent],
    ) -> tuple[KnowledgeRecord, ...]:
        if not isinstance(intents, Sequence) or isinstance(intents, (str, bytes)):
            raise TypeError("SUPPORTED_INTENT_SEQUENCE_REQUIRED")
        selected_intents = tuple(intents)
        if (
            not selected_intents
            or len(set(selected_intents)) != len(selected_intents)
            or any(
                type(intent) is not Intent or intent not in _SUPPORTED_INTENTS
                for intent in selected_intents
            )
        ):
            raise ValueError("SUPPORTED_INTENT_SEQUENCE_REQUIRED")
        try:
            snapshot_parts = await asyncio.gather(
                *(
                    self._repository.list_active_kb(intent)
                    for intent in selected_intents
                )
            )
        except DatabaseUnavailableError:
            raise ChatUnavailableError() from None

        snapshot: list[KnowledgeRecord] = []
        for expected_intent, records in zip(selected_intents, snapshot_parts, strict=True):
            if not isinstance(records, Sequence) or isinstance(records, (str, bytes)):
                raise ChatUnavailableError()
            for record in records:
                if type(record) is not KnowledgeRecord or record.category is not expected_intent:
                    raise ChatUnavailableError()
                snapshot.append(record)
        return tuple(sorted(snapshot, key=lambda record: record.public_id))

    async def _select_topic(
        self,
        question: SafeQuestion,
        *,
        outcome: ClassificationOutcome,
        prior_context: ChatContext | None,
        deadline: float,
    ) -> TopicSelection | FollowupPlan | ClassifierDecision | None:
        if type(question) is not SafeQuestion or type(outcome) is not ClassificationOutcome:
            raise TypeError("TOPIC_SELECTION_INPUT_INVALID")
        if prior_context is not None and type(prior_context) is not ChatContext:
            raise TypeError("TOPIC_SELECTION_INPUT_INVALID")
        if type(deadline) is not float:
            raise TypeError("TOPIC_SELECTION_INPUT_INVALID")

        known_intent = outcome.intent if outcome.intent in _SUPPORTED_INTENTS else None
        selected_intents = (
            _SUPPORTED_INTENT_ORDER if outcome.needs_provider else (known_intent,)
        )
        if known_intent is None and not outcome.needs_provider:
            return None
        snapshot = await self._load_active_snapshot(
            cast(Sequence[Intent], selected_intents)
        )
        try:
            catalog = build_topic_catalog(snapshot, self._topic_coverage)
        except (TypeError, ValueError):
            return None

        if known_intent is not None:
            deterministic = select_deterministic_topic(
                question,
                known_intent,
                catalog,
            )
            if deterministic is not None:
                return deterministic

            contextual_action = _resolve_contextual_action(
                question.text,
                prior_context,
            )
            if (
                prior_context is not None
                and prior_context.last_intent == known_intent.value
                and prior_context.topic_id is not None
                and contextual_action is not None
            ):
                contextual_topic = catalog.find(prior_context.topic_id)
                if contextual_topic is None:
                    return ClassifierDecision(
                        route=ClassifierRoute.NO_TOPIC_MATCH,
                        intent=known_intent,
                        topic_id=None,
                        coverage_id=None,
                        pending_slot=None,
                    )
                if (
                    contextual_action == "CHANGING_REGION"
                    or _record_supports_context_facet(
                        contextual_topic.record,
                        contextual_action,
                    )
                ):
                    return TopicSelection(
                        topic=contextual_topic,
                        evidence=GroundingEvidence(
                            kind=GroundingEvidenceKind.VALIDATED_CONTEXT_FACET,
                            topic_id=contextual_topic.record.public_id,
                            coverage_id=contextual_topic.coverage.coverage_id,
                        ),
                    )

        classifier = self._question_classifier
        if classifier is None or not catalog.provider_eligible:
            return None
        try:
            async with asyncio.timeout_at(deadline):
                decision = await classifier.classify(question, catalog)
        except Exception:
            return None
        if type(decision) is not ClassifierDecision:
            return None
        if decision.route is ClassifierRoute.SUPPORTED:
            return validate_semantic_selection(decision, catalog)
        if (
            known_intent is not None
            and decision.route
            in {
                ClassifierRoute.NO_TOPIC_MATCH,
                ClassifierRoute.NEEDS_FOLLOWUP,
            }
            and decision.intent is not known_intent
        ):
            return None
        return decision

    def _build_followup_execution(
        self,
        *,
        request_id: UUID,
        intent: Intent,
        pending_slot: PendingSlot | None,
        selected_region: Region | None,
        started_ns: int,
        persist_event: bool,
        topic_id: str | None = None,
    ) -> _ChatExecution:
        option_ids = _followup_options(pending_slot)
        token = self._issue_context(
            intent=intent,
            selected_region=selected_region,
            answer_status="FOLLOWUP",
            pending_slot=pending_slot,
            dialog_act="ASKING_SLOT",
            topic_id=topic_id,
        )
        response = build_followup_response(
            request_id=request_id,
            intent=intent,
            confidence=None,
            option_ids=option_ids,
            context_token=token,
        )
        interaction = (
            self._build_interaction(
                request_id=request_id,
                intent=intent,
                answer_status=AnswerStatus.FOLLOWUP,
                fallback_reason=None,
                used_source_ids=(),
                selected_region=selected_region,
                office=None,
                masked_question=None,
                started_ns=started_ns,
            )
            if persist_event
            else None
        )
        return _ChatExecution(response=response, interaction=interaction)

    async def _load_optional_office(
        self,
        selected_region: Region | None,
        intent: Intent,
    ) -> OfficeRecord | None:
        if selected_region is None or intent not in _SUPPORTED_INTENTS:
            return None
        try:
            offices = await self._repository.list_offices(selected_region, intent)
        except DatabaseUnavailableError:
            return None
        return offices[0] if offices else None

    def _issue_context(
        self,
        *,
        intent: Intent,
        selected_region: Region | None,
        answer_status: Literal["SUCCESS", "FOLLOWUP"],
        dialog_act: Literal[
            "ANSWERED",
            "ASKING_SLOT",
            "CHANGING_REGION",
            "CHANGING_TOPIC",
        ],
        topic_id: str | None = None,
        pending_slot: PendingSlot | None = None,
    ) -> str:
        context_pending_slot: Literal[
            "CERTIFICATE_KIND",
            "REGION",
            "WASTE_ITEM",
        ] | None = None
        if pending_slot is PendingSlot.CERTIFICATE_KIND:
            context_pending_slot = "CERTIFICATE_KIND"
        elif pending_slot is PendingSlot.REGION:
            context_pending_slot = "REGION"
        elif pending_slot is PendingSlot.WASTE_ITEM:
            context_pending_slot = "WASTE_ITEM"
        return self._context_codec.issue(
            last_intent=intent.value,
            selected_region=selected_region.value if selected_region is not None else None,
            answer_status=answer_status,
            topic_id=topic_id,
            pending_slot=context_pending_slot,
            dialog_act=dialog_act,
        )

    def _build_interaction(
        self,
        *,
        request_id: UUID,
        intent: Intent,
        answer_status: AnswerStatus,
        fallback_reason: FallbackReason | None,
        used_source_ids: tuple[str, ...],
        selected_region: Region | None,
        office: OfficeRecord | None,
        masked_question: str | None,
        started_ns: int,
    ) -> InteractionWrite:
        return InteractionWrite(
            request_id=request_id,
            intent=intent,
            answer_status=answer_status,
            fallback_reason=fallback_reason,
            used_source_ids=used_source_ids,
            response_time_ms=max(0, (self._read_monotonic_ns() - started_ns) // 1_000_000),
            selected_region=selected_region,
            routed_office_public_id=office.public_id if office is not None else None,
            is_test=self._is_test,
            masked_question=masked_question,
        )

    async def _record_best_effort(self, event: InteractionWrite) -> None:
        try:
            await self._repository.record_interaction(event)
        except DatabaseUnavailableError:
            return

    async def _record_scope_gap_best_effort(self, masked_question: str) -> None:
        try:
            await self._repository.record_civic_scope_gap(masked_question)
        except Exception:
            return

    def _read_monotonic_ns(self) -> int:
        value = self._monotonic_ns()
        if type(value) is not int or value < 0:
            raise TypeError("MONOTONIC_CLOCK_INVALID")
        return value


def _selected_region(selected: str | None, context: ChatContext | None) -> Region | None:
    if selected is not None:
        return Region(selected)
    if context is None:
        return None
    return Region(context.selected_region) if context.selected_region is not None else None


def _compact_context_input(value: str) -> str:
    return re.sub(
        r"[^0-9a-z가-힣]",
        "",
        unicodedata.normalize("NFKC", value).casefold(),
    )


def _resolve_contextual_action(
    value: str,
    context: ChatContext | None,
) -> ContextualAction | None:
    if context is None:
        return None
    compact = _compact_context_input(value)
    if any(term in compact for term in _EXPLICIT_INTENT_TERMS):
        return None
    if _contextual_region(value, context) is not None:
        return "CHANGING_REGION"
    match = _CONTEXT_FACET_UTTERANCE_PATTERN.fullmatch(compact)
    if match is None:
        return None
    facet_root = match.group("facet")
    return next(
        action
        for root, action in _CONTEXT_FACET_ROOTS
        if root == facet_root
    )


def _record_supports_context_facet(
    record: KnowledgeRecord,
    action: ContextualAction,
) -> bool:
    if type(record) is not KnowledgeRecord:
        return False
    if action == "FEE":
        return record.fee is not None
    if action == "REQUIRED_DOCUMENTS":
        return bool(record.required_documents)
    if action == "PROCESSING_TIME":
        return record.processing_time is not None
    if action == "OFFICE":
        department = _compact_context_input(record.department)
        return any(term in department for term in _APPROVED_OFFICE_CONTENT_TERMS)
    if action == "ONLINE":
        approved_content = _compact_context_input(
            " ".join(
                (
                    record.service_name,
                    record.answer_summary,
                    *record.procedure_steps,
                    *record.required_documents,
                    record.processing_time or "",
                    record.fee or "",
                    record.department,
                    record.caution or "",
                    *record.question_examples,
                )
            )
        )
        return any(term in approved_content for term in _APPROVED_ONLINE_CONTENT_TERMS)
    return False


def _contextual_region(
    value: str,
    context: ChatContext | None,
) -> Region | None:
    if context is None:
        return None
    compact = re.sub(
        r"[^0-9a-z가-힣]",
        "",
        unicodedata.normalize("NFKC", value).casefold(),
    )
    selected = next(
        (region for region in Region if region.value in compact),
        None,
    )
    if selected is None:
        return None
    if context.pending_slot == "REGION" or any(
        term in compact for term in _CONTEXT_REGION_CHANGE_TERMS
    ):
        return selected
    return None


def _confidence(selection: TopicSelection | None) -> float:
    if selection is None:
        raise ValueError("TOPIC_SELECTION_REQUIRED")
    if selection.evidence.kind is GroundingEvidenceKind.EXACT_APPROVED_EXAMPLE:
        return 0.99
    if selection.evidence.kind is GroundingEvidenceKind.UNIQUE_LEXICAL_MATCH:
        return min(0.95, 0.7 + len(selection.evidence.matched_tokens) * 0.05)
    return 0.9


def _followup_options(
    pending_slot: PendingSlot | None,
) -> tuple[FollowupOptionId, ...]:
    if pending_slot is PendingSlot.CERTIFICATE_KIND:
        return _CERTIFICATE_FOLLOWUP_OPTIONS
    if pending_slot is PendingSlot.REGION:
        return _REGION_FOLLOWUP_OPTIONS
    if pending_slot is PendingSlot.WASTE_ITEM:
        return _WASTE_ITEM_FOLLOWUP_OPTIONS
    return cast(tuple[FollowupOptionId, ...], _FOLLOWUP_OPTIONS)


__all__ = ["ChatRepository", "ChatResult", "ChatService", "ChatUnavailableError"]
