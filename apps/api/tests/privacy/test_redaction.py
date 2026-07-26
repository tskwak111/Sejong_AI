from __future__ import annotations

import json
import logging
import time
from dataclasses import FrozenInstanceError
from pathlib import Path
from typing import TypedDict, cast

import pytest

import sejong_ai_api.privacy.redaction as redaction_module
from sejong_ai_api.privacy import (
    PiiCategory,
    RedactionFinding,
    RedactionResult,
    UnresolvedReason,
    redact_question,
)


class FixtureCase(TypedDict):
    id: str
    input: str
    outcome: str
    categories: list[str]
    tokens: list[str]
    expected_masked_text: str | None
    unresolved_reason: str | None


class FixtureDocument(TypedDict):
    fixture_version: int
    synthetic_only: bool
    cases: list[FixtureCase]


def test_fixed_label_lookup_has_no_mutable_global_mapping() -> None:
    lookup = redaction_module._FIXED_TOKEN_BY_LABEL
    assert type(lookup) is tuple
    assert all(type(entry) is tuple and len(entry) == 2 for entry in lookup)


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "pii_masking_cases.v1.json"
CASES = cast(
    FixtureDocument,
    json.loads(FIXTURE_PATH.read_text(encoding="utf-8")),
)
EXPECTED_TOKENS = {
    "[이름]",
    "[주민등록번호]",
    "[여권·면허번호]",
    "[전화번호]",
    "[이메일]",
    "[상세주소]",
    "[계좌번호]",
    "[카드번호]",
    "[인증정보]",
    "[차량번호]",
    "[접수번호]",
    "[건강·복지정보]",
    "[정밀위치]",
}


def test_fixture_contract_is_frozen_synthetic_and_complete() -> None:
    assert CASES["fixture_version"] == 1
    assert CASES["synthetic_only"] is True
    cases = CASES["cases"]
    assert len(cases) == 74
    positive_prefixes = (
        "name",
        "rrn",
        "identity",
        "phone",
        "email",
        "address",
        "account",
        "card",
        "auth",
        "vehicle",
        "case",
        "sensitive",
        "location",
    )
    expected_ids = {
        *(f"{prefix}-{number:02d}" for prefix in positive_prefixes for number in range(1, 4)),
        *(f"unicode-{number:02d}" for number in range(1, 11)),
        *(f"overlap-{number:02d}" for number in range(1, 6)),
        *(f"negative-{number:02d}" for number in range(1, 21)),
    }
    assert {case["id"] for case in cases} == expected_ids
    assert [case["outcome"] for case in cases].count("MASKED") == 50
    assert [case["outcome"] for case in cases].count("SAFE_UNCHANGED") == 20
    assert [case["outcome"] for case in cases].count("UNRESOLVED") == 4
    exact_keys = {
        "id",
        "input",
        "outcome",
        "categories",
        "tokens",
        "expected_masked_text",
        "unresolved_reason",
    }
    expected_key_order = (
        "id",
        "input",
        "outcome",
        "categories",
        "tokens",
        "expected_masked_text",
        "unresolved_reason",
    )
    for case in cases:
        assert set(case) == exact_keys
        assert tuple(case) == expected_key_order
        assert case["outcome"] in {"MASKED", "SAFE_UNCHANGED", "UNRESOLVED"}
        assert set(case["categories"]) <= {category.value for category in PiiCategory}
        assert set(case["tokens"]) <= EXPECTED_TOKENS
        reason = case["unresolved_reason"]
        assert reason is None or reason in {item.value for item in UnresolvedReason}
        assert (case["outcome"] == "UNRESOLVED") is (reason is not None)
        assert (case["outcome"] == "UNRESOLVED") is (case["expected_masked_text"] is None)
    for prefix in positive_prefixes:
        assert sum(case["id"].startswith(f"{prefix}-") for case in cases) == 3


def _case_id(case: FixtureCase) -> str:
    return case["id"]


@pytest.mark.parametrize("case", CASES["cases"], ids=_case_id)
def test_frozen_v1_case(case: FixtureCase) -> None:
    raw = case["input"]
    assert type(raw) is str
    result = redact_question(raw)
    assert isinstance(result, RedactionResult)
    assert [finding.category.value for finding in result.findings] == case["categories"]
    assert result.masked_text == case["expected_masked_text"]
    if case["outcome"] == "SAFE_UNCHANGED":
        assert result.safe_for_failure_storage is True
        assert result.safe_for_synthetic_provider is True
        assert result.unresolved_reason is None
    elif case["outcome"] == "MASKED":
        assert result.masked_text is not None
        assert result.masked_text != raw
        assert all(token in result.masked_text for token in case["tokens"])
        assert result.safe_for_failure_storage is True
        assert result.safe_for_synthetic_provider is True
        assert result.unresolved_reason is None
    else:
        reason = case["unresolved_reason"]
        assert reason is not None
        assert result.masked_text is None
        assert result.safe_for_failure_storage is False
        assert result.safe_for_synthetic_provider is False
        assert result.unresolved_reason is UnresolvedReason(reason)


def test_enum_values_are_closed_and_exact() -> None:
    assert [item.value for item in PiiCategory] == [
        "NAME",
        "RESIDENT_REGISTRATION_NUMBER",
        "PASSPORT_OR_LICENSE",
        "PHONE_NUMBER",
        "EMAIL",
        "DETAILED_ADDRESS",
        "FINANCIAL_ACCOUNT",
        "PAYMENT_CARD",
        "AUTH_SECRET",
        "VEHICLE_PLATE",
        "CASE_REFERENCE",
        "SENSITIVE_HEALTH_WELFARE",
        "PRECISE_LOCATION",
    ]


def test_value_objects_are_frozen_slotted_and_value_free() -> None:
    finding = RedactionFinding(PiiCategory.EMAIL, 3, 10, "[이메일]")
    result = RedactionResult("메일 [이메일]", (finding,), True, True, None)
    assert not hasattr(finding, "__dict__")
    assert not hasattr(result, "__dict__")
    assert not hasattr(finding, "matched_value")
    with pytest.raises(FrozenInstanceError):
        finding.start = 0  # type: ignore[misc]
    with pytest.raises(ValueError, match="^REDACTION_FINDING_INVALID$"):
        RedactionFinding(PiiCategory.EMAIL, 3, 10, "raw@example.invalid")
    with pytest.raises(ValueError, match="^REDACTION_RESULT_INVALID$"):
        RedactionResult("raw", (), False, True, None)
    assert [item.value for item in UnresolvedReason] == [
        "INPUT_INVALID",
        "UNSAFE_UNICODE",
        "AMBIGUOUS_PERSON_NAME",
        "AMBIGUOUS_DETAILED_ADDRESS",
        "RESIDUAL_HIGH_RISK_PATTERN",
    ]


@pytest.mark.parametrize("raw", [None, 1, b"question", "", " ", "x" * 1001])
def test_invalid_input_is_closed_without_text(raw: object) -> None:
    result = redact_question(raw)  # type: ignore[arg-type]
    assert result == RedactionResult(None, (), False, False, UnresolvedReason.INPUT_INVALID)


@pytest.mark.parametrize("raw", ["x\x00y", "x\u202ey", "x\u2063y", "x\ud800y"])
def test_unsafe_unicode_is_closed_without_findings(raw: str) -> None:
    result = redact_question(raw)
    assert result == RedactionResult(None, (), False, False, UnresolvedReason.UNSAFE_UNICODE)


@pytest.mark.parametrize("character", ["\u200b", "\u200c", "\u200d", "\u2060", "\ufeff"])
def test_approved_zero_width_characters_are_removed_before_detection(character: str) -> None:
    result = redact_question(f"일반{character}질문")
    assert result == RedactionResult("일반질문", (), True, True, None)


@pytest.mark.parametrize(
    "character",
    ["\u202a", "\u202b", "\u202c", "\u202d", "\u202e", "\u2066", "\u2067", "\u2068", "\u2069"],
)
def test_every_bidi_override_or_isolate_is_rejected(character: str) -> None:
    result = redact_question(f"질문{character}값")
    assert result.unresolved_reason is UnresolvedReason.UNSAFE_UNICODE
    assert result.masked_text is None


def test_exact_replacement_and_normalized_offsets() -> None:
    result = redact_question("연락처 010\u200b-0000-0000")
    assert result.masked_text == "연락처 [전화번호]"
    assert result.findings == (RedactionFinding(PiiCategory.PHONE_NUMBER, 4, 17, "[전화번호]"),)


