import json
from datetime import date

import pytest

import sejong_ai_api.llm.classifier_prompt as classifier_prompt_module
from sejong_ai_api.chat.classification import SafeQuestion
from sejong_ai_api.chat.topic_catalog import RuntimeTopic, TopicCatalog, TopicCoverage
from sejong_ai_api.db.models import Intent, KnowledgeRecord
from sejong_ai_api.llm.classifier_prompt import build_classifier_messages
from sejong_ai_api.llm.contracts import GroundedFixture
from sejong_ai_api.llm.prompt import (
    PROMPT_VERSION,
    build_upstage_messages,
    estimate_input_token_upper_bound,
)
from sejong_ai_api.privacy.redaction import redact_question

CLASSIFIER_CATALOG_COLUMNS = [
    "topic_id",
    "intent",
    "service_name",
    "coverage_id",
    "coverage_label",
    "approved_examples",
]


def _safe_question(text: str = "안전한 질문") -> SafeQuestion:
    return SafeQuestion(redact_question(text))


def _forged_oversized_safe_question() -> SafeQuestion:
    question = object.__new__(SafeQuestion)
    object.__setattr__(question, "_text", "가" * 1025)
    return question


def _runtime_topic(
    index: int = 1,
    *,
    examples: tuple[str, ...] = ("대형폐기물은 어떻게 신청하나요?",),
    coverage_label: str = "일반 가구류 배출 절차",
) -> RuntimeTopic:
    topic_id = f"KB-WASTE-{index:02d}"
    intent = Intent.BULKY_WASTE
    return RuntimeTopic(
        record=KnowledgeRecord(
            public_id=topic_id,
            category=intent,
            service_name="대형폐기물 배출신청 절차",
            answer_summary="FACT-SENTINEL",
            procedure_steps=("PROCEDURE-SENTINEL",),
            required_documents=("DOCUMENT-SENTINEL",),
            processing_time="PROCESSING-SENTINEL",
            fee="FEE-SENTINEL",
            department="OFFICE-SENTINEL",
            source_title="SOURCE-SENTINEL",
            source_url="https://example.invalid/source-sentinel",
            last_verified_at=date(2026, 7, 27),
            caution="CAUTION-SENTINEL",
            question_examples=examples,
        ),
        coverage=TopicCoverage(
            topic_id=topic_id,
            intent=intent,
            coverage_id=(
                "GENERAL_BULKY_DISPOSAL" if index == 1 else f"GENERAL_BULKY_DISPOSAL_{index:02d}"
            ),
            coverage_label=coverage_label,
        ),
    )


def _catalog(
    size: int = 1,
    *,
    examples: tuple[str, ...] = ("대형폐기물은 어떻게 신청하나요?",),
    coverage_label: str = "일반 가구류 배출 절차",
) -> TopicCatalog:
    return TopicCatalog(
        tuple(
            _runtime_topic(
                index,
                examples=examples,
                coverage_label=coverage_label,
            )
            for index in range(1, size + 1)
        )
    )


def test_canonical_prompt_stays_within_conservative_input_upper_bound(
    grounded_fixture: GroundedFixture,
) -> None:
    messages = build_upstage_messages(grounded_fixture)
    assert estimate_input_token_upper_bound(messages) <= 4096


def test_prompt_is_source_free_and_system_requires_strict_json(
    grounded_fixture: GroundedFixture,
) -> None:
    messages = build_upstage_messages(grounded_fixture)
    serialized = json.dumps(messages, ensure_ascii=False, separators=(",", ":"))
    assert PROMPT_VERSION == "0.1.0-upstage-solar-pro3-synthetic"
    for forbidden in (
        "source_title",
        "source_url",
        "last_verified_at",
        "question_examples",
        "public_id",
    ):
        assert forbidden not in serialized
    assert messages[0]["role"] == "system"
    assert "사실을 추가" in messages[0]["content"]
    assert "JSON만" in messages[0]["content"]
    assert "null" in messages[0]["content"]
    assert "source" in messages[0]["content"]
    assert "intent" in messages[0]["content"]
    assert "status" in messages[0]["content"]


