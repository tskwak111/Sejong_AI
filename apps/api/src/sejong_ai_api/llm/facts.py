"""Pure request-local fact construction and fail-closed draft materialization."""

from __future__ import annotations

import re
import unicodedata
from typing import Final

from sejong_ai_api.db.models import Intent, KnowledgeRecord
from sejong_ai_api.llm.chat_contracts import (
    FactKind,
    GeneratedChatDraft,
    GroundedChatRequest,
    GroundedFact,
    MaterializedChatAnswer,
)
from sejong_ai_api.privacy import redact_question

_PRESENTATION_LEXICON: Final = frozenset({"공식", "안내", "정보", "쉽게", "정리", "확인", "드려요"})
_KOREAN_PARTICLE_SUFFIXES: Final = (
    "으로부터",
    "에게서",
    "에서",
    "으로",
    "부터",
    "까지",
    "처럼",
    "보다",
    "라도",
    "이나",
    "이며",
    "이고",
    "하고",
    "하면",
    "합니다",
    "입니다",
    "인데요",
    "인데",
    "은",
    "는",
    "이",
    "가",
    "을",
    "를",
    "에",
    "의",
    "와",
    "과",
    "도",
    "만",
    "로",
    "나",
    "든",
    "께",
)
_MASK_TOKEN = re.compile(r"\[[^\]\r\n]{1,50}\]")
_URL = re.compile(r"(?:https?://|www\.)", re.IGNORECASE)
_EMAIL = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
_PHONE = re.compile(r"(?<!\d)(?:(?:0\d{1,2}|1[5-8]\d{2})[-\s]?\d{3,4}[-\s]?\d{4})(?!\d)")
_NUMBER_OR_DATE_OR_CURRENCY = re.compile(
    r"(?<!\d)\d+(?:[,.\-/]\d+)*(?:\s*(?:년|월|일|원|만원|천원|%|퍼센트))?(?!\d)"
)
_SIGNIFICANT_TOKEN = re.compile(r"[가-힣]{2,}|[A-Za-z][A-Za-z0-9_-]*")


def build_grounded_chat_request(
    *,
    masked_question: str,
    intent: Intent,
    record: KnowledgeRecord,
) -> GroundedChatRequest:
    """Issue the only fact IDs a provider may reference for one grounded record."""
    if (
        type(masked_question) is not str
        or not masked_question
        or masked_question.strip() != masked_question
    ):
        raise ValueError("MASKED_QUESTION_INVALID")
    if (
        type(intent) is not Intent
        or type(record) is not KnowledgeRecord
        or record.category is not intent
    ):
        raise ValueError("GROUNDED_RECORD_INVALID")
    if len(record.procedure_steps) > 12 or len(record.required_documents) > 12:
        raise ValueError("GROUNDED_FACT_LIMIT_INVALID")

    facts = tuple(
        [
            *(
                GroundedFact(f"STEP-{index:02d}", FactKind.PROCEDURE_STEP, step)
                for index, step in enumerate(record.procedure_steps, start=1)
            ),
            *(
                GroundedFact(f"DOC-{index:02d}", FactKind.REQUIRED_DOCUMENT, document)
                for index, document in enumerate(record.required_documents, start=1)
            ),
            *(
                (GroundedFact("TIME-01", FactKind.PROCESSING_TIME, record.processing_time),)
                if record.processing_time is not None
                else ()
            ),
            *(
                (GroundedFact("FEE-01", FactKind.FEE, record.fee),)
                if record.fee is not None
                else ()
            ),
            GroundedFact("DEPT-01", FactKind.DEPARTMENT, record.department),
        ]
    )
    return GroundedChatRequest(
        masked_question=masked_question,
        intent=intent,
        service_name=record.service_name,
        approved_summary=record.answer_summary,
        facts=facts,
    )