def test_multiple_findings_are_returned_in_text_order() -> None:
    result = redact_question("메일 qa@example.invalid 전화 010-0000-0000")
    assert [item.category for item in result.findings] == [
        PiiCategory.EMAIL,
        PiiCategory.PHONE_NUMBER,
    ]
    assert result.masked_text == "메일 [이메일] 전화 [전화번호]"


EXPECTED_CATEGORY_PRIORITY = (
    PiiCategory.RESIDENT_REGISTRATION_NUMBER,
    PiiCategory.PAYMENT_CARD,
    PiiCategory.FINANCIAL_ACCOUNT,
    PiiCategory.AUTH_SECRET,
    PiiCategory.PASSPORT_OR_LICENSE,
    PiiCategory.PHONE_NUMBER,
    PiiCategory.EMAIL,
    PiiCategory.PRECISE_LOCATION,
    PiiCategory.VEHICLE_PLATE,
    PiiCategory.CASE_REFERENCE,
    PiiCategory.DETAILED_ADDRESS,
    PiiCategory.NAME,
    PiiCategory.SENSITIVE_HEALTH_WELFARE,
)
TOKEN_BY_CATEGORY = dict(
    zip(
        EXPECTED_CATEGORY_PRIORITY,
        (
            "[주민등록번호]",
            "[카드번호]",
            "[계좌번호]",
            "[인증정보]",
            "[여권·면허번호]",
            "[전화번호]",
            "[이메일]",
            "[정밀위치]",
            "[차량번호]",
            "[접수번호]",
            "[상세주소]",
            "[이름]",
            "[건강·복지정보]",
        ),
        strict=True,
    )
)


@pytest.mark.parametrize(
    ("higher", "lower"),
    tuple(
        zip(
            EXPECTED_CATEGORY_PRIORITY[:-1],
            EXPECTED_CATEGORY_PRIORITY[1:],
            strict=True,
        )
    ),
)
def test_every_adjacent_total_priority_pair_selects_higher(
    higher: PiiCategory,
    lower: PiiCategory,
) -> None:
    from sejong_ai_api.privacy.redaction import _select_findings

    candidates = (
        RedactionFinding(lower, 2, 10, TOKEN_BY_CATEGORY[lower]),
        RedactionFinding(higher, 2, 10, TOKEN_BY_CATEGORY[higher]),
    )
    assert _select_findings(candidates) == (candidates[1],)


def test_same_category_prefers_longer_then_earlier_overlap() -> None:
    from sejong_ai_api.privacy.redaction import _select_findings

    category = PiiCategory.EMAIL
    token = TOKEN_BY_CATEGORY[category]
    short = RedactionFinding(category, 2, 8, token)
    long = RedactionFinding(category, 2, 10, token)
    later_tie = RedactionFinding(category, 3, 11, token)
    assert _select_findings((short, long)) == (long,)
    assert _select_findings((later_tie, long)) == (long,)


@pytest.mark.parametrize(
    ("raw", "expected_text", "expected_category"),
    [
        ("연락처 070-1234-5678", "연락처 [전화번호]", PiiCategory.PHONE_NUMBER),
        ("연락처 010.1234.5678", "연락처 [전화번호]", PiiCategory.PHONE_NUMBER),
        (
            "면허번호 부산 12-34-567890-12",
            "면허번호 [여권·면허번호]",
            PiiCategory.PASSPORT_OR_LICENSE,
        ),
        ("비밀번호 !secret!", "비밀번호 [인증정보]", PiiCategory.AUTH_SECRET),
        (
            "비밀번호 sample-secret입니다.",
            "비밀번호 [인증정보]입니다.",
            PiiCategory.AUTH_SECRET,
        ),
        ("카드 3782-822463-10005", "카드 [카드번호]", PiiCategory.PAYMENT_CARD),
    ],
)
def test_identifier_separator_bypasses_are_not_fail_open(
    raw: str,
    expected_text: str,
    expected_category: PiiCategory,
) -> None:
    result = redact_question(raw)
    assert result.masked_text == expected_text
    assert [finding.category for finding in result.findings] == [expected_category]


def test_q_pii_003_a_masks_phone_even_when_input_calls_it_official() -> None:
    result = redact_question("세종시청 대표전화 044-000-0000")
    assert result.masked_text == "세종시청 대표전화 [전화번호]"
    assert [finding.category for finding in result.findings] == [PiiCategory.PHONE_NUMBER]


def test_q_pii_003_a_masks_representative_phone_value() -> None:
    result = redact_question("대표전화 1588-1234")
    assert result.masked_text == "대표전화 [전화번호]"
    assert [finding.category for finding in result.findings] == [PiiCategory.PHONE_NUMBER]


def test_input_is_not_mutated_and_repeated_results_are_identical() -> None:
    raw = "제 이름은 김가상이고 주소는 세종시 테스트길 34-5입니다."
    first = redact_question(raw)
    second = redact_question(raw)
    assert raw == "제 이름은 김가상이고 주소는 세종시 테스트길 34-5입니다."
    assert first == second


def test_safe_unchanged_result_does_not_reuse_the_input_string_object() -> None:
    raw = "일반질문"
    result = redact_question(raw)
    assert result.masked_text == raw
    assert result.masked_text is not raw


@pytest.mark.parametrize(
    ("raw", "reason"),
    [
        ("민원인은 가상씨라고 합니다.", UnresolvedReason.AMBIGUOUS_PERSON_NAME),
        ("샘플아파트 101동 202호", UnresolvedReason.AMBIGUOUS_DETAILED_ADDRESS),
        ("아름동 123 번지", UnresolvedReason.AMBIGUOUS_DETAILED_ADDRESS),
        ("아름동 123 - 4 번지", UnresolvedReason.AMBIGUOUS_DETAILED_ADDRESS),
        ("가상아파트 101 동 202 호", UnresolvedReason.AMBIGUOUS_DETAILED_ADDRESS),
        ("가상빌라 3 동 4 호", UnresolvedReason.AMBIGUOUS_DETAILED_ADDRESS),
        ("가상아파트 101동, 202호", UnresolvedReason.AMBIGUOUS_DETAILED_ADDRESS),
        ("가상아파트 101동-202호", UnresolvedReason.AMBIGUOUS_DETAILED_ADDRESS),
    ],
)
def test_ambiguous_context_returns_no_text(raw: str, reason: UnresolvedReason) -> None:
    result = redact_question(raw)
    assert result.masked_text is None
    assert result.safe_for_failure_storage is False
    assert result.safe_for_synthetic_provider is False
    assert result.unresolved_reason is reason


def test_residual_unclassified_numeric_identifier_is_closed() -> None:
    for raw in (
        "식별번호 123456789012",
        "식별번호 12345678901234567890",
        "식별번호 1234-5678-9012-3456-7890",
    ):
        result = redact_question(raw)
        assert result.masked_text is None
        assert result.safe_for_failure_storage is False
        assert result.safe_for_synthetic_provider is False
        assert result.unresolved_reason is UnresolvedReason.RESIDUAL_HIGH_RISK_PATTERN


@pytest.mark.parametrize(
    "raw",
    [
        "연락처 010\t0000\t0000",
        "연락처 010\n\n0000\n0000",
        "카드번호 0000\t\t0000\n0000 0000",
    ],
)
def test_allowed_whitespace_cannot_split_numeric_identifiers_fail_open(raw: str) -> None:
    result = redact_question(raw)
    assert result.masked_text is None
    assert result.findings == ()
    assert result.safe_for_failure_storage is False
    assert result.safe_for_synthetic_provider is False
    assert result.unresolved_reason is UnresolvedReason.RESIDUAL_HIGH_RISK_PATTERN


def test_allowed_whitespace_without_high_risk_identifier_stays_safe() -> None:
    raw = "운영시간\t09:00\n확인일 2026-07-20"
    assert redact_question(raw) == RedactionResult(raw, (), True, True, None)


def test_combining_mark_cannot_split_phone_identifier_fail_open() -> None:
    result = redact_question("010\ufe0f-1234-5678")
    assert result.masked_text is None
    assert result.safe_for_failure_storage is False
    assert result.safe_for_synthetic_provider is False
    assert result.unresolved_reason is UnresolvedReason.RESIDUAL_HIGH_RISK_PATTERN