def test_input_upper_bound_is_canonical_complete_message_utf8_length() -> None:
    messages = (
        {"role": "system", "content": "가"},
        {"role": "user", "content": "나"},
    )
    canonical = json.dumps(messages, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    assert estimate_input_token_upper_bound(messages) == len(canonical)


def test_classifier_prompt_contains_only_masked_question_and_governed_catalog_fields() -> None:
    messages = build_classifier_messages(
        _safe_question(),
        _catalog(),
        max_input_chars=1024,
    )

    assert json.loads(messages[1]["content"]) == {
        "ask": "안전한 질문",
        "c": [
            CLASSIFIER_CATALOG_COLUMNS,
            [
                [
                    "KB-WASTE-01",
                    "BULKY_WASTE",
                    "대형폐기물 배출신청 절차",
                    "GENERAL_BULKY_DISPOSAL",
                    "일반 가구류 배출 절차",
                    ["대형폐기물은 어떻게 신청하나요?"],
                ]
            ],
        ],
    }
    serialized = json.dumps(messages, ensure_ascii=False, separators=(",", ":"))
    for forbidden in (
        "FACT-SENTINEL",
        "PROCEDURE-SENTINEL",
        "DOCUMENT-SENTINEL",
        "PROCESSING-SENTINEL",
        "FEE-SENTINEL",
        "OFFICE-SENTINEL",
        "SOURCE-SENTINEL",
        "CAUTION-SENTINEL",
        "answer_summary",
        "procedure_steps",
        "required_documents",
        "processing_time",
        "fee",
        "department",
        "source_title",
        "source_url",
        "last_verified_at",
        "caution",
    ):
        assert forbidden not in serialized


def test_classifier_prompt_explicitly_requires_json_output() -> None:
    messages = build_classifier_messages(
        _safe_question(),
        _catalog(),
        max_input_chars=1024,
    )

    assert any("json" in message["content"].casefold() for message in messages)


def test_classifier_prompt_uses_canonical_wire_names_and_exact_none() -> None:
    system = build_classifier_messages(
        _safe_question(),
        _catalog(),
        max_input_chars=1024,
    )[0]["content"]

    for field in ("route", "intent", "topic_id", "coverage_id", "pending_slot"):
        assert field in system
    assert "NONE" in system
    for forbidden in (
        "route/I:",
        "T:topic_id",
        "C:coverage_id",
        "P:pending_slot",
        "∅",
        "n³",
        "n⁴",
    ):
        assert forbidden not in system


def test_classifier_prompt_explicitly_maps_supported_values_and_forbids_extra_keys() -> None:
    system = build_classifier_messages(
        _safe_question(),
        _catalog(),
        max_input_chars=1024,
    )[0]["content"]

    assert "extra=NO" in system
    assert "default=NONE" in system
    assert "SUPPORTED=cat[intent,topic_id,coverage_id]" in system
    assert "NO_TOPIC_MATCH=지원" in system
    assert "CIVIC_SCOPE_GAP/NON_CIVIC" in system
    assert "NEEDS_FOLLOWUP=DOMAIN?NONE:지원,,," in system
    for forbidden in ("+X", "row*3"):
        assert forbidden not in system


def test_classifier_prompt_uses_at_most_two_approved_examples_without_sampling_topics() -> None:
    catalog = _catalog(
        2,
        examples=("첫 번째 승인 예시", "두 번째 승인 예시", "세 번째 승인 예시"),
    )

    messages = build_classifier_messages(
        _safe_question(),
        catalog,
        max_input_chars=1024,
    )
    payload = json.loads(messages[1]["content"])

    assert len(payload["c"][1]) == 2
    assert payload["c"][1][0][5] == [
        "첫 번째 승인 예시",
        "두 번째 승인 예시",
    ]
    assert payload["c"][1][1][5] == [
        "첫 번째 승인 예시",
        "두 번째 승인 예시",
    ]


@pytest.mark.parametrize(
    ("catalog_fixture", "expected_size"),
    [
        ("governed_catalog_19", 19),
        ("governed_catalog_20", 20),
    ],
)
def test_real_governed_catalog_fits_and_preserves_every_approved_value(
    request: pytest.FixtureRequest,
    catalog_fixture: str,
    expected_size: int,
) -> None:
    catalog: TopicCatalog = request.getfixturevalue(catalog_fixture)
    messages = build_classifier_messages(
        _safe_question(),
        catalog,
        max_input_chars=1024,
    )

    assert len(catalog.topics) == expected_size
    assert classifier_prompt_module.estimate_classifier_input_upper_bound(messages) <= 4096
    assert json.loads(messages[1]["content"]) == {
        "ask": "안전한 질문",
        "c": [
            CLASSIFIER_CATALOG_COLUMNS,
            [
                [
                    topic.record.public_id,
                    topic.record.category.value,
                    topic.record.service_name,
                    topic.coverage.coverage_id,
                    topic.coverage.coverage_label,
                    list(topic.record.question_examples[:2]),
                ]
                for topic in catalog.topics
            ],
        ],
    }


def test_classifier_prompt_rejects_question_over_1024_chars_without_truncation() -> None:
    with pytest.raises(ValueError, match="^CLASSIFIER_PROMPT_INVALID$"):
        build_classifier_messages(
            _forged_oversized_safe_question(),
            _catalog(),
            max_input_chars=1024,
        )


@pytest.mark.parametrize("size", [0, 21])
def test_classifier_prompt_rejects_ineligible_catalog_size(size: int) -> None:
    with pytest.raises(ValueError, match="^CLASSIFIER_PROMPT_INVALID$"):
        build_classifier_messages(
            _safe_question(),
            _catalog(size),
            max_input_chars=1024,
        )


def test_classifier_input_estimate_counts_complete_content_and_can_exceed_bound() -> None:
    messages = build_classifier_messages(
        _safe_question(),
        _catalog(coverage_label="가" * 4096),
        max_input_chars=1024,
    )

    assert classifier_prompt_module.estimate_classifier_input_upper_bound(messages) == sum(
        len(message["content"]) for message in messages
    )
    assert classifier_prompt_module.estimate_classifier_input_upper_bound(messages) > 4096
