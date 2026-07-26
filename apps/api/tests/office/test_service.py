from datetime import date

import pytest

from sejong_ai_api.contracts.chat import Office
from sejong_ai_api.db.errors import DatabaseUnavailableError
from sejong_ai_api.db.models import Intent, OfficeRecord, Region
from sejong_ai_api.office.service import (
    ClosedOfficeDirectory,
    GuardedOfficeDirectory,
    OfficeDirectoryService,
    OfficeDirectoryUnavailableError,
)


def office_record(public_id: str) -> OfficeRecord:
    return OfficeRecord(
        public_id=public_id,
        region=Region.AREUM_DONG,
        office_name=f"{public_id} 행정복지센터",
        address="세종특별자치시 보듬3로 114",
        phone="044-301-6300",
        opening_hours=None,
        map_url=None,
        department_label="내부 담당 부서",
        source_title="세종특별자치시 공식 기관 안내",
        source_url="https://www.sejong.go.kr/office",
        last_verified_at=date(2026, 7, 19),
    )


class FakeRepository:
    def __init__(
        self,
        records: tuple[OfficeRecord, ...] = (),
        error: Exception | None = None,
    ) -> None:
        self.records = records
        self.error = error
        self.calls: list[tuple[Region, Intent]] = []

    async def list_offices(self, region: Region, intent: Intent) -> tuple[OfficeRecord, ...]:
        self.calls.append((region, intent))
        if self.error is not None:
            raise self.error
        return self.records


class FakeProbe:
    def __init__(self, ready: bool) -> None:
        self.ready = ready
        self.mark_count = 0

    async def check_ready(self) -> bool:
        return self.ready

    def mark_unavailable(self) -> None:
        self.mark_count += 1
        self.ready = False


class FakeDirectory:
    def __init__(self) -> None:
        self.calls: list[tuple[Region, Intent]] = []

    async def list_offices(self, region: Region, intent: Intent) -> tuple[Office, ...]:
        self.calls.append((region, intent))
        return ()


class FailingDirectory:
    async def list_offices(self, region: Region, intent: Intent) -> tuple[Office, ...]:
        del region, intent
        raise OfficeDirectoryUnavailableError


@pytest.mark.asyncio
async def test_service_passes_typed_filters_and_preserves_record_order() -> None:
    repository = FakeRepository((office_record("OFFICE-02"), office_record("OFFICE-01")))
    directory = OfficeDirectoryService(repository)

    result = await directory.list_offices(Region.AREUM_DONG, Intent.BULKY_WASTE)

    assert repository.calls == [(Region.AREUM_DONG, Intent.BULKY_WASTE)]
    assert tuple(item.id for item in result) == ("OFFICE-02", "OFFICE-01")


@pytest.mark.asyncio
async def test_service_maps_only_database_unavailable_to_directory_unavailable() -> None:
    directory = OfficeDirectoryService(FakeRepository(error=DatabaseUnavailableError()))

    with pytest.raises(OfficeDirectoryUnavailableError):
        await directory.list_offices(Region.AREUM_DONG, Intent.BULKY_WASTE)


@pytest.mark.asyncio
async def test_service_propagates_raw_repository_runtime_error() -> None:
    directory = OfficeDirectoryService(FakeRepository(error=RuntimeError("unexpected")))

    with pytest.raises(RuntimeError, match="unexpected"):
        await directory.list_offices(Region.AREUM_DONG, Intent.BULKY_WASTE)


@pytest.mark.asyncio
async def test_closed_directory_always_raises_directory_unavailable() -> None:
    with pytest.raises(OfficeDirectoryUnavailableError):
        await ClosedOfficeDirectory().list_offices(Region.AREUM_DONG, Intent.BULKY_WASTE)


@pytest.mark.asyncio
async def test_guard_skips_directory_when_readiness_is_false() -> None:
    wrapped = FakeDirectory()
    guarded = GuardedOfficeDirectory(FakeProbe(False), wrapped)

    with pytest.raises(OfficeDirectoryUnavailableError):
        await guarded.list_offices(Region.AREUM_DONG, Intent.BULKY_WASTE)

    assert wrapped.calls == []


@pytest.mark.asyncio
async def test_guard_marks_probe_unavailable_after_typed_read_failure() -> None:
    probe = FakeProbe(True)
    guarded = GuardedOfficeDirectory(probe, FailingDirectory())

    with pytest.raises(OfficeDirectoryUnavailableError):
        await guarded.list_offices(Region.AREUM_DONG, Intent.BULKY_WASTE)

    assert probe.mark_count == 1