def test_ordinary_emoji_variation_mark_is_not_rejected() -> None:
    raw = "☎️ 번호가 궁금해요"
    assert redact_question(raw) == RedactionResult(raw, (), True, True, None)


def test_repeated_separators_cannot_split_card_identifier_fail_open() -> None:
    result = redact_question("카드 4242  4242  4242  4242")
    assert result.masked_text is None
    assert result.safe_for_failure_storage is False
    assert result.safe_for_synthetic_provider is False
    assert result.unresolved_reason is UnresolvedReason.RESIDUAL_HIGH_RISK_PATTERN


@pytest.mark.parametrize(
    "raw",
    [
        "1588  1234",
        "1588\t1234",
        "1588\n1234",
        "010-\ufe0f-1234-5678",
        "010-\u0301-1234-5678",
        "010‐1234‐5678",
        "010–1234–5678",
        "값 7 010–1234–5678 8",
        "값 7 1588  1234 8",
        "01\u03010-1234-5678",
        "010-12\u030134-5678",
        "158\u03018-1234",
        "4242-42\u030142-4242-4242",
        "00010\u03011-3000000",
        "01\ufe0f0-1234-5678",
        "12\u0301가0000",
        "12가00\u030100",
        "123나0\ufe0f000",
        "김\u0301철수입니다.",
        "민원인은 김\u0301철수입니다.",
        "김철\u0301수이에요.",
        "당뇨\u0301 진단을 받았습니다.",
        "암\u0301 환자입니다.",
        "세종시 테스트길\u0301 34-5, 101동 202호",
        "민원인은 김철수\u0301 입니다.",
        "12가\u0301 0000",
    ],
)
def test_composed_numeric_obfuscation_cannot_fail_open(raw: str) -> None:
    result = redact_question(raw)
    assert result.masked_text is None
    assert result.safe_for_failure_storage is False
    assert result.safe_for_synthetic_provider is False
    assert result.unresolved_reason is UnresolvedReason.RESIDUAL_HIGH_RISK_PATTERN


@pytest.mark.parametrize(
    ("raw", "expected_text"),
    [
        ("대표전화 120", "대표전화 [전화번호]"),
        ("대표전화 1339", "대표전화 [전화번호]"),
        ("콜센터: 110", "콜센터: [전화번호]"),
    ],
)
def test_explicit_short_service_phone_is_masked(raw: str, expected_text: str) -> None:
    result = redact_question(raw)
    assert result.masked_text == expected_text
    assert [finding.category for finding in result.findings] == [PiiCategory.PHONE_NUMBER]


@pytest.mark.parametrize(
    ("raw", "reason"),
    [
        ("메일 홍길동@예시.한국", UnresolvedReason.RESIDUAL_HIGH_RISK_PATTERN),
        ("민원인은 김철수입니다.", UnresolvedReason.AMBIGUOUS_PERSON_NAME),
        ("주소 아름동 123번지 101호", UnresolvedReason.AMBIGUOUS_DETAILED_ADDRESS),
    ],
)
def test_explicit_but_unclassified_pii_context_is_closed(
    raw: str,
    reason: UnresolvedReason,
) -> None:
    result = redact_question(raw)
    assert result.masked_text is None
    assert result.safe_for_failure_storage is False
    assert result.safe_for_synthetic_provider is False
    assert result.unresolved_reason is reason


@pytest.mark.parametrize(
    ("raw", "reason"),
    [
        ("김철수", UnresolvedReason.AMBIGUOUS_PERSON_NAME),
        ("김 철 수", UnresolvedReason.AMBIGUOUS_PERSON_NAME),
        ("황길동", UnresolvedReason.AMBIGUOUS_PERSON_NAME),
        ("송가상", UnresolvedReason.AMBIGUOUS_PERSON_NAME),
        ("안테스트", UnresolvedReason.AMBIGUOUS_PERSON_NAME),
        ("류현진", UnresolvedReason.AMBIGUOUS_PERSON_NAME),
        ("엄정화", UnresolvedReason.AMBIGUOUS_PERSON_NAME),
        ("제갈량", UnresolvedReason.AMBIGUOUS_PERSON_NAME),
        ("김철수입니다.", UnresolvedReason.AMBIGUOUS_PERSON_NAME),
        ("김 철수입니다.", UnresolvedReason.AMBIGUOUS_PERSON_NAME),
        ("김 철 수입니다.", UnresolvedReason.AMBIGUOUS_PERSON_NAME),
        ("김철수 입니다.", UnresolvedReason.AMBIGUOUS_PERSON_NAME),
        ("김 철 수 입니다.", UnresolvedReason.AMBIGUOUS_PERSON_NAME),
        ("김철수 씨입니다.", UnresolvedReason.AMBIGUOUS_PERSON_NAME),
        ("김철수 님 입니다.", UnresolvedReason.AMBIGUOUS_PERSON_NAME),
        ("엄정화입니다.", UnresolvedReason.AMBIGUOUS_PERSON_NAME),
        ("류현진입니다.", UnresolvedReason.AMBIGUOUS_PERSON_NAME),
        ("제갈량입니다.", UnresolvedReason.AMBIGUOUS_PERSON_NAME),
        ("아름동 123번지", UnresolvedReason.AMBIGUOUS_DETAILED_ADDRESS),
        ("홍길동@예시.한국", UnresolvedReason.RESIDUAL_HIGH_RISK_PATTERN),
        ("메일 홍길동@예시.한국 [이메일]", UnresolvedReason.RESIDUAL_HIGH_RISK_PATTERN),
        (
            "메일 홍길동@예시.한국 test@example.invalid",
            UnresolvedReason.RESIDUAL_HIGH_RISK_PATTERN,
        ),
        ("메일 문의 홍길동@예시.한국", UnresolvedReason.RESIDUAL_HIGH_RISK_PATTERN),
        ("메일은 홍길동@예시.한국", UnresolvedReason.RESIDUAL_HIGH_RISK_PATTERN),
    ],
)
def test_independent_and_token_or_inquiry_suffix_pii_is_closed(
    raw: str,
    reason: UnresolvedReason,
) -> None:
    result = redact_question(raw)
    assert result.masked_text is None
    assert result.safe_for_failure_storage is False
    assert result.safe_for_synthetic_provider is False
    assert result.unresolved_reason is reason


@pytest.mark.parametrize(
    "raw",
    [
        "아름동입니다.",
        "전입신고입니다.",
        "이메일입니다.",
        "신청서입니다.",
        "민원인입니다.",
        "민원인 님입니다.",
    ],
)
def test_standalone_admin_terms_are_not_person_names(raw: str) -> None:
    assert redact_question(raw) == RedactionResult(raw, (), True, True, None)


def test_masked_email_followed_by_ascii_public_term_stays_safe() -> None:
    result = redact_question("메일 test@example.invalid FAQ 확인")
    assert result.masked_text == "메일 [이메일] FAQ 확인"
    assert [finding.category for finding in result.findings] == [PiiCategory.EMAIL]


@pytest.mark.parametrize(
    ("raw", "expected_text", "expected_category"),
    [
        ("위치는 36.5,127.25", "위치는 [정밀위치]", PiiCategory.PRECISE_LOCATION),
        ("한누리대로 123 101동 202호", "[상세주소]", PiiCategory.DETAILED_ADDRESS),
        ("진단명 희귀가상증후군", "진단명 [건강·복지정보]", PiiCategory.SENSITIVE_HEALTH_WELFARE),
        ("복지대상 가상지원등급", "복지대상 [건강·복지정보]", PiiCategory.SENSITIVE_HEALTH_WELFARE),
    ],
)
def test_contextual_labeled_pii_bypasses_are_not_fail_open(
    raw: str,
    expected_text: str,
    expected_category: PiiCategory,
) -> None:
    result = redact_question(raw)
    assert result.masked_text == expected_text
    assert [finding.category for finding in result.findings] == [expected_category]


