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

from sejong_ai_api.chat.classification import SafeQuestion, classify_question
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
from sejong_ai_api.chat.retrieval import RankedKnowledge, rank_active_knowledge
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
_SUPPORTED_INTENTS = frozenset(
    {
        Intent.MOVE_IN_RESIDENT_REGISTRATION,
        Intent.CERTIFICATE_ISSUANCE,
        Intent.BULKY_WASTE,
        Intent.LOCAL_TAX_GENERAL,
    }
)
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
_WASTE_ITEM_FOLLOWUP_OPTIONS: tuple[FollowupOptionId, ...] = (
    "waste.item.describe",
)
_PROVIDER_HARD_WALL_SECONDS = 12.0
_CONTEXT_DETAIL_TERMS = (
    "준비물",
    "서류",
    "수수료",
    "비용",
    "기간",
    "처리시간",
    "어디",
    "방문",
    "온라인",
    "신청",
    "발급",
    "배출",
    "납부",
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


class ChatRepository(Protocol):
    async def list_active_kb(self, intent: Intent) -> Sequence[KnowledgeRecord]: ...

    async def list_offices(self, region: Region, intent: Intent) -> Sequence[OfficeRecord]: ...

    async def record_interaction(self, event: InteractionWrite) -> InteractionWriteResult: ...

    async def record_civic_scope_gap(self, masked_question: str) -> None: ...


class QuestionClassifierPort(Protocol):
    async def classify(self, question: SafeQuestion) -> ClassifierDecision | None: ...


class ChatUnavailableError(Exception):
    """A value-free signal that no safe grounded response can be produced."""

    def __init__(self) -> None:
        super().__init__("CHAT_UNAVAILABLE")


@dataclass(frozen=True, slots=True)
class _ChatExecution:
    response: ChatResult
    interaction: InteractionWrite | None
    scope_gap_question: str | None = None


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
        if (
            outcome.followup_required
            and prior_context is not None
            and _is_contextual_followup(safe_question.text)
        ):
            prior_intent = Intent(prior_context.last_intent)
            if prior_intent in _SUPPORTED_INTENTS:
                intent = prior_intent
                intent_from_context = True

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

        pending_slot = outcome.pending_slot
        if outcome.needs_provider and not intent_from_context:
            decision = await self._classify_best_effort(
                safe_question,
                deadline=provider_deadline,
            )
            if decision is None:
                return self._build_followup_execution(
                    request_id=selected_request_id,
                    intent=Intent.UNKNOWN,
                    pending_slot=None,
                    selected_region=selected_region,
                    started_ns=started_ns,
                    persist_event=False,
                )
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
            if decision.intent is None:
                return self._build_followup_execution(
                    request_id=selected_request_id,
                    intent=Intent.UNKNOWN,
                    pending_slot=None,
                    selected_region=selected_region,
                    started_ns=started_ns,
                    persist_event=False,
                )
            intent = decision.intent
            pending_slot = decision.pending_slot
            if decision.route is ClassifierRoute.NEEDS_FOLLOWUP:
                return self._build_followup_execution(
                    request_id=selected_request_id,
                    intent=intent,
                    pending_slot=pending_slot,
                    selected_region=selected_region,
                    started_ns=started_ns,
                    persist_event=True,
                )

        if outcome.route is ClassifierRoute.NEEDS_FOLLOWUP and not intent_from_context:
            return self._build_followup_execution(
                request_id=selected_request_id,
                intent=intent,
                pending_slot=pending_slot,
                selected_region=selected_region,
                started_ns=started_ns,
                persist_event=True,
            )

        if intent is Intent.UNKNOWN:
            return self._build_followup_execution(
                request_id=selected_request_id,
                intent=Intent.UNKNOWN,
                selected_region=selected_region,
                pending_slot=None,
                started_ns=started_ns,
                persist_event=False,
            )

        ranked = await self._ranked_knowledge(safe_question, intent)
        top = ranked[0] if ranked else None
        grounding = evaluate_grounding(
            safe_question,
            intent,
            top.record if top is not None else None,
            allow_contextual_detail=intent_from_context,
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

        office = await self._load_optional_office(selected_region, intent)
        token = self._issue_context(
            intent=intent,
            selected_region=selected_region,
            answer_status="SUCCESS",
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
            confidence=_confidence(top),
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

    async def _classify_best_effort(
        self,
        question: SafeQuestion,
        *,
        deadline: float,
    ) -> ClassifierDecision | None:
        classifier = self._question_classifier
        if classifier is None:
            return None
        try:
            async with asyncio.timeout_at(deadline):
                decision = await classifier.classify(question)
        except Exception:
            return None
        return decision if type(decision) is ClassifierDecision else None

    def _build_followup_execution(
        self,
        *,
        request_id: UUID,
        intent: Intent,
        pending_slot: PendingSlot | None,
        selected_region: Region | None,
        started_ns: int,
        persist_event: bool,
    ) -> _ChatExecution:
        option_ids = _followup_options(pending_slot)
        token = self._issue_context(
            intent=intent,
            selected_region=selected_region,
            answer_status="FOLLOWUP",
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

    async def _ranked_knowledge(
        self,
        question: SafeQuestion,
        intent: Intent,
    ) -> tuple[RankedKnowledge, ...]:
        try:
            records = await self._repository.list_active_kb(intent)
        except DatabaseUnavailableError:
            raise ChatUnavailableError() from None
        return rank_active_knowledge(question, intent, records)

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
    ) -> str:
        return self._context_codec.issue(
            last_intent=intent.value,
            selected_region=selected_region.value if selected_region is not None else None,
            answer_status=answer_status,
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


def _is_contextual_followup(value: str) -> bool:
    compact = re.sub(
        r"[^0-9a-z가-힣]",
        "",
        unicodedata.normalize("NFKC", value).casefold(),
    )
    return any(term in compact for term in _CONTEXT_DETAIL_TERMS) and not any(
        term in compact for term in _EXPLICIT_INTENT_TERMS
    )


def _confidence(item: RankedKnowledge | None) -> float:
    if item is None:
        raise ValueError("RANKED_KNOWLEDGE_REQUIRED")
    if item.exact_question_match:
        return 0.99
    overlap = item.service_or_example_overlap + item.procedure_document_overlap
    return min(0.95, 0.7 + overlap * 0.05)


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
