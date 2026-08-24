"""Shared boundary-safe free-text scanning for EVM addresses.

Used by adapters whose source has no dedicated, typed crypto-address field, to
extract addresses that are still explicitly present as literal tokens in an
official record's free-text fields (e.g. a sanctions designation's remarks).

This is deliberately narrow: it is only ever pointed at specific free-text
fields *within an official machine-readable record*, never at arbitrary prose,
web pages, or fields unrelated to the record (such as entity names). It is not
a substitute for -- and must not be confused with -- inferring addresses from
names or enriching data via external providers.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable

BOUNDARY_RE = re.compile(r"(?<![0-9a-fA-F])0x[0-9a-fA-F]{40}(?![0-9a-fA-F])", re.IGNORECASE)
KEYWORDS = ("wallet", "crypto", "blockchain", "digital currency", "digital asset")
_PROXIMITY_CHARS = 200

logger = logging.getLogger(__name__)


def scan_text_fields(texts: Iterable[str | None], *, record_id: str, source_id: str) -> list[str]:
    """Return normalized, deduplicated EVM addresses found in ``texts``.

    The boundary-safe regex rejects a 40-hex-char run that is itself a substring
    of a longer hex token (e.g. a 64-hex-char transaction hash), so only tokens
    that are exactly 40 hex characters long are matched.

    For each match, logs at DEBUG level (visible with the CLI's ``--verbose``
    flag; never persisted in output files) whether a crypto-related keyword
    appears nearby -- a review signal for maintainers. The keyword is never
    required for extraction.
    """
    found: dict[str, None] = {}
    for text in texts:
        if not text:
            continue
        for match in BOUNDARY_RE.finditer(text):
            address = match.group(0).lower()
            found[address] = None
            window_start = max(0, match.start() - _PROXIMITY_CHARS)
            window_end = match.end() + _PROXIMITY_CHARS
            window = text[window_start:window_end].lower()
            has_keyword = any(keyword in window for keyword in KEYWORDS)
            logger.debug(
                "%s: free-text address match %s in record %s (keyword_nearby=%s)",
                source_id,
                address,
                record_id,
                has_keyword,
            )
    return list(found)