@pytest.mark.parametrize(
    ("raw", "expected_text", "expected_category"),
    [
        (
            "주소 세종시 테스트길 34-5, 101동 202호",
            "주소 [상세주소]",
            PiiCategory.DETAILED_ADDRESS,
        ),
        (
            "진단명 희귀 가상 증후군",
            "진단명 [건강·복지정보]",
            PiiCategory.SENSITIVE_HEALTH_WELFARE,
        ),
        ("성명: 김철수(가명)", "성명: [이름](가명)", PiiCategory.NAME),
        ("신청인 이름 홍길동", "신청인 이름 [이름]", PiiCategory.NAME),
        ("성명은 홍길동", "성명은 [이름]", PiiCategory.NAME),
    ],
)
def test_contextual_rule_cannot_leave_raw_value_tail(
    raw: str,
    expected_text: str,
    expected_category: PiiCategory,
) -> None:
    result = redact_question(raw)
    assert result.masked_text == expected_text
    assert [finding.category for finding in result.findings] == [expected_category]


@pytest.mark.parametrize(
    ("raw", "expected_text", "expected_category"),
    [
        ("비밀번호 sample secret", "비밀번호 [인증정보]", PiiCategory.AUTH_SECRET),
        ("비밀번호는 실제비밀", "비밀번호는 [인증정보]", PiiCategory.AUTH_SECRET),
        ("비밀번호 가나", "비밀번호 [인증정보]", PiiCategory.AUTH_SECRET),
        ("비밀번호 실제 비밀", "비밀번호 [인증정보]", PiiCategory.AUTH_SECRET),
        ("OTP 가 나 다 라", "OTP [인증정보]", PiiCategory.AUTH_SECRET),
        ("이름 김 철 수", "이름 [이름]", PiiCategory.NAME),
        ("이름을 김철수라고 합니다", "이름을 [이름]라고 합니다", PiiCategory.NAME),
        ("진단명 암", "진단명 [건강·복지정보]", PiiCategory.SENSITIVE_HEALTH_WELFARE),
        (
            "복지대상 한부모 가족",
            "복지대상 [건강·복지정보]",
            PiiCategory.SENSITIVE_HEALTH_WELFARE,
        ),
        (
            "진단명 희귀 가상 매우 위험 증후군",
            "진단명 [건강·복지정보]",
            PiiCategory.SENSITIVE_HEALTH_WELFARE,
        ),
        (
            "당뇨병 환자입니다.",
            "[건강·복지정보]입니다.",
            PiiCategory.SENSITIVE_HEALTH_WELFARE,
        ),
        (
            "우울증 중증 치료 중입니다.",
            "[건강·복지정보]입니다.",
            PiiCategory.SENSITIVE_HEALTH_WELFARE,
        ),
        (
            "암 4기 환자입니다.",
            "[건강·복지정보]입니다.",
            PiiCategory.SENSITIVE_HEALTH_WELFARE,
        ),
        (
            "천식 환자입니다.",
            "[건강·복지정보]입니다.",
            PiiCategory.SENSITIVE_HEALTH_WELFARE,
        ),
        (
            "치매 진단을 받았습니다.",
            "[건강·복지정보]을 받았습니다.",
            PiiCategory.SENSITIVE_HEALTH_WELFARE,
        ),
        (
            "정신과 치료 중입니다.",
            "[건강·복지정보]입니다.",
            PiiCategory.SENSITIVE_HEALTH_WELFARE,
        ),
        (
            "차상위계층입니다.",
            "[건강·복지정보]입니다.",
            PiiCategory.SENSITIVE_HEALTH_WELFARE,
        ),
        (
            "한부모가족입니다.",
            "[건강·복지정보]입니다.",
            PiiCategory.SENSITIVE_HEALTH_WELFARE,
        ),
        ("민원인 김철수", "민원인 [이름]", PiiCategory.NAME),
        ("민원인: 김철수", "민원인: [이름]", PiiCategory.NAME),
        ("보호자 김철수", "보호자 [이름]", PiiCategory.NAME),
        ("한누리대로123 101동202호", "[상세주소]", PiiCategory.DETAILED_ADDRESS),
        ("세종시 가상로12-3", "[상세주소]", PiiCategory.DETAILED_ADDRESS),
        ("가상길34-5", "[상세주소]", PiiCategory.DETAILED_ADDRESS),
        (
            "세종시 가상로12,101동202호",
            "[상세주소]",
            PiiCategory.DETAILED_ADDRESS,
        ),
        (
            "제 계좌는 110-123-456789입니다.",
            "제 계좌는 [계좌번호]입니다.",
            PiiCategory.FINANCIAL_ACCOUNT,
        ),
        ("인증코드 123456", "인증코드 [인증정보]", PiiCategory.AUTH_SECRET),
        ("보안코드 ABC123", "보안코드 [인증정보]", PiiCategory.AUTH_SECRET),
        ("여권 M12345678", "여권 [여권·면허번호]", PiiCategory.PASSPORT_OR_LICENSE),
        (
            "운전면허 11-12-123456-78",
            "운전면허 [여권·면허번호]",
            PiiCategory.PASSPORT_OR_LICENSE,
        ),
        ("+82-2-1234-5678", "[전화번호]", PiiCategory.PHONE_NUMBER),
        ("36.5°N 127.25°E", "[정밀위치]", PiiCategory.PRECISE_LOCATION),
    ],
)
def test_explicit_context_masks_complete_bounded_value(
    raw: str,
    expected_text: str,
    expected_category: PiiCategory,
) -> None:
    result = redact_question(raw)
    assert result.masked_text == expected_text
    assert [finding.category for finding in result.findings] == [expected_category]


@pytest.mark.parametrize(
    "raw",
    [
        "성명: 김철수(본인)",
        "이름: 金哲洙",
        "주소 세종시 테스트길 34-5, 101동 202호 303호",
        "비밀번호는 어디서 변경하나요? 실제비밀",
        "이름은 어디에 쓰나요? 김철수",
        "진단명은 어디서 확인하나요? 암",
        "대표전화는 어디서 확인하나요? 1339",
        "비밀번호는 어디서 실제비밀 확인하나요?",
        "이름은 어디에 김철수 쓰나요?",
        "진단명은 어디서 암 확인하나요?",
        "세종시 테스트길 34-5, 101동 202호 303호",
        "당뇨 진단 2형입니다.",
        "4기 암 환자입니다.",
        "303호 세종시 테스트길 34-5, 101동 202호",
        "식별번호 2026-07-20 09:00",
        "연락처 김철수 010-1234-5678",
        "이메일 김철수 test@example.invalid",
        "test @example.invalid",
        "홍길동 @예시.한국",
        "주소 김철수 가상로 12가0000",
        "주소 홍길동 세종시 가상로 12가0000",
        "0 1 0 1 2 3 4 5 6 7 8",
        "1 5 8 8 1 2 3 4",
        "4 2 4 2 4 2 4 2 4 2 4 2 4 2 4 2",
        "당뇨 진단 test@example.invalid 2형입니다.",
        "암 환자 test@example.invalid 4기입니다.",
        "세종시 테스트길 34-5, 101동 202호 test@example.invalid 303호",
        "010-1234-5678 test@example.invalid 내선 1234",
        "(010) 1234-5678",
        "(044) 123-4567",
        "010,1234,5678",
        "010_1234_5678",
        "4242,4242,4242,4242",
        "000101(3)000000",
        "010|1234|5678",
        "주소 변경 방법 알려줘. 세종시 가상로12-3",
        "세종시 테스트길 34-5, 101동 202호\n303호",
        "세종시 테스트길 34-5\n101호",
        "당뇨 진단을 받았습니다.\n2형입니다.",
        "암 환자입니다.\n4기입니다.",
        "test\n@\nexample.invalid",
        "010·1234·5678",
        "000101•3000000",
        "4242∙4242∙4242∙4242",
        "010~1234~5678",
        "010+1234+5678",
        "010*1234*5678",
        "010&1234&5678",
        "010=1234=5678",
    ],
)
def test_unclassified_explicit_context_tail_is_closed(raw: str) -> None:
    result = redact_question(raw)
    assert result.masked_text is None
    assert result.safe_for_failure_storage is False
    assert result.safe_for_synthetic_provider is False
    assert result.unresolved_reason is UnresolvedReason.RESIDUAL_HIGH_RISK_PATTERN


