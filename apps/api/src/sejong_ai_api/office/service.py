"""Read-only official office directory and fail-closed readiness boundary."""

from collections.abc import Sequence
from typing import Protocol

from sejong_ai_api.contracts.chat import Office
from sejong_ai_api.db.errors import DatabaseUnavailableError
from sejong_ai_api.db.models import Intent, OfficeRecord, Region
from sejong_ai_api.office.response import build_public_office


class OfficeRepository(Protocol):
    async def list_offices(self, region: Region, intent: Intent) -> Sequence[OfficeRecord]: ...


class OfficeDirectory(Protocol):
    async def list_offices(self, region: Region, intent: Intent) -> tuple[Office, ...]: ...


class OfficeReadinessProbe(Protocol):
    async def check_ready(self) -> bool: ...

    def mark_unavailable(self) -> None: ...


class OfficeDirectoryUnavailableError(Exception):
    """Signal that no safe official directory response can be produced."""


class ClosedOfficeDirectory:
    async def list_offices(self, region: Region, intent: Intent) -> tuple[Office, ...]:
        del region, intent
        raise OfficeDirectoryUnavailableError


class OfficeDirectoryService:
    def __init__(self, repository: OfficeRepository) -> None:
        self._repository = repository

    async def list_offices(self, region: Region, intent: Intent) -> tuple[Office, ...]:
        try:
            records = await self._repository.list_offices(region, intent)
        except DatabaseUnavailableError as exc:
            raise OfficeDirectoryUnavailableError from exc
        return tuple(build_public_office(record) for record in records)


class GuardedOfficeDirectory:
    def __init__(self, probe: OfficeReadinessProbe, directory: OfficeDirectory) -> None:
        self._probe = probe
        self._directory = directory

    async def list_offices(self, region: Region, intent: Intent) -> tuple[Office, ...]:
        if not await self._probe.check_ready():
            raise OfficeDirectoryUnavailableError
        try:
            return await self._directory.list_offices(region, intent)
        except OfficeDirectoryUnavailableError:
            self._probe.mark_unavailable()
            raise


__all__ = [
    "ClosedOfficeDirectory",
    "GuardedOfficeDirectory",
    "OfficeDirectory",
    "OfficeDirectoryService",
    "OfficeDirectoryUnavailableError",
    "OfficeReadinessProbe",
    "OfficeRepository",
]
