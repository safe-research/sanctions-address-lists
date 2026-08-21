"""Registry of all source adapters, in implementation-priority order."""

from __future__ import annotations

from sanctions_address_lists.sources.base import SourceAdapter
from sanctions_address_lists.sources.eu import EuAdapter
from sanctions_address_lists.sources.ofac import OfacAdapter
from sanctions_address_lists.sources.seco import SecoAdapter
from sanctions_address_lists.sources.uk import UkAdapter
from sanctions_address_lists.sources.un import UnAdapter

ALL_SOURCES: tuple[type[SourceAdapter], ...] = (
    OfacAdapter,
    EuAdapter,
    UkAdapter,
    UnAdapter,
    SecoAdapter,
)


def get_source(source_id: str) -> type[SourceAdapter]:
    for adapter_cls in ALL_SOURCES:
        if source_id == adapter_cls.SOURCE_ID:
            return adapter_cls
    raise KeyError(f"unknown source id: {source_id!r}")