@pytest.mark.parametrize(
    ("raw", "reason"),
    [
        ("김철수 010-1234-5678", UnresolvedReason.AMBIGUOUS_PERSON_NAME),
        ("김철수 test@example.invalid", UnresolvedReason.AMBIGUOUS_PERSON_NAME),
        ("홍길동 000101-3000000", UnresolvedReason.AMBIGUOUS_PERSON_NAME),
        ("송가상 010-1234-5678", UnresolvedReason.AMBIGUOUS_PERSON_NAME),
        ("세종시 아름동 123-4", UnresolvedReason.AMBIGUOUS_DETAILED_ADDRESS),
        ("아름동 123-4 101호", UnresolvedReason.AMBIGUOUS_DETAILED_ADDRESS),
        ("가상오피스텔 101동 202호", UnresolvedReason.AMBIGUOUS_DETAILED_ADDRESS),
        ("첫마을 1단지 101동 202호", UnresolvedReason.AMBIGUOUS_DETAILED_ADDRESS),
    ],
)
def test_independent_name_and_address_variants_are_closed(
    raw: str,
    reason: UnresolvedReason,
) -> None:
    result = redact_question(raw)
    assert result.masked_text is None
    assert result.safe_for_failure_storage is False
    assert result.safe_for_synthetic_provider is False
    assert result.unresolved_reason is reason


@pytest.mark.parametrize(
    ("raw", "expected_text"),
    [
        ("12 가 0000", "[차량번호]"),
        ("1 2 가 0 0 0 0", "[차량번호]"),
    ],
)
def test_spaced_vehicle_plate_is_masked(raw: str, expected_text: str) -> None:
    result = redact_question(raw)
    assert result.masked_text == expected_text
    assert [finding.category for finding in result.findings] == [PiiCategory.VEHICLE_PLATE]


def test_phone_extension_is_masked_with_phone_number() -> None:
    result = redact_question("010-1234-5678 내선 1234")
    assert result.masked_text == "[전화번호]"
    assert [finding.category for finding in result.findings] == [PiiCategory.PHONE_NUMBER]


def test_fixed_tokens_are_not_reclassified_as_raw_pii() -> None:
    for raw in (
        "비밀번호 [인증정보] 진단명 [건강·복지정보]",
        "인증 문자 [인증정보]",
    ):
        result = redact_question(raw)
        assert result == RedactionResult(raw, (), True, True, None)


@pytest.mark.parametrize(
    "raw",
    [
        "비밀번호 [인증정보] sample-secret",
        "주소 [상세주소], 101동 202호",
        "진단명 [건강·복지정보] 가상 증후군",
    ],
)
def test_fixed_token_cannot_exempt_trailing_raw_pii(raw: str) -> None:
    result = redact_question(raw)
    assert result.masked_text is None
    assert result.safe_for_failure_storage is False
    assert result.safe_for_synthetic_provider is False
    assert result.unresolved_reason is UnresolvedReason.RESIDUAL_HIGH_RISK_PATTERN


@pytest.mark.parametrize(
    ("raw", "expected_text", "expected_category"),
    [
        ("비밀번호 실제비밀", "비밀번호 [인증정보]", PiiCategory.AUTH_SECRET),
        ("OTP 가나다라", "OTP [인증정보]", PiiCategory.AUTH_SECRET),
        ("이름 김 철수", "이름 [이름]", PiiCategory.NAME),
    ],
)
def test_explicit_hangul_pii_context_cannot_fail_open(
    raw: str,
    expected_text: str,
    expected_category: PiiCategory,
) -> None:
    result = redact_question(raw)
    assert result.masked_text == expected_text
    assert [finding.category for finding in result.findings] == [expected_category]


@pytest.mark.parametrize("raw", ["비밀번호입니다.", "OTP설정방법"])
def test_auth_label_without_value_delimiter_stays_safe(raw: str) -> None:
    assert redact_question(raw) == RedactionResult(raw, (), True, True, None)


def test_mismatched_fixed_token_cannot_be_trusted() -> None:
    result = redact_question("비밀번호 [전화번호]")
    assert result.masked_text is None
    assert result.safe_for_failure_storage is False
    assert result.safe_for_synthetic_provider is False
    assert result.unresolved_reason is UnresolvedReason.RESIDUAL_HIGH_RISK_PATTERN


@pytest.mark.parametrize(
    "raw",
    [
        "주민 등록 번호 [건강·복지정보]",
        "주민 등록 번호 [주민등록번호] raw-tail",
    ],
)
def test_spaced_resident_label_cannot_bypass_token_provenance(raw: str) -> None:
    result = redact_question(raw)
    assert result.masked_text is None
    assert result.safe_for_failure_storage is False
    assert result.safe_for_synthetic_provider is False
    assert result.unresolved_reason is UnresolvedReason.RESIDUAL_HIGH_RISK_PATTERN


def test_spaced_resident_label_accepts_only_the_matching_fixed_token() -> None:
    raw = "주민 등록 번호 [주민등록번호]"
    assert redact_question(raw) == RedactionResult(raw, (), True, True, None)


_VALUELESS_PII_INQUIRIES = (
    "비밀번호는 어디서 변경하나요?",
    "비밀번호는 어디에서 변경하나요?",
    "비밀번호 변경 방법을 알려주세요.",
    "비밀번호를 바꾸는 방법을 알려주세요.",
    "비밀번호는 어떻게 바꾸나요?",
    "비밀번호는 어디서 바꿔요?",
    "비밀번호를 변경하려면 어떻게 하나요?",
    "비밀번호를 잊어버렸어요.",
    "비밀번호를 잊어버렸는데 어떻게 해요?",
    "비밀번호 변경은 어떻게 해요?",
    "비밀번호가 기억나지 않아요.",
    "비밀번호는  어디서 변경하나요?",
    "비밀번호는 어디서 변경하나요? ",
    "주소를 바꾸려면 어떻게 하나요?",
    "주소 변경 방법을 알려주세요.",
    "주소 변경 방법 알려줘.",
    "주소는 어떻게 변경하나요?",
    "주소 이전은 어떻게 하나요?",
    "주소 변경하려면 어디로 가나요?",
    "전입신고 주소 변경 방법을 알려주세요.",
    "대표전화는 어디서 확인하나요?",
    "대표번호 좀 알려주세요.",
    "대표전화가 궁금해요.",
    "대표 전화가 궁금해요.",
    "콜센터 번호 알려주세요.",
    "전화번호가 어떻게 되나요?",
    "이름은 어디에 쓰나요?",
    "이름은 꼭 필요한가요?",
    "이름을 왜 입력해야 하나요?",
    "신청인 이름을 어디에 쓰나요?",
    "진단명은 어디서 확인하나요?",
    "진단명 확인할 수 있나요?",
    "진단명 확인 방법 알려줘.",
    "복지대상인지 어떻게 확인하나요?",
)

_NATURAL_VALUELESS_ADMIN_QUESTIONS = (
    "전입신고 후 주소 변경은 언제 하나요?",
    "주소는 어디까지 써야 하나요?",
    "주소를 적지 않고 전입신고할 수 있나요?",
    "주소 변경 통보서비스 신청 방법은 무엇인가요?",
    "0507 안심번호도 연락처로 쓸 수 있나요?",
    "전화 번호 없이 전입신고할 수 있나요?",
    "휴대폰 번호는 꼭 필요한가요?",
    "대표 전화 번호는 어디서 보나요?",
    "주민 등록 번호는 증명서에 표시되나요?",
    "주민등록 번호 뒷자리는 가려지나요?",
    "여권 번호는 어디에 쓰나요?",
    "운전 면허 번호가 꼭 필요한가요?",
    "면허증 번호 없이 신청할 수 있나요?",
    "계좌 번호 없이 환불받을 수 있나요?",
    "통장 번호는 왜 필요한가요?",
    "카드 번호를 입력해야 하나요?",
    "다이너스 카드를 쓸 수 있나요?",
    "비번을 잊으면 어떻게 하나요?",
    "패스워드 변경 방법이 궁금해요.",
    "OTP 번호는 몇 분 동안 유효한가요?",
    "PIN 번호는 어디에 쓰나요?",
    "본인확인 코드는 어디에 쓰나요?",
    "인증 문자는 언제 오나요?",
    "차량 번호가 없어도 자동차세를 낼 수 있나요?",
    "번호판을 바꾸면 신고해야 하나요?",
    "접수 코드는 어디에서 확인하나요?",
    "접수 ID는 어디에 쓰나요?",
    "민원 번호 처리 상태는 어디서 보나요?",
    "위도와 경도는 어디에 쓰나요?",
    "좌표는 왜 필요한가요?",
    "현재 위치를 보내야 하나요?",
    "이름 없이 증명서를 발급할 수 있나요?",
    "성명은 어디에 표시되나요?",
    "신청자 이름이 꼭 필요한가요?",
)

