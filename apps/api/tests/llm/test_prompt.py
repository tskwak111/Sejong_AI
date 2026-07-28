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


def test_classifier_prompt_contains_only_masked_question_governed_catalog_and_wire_examples() -> (
    None
):
    messages = build_classifier_messages(
        _safe_question(),
        _catalog(),
        max_input_chars=1024,
    )

    assert json.loads(messages[1]["content"]) == {
        "ask": "안전한 질문",
        "cat": {
            "BULKY_WASTE": [
                [
                    "KB-WASTE-01",
                    "GENERAL_BULKY_DISPOSAL",
                    "일반 가구류 배출 절차",
                    ["대형폐기물은 어떻게 신청하나요?"],
                ]
            ]
        },
        "ex": [
            [
                "SUPPORTED",
                "BULKY_WASTE",
                "KB-WASTE-01",
                "GENERAL_BULKY_DISPOSAL",
                "NONE",
            ],
            ["CIVIC_SCOPE_GAP", "NONE", "NONE", "NONE", "NONE"],
        ],
    }
    serialized = messages[1]["content"]
    for forbidden in (
        "대형폐기물 배출신청 절차",
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
        "service_name",
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


def test_classifier_prompt_declares_exact_closed_wire_vocabularies_without_ambiguous_defaults() -> (
    None
):
    system = build_classifier_messages(
        _safe_question(),
        _catalog(),
        max_input_chars=1024,
    )[0]["content"]

    for route in (
        "SUPPORTED",
        "NO_TOPIC_MATCH",
        "CIVIC_SCOPE_GAP",
        "NON_CIVIC",
        "NEEDS_FOLLOWUP",
    ):
        assert route in system
    for intent in (
        "MOVE_IN_RESIDENT_REGISTRATION",
        "CERTIFICATE_ISSUANCE",
        "BULKY_WASTE",
        "LOCAL_TAX_GENERAL",
    ):
        assert intent in system
    for pending_slot in (
        "DOMAIN",
        "TOPIC_CHOICE",
        "CERTIFICATE_KIND",
        "REGION",
        "WASTE_ITEM",
    ):
        assert pending_slot in system
    assert "provider intents: the four supported intents or NONE" in system
    for forbidden in (
        "default=NONE",
        "NONE=없음",
        "NO_TOPIC_MATCH=지원",
        "DOMAIN?NONE:지원,,,",
    ):
        assert forbidden not in system


def test_classifier_prompt_encodes_every_complete_route_matrix_row() -> None:
    system = build_classifier_messages(
        _safe_question(),
        _catalog(),
        max_input_chars=1024,
    )[0]["content"]

    assert "keys: route,intent,topic_id,coverage_id,pending_slot" in system
    assert "valid tuples in key order:" in system
    for row in (
        "SUPPORTED|catalog intent|same-row topic_id|same-row coverage_id|NONE",
        "NO_TOPIC_MATCH|supported intent|NONE|NONE|NONE",
        "CIVIC_SCOPE_GAP|NONE|NONE|NONE|NONE",
        "NON_CIVIC|NONE|NONE|NONE|NONE",
        "NEEDS_FOLLOWUP|NONE|NONE|NONE|DOMAIN",
        "NEEDS_FOLLOWUP|supported intent|NONE|NONE|TOPIC_CHOICE",
        "NEEDS_FOLLOWUP|CERTIFICATE_ISSUANCE|NONE|NONE|CERTIFICATE_KIND",
        "NEEDS_FOLLOWUP|supported intent|NONE|NONE|REGION",
        "NEEDS_FOLLOWUP|BULKY_WASTE|NONE|NONE|WASTE_ITEM",
    ):
        assert row in system


def test_classifier_prompt_builds_supported_example_from_first_same_catalog_row() -> None:
    catalog = _catalog(2)
    payload = json.loads(
        build_classifier_messages(
            _safe_question(),
            catalog,
            max_input_chars=1024,
        )[1]["content"]
    )
    first = catalog.topics[0]

    assert payload["ex"][0] == [
        "SUPPORTED",
        first.record.category.value,
        first.record.public_id,
        first.coverage.coverage_id,
        "NONE",
    ]


def test_classifier_prompt_includes_exact_all_none_scope_gap_example() -> None:
    payload = json.loads(
        build_classifier_messages(
            _safe_question(),
            _catalog(),
            max_input_chars=1024,
        )[1]["content"]
    )

    assert payload["ex"][1] == [
        "CIVIC_SCOPE_GAP",
        "NONE",
        "NONE",
        "NONE",
        "NONE",
    ]


def test_classifier_prompt_forbids_none_translations_null_and_explanatory_output() -> None:
    system = build_classifier_messages(
        _safe_question(),
        _catalog(),
        max_input_chars=1024,
    )[0]["content"]

    assert "all five values are strings" in system
    assert "no extra key, prose or Markdown" in system
    assert "NONE is exact uppercase ASCII; 없음/none/null/empty are forbidden" in system
    assert "cat={intent:[[topic_id,coverage_id,coverage_label,approved_examples]]}" in system
    assert "SUPPORTED intent=cat group key; topic_id/coverage_id=same row" in system
    assert "NONE=없음" not in system


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

    assert len(payload["cat"]["BULKY_WASTE"]) == 2
    assert payload["cat"]["BULKY_WASTE"][0][3] == [
        "첫 번째 승인 예시",
        "두 번째 승인 예시",
    ]
    assert payload["cat"]["BULKY_WASTE"][1][3] == [
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
    payload = json.loads(messages[1]["content"])
    assert payload["cat"] == {
        intent.value: [
            [
                topic.record.public_id,
                topic.coverage.coverage_id,
                topic.coverage.coverage_label,
                list(topic.record.question_examples[:2]),
            ]
            for topic in catalog.topics
            if topic.record.category is intent
        ]
        for intent in (
            Intent.MOVE_IN_RESIDENT_REGISTRATION,
            Intent.CERTIFICATE_ISSUANCE,
            Intent.BULKY_WASTE,
            Intent.LOCAL_TAX_GENERAL,
        )
        if any(topic.record.category is intent for topic in catalog.topics)
    }
    first = catalog.topics[0]
    assert payload["ex"] == [
        [
            "SUPPORTED",
            first.record.category.value,
            first.record.public_id,
            first.coverage.coverage_id,
            "NONE",
        ],
        ["CIVIC_SCOPE_GAP", "NONE", "NONE", "NONE", "NONE"],
    ]

    grouped_rows = [row for rows in payload["cat"].values() for row in rows]
    for topic in catalog.topics:
        assert sum(row[0] == topic.record.public_id for row in grouped_rows) == 1
        assert sum(row[1] == topic.coverage.coverage_id for row in grouped_rows) == 1
        assert sum(row[2] == topic.coverage.coverage_label for row in grouped_rows) == 1
        for example in topic.record.question_examples[:2]:
            assert sum(candidate == example for row in grouped_rows for candidate in row[3]) == 1

    serialized = messages[1]["content"]
    for forbidden_key in (
        "service_name",
        "source",
        "answer",
        "procedure",
        "office",
        "fee",
        "caution",
    ):
        assert f'"{forbidden_key}"' not in serialized


def test_real_governed_20_catalog_with_256_character_question_fits_route_matrix_guard(
    governed_catalog_20: TopicCatalog,
) -> None:
    safe = _safe_question("가" * 256)
    messages = build_classifier_messages(
        safe,
        governed_catalog_20,
        max_input_chars=1024,
    )

    assert len(safe.text) == 256
    assert classifier_prompt_module.estimate_classifier_input_upper_bound(messages) == sum(
        len(message["content"]) for message in messages
    )
    assert classifier_prompt_module.estimate_classifier_input_upper_bound(messages) <= 4096


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
