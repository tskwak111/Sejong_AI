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
_DOMAIN_FOLLOWUP_OPTIONS = (
    "전입·주민등록",
    "증명서 발급",
    "대형폐기물",
    "지방세 일반 안내",
)
_REGION_FOLLOWUP_OPTIONS = ("아름동", "도담동", "조치원읍")
_WASTE_ITEM_FOLLOWUP_OPTIONS = ("버리려는 물품을 적어 주세요",)
_TOPIC_FOLLOWUP_ORDER: dict[Intent, tuple[str, ...]] = {
    Intent.MOVE_IN_RESIDENT_REGISTRATION: (
        "KB-MOVE-01",
        "KB-MOVE-02",
        "KB-MOVE-03",
        "KB-MOVE-04",
    ),
    Intent.CERTIFICATE_ISSUANCE: (
        "KB-CERT-02",
        "KB-CERT-03",
        "KB-CERT-01",
    ),
    Intent.BULKY_WASTE: (
        "KB-WASTE-01",
        "KB-WASTE-02",
        "KB-WASTE-03",
        "KB-WASTE-04",
        "KB-WASTE-05",
    ),
    Intent.LOCAL_TAX_GENERAL: (
        "KB-TAX-01",
        "KB-TAX-02",
        "KB-TAX-03",
        "KB-TAX-04",
        "KB-TAX-05",
    ),
}
_CERTIFICATE_SHORT_LABELS = {
    "KB-CERT-02": "주민등록등본 발급",
    "KB-CERT-03": "주민등록초본 발급",
    "KB-CERT-01": "등본과 초본의 차이",
}
_GENERIC_TOPIC_CHOICE_UTTERANCES: dict[Intent, frozenset[str]] = {
    Intent.MOVE_IN_RESIDENT_REGISTRATION: frozenset(
        {
            "전입주민등록안내",
            "전입신고일반안내",
            "주민등록일반안내",
        }
    ),
    Intent.BULKY_WASTE: frozenset(
        {
            "대형폐기물",
            "대형폐기물안내",
            "대형폐기물일반안내",
        }
    ),
    Intent.LOCAL_TAX_GENERAL: frozenset(
        {
            "지방세",
            "지방세안내",
            "지방세일반안내",
            "재산세일반안내",
        }
    ),
}
_UNSUPPORTED_WASTE_TERMS = ("냉장고", "폐가전")
_UNSUPPORTED_WASTE_DETAIL_TERMS = ("전용수거", "수거")
_UNSUPPORTED_TAX_DETAIL_TERMS = ("세율", "감면", "부과기준")
_WASTE_CANCEL_UTTERANCE_PATTERN = re.compile(
    r"취소(?:하려면|하려고요|하고싶어요|할래요|는요|요)?\Z"
)
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

    def __post_init__(self) -> None:
        if (
            type(self.intent) is not Intent
            or type(self.pending_slot) is not PendingSlot
            or type(self.options) is not tuple
            or not 1 <= len(self.options) <= 5
            or len(set(self.options)) != len(self.options)
            or any(
                type(option) is not str or not option or option.strip() != option
                for option in self.options
            )
        ):
            raise ValueError("FOLLOWUP_PLAN_INVALID")
        if self.pending_slot is PendingSlot.DOMAIN:
            if self.intent is not Intent.UNKNOWN:
                raise ValueError("FOLLOWUP_PLAN_INVALID")
            return
        if self.intent not in _SUPPORTED_INTENTS:
            raise ValueError("FOLLOWUP_PLAN_INVALID")
        if (
            self.pending_slot is PendingSlot.CERTIFICATE_KIND
            and self.intent is not Intent.CERTIFICATE_ISSUANCE
        ):
            raise ValueError("FOLLOWUP_PLAN_INVALID")
        if self.pending_slot is PendingSlot.WASTE_ITEM and self.intent is not Intent.BULKY_WASTE:
            raise ValueError("FOLLOWUP_PLAN_INVALID")


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
        if not isinstance(topic_coverage, Sequence) or isinstance(topic_coverage, (str, bytes)):
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
                plan=_domain_followup_plan(),
                selected_region=selected_region,
                started_ns=started_ns,
                persist_event=False,
            )

        selected_topic: TopicSelection | None = None
        if type(selection_result) is FollowupPlan:
            return self._build_followup_execution(
                request_id=selected_request_id,
                plan=selection_result,
                selected_region=selected_region,
                started_ns=started_ns,
                persist_event=True,
            )
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
                    plan=_domain_followup_plan(),
                    selected_region=selected_region,
                    started_ns=started_ns,
                    persist_event=False,
                )
            if decision.route is ClassifierRoute.NO_TOPIC_MATCH and decision.intent is not None:
                intent = decision.intent
                grounding = evaluate_grounding(safe_question, intent, None)
            else:
                return self._build_followup_execution(
                    request_id=selected_request_id,
                    plan=_domain_followup_plan(),
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
                plan=_domain_followup_plan(),
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
                plan=FollowupPlan(
                    intent=intent,
                    pending_slot=PendingSlot.REGION,
                    options=_REGION_FOLLOWUP_OPTIONS,
                ),
                selected_region=None,
                started_ns=started_ns,
                persist_event=True,
                topic_id=grounding.record.public_id,
            )

        office = await self._load_optional_office(selected_region, intent)
        context_changed_topic = (
            prior_context is not None
            and prior_context.topic_id is not None
            and prior_context.topic_id != grounding.record.public_id
        )
        token = self._issue_context(
            intent=intent,
            selected_region=selected_region,
            answer_status="SUCCESS",
            topic_id=grounding.record.public_id,
            dialog_act=(
                "CHANGING_TOPIC"
                if topic_changed or context_changed_topic
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
                pending_slot = (
                    None
                    if replay.answer_status == "SUCCESS"
                    else _replayed_followup_pending_slot(replay)
                )
                payload["context_token"] = self._issue_context(
                    intent=Intent(replay.intent),
                    selected_region=selected_region,
                    answer_status=replay.answer_status,
                    pending_slot=pending_slot,
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
                *(self._repository.list_active_kb(intent) for intent in selected_intents)
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

        unsupported_detail_intent = _unsupported_detail_intent(question.text)
        known_intent = (
            unsupported_detail_intent
            if unsupported_detail_intent is not None
            else (outcome.intent if outcome.intent in _SUPPORTED_INTENTS else None)
        )
        selected_intents = (
            _SUPPORTED_INTENT_ORDER
            if outcome.needs_provider and unsupported_detail_intent is None
            else (known_intent,)
        )
        if known_intent is None and not outcome.needs_provider:
            return None
        snapshot = await self._load_active_snapshot(cast(Sequence[Intent], selected_intents))
        try:
            catalog = build_topic_catalog(snapshot, self._topic_coverage)
        except (TypeError, ValueError):
            return None

        if unsupported_detail_intent is not None:
            return ClassifierDecision(
                route=ClassifierRoute.NO_TOPIC_MATCH,
                intent=unsupported_detail_intent,
                topic_id=None,
                coverage_id=None,
                pending_slot=None,
            )

        if outcome.route is ClassifierRoute.NEEDS_FOLLOWUP:
            if outcome.pending_slot is None:
                return None
            return _followup_plan_from_catalog(
                outcome.intent,
                outcome.pending_slot,
                catalog,
            )

        context_topic_change = _select_context_topic_change(
            question.text,
            prior_context,
            catalog,
        )
        if context_topic_change is not None:
            return context_topic_change

        if known_intent is not None:
            if _is_generic_topic_choice(question.text, known_intent):
                return _followup_plan_from_catalog(
                    known_intent,
                    PendingSlot.TOPIC_CHOICE,
                    catalog,
                )
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
                if contextual_action == "CHANGING_REGION" or _record_supports_context_facet(
                    contextual_topic.record,
                    contextual_action,
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
        if decision.route is ClassifierRoute.NEEDS_FOLLOWUP:
            if decision.pending_slot is None:
                return None
            return _followup_plan_from_catalog(
                decision.intent or Intent.UNKNOWN,
                decision.pending_slot,
                catalog,
            )
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
        plan: FollowupPlan,
        selected_region: Region | None,
        started_ns: int,
        persist_event: bool,
        topic_id: str | None = None,
    ) -> _ChatExecution:
        token = self._issue_context(
            intent=plan.intent,
            selected_region=selected_region,
            answer_status="FOLLOWUP",
            pending_slot=plan.pending_slot,
            dialog_act="ASKING_SLOT",
            topic_id=topic_id,
        )
        response = build_followup_response(
            request_id=request_id,
            intent=plan.intent,
            confidence=None,
            options=plan.options,
            context_token=token,
        )
        interaction = (
            self._build_interaction(
                request_id=request_id,
                intent=plan.intent,
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
        context_pending_slot: (
            Literal[
                "DOMAIN",
                "TOPIC_CHOICE",
                "CERTIFICATE_KIND",
                "REGION",
                "WASTE_ITEM",
            ]
            | None
        ) = None
        if pending_slot is PendingSlot.DOMAIN:
            context_pending_slot = "DOMAIN"
        elif pending_slot is PendingSlot.TOPIC_CHOICE:
            context_pending_slot = "TOPIC_CHOICE"
        elif pending_slot is PendingSlot.CERTIFICATE_KIND:
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
    return next(action for root, action in _CONTEXT_FACET_ROOTS if root == facet_root)


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


def _domain_followup_plan() -> FollowupPlan:
    return FollowupPlan(
        intent=Intent.UNKNOWN,
        pending_slot=PendingSlot.DOMAIN,
        options=_DOMAIN_FOLLOWUP_OPTIONS,
    )


def _followup_plan_from_catalog(
    intent: Intent,
    pending_slot: PendingSlot,
    catalog: TopicCatalog,
) -> FollowupPlan | None:
    if pending_slot is PendingSlot.DOMAIN:
        return _domain_followup_plan()
    if pending_slot is PendingSlot.REGION and intent in _SUPPORTED_INTENTS:
        return FollowupPlan(intent, pending_slot, _REGION_FOLLOWUP_OPTIONS)
    if pending_slot is PendingSlot.WASTE_ITEM and intent is Intent.BULKY_WASTE:
        return FollowupPlan(intent, pending_slot, _WASTE_ITEM_FOLLOWUP_OPTIONS)
    if pending_slot not in {
        PendingSlot.TOPIC_CHOICE,
        PendingSlot.CERTIFICATE_KIND,
    }:
        return None
    if intent not in _SUPPORTED_INTENTS:
        return None
    if pending_slot is PendingSlot.CERTIFICATE_KIND and intent is not Intent.CERTIFICATE_ISSUANCE:
        return None

    topics_by_id = {
        topic.record.public_id: topic for topic in catalog.topics if topic.record.category is intent
    }
    ordered_ids = _TOPIC_FOLLOWUP_ORDER[intent]
    options = tuple(
        (
            _CERTIFICATE_SHORT_LABELS[topic_id]
            if pending_slot is PendingSlot.CERTIFICATE_KIND
            else topics_by_id[topic_id].record.service_name
        )
        for topic_id in ordered_ids
        if topic_id in topics_by_id
    )
    if not options:
        return None
    return FollowupPlan(intent, pending_slot, options)


def _is_generic_topic_choice(value: str, intent: Intent) -> bool:
    compact = _compact_context_input(value)
    return compact in _GENERIC_TOPIC_CHOICE_UTTERANCES.get(intent, frozenset())


def _unsupported_detail_intent(value: str) -> Intent | None:
    compact = _compact_context_input(value)
    if any(term in compact for term in _UNSUPPORTED_WASTE_TERMS) and any(
        term in compact for term in _UNSUPPORTED_WASTE_DETAIL_TERMS
    ):
        return Intent.BULKY_WASTE
    if "재산세" in compact and any(term in compact for term in _UNSUPPORTED_TAX_DETAIL_TERMS):
        return Intent.LOCAL_TAX_GENERAL
    return None


def _select_context_topic_change(
    value: str,
    context: ChatContext | None,
    catalog: TopicCatalog,
) -> TopicSelection | None:
    if (
        context is None
        or context.last_intent != Intent.BULKY_WASTE.value
        or _WASTE_CANCEL_UTTERANCE_PATTERN.fullmatch(_compact_context_input(value)) is None
    ):
        return None
    prior_topic = catalog.find(context.topic_id) if context.topic_id is not None else None
    if prior_topic is None or prior_topic.record.category is not Intent.BULKY_WASTE:
        return None
    topic = catalog.find("KB-WASTE-02")
    if topic is None or topic.record.category is not Intent.BULKY_WASTE:
        return None
    return TopicSelection(
        topic=topic,
        evidence=GroundingEvidence(
            kind=GroundingEvidenceKind.UNIQUE_LEXICAL_MATCH,
            topic_id=topic.record.public_id,
            coverage_id=None,
            matched_tokens=("취소",),
        ),
    )


def _replayed_followup_pending_slot(response: FollowupResponse) -> PendingSlot:
    options = tuple(response.followup_options)
    if response.intent == Intent.UNKNOWN.value:
        return PendingSlot.DOMAIN
    if options == _REGION_FOLLOWUP_OPTIONS:
        return PendingSlot.REGION
    if options == _WASTE_ITEM_FOLLOWUP_OPTIONS:
        return PendingSlot.WASTE_ITEM
    if response.intent == Intent.CERTIFICATE_ISSUANCE.value:
        return PendingSlot.CERTIFICATE_KIND
    return PendingSlot.TOPIC_CHOICE


__all__ = [
    "ChatRepository",
    "ChatResult",
    "ChatService",
    "ChatUnavailableError",
    "FollowupPlan",
]