_P0_VALUELESS_WORKFLOW_QUESTIONS = (
    "전입신고 후 주소 변경은 어떻게 하나요?",
    "전입신고할 때 주소는 어디까지 적어야 하나요?",
    "전입신고 주소가 잘못 등록됐어요.",
    "새 주소가 등본에 아직 안 나와요.",
    "상세주소를 빼고 전입신고해도 되나요?",
    "전입신고할 때 주민등록번호가 필요한가요?",
    "주민번호 뒷자리는 안 적어도 되나요?",
    "신청인 이름이 틀렸는데 고칠 수 있나요?",
    "성명은 한글로만 적어야 하나요?",
    "전화번호를 잘못 적었는데 수정할 수 있나요?",
    "연락처가 바뀌면 다시 신고해야 하나요?",
    "이메일 대신 문자로 결과를 받을 수 있나요?",
    "접수번호를 못 찾겠어요.",
    "전입신고 접수번호는 언제 발급되나요?",
    "민원번호가 아직 안 보여요.",
    "인증번호가 아직 안 왔어요.",
    "인증번호를 다시 보내주세요.",
    "전입신고 인증번호는 몇 분 동안 유효한가요?",
    "비밀번호를 모르겠어요.",
    "비밀번호를 잊어버렸는데 다시 설정하려면 어떻게 하나요?",
    "등본 주소가 잘못 나왔어요.",
    "초본에 이전 주소가 빠졌어요.",
    "증명서에 주민번호가 몇 자리 나오나요?",
    "등본에는 주민번호 앞자리만 표시되나요?",
    "주민번호를 가린 등본도 발급되나요?",
    "증명서 이름이 잘못 표시됐어요.",
    "증명서 신청인 이름이 달라도 발급되나요?",
    "증명서 성명은 한글로 나오나요?",
    "증명서 전화번호를 잘못 입력했어요.",
    "연락처 없이 증명서를 신청할 수 있나요?",
    "증명서 이메일 전송이 안 돼요.",
    "증명서 접수번호를 못 찾겠어요.",
    "접수번호가 없어도 재발급할 수 있나요?",
    "증명서 인증번호가 아직 안 왔어요.",
    "인증번호를 다시 받을 수 있나요?",
    "등본 발급 비밀번호를 잊었으면 어떻게 하나요?",
    "증명서 비밀번호를 재설정할 수 있나요?",
    "무인발급기에서 카드번호를 꼭 입력하나요?",
    "카드번호 없이 수수료를 결제할 수 있나요?",
    "대형폐기물 신청을 취소하면 환불되나요?",
    "대형폐기물 배출 주소를 잘못 적었어요.",
    "배출 주소가 바뀌면 신고를 수정해야 하나요?",
    "배출 위치를 잘못 선택했어요.",
    "현재 위치 대신 주소를 직접 적나요?",
    "신청인 이름이 스티커에 나오나요?",
    "신고자 이름을 잘못 입력했어요.",
    "전화번호를 잘못 적어서 수거 연락을 못 받았어요.",
    "연락처 없이 대형폐기물을 신고할 수 있나요?",
    "대형폐기물 이메일 알림이 안 와요.",
    "대형폐기물 접수번호를 못 찾겠어요.",
    "접수번호가 없어도 신고를 취소할 수 있나요?",
    "대형폐기물 신고 인증번호가 오지 않아요.",
    "인증번호를 다시 보내줄 수 있나요?",
    "대형폐기물 비밀번호가 기억나지 않아요.",
    "비밀번호를 재설정하면 기존 신고를 볼 수 있나요?",
    "카드번호 없이 대형폐기물 수수료를 낼 수 있나요?",
    "지방세 고지서의 주소를 바꾸려면 어떻게 하나요?",
    "지방세 고지서 주소가 잘못됐어요.",
    "고지서 상세주소를 수정할 수 있나요?",
    "지방세 고지서 주민번호가 그대로 보여요.",
    "주민번호 뒷자리를 가린 고지서를 받을 수 있나요?",
    "납세자 이름이 잘못 표시됐어요.",
    "지방세 확인서 성명은 한글로 나오나요?",
    "지방세 전화번호를 잘못 입력했어요.",
    "지방세 이메일 고지가 안 와요.",
    "지방세 접수번호를 못 찾겠어요.",
    "접수번호 없이 납부 확인이 되나요?",
    "지방세 인증번호가 아직 안 왔어요.",
    "인증번호를 다시 받을 수 있나요?",
    "지방세 비밀번호가 기억나지 않아요.",
    "비밀번호를 재설정할 수 있나요?",
    "자동차세 차량번호가 잘못 표시됐어요.",
    "차량번호를 바꾸면 자동차세 신고도 해야 하나요?",
    "번호판을 바꿨는데 고지서는 언제 바뀌나요?",
    "카드번호 없이 자동차세를 낼 수 있나요?",
    "지방세 환급 계좌번호를 잘못 적었어요.",
    "계좌번호를 바꾸려면 어디에 신청하나요?",
    "환급 계좌는 납세자 이름과 같아야 하나요?",
)


@pytest.mark.parametrize("raw", _VALUELESS_PII_INQUIRIES)
def test_value_less_pii_inquiry_stays_exactly_unchanged(raw: str) -> None:
    assert redact_question(raw) == RedactionResult(raw, (), True, True, None)


@pytest.mark.parametrize("raw", _NATURAL_VALUELESS_ADMIN_QUESTIONS)
def test_natural_value_less_admin_question_stays_exactly_unchanged(raw: str) -> None:
    assert redact_question(raw) == RedactionResult(raw, (), True, True, None)


@pytest.mark.parametrize("raw", _P0_VALUELESS_WORKFLOW_QUESTIONS)
def test_p0_value_less_workflow_question_stays_exactly_unchanged(raw: str) -> None:
    assert redact_question(raw) == RedactionResult(raw, (), True, True, None)


@pytest.mark.parametrize("raw", _VALUELESS_PII_INQUIRIES)
@pytest.mark.parametrize(
    "sentinel",
    ("김철수", "010-1234-5678", "test@example.invalid", "실제비밀", "암"),
)
def test_value_less_inquiry_allowlist_cannot_hide_appended_raw_pii(
    raw: str,
    sentinel: str,
) -> None:
    result = redact_question(f"{raw} {sentinel}")
    assert result.masked_text is None
    assert result.safe_for_failure_storage is False
    assert result.safe_for_synthetic_provider is False


@pytest.mark.parametrize("raw", _NATURAL_VALUELESS_ADMIN_QUESTIONS)
@pytest.mark.parametrize(
    "sentinel",
    ("김철수", "010-1234-5678", "test@example.invalid"),
)
def test_natural_value_less_question_cannot_hide_appended_raw_pii(
    raw: str,
    sentinel: str,
) -> None:
    result = redact_question(f"{raw} {sentinel}")
    assert result.masked_text is None or sentinel not in result.masked_text
    if result.masked_text is None:
        assert result.safe_for_failure_storage is False
        assert result.safe_for_synthetic_provider is False
    else:
        assert result.findings


@pytest.mark.parametrize(
    "raw",
    [
        "비밀번호는 어디서 변경하나요?",
        "이름은 어디에 쓰나요?",
        "진단명은 어디서 확인하나요?",
        "대표전화는 어디서 확인하나요?",
        "신청인 이름을 어디에 쓰나요?",
        "신청인은 어디에 쓰나요?",
        "수수료 120원",
        "문서 코드 1339",
        "확인일 2026-07-20 09:00",
        "운영시간 09:00\n확인일 2026-07-20",
        "1️⃣ 전입신고",
        "수수료 비교 1000 2000 3000",
        "처리기간 10 20 30 40 50일",
        "운영시간 09 00 18 00 20 00",
        "주소를 바꾸려면 어떻게 하나요?",
        "대표번호 좀 알려주세요.",
        "비밀번호를 잊어버렸어요.",
        "비밀번호를  어디서 변경하나요?",
        "진단명 확인할 수 있나요?",
        "문서에서 A @ B 표기를 사용합니다.",
        "처리 단계 (1), (2), (3)을 확인하세요.",
        "기간 2026-07-01 ~ 2026-07-07",
        "연도 2020, 2021, 2022, 2023",
        "금액 1,000 / 2,000 / 3,000 / 4,000",
        "문서번호 2026-0001, 2026-0002",
        "비밀번호를 바꾸는 방법을 알려주세요.",
        "비밀번호를 변경하려면 어떻게 하나요?",
        "주소 변경 방법 알려줘.",
        "대표전화가 궁금해요.",
        "전화번호가 어떻게 되나요?",
        "이름은 꼭 필요한가요?",
        "이름은 어디에 쓰나요?   ",
    ],
)
def test_context_and_numeric_security_controls_stay_safe(raw: str) -> None:
    assert redact_question(raw) == RedactionResult(raw, (), True, True, None)


