from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from sejong_ai_api.chat.classification import SafeQuestion, classify_question
from sejong_ai_api.db.models import FallbackReason, Intent
from sejong_ai_api.llm.classifier_contracts import ClassifierRoute, PendingSlot
from sejong_ai_api.privacy.redaction import redact_question


def safe_question(text: str) -> SafeQuestion:
    return SafeQuestion(redact_question(text))


@pytest.mark.parametrize(
    ("question", "expected_intent"),
    [
        ("전입신고 절차가 궁금해요.", Intent.MOVE_IN_RESIDENT_REGISTRATION),
        ("주민등록등본 발급 방법을 알려주세요.", Intent.CERTIFICATE_ISSUANCE),
        ("대형폐기물 소파 배출 방법을 알려주세요.", Intent.BULKY_WASTE),
        ("자동차세 납부 방법을 알려주세요.", Intent.LOCAL_TAX_GENERAL),
    ],
)
def test_classifies_the_four_supported_intents(
    question: str,
    expected_intent: Intent,
) -> None:
    outcome = classify_question(safe_question(question))

    assert outcome.intent is expected_intent
    assert outcome.followup_required is False
    assert outcome.fallback_reason is None


def test_clear_out_of_scope_question_uses_the_policy_fallback() -> None:
    outcome = classify_question(safe_question("오늘 세종시 날씨를 알려주세요."))

    assert outcome.intent is Intent.OUT_OF_SCOPE
    assert outcome.route is ClassifierRoute.NON_CIVIC
    assert outcome.followup_required is False
    assert outcome.fallback_reason is FallbackReason.OUT_OF_SCOPE


def test_unsupported_pet_registration_is_deferred_to_the_closed_provider() -> None:
    outcome = classify_question(safe_question("반려동물 등록 어디서 해요?"))

    assert outcome.intent is Intent.UNKNOWN
    assert outcome.route is None
    assert outcome.needs_provider is True
    assert outcome.followup_required is True
    assert outcome.fallback_reason is None


@pytest.mark.parametrize(
    "question",
    [
        "신고하고 싶어요.",
        "전입신고 후 주민등록등본도 발급하고 싶어요.",
    ],
)
def test_ambiguous_supported_question_requests_followup(question: str) -> None:
    outcome = classify_question(safe_question(question))

    assert outcome.intent is Intent.UNKNOWN
    assert outcome.followup_required is True
    assert outcome.fallback_reason is None


def test_personal_lookup_is_decided_before_retrieval() -> None:
    outcome = classify_question(safe_question("내 자동차세 체납액을 조회해줘."))

    assert outcome.intent is Intent.UNKNOWN
    assert outcome.followup_required is False
    assert outcome.fallback_reason is FallbackReason.PERSONAL_LOOKUP


def test_legal_judgment_is_decided_before_retrieval() -> None:
    outcome = classify_question(
        safe_question("대형폐기물 신고를 안 하면 법적으로 처벌받는지 판단해줘.")
    )

    assert outcome.intent is Intent.UNKNOWN
    assert outcome.followup_required is False
    assert outcome.fallback_reason is FallbackReason.LEGAL_JUDGMENT


def test_classifier_rejects_raw_or_unresolved_text_at_its_boundary() -> None:
    with pytest.raises(TypeError, match="^SAFE_QUESTION_REQUIRED$"):
        classify_question("raw citizen text")  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="^SAFE_QUESTION_REQUIRED$"):
        SafeQuestion(redact_question(""))


def test_safe_question_cannot_be_replaced_after_redaction() -> None:
    question = safe_question("자동차세 납부 방법")

    with pytest.raises(FrozenInstanceError):
        question._text = "raw replacement"  # type: ignore[misc]


def test_general_tax_arrears_guidance_is_not_mistaken_for_personal_lookup() -> None:
    outcome = classify_question(safe_question("자동차세 체납액 기준을 안내해줘."))

    assert outcome.intent is Intent.LOCAL_TAX_GENERAL
    assert outcome.fallback_reason is None


