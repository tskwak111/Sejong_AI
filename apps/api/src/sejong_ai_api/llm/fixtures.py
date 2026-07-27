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
_INTENT_LABEL_BY_INTENT = {intent: label for label, intent in _INTENT_LABELS.items()}
_PII_LABEL_BY_FLAG = {contains_pii: label for label, contains_pii in _PII_LABELS.items()}
_CANONICAL_FIXTURE_SHA256_BY_ID = {
    "T-01": "c8a5a33a8348ea04dd7795bd28f681b66931cedbf49fc42bbf9caaaf3324b138",
    "T-02": "0abb9548def2a74f63bd52f2e80ae9ea0c20a4186b04fed89102f60923945d35",
    "T-03": "ddd1741b7a1e25688a84f3cc9783943cdc1d160a3b7da8d307cc32538690d2b0",
    "T-04": "4431e745e784aa6301698d85ac3c556f06957cc67fbb20577ac7eac60bd79b90",
    "T-05": "5da4b46e9cd6d541697e2216f497b3745032495efc1e071d4abbc1bd912e9b12",
    "T-06": "63eb29c10b296f966f9f696356256d66137cae2e2cb5ab752e3bb5bb3419604f",
    "T-07": "65dd36d54b591790ecd406617617cdd6842d6cc1ed97dadd9afb6bba1942e209",
    "T-08": "0e4317ae17a1a1cf2324c9b149024b248a12b8aa3930c5d6618d65cf82ecb110",
    "T-09": "84f70f135912e8f76fb082a93f3163032ca3de94413e0500c9649b498aeaa24b",
    "T-10": "a84ba74005d241ae61dfd9592311510859294da35d60a075b930538994e30b9c",
}
_EXPECTED_TOPIC_IDS_BY_FIXTURE = {
    "T-02": "KB-MOVE-02",
    "T-07": "KB-WASTE-01",
    "T-08": "KB-WASTE-02",
}


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


def lookup_canonical_semantic_topic_id(fixture: SyntheticFixture) -> str | None:
    """Return the private mapping only for an exact canonical fixture."""
    if (
        type(fixture) is not SyntheticFixture
        or type(fixture.fixture_id) is not str
        or type(fixture.question) is not str
        or type(fixture.expected_intent) is not Intent
        or type(fixture.expected_status) is not AnswerStatus
        or type(fixture.contains_pii) is not bool
    ):
        raise ValueError("SYNTHETIC_FIXTURE_NOT_ALLOWED")

    expected_digest = _CANONICAL_FIXTURE_SHA256_BY_ID.get(fixture.fixture_id)
    intent_label = _INTENT_LABEL_BY_INTENT.get(fixture.expected_intent)
    if expected_digest is None or intent_label is None:
        raise ValueError("SYNTHETIC_FIXTURE_NOT_ALLOWED")
    projection = (
        fixture.fixture_id,
        fixture.question,
        intent_label,
        fixture.expected_status.value,
        _PII_LABEL_BY_FLAG[fixture.contains_pii],
    )
    canonical = json.dumps(
        projection,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    if hashlib.sha256(canonical).hexdigest() != expected_digest:
        raise ValueError("SYNTHETIC_FIXTURE_NOT_ALLOWED")
    return _EXPECTED_TOPIC_IDS_BY_FIXTURE.get(fixture.fixture_id)


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
    "lookup_canonical_semantic_topic_id",
]
