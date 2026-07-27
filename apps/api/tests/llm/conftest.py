import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from sejong_ai_api.chat.topic_catalog import (
    TopicCatalog,
    build_topic_catalog,
    load_topic_coverage,
)
from sejong_ai_api.db.models import Intent, KnowledgeRecord
from sejong_ai_api.llm.contracts import GroundedFixture
from sejong_ai_api.llm.settings import UpstageSyntheticSettings

REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
RELEASE_PATH = (
    REPOSITORY_ROOT / "data" / "official" / "releases" / "0.1.0-initial.2" / "kb_records.json"
)
COVERAGE_PATH = REPOSITORY_ROOT / "data" / "retrieval" / "topic-coverage.v1.json"


def _load_tracked_records() -> tuple[KnowledgeRecord, ...]:
    payload: dict[str, Any] = json.loads(RELEASE_PATH.read_text(encoding="utf-8"))
    return tuple(
        KnowledgeRecord(
            public_id=item["id"],
            category=Intent(item["category"]),
            service_name=item["service_name"],
            answer_summary=item["answer_summary"],
            procedure_steps=tuple(item["procedure_steps"]),
            required_documents=tuple(item["required_documents"]),
            processing_time=item["processing_time"],
            fee=item["fee"],
            department=item["department"],
            source_title=item["source_title"],
            source_url=item["source_url"],
            last_verified_at=date.fromisoformat(item["last_verified_at"]),
            caution=item["caution"],
            question_examples=tuple(item["question_examples"]),
        )
        for item in payload["records"]
    )


def _canonical_waste_03() -> KnowledgeRecord:
    return KnowledgeRecord(
        public_id="KB-WASTE-03",
        category=Intent.BULKY_WASTE,
        service_name="침대 프레임 배출 수수료",
        answer_summary=(
            "공식 품목표의 침대 프레임 수수료는 1인용침대 8,000원, "
            "2인용침대 10,000원으로 표시됩니다."
        ),
        procedure_steps=(
            "공식 품목표에서 침대 프레임의 1인용침대 또는 2인용침대 항목을 확인합니다.",
            "해당 수수료로 공식 배출 절차를 진행합니다.",
        ),
        required_documents=(),
        processing_time=None,
        fee="1인용침대 8,000원; 2인용침대 10,000원",
        department="세종특별자치시시설관리공단",
        source_title="배출항목선택",
        source_url="https://www.sjwaste.kr/wasteApp/appCategoryPopup.do?menuId=MENU00305",
        last_verified_at=date(2026, 7, 18),
        caution=(
            "공식 품목표의 1인용침대·2인용침대 항목을 그대로 따릅니다. "
            "매트리스 포함 가격이나 실제 규격을 단정하지 않습니다."
        ),
        question_examples=("침대 2인용 프레임 수수료가 얼마예요?",),
    )


@pytest.fixture
def exact_settings() -> UpstageSyntheticSettings:
    return UpstageSyntheticSettings(api_key="synthetic-test-key-not-a-real-secret")


@pytest.fixture
def grounded_fixture() -> GroundedFixture:
    record = KnowledgeRecord(
        public_id="KB-BULKY-001",
        category=Intent.BULKY_WASTE,
        service_name="대형폐기물 배출",
        answer_summary="신고 후 배출번호를 표시해 지정한 날짜와 장소에 배출합니다.",
        procedure_steps=("배출 품목을 확인합니다.", "신고 후 배출번호를 표시합니다."),
        required_documents=(),
        processing_time="신고 즉시",
        fee="품목별 수수료",
        department="자원순환 담당부서",
        source_title="세종특별자치시 대형폐기물 안내",
        source_url="https://www.sejong.go.kr/",
        last_verified_at=date(2026, 7, 20),
        caution=None,
        question_examples=("소파를 버리려면 어떻게 하나요?",),
    )
    return GroundedFixture(
        fixture_id="T-09",
        masked_question="소파를 버리려면 어떻게 하나요?",
        intent=Intent.BULKY_WASTE,
        record=record,
    )


@pytest.fixture
def governed_catalog_19() -> TopicCatalog:
    return build_topic_catalog(
        _load_tracked_records(),
        load_topic_coverage(COVERAGE_PATH),
    )


@pytest.fixture
def governed_catalog_20() -> TopicCatalog:
    return build_topic_catalog(
        (*_load_tracked_records(), _canonical_waste_03()),
        load_topic_coverage(COVERAGE_PATH),
    )
