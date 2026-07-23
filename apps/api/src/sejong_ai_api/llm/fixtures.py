"""Hash-bound canonical synthetic fixtures for the local Upstage evaluation."""

import csv
import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from sejong_ai_api.db.models import AnswerStatus, Intent

_CSV_HEADER = (
    "test_id",
    "질문",
    "유형",
    "기대 intent",
    "기대 상태",
    "기대 폴백 사유",
    "KB 후보 적격",
    "기대 행동",
    "PII 포함",
    "비고",
)
_PROJECTION_FIELDS = ("test_id", "질문", "기대 intent", "기대 상태", "PII 포함")
_ALLOWED_IDS = tuple(f"T-{number:02d}" for number in range(1, 11))
_ALLOWED_ID_SET = frozenset(_ALLOWED_IDS)
_EXPECTED_PROJECTION_SHA256 = "26a60e4d3c0e349beabec7c26206f3ffca2d7c46006309a09b3711ac6f61148a"
_INTENT_LABELS = {
    "전입·주민등록": Intent.MOVE_IN_RESIDENT_REGISTRATION,
    "증명서 발급": Intent.CERTIFICATE_ISSUANCE,
    "대형폐기물": Intent.BULKY_WASTE,
    "지방세 일반 안내": Intent.LOCAL_TAX_GENERAL,
}
_PII_LABELS = {"아니오": False, "예": True}


class PreparationCode(str, Enum):  # noqa: UP042 - approved str/Enum contract
    PRIVACY_UNRESOLVED = "PRIVACY_UNRESOLVED"
    NOT_DETERMINISTIC_SUCCESS = "NOT_DETERMINISTIC_SUCCESS"
    INSUFFICIENT_GROUNDING = "INSUFFICIENT_GROUNDING"


@dataclass(frozen=True, slots=True)
class SyntheticFixture:
    fixture_id: str
    question: str
    expected_intent: Intent
    expected_status: AnswerStatus
    contains_pii: bool


@dataclass(frozen=True, slots=True)
class PreparedCaseFailure:
    code: PreparationCode


def load_allowed_fixtures(path: Path) -> tuple[SyntheticFixture, ...]:
    """Load only the exact approved T-01..T-10 raw-field projection."""
    if not isinstance(path, Path):
        raise ValueError("SYNTHETIC_FIXTURE_SET_INVALID")

    try:
        with path.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle, strict=True)
            if tuple(reader.fieldnames or ()) != _CSV_HEADER:
                raise ValueError("SYNTHETIC_FIXTURE_SET_INVALID")
            rows = list(reader)

        if any(None in row or any(row.get(field) is None for field in _CSV_HEADER) for row in rows):
            raise ValueError("SYNTHETIC_FIXTURE_SET_INVALID")

        allowed_rows = tuple(row for row in rows if row["test_id"] in _ALLOWED_ID_SET)
        projection = [[row[field] for field in _PROJECTION_FIELDS] for row in allowed_rows]
        canonical = json.dumps(
            projection,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        if hashlib.sha256(canonical).hexdigest() != _EXPECTED_PROJECTION_SHA256:
            raise ValueError("SYNTHETIC_FIXTURE_SET_INVALID")
        if tuple(row["test_id"] for row in allowed_rows) != _ALLOWED_IDS:
            raise ValueError("SYNTHETIC_FIXTURE_SET_INVALID")

        return tuple(
            SyntheticFixture(
                fixture_id=row["test_id"],
                question=row["질문"],
                expected_intent=_INTENT_LABELS[row["기대 intent"]],
                expected_status=AnswerStatus(row["기대 상태"]),
                contains_pii=_PII_LABELS[row["PII 포함"]],
            )
            for row in allowed_rows
        )
    except (OSError, UnicodeError, csv.Error, KeyError, ValueError):
        raise ValueError("SYNTHETIC_FIXTURE_SET_INVALID") from None


__all__ = [
    "PreparationCode",
    "PreparedCaseFailure",
    "SyntheticFixture",
    "load_allowed_fixtures",
]