@pytest.mark.parametrize("question", ["졸업증명서 발급 방법", "건강진단서 발급 방법"])
def test_unsupported_certificate_domains_are_deferred_to_provider(question: str) -> None:
    outcome = classify_question(safe_question(question))

    assert outcome.intent is Intent.UNKNOWN
    assert outcome.needs_provider is True
    assert outcome.fallback_reason is None


def test_family_relation_certificate_is_deferred_to_provider() -> None:
    outcome = classify_question(safe_question("가족관계증명서 어떻게 발급받아요?"))

    assert outcome.intent is Intent.UNKNOWN
    assert outcome.needs_provider is True
    assert outcome.pending_slot is None


def test_canonical_bed_frame_question_is_supported_bulky_waste() -> None:
    outcome = classify_question(safe_question("침대 2인용 프레임 수수료가 얼마예요?"))

    assert outcome.intent is Intent.BULKY_WASTE
    assert outcome.fallback_reason is None


def test_legal_wording_is_not_grounded_as_general_move_in_guidance() -> None:
    outcome = classify_question(safe_question("전입신고 벌금이 합법인가요?"))

    assert outcome.intent is Intent.UNKNOWN
    assert outcome.fallback_reason is FallbackReason.LEGAL_JUDGMENT


@pytest.mark.parametrize(
    ("question", "expected_reason"),
    [
        ("접수번호 SJ-2026-123456 처리됐어?", FallbackReason.PERSONAL_LOOKUP),
        ("내가 기초생활수급 대상인지 판단해줘.", FallbackReason.LEGAL_JUDGMENT),
        ("이 행정처분이 법적으로 부당한가요?", FallbackReason.LEGAL_JUDGMENT),
    ],
)
def test_generic_policy_fallbacks_use_unknown_intent(
    question: str,
    expected_reason: FallbackReason,
) -> None:
    outcome = classify_question(safe_question(question))

    assert outcome.intent is Intent.UNKNOWN
    assert outcome.followup_required is False
    assert outcome.fallback_reason is expected_reason


def test_deterministic_supported_fast_path_has_closed_route() -> None:
    outcome = classify_question(safe_question("주민등록등본 발급"))

    assert outcome.route is ClassifierRoute.SUPPORTED
    assert outcome.intent is Intent.CERTIFICATE_ISSUANCE
    assert outcome.topic_id is None
    assert outcome.coverage_id is None
    assert outcome.needs_provider is False


def test_generic_certificate_uses_bounded_certificate_followup() -> None:
    outcome = classify_question(safe_question("증명서 발급해야해"))

    assert outcome.route is ClassifierRoute.NEEDS_FOLLOWUP
    assert outcome.intent is Intent.CERTIFICATE_ISSUANCE
    assert outcome.followup_required is True
    assert outcome.pending_slot is PendingSlot.CERTIFICATE_KIND
    assert outcome.needs_provider is False


def test_unsupported_civic_question_requires_closed_provider_classification() -> None:
    outcome = classify_question(safe_question("청년 월세 지원 어떻게 해요?"))

    assert outcome.route is None
    assert outcome.intent is Intent.UNKNOWN
    assert outcome.followup_required is True
    assert outcome.needs_provider is True


def test_classifier_outcome_rejects_inconsistent_provider_state() -> None:
    with pytest.raises(ValueError, match="^CLASSIFICATION_OUTCOME_INVALID$"):
        classify_question(safe_question("주민등록등본 발급")).__class__(
            intent=Intent.CERTIFICATE_ISSUANCE,
            followup_required=False,
            fallback_reason=None,
            route=ClassifierRoute.NON_CIVIC,
            topic_id=None,
            coverage_id=None,
            pending_slot=None,
            needs_provider=False,
        )


def test_classifier_outcome_rejects_topic_without_matching_coverage() -> None:
    with pytest.raises(ValueError, match="^CLASSIFICATION_OUTCOME_INVALID$"):
        classify_question(safe_question("주민등록등본 발급")).__class__(
            intent=Intent.CERTIFICATE_ISSUANCE,
            followup_required=False,
            fallback_reason=None,
            route=ClassifierRoute.SUPPORTED,
            topic_id="KB-CERT-01",
            coverage_id=None,
            pending_slot=None,
            needs_provider=False,
        )
