from datetime import date

import pytest
from pydantic import ValidationError

from sejong_ai_api.contracts.offices import OfficeListResponse
from sejong_ai_api.db.models import OfficeRecord, Region
from sejong_ai_api.office.response import build_public_office


def office_record() -> OfficeRecord:
    return OfficeRecord(
        public_id="OFFICE-AREUM",
        region=Region.AREUM_DONG,
        office_name="아름동 행정복지센터",
        address="세종특별자치시 보듬3로 114",
        phone="044-301-6300",
        opening_hours="평일 09:00~18:00",
        map_url="https://www.sejong.go.kr/office/map",
        department_label="내부 담당 부서",
        source_title="세종특별자치시 공식 기관 안내",
        source_url="https://www.sejong.go.kr/office",
        last_verified_at=date(2026, 7, 19),
    )


def test_office_list_requires_explicit_items_and_accepts_empty_list() -> None:
    assert OfficeListResponse(items=[]).model_dump(mode="json") == {"items": []}
    with pytest.raises(ValidationError):
        OfficeListResponse.model_validate({})


def test_office_record_maps_only_exact_public_fields() -> None:
    public = build_public_office(office_record())
    payload = public.model_dump(mode="json")
    assert payload == {
        "id": "OFFICE-AREUM",
        "region": "아름동",
        "office_name": "아름동 행정복지센터",
        "address": "세종특별자치시 보듬3로 114",
        "phone": "044-301-6300",
        "opening_hours": "평일 09:00~18:00",
        "map_url": "https://www.sejong.go.kr/office/map",
        "source_title": "세종특별자치시 공식 기관 안내",
        "source_url": "https://www.sejong.go.kr/office",
        "last_verified_at": "2026-07-19",
    }
    assert "department_label" not in payload
    assert build_public_office(None) is None