def materialize_grounded_answer(
    request: GroundedChatRequest,
    draft: GeneratedChatDraft,
) -> MaterializedChatAnswer | None:
    """Return a fully validated local answer or reject the entire draft."""
    if type(request) is not GroundedChatRequest or type(draft) is not GeneratedChatDraft:
        return None
    summary = _validate_summary(request, draft.summary)
    if summary is None:
        return None

    expected_steps = _fact_ids(request.facts, FactKind.PROCEDURE_STEP)
    expected_documents = _fact_ids(request.facts, FactKind.REQUIRED_DOCUMENT)
    if tuple(draft.procedure_step_ids) != expected_steps:
        return None
    if tuple(draft.required_document_ids) != expected_documents:
        return None

    processing_time = _optional_fact_text(request.facts, FactKind.PROCESSING_TIME, "TIME-01")
    fee = _optional_fact_text(request.facts, FactKind.FEE, "FEE-01")
    if draft.processing_time_id != ("TIME-01" if processing_time is not None else None):
        return None
    if draft.fee_id != ("FEE-01" if fee is not None else None):
        return None
    if draft.department_id != "DEPT-01":
        return None

    return MaterializedChatAnswer(
        summary=summary,
        procedure_steps=_fact_texts(request.facts, FactKind.PROCEDURE_STEP),
        required_documents=_fact_texts(request.facts, FactKind.REQUIRED_DOCUMENT),
        processing_time=processing_time,
        fee=fee,
        department=_required_fact_text(request.facts, FactKind.DEPARTMENT, "DEPT-01"),
    )


def _fact_ids(facts: tuple[GroundedFact, ...], kind: FactKind) -> tuple[str, ...]:
    return tuple(fact.fact_id for fact in facts if fact.kind is kind)


def _fact_texts(facts: tuple[GroundedFact, ...], kind: FactKind) -> tuple[str, ...]:
    return tuple(fact.text for fact in facts if fact.kind is kind)


def _optional_fact_text(
    facts: tuple[GroundedFact, ...], kind: FactKind, expected_id: str
) -> str | None:
    matching = tuple(fact for fact in facts if fact.kind is kind)
    if not matching:
        return None
    if len(matching) != 1 or matching[0].fact_id != expected_id:
        raise ValueError("GROUNDED_FACT_STRUCTURE_INVALID")
    return matching[0].text


def _required_fact_text(facts: tuple[GroundedFact, ...], kind: FactKind, expected_id: str) -> str:
    value = _optional_fact_text(facts, kind, expected_id)
    if value is None:
        raise ValueError("GROUNDED_FACT_STRUCTURE_INVALID")
    return value


def _validate_summary(request: GroundedChatRequest, summary: str) -> str | None:
    if type(summary) is not str:
        return None
    normalized = unicodedata.normalize("NFKC", summary)
    if not normalized or len(normalized) > 500 or normalized != summary:
        return None
    if any(unicodedata.category(character).startswith("C") for character in normalized):
        return None
    if _MASK_TOKEN.search(normalized) or _URL.search(normalized) or _EMAIL.search(normalized):
        return None
    if _PHONE.search(normalized):
        return None

    redaction = redact_question(normalized)
    if (
        redaction.masked_text != normalized
        or not redaction.safe_for_synthetic_provider
        or redaction.findings
        or redaction.unresolved_reason is not None
    ):
        return None

    corpus = _canonical_corpus(request)
    if any(
        not _token_occurs_exactly(token, corpus)
        for token in _NUMBER_OR_DATE_OR_CURRENCY.findall(normalized)
    ):
        return None
    return normalized if _semantic_tokens_are_grounded(normalized, corpus) else None


def _canonical_corpus(request: GroundedChatRequest) -> str:
    return unicodedata.normalize(
        "NFKC",
        " ".join(
            (request.service_name, request.approved_summary, *(fact.text for fact in request.facts))
        ),
    )


def _token_occurs_exactly(token: str, corpus: str) -> bool:
    return re.search(rf"(?<!\d){re.escape(token)}(?!\d)", corpus) is not None


def _semantic_tokens_are_grounded(summary: str, corpus: str) -> bool:
    corpus_tokens = {
        _normalize_significant_token(token) for token in _SIGNIFICANT_TOKEN.findall(corpus)
    }
    corpus_tokens.discard("")
    summary_tokens = tuple(
        token
        for token in (
            _normalize_significant_token(value) for value in _SIGNIFICANT_TOKEN.findall(summary)
        )
        if token
    )
    if not summary_tokens:
        return False
    if any(
        token not in corpus_tokens and token not in _PRESENTATION_LEXICON
        for token in summary_tokens
    ):
        return False
    return any(token in corpus_tokens for token in summary_tokens)


def _normalize_significant_token(token: str) -> str:
    normalized = token.casefold()
    if re.fullmatch(r"[가-힣]+", normalized) is None:
        return normalized
    for suffix in _KOREAN_PARTICLE_SUFFIXES:
        if normalized.endswith(suffix) and len(normalized) - len(suffix) >= 2:
            return normalized[: -len(suffix)]
    return normalized
