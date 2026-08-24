"""EVM address validation and normalization.

Only strings matching ``0x`` followed by exactly 40 hexadecimal characters are
accepted. Addresses are normalized to lowercase for deterministic deduplication
and sorting.
"""

from __future__ import annotations

import re

EVM_ADDRESS_RE = re.compile(r"0x[0-9a-fA-F]{40}", re.IGNORECASE)


def normalize_address(value: str | None) -> str | None:
    """Return the lowercase form of ``value`` if it is exactly an EVM address, else None.

    This performs a full match, not a search: the entire (stripped) value must be
    the address. Use this for values from a dedicated, typed address field.
    """
    if value is None:
        return None
    candidate = value.strip()
    if not EVM_ADDRESS_RE.fullmatch(candidate):
        return None
    return candidate.lower()