@pytest.mark.parametrize(
    "raw",
    [
        "전입신고",
        "주민등록",
        "주민센터",
        "지방세",
        "가족관계",
        "여권",
        "계좌",
        "주소",
        "위치",
        "전화번호",
        "복지대상",
        "진단명",
        "인증번호",
        "민원번호",
        "차량번호",
        "한솔동",
        "도담동",
        "아름동",
        "조치원읍",
    ],
)
def test_supported_admin_terms_and_selected_regions_are_not_names(raw: str) -> None:
    assert redact_question(raw) == RedactionResult(raw, (), True, True, None)


@pytest.mark.parametrize(
    "raw",
    [
        "전입신고 후 주소 변경은 어떻게 하나요?",
        "주소 변경을 언제까지 해야 하나요?",
        "주소 변경 통보서비스는 어떻게 신청하나요?",
        "전화번호 없이 전입신고할 수 있나요?",
        "증명서에 주민번호가 모두 나오나요?",
        "차량번호가 없어도 자동차세를 낼 수 있나요?",
        "대형폐기물 신고를 바꾸거나 취소하려면 어떻게 해요?",
        "자동차세 고지는 어디서 확인하나요?",
        "대형폐기물 신청을 취소하면 환불되나요?",
    ],
)
def test_supported_admin_questions_with_pii_labels_stay_safe(raw: str) -> None:
    assert redact_question(raw) == RedactionResult(raw, (), True, True, None)


@pytest.mark.parametrize(
    ("raw", "expected_text", "expected_category"),
    [
        ("저는 김철수 라고 합니다.", "저는 [이름] 라고 합니다.", PiiCategory.NAME),
        (
            "면허 번호 11-12-123456-78",
            "면허 번호 [여권·면허번호]",
            PiiCategory.PASSPORT_OR_LICENSE,
        ),
        (
            "운전 면허 번호 11-12-123456-78",
            "운전 면허 번호 [여권·면허번호]",
            PiiCategory.PASSPORT_OR_LICENSE,
        ),
        (
            "여권 번호 M12345678",
            "여권 번호 [여권·면허번호]",
            PiiCategory.PASSPORT_OR_LICENSE,
        ),
        (
            "주민 등록 번호 000101-3000000",
            "주민 등록 번호 [주민등록번호]",
            PiiCategory.RESIDENT_REGISTRATION_NUMBER,
        ),
        (
            "면허증 번호 11-12-123456-78",
            "면허증 번호 [여권·면허번호]",
            PiiCategory.PASSPORT_OR_LICENSE,
        ),
        (
            "운전면허증 11-12-123456-78",
            "운전면허증 [여권·면허번호]",
            PiiCategory.PASSPORT_OR_LICENSE,
        ),
        (
            "0507-1234-5678로 연락해 주세요.",
            "[전화번호]로 연락해 주세요.",
            PiiCategory.PHONE_NUMBER,
        ),
        (
            "030-12345-6789로 연락해 주세요.",
            "[전화번호]로 연락해 주세요.",
            PiiCategory.PHONE_NUMBER,
        ),
        (
            "통장번호 123-456-789012",
            "통장번호 [계좌번호]",
            PiiCategory.FINANCIAL_ACCOUNT,
        ),
        (
            "카드 번호 4000 0000 0000 6",
            "카드 번호 [카드번호]",
            PiiCategory.PAYMENT_CARD,
        ),
        ("비번은 qwerty1234", "비번은 [인증정보]", PiiCategory.AUTH_SECRET),
        ("패스워드는 qwerty1234", "패스워드는 [인증정보]", PiiCategory.AUTH_SECRET),
        ("OTP번호는 123456", "OTP번호는 [인증정보]", PiiCategory.AUTH_SECRET),
        ("PIN번호 1234", "PIN번호 [인증정보]", PiiCategory.AUTH_SECRET),
        ("인증 코드는 123456", "인증 코드는 [인증정보]", PiiCategory.AUTH_SECRET),
        ("인증문자 123456", "인증문자 [인증정보]", PiiCategory.AUTH_SECRET),
        (
            "본인확인 코드 123456",
            "본인확인 코드 [인증정보]",
            PiiCategory.AUTH_SECRET,
        ),
        ("12가-0000", "[차량번호]", PiiCategory.VEHICLE_PLATE),
        ("12-가-0000", "[차량번호]", PiiCategory.VEHICLE_PLATE),
        ("12·가·0000", "[차량번호]", PiiCategory.VEHICLE_PLATE),
        (
            "접수 번호 SJ-2026-123456",
            "접수 번호 [접수번호]",
            PiiCategory.CASE_REFERENCE,
        ),
        (
            "접수번호 SJ-2026-123456 처리됐어?",
            "접수번호 [접수번호] 처리됐어?",
            PiiCategory.CASE_REFERENCE,
        ),
        (
            "민원 번호는 2026-123456",
            "민원 번호는 [접수번호]",
            PiiCategory.CASE_REFERENCE,
        ),
        (
            "접수코드 SJ-2026-123456",
            "접수코드 [접수번호]",
            PiiCategory.CASE_REFERENCE,
        ),
        (
            "접수 ID SJ-2026-123456",
            "접수 ID [접수번호]",
            PiiCategory.CASE_REFERENCE,
        ),
        ("고혈압이 있습니다.", "[건강·복지정보]이 있습니다.", PiiCategory.SENSITIVE_HEALTH_WELFARE),
        ("암 4기입니다.", "[건강·복지정보]입니다.", PiiCategory.SENSITIVE_HEALTH_WELFARE),
        ("장애 3급입니다.", "[건강·복지정보]입니다.", PiiCategory.SENSITIVE_HEALTH_WELFARE),
        ("중증장애인입니다.", "[건강·복지정보]입니다.", PiiCategory.SENSITIVE_HEALTH_WELFARE),
        (
            "기초생활수급을 받고 있습니다.",
            "[건강·복지정보]을 받고 있습니다.",
            PiiCategory.SENSITIVE_HEALTH_WELFARE,
        ),
        (
            "진단은 당뇨입니다.",
            "진단은 [건강·복지정보]입니다.",
            PiiCategory.SENSITIVE_HEALTH_WELFARE,
        ),
        ("당뇨가 있어요.", "[건강·복지정보]가 있어요.", PiiCategory.SENSITIVE_HEALTH_WELFARE),
        ("고혈압이 있어요.", "[건강·복지정보]이 있어요.", PiiCategory.SENSITIVE_HEALTH_WELFARE),
        (
            "기초생활수급을 받고 있어요.",
            "[건강·복지정보]을 받고 있어요.",
            PiiCategory.SENSITIVE_HEALTH_WELFARE,
        ),
        ("차상위 계층입니다.", "[건강·복지정보]입니다.", PiiCategory.SENSITIVE_HEALTH_WELFARE),
        ("한부모 가족입니다.", "[건강·복지정보]입니다.", PiiCategory.SENSITIVE_HEALTH_WELFARE),
        ("희귀병이 있습니다.", "[건강·복지정보]이 있습니다.", PiiCategory.SENSITIVE_HEALTH_WELFARE),
        ("임신 중입니다.", "[건강·복지정보]입니다.", PiiCategory.SENSITIVE_HEALTH_WELFARE),
        ("좌표 36.5 127.25", "좌표 [정밀위치]", PiiCategory.PRECISE_LOCATION),
        ("위도: 36.5 경도: 127.25", "위도: [정밀위치]", PiiCategory.PRECISE_LOCATION),
        ("위도 36.5, 경도 127.25", "위도 [정밀위치]", PiiCategory.PRECISE_LOCATION),
        ("36.5 127.25에 있습니다.", "[정밀위치]에 있습니다.", PiiCategory.PRECISE_LOCATION),
        ("36.5;127.25", "[정밀위치]", PiiCategory.PRECISE_LOCATION),
        ("N36.5 E127.25", "[정밀위치]", PiiCategory.PRECISE_LOCATION),
        (
            "36°29'15\"N 127°17'20\"E",
            "[정밀위치]",
            PiiCategory.PRECISE_LOCATION,
        ),
        (
            "위도 36도 30분 경도 127도 15분",
            "위도 [정밀위치]",
            PiiCategory.PRECISE_LOCATION,
        ),
        (
            "다이너스 카드 3056 9309 0259 04",
            "다이너스 카드 [카드번호]",
            PiiCategory.PAYMENT_CARD,
        ),
    ],
)
def test_additional_realistic_pii_variants_are_masked(
    raw: str,
    expected_text: str,
    expected_category: PiiCategory,
) -> None:
    result = redact_question(raw)
    assert result.masked_text == expected_text
    assert [finding.category for finding in result.findings] == [expected_category]


