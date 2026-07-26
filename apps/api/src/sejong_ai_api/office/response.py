"""Server-owned conversion from database office records to public cards."""

from typing import overload

from pydantic import AnyUrl

from sejong_ai_api.contracts.chat import Office
from sejong_ai_api.db.models import OfficeRecord


@overload
def build_public_office(record: OfficeRecord) -> Office: ...


@overload
def build_public_office(record: None) -> None: ...


def build_public_office(record: OfficeRecord | None) -> Office | None:
    if record is None:
        return None
    return Office(
        id=record.public_id,
        region=record.region.value,
        office_name=record.office_name,
        address=record.address,
        phone=record.phone,
        opening_hours=record.opening_hours,
        map_url=AnyUrl(record.map_url) if record.map_url is not None else None,
        source_title=record.source_title,
        source_url=AnyUrl(record.source_url),
        last_verified_at=record.last_verified_at,
    )


__all__ = ["build_public_office"]
