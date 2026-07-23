from datetime import date

import pytest

from sejong_ai_api.db.models import Intent, KnowledgeRecord
from sejong_ai_api.llm.contracts import GroundedFixture
from sejong_ai_api.llm.settings import UpstageSyntheticSettings


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