@pytest.mark.parametrize(
    ("raw", "reason"),
    [
        ("김철수라고 합니다.", UnresolvedReason.AMBIGUOUS_PERSON_NAME),
        ("김철수라고 해요.", UnresolvedReason.AMBIGUOUS_PERSON_NAME),
        ("김철입니다.", UnresolvedReason.AMBIGUOUS_PERSON_NAME),
        ("제갈공명입니다.", UnresolvedReason.AMBIGUOUS_PERSON_NAME),
        ("전입신고 김철수", UnresolvedReason.AMBIGUOUS_PERSON_NAME),
        ("김철수 전입신고", UnresolvedReason.AMBIGUOUS_PERSON_NAME),
        ("문의자 송가상", UnresolvedReason.AMBIGUOUS_PERSON_NAME),
        ("신청자 안테스트", UnresolvedReason.AMBIGUOUS_PERSON_NAME),
        ("김철수, 010-1234-5678", UnresolvedReason.AMBIGUOUS_PERSON_NAME),
        ("010-1234-5678. 김철수", UnresolvedReason.AMBIGUOUS_PERSON_NAME),
        ("test@example.invalid; 김철수", UnresolvedReason.AMBIGUOUS_PERSON_NAME),
        ("test@example.invalid (김철수)", UnresolvedReason.AMBIGUOUS_PERSON_NAME),
        ("010-1234-5678 (김철수)", UnresolvedReason.AMBIGUOUS_PERSON_NAME),
        ("대형폐기물 김철수", UnresolvedReason.AMBIGUOUS_PERSON_NAME),
        ("가상 아파트 101동 202호", UnresolvedReason.AMBIGUOUS_DETAILED_ADDRESS),
        ("가상주공 101동 202호", UnresolvedReason.AMBIGUOUS_DETAILED_ADDRESS),
        ("101동 202호에 살아요.", UnresolvedReason.AMBIGUOUS_DETAILED_ADDRESS),
        ("집은 101동 202호입니다.", UnresolvedReason.AMBIGUOUS_DETAILED_ADDRESS),
        ("101동 202호에 거주 중입니다.", UnresolvedReason.AMBIGUOUS_DETAILED_ADDRESS),
        ("101동 202호로 이사했어요.", UnresolvedReason.AMBIGUOUS_DETAILED_ADDRESS),
        ("조치원읍 123-4", UnresolvedReason.AMBIGUOUS_DETAILED_ADDRESS),
        ("연서면 123-4", UnresolvedReason.AMBIGUOUS_DETAILED_ADDRESS),
        ("가상타워 101동 202호", UnresolvedReason.AMBIGUOUS_DETAILED_ADDRESS),
        ("당뇨 환자입니다. 중증", UnresolvedReason.RESIDUAL_HIGH_RISK_PATTERN),
        ("암 환자입니다. 합병증 있음", UnresolvedReason.RESIDUAL_HIGH_RISK_PATTERN),
        ("암 환자입니다. 말기", UnresolvedReason.RESIDUAL_HIGH_RISK_PATTERN),
        ("세종시 가상로12. 김철수", UnresolvedReason.AMBIGUOUS_PERSON_NAME),
        ("세종시 가상로12. 건물명 가상타워", UnresolvedReason.RESIDUAL_HIGH_RISK_PATTERN),
        ("1\u20e32가0000", UnresolvedReason.RESIDUAL_HIGH_RISK_PATTERN),
        ("12가00\u20e300", UnresolvedReason.RESIDUAL_HIGH_RISK_PATTERN),
        ("36\u20e3.5,127.25", UnresolvedReason.RESIDUAL_HIGH_RISK_PATTERN),
        ("36.5,127\u20e3.25", UnresolvedReason.RESIDUAL_HIGH_RISK_PATTERN),
    ],
)
def test_ambiguous_or_obfuscated_pii_never_fails_open(
    raw: str,
    reason: UnresolvedReason,
) -> None:
    result = redact_question(raw)
    assert result.masked_text is None
    assert result.safe_for_failure_storage is False
    assert result.safe_for_synthetic_provider is False
    assert result.unresolved_reason is reason


@pytest.mark.parametrize(
    "raw",
    [
        "SPIN 1234",
        "SPIN class",
        "PINTEREST",
        "HOTPLACE",
        "AGPS device",
        "현재 위치 [정밀위치]",
    ],
)
def test_ascii_label_substrings_and_current_location_token_stay_safe(raw: str) -> None:
    assert redact_question(raw) == RedactionResult(raw, (), True, True, None)


@pytest.mark.parametrize(
    "raw",
    [
        "12월 3456원 지방세를 냈어요.",
        "24년 1234원 자동차세입니다.",
        "수수료는 1000 2000 3000 4000원입니다.",
        "수수료율 1.2 3.4 중 어느 것인가요?",
        "어진동입니다.",
        "고운동입니다.",
        "연기면입니다.",
        "부강면입니다.",
        "전의면입니다.",
        "연서면입니다.",
        "세종시입니다.",
        "전입신고할 때 주소는 어디까지 적어야 하나요?",
        "전입신고할 때 주소는 어떻게 적나요?",
        "대형폐기물 배출 주소는 수거 장소와 같아야 하나요?",
        "자동차세 차량번호는 실제 번호판과 같아야 하나요?",
        "전입신고 인증번호는 몇 분 동안 유효한가요?",
        "지방세 납부 확인서에 이름이 나오나요?",
        "전입신고서에 이름을 꼭 적어야 하나요?",
        "지방세 고지서의 주소를 바꾸려면 어떻게 하나요?",
        "전입신고 민원번호는 어디에 쓰나요?",
        "증명서 이메일은 어디에서 변경하나요?",
    ],
)
def test_p0_values_regions_and_compositional_questions_stay_safe(raw: str) -> None:
    assert redact_question(raw) == RedactionResult(raw, (), True, True, None)


def test_raw_identifier_never_appears_in_result_exception_or_log(
    caplog: pytest.LogCaptureFixture,
) -> None:
    sentinel = "unique.secret@example.invalid"
    with caplog.at_level(logging.DEBUG):
        result = redact_question(f"이메일 {sentinel}")
    assert sentinel not in repr(result)
    assert sentinel not in repr(result.findings)
    assert all(sentinel not in record.getMessage() for record in caplog.records)


def test_pathological_1000_character_inputs_finish_within_two_seconds() -> None:
    inputs = (
        ("0-" * 499) + "0x",
        ("가" * 970) + "아파트 999동 999호?",
        ("a." * 490) + "@invalid",
        ("저는 " * 200) + "가가가가라",
        ("면허번호 " * 100) + "00-00-000000-x",
    )
    assert all(len(raw) <= 1000 for raw in inputs)
    started = time.perf_counter()
    for raw in inputs:
        for _ in range(20):
            redact_question(raw)
    assert time.perf_counter() - started < 2.0


@pytest.mark.parametrize(
    "question",
    [
        "오늘 날씨 어때요?",
        "청년 월세 지원 어떻게 해요?",
        "장학금 신청 어떻게 해요?",
        "가족관계증명서 어떻게 발급받아요?",
        "증명서 발급해야해",
    ],
)
def test_ordinary_korean_is_not_an_ambiguous_person_name(question: str) -> None:
    result = redact_question(question)

    assert result.unresolved_reason is None
    assert result.masked_text == question
    assert result.safe_for_failure_storage is True
    assert result.safe_for_synthetic_provider is True
