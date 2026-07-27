from pathlib import Path

import pytest

from sejong_ai_api.db.models import AnswerStatus, Intent
from sejong_ai_api.llm.fixtures import load_allowed_fixtures

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
CANONICAL_PATH = REPOSITORY_ROOT / "data" / "evaluation" / "sample_questions_20.csv"


def test_canonical_loader_returns_only_exact_success_ids() -> None:
    fixtures = load_allowed_fixtures(CANONICAL_PATH)

    assert tuple(item.fixture_id for item in fixtures) == tuple(
        f"T-{number:02d}" for number in range(1, 11)
    )
    assert all(item.expected_status is AnswerStatus.SUCCESS for item in fixtures)
    assert all(item.contains_pii is False for item in fixtures)
    assert tuple(item.expected_intent for item in fixtures) == (
        Intent.MOVE_IN_RESIDENT_REGISTRATION,
        Intent.MOVE_IN_RESIDENT_REGISTRATION,
        Intent.MOVE_IN_RESIDENT_REGISTRATION,
        Intent.CERTIFICATE_ISSUANCE,
        Intent.CERTIFICATE_ISSUANCE,
        Intent.CERTIFICATE_ISSUANCE,
        Intent.BULKY_WASTE,
        Intent.BULKY_WASTE,
        Intent.LOCAL_TAX_GENERAL,
        Intent.LOCAL_TAX_GENERAL,
    )
    assert tuple(item.expected_topic_id for item in fixtures) == (
        None,
        "KB-MOVE-02",
        None,
        None,
        None,
        None,
        "KB-WASTE-01",
        "KB-WASTE-02",
        None,
        None,
    )


def test_changed_allowed_projection_fails_closed(tmp_path: Path) -> None:
    candidate = tmp_path / "sample.csv"
    content = CANONICAL_PATH.read_text(encoding="utf-8")
    candidate.write_text(
        content.replace(
            "T-01,이사했는데 전입신고 어떻게 해요?",
            "T-01,임의 자유 입력",
            1,
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="SYNTHETIC_FIXTURE_SET_INVALID"):
        load_allowed_fixtures(candidate)


def test_noncanonical_header_fails_closed(tmp_path: Path) -> None:
    candidate = tmp_path / "sample.csv"
    content = CANONICAL_PATH.read_text(encoding="utf-8")
    candidate.write_text(
        content.replace("test_id,질문,유형", "test_id,질문,변경된 유형", 1),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="SYNTHETIC_FIXTURE_SET_INVALID"):
        load_allowed_fixtures(candidate)


def test_changes_outside_allowed_projection_do_not_expand_allowlist(tmp_path: Path) -> None:
    candidate = tmp_path / "sample.csv"
    content = CANONICAL_PATH.read_text(encoding="utf-8")
    candidate.write_text(
        content.replace("T-11,신고하고 싶어요.", "T-11,외부 전송 금지 행 변경", 1),
        encoding="utf-8",
    )

    fixtures = load_allowed_fixtures(candidate)

    assert tuple(item.fixture_id for item in fixtures) == tuple(
        f"T-{number:02d}" for number in range(1, 11)
    )
