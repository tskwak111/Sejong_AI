"""Public response contract for the official office directory."""

from sejong_ai_api.contracts.chat import Office
from sejong_ai_api.contracts.health import StrictPublicModel


class OfficeListResponse(StrictPublicModel):
    items: list[Office]


__all__ = ["OfficeListResponse"]
