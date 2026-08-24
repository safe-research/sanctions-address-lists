"""Registry of all source adapters, in implementation-priority order.

Empty for now -- adapters are registered here as they're added in
subsequent PRs (see the "Adding a source adapter" section of the README).
"""

from __future__ import annotations

from sanctions_address_lists.sources.base import SourceAdapter

ALL_SOURCES: tuple[type[SourceAdapter], ...] = ()


def get_source(source_id: str) -> type[SourceAdapter]:
    for adapter_cls in ALL_SOURCES:
        if source_id == adapter_cls.SOURCE_ID:
            return adapter_cls
    raise KeyError(f"unknown source id: {source_id!r}")
