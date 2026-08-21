"""UK Sanctions List adapter.

The UK schema defines a dedicated ``CryptoWalletAddresses/CryptoWalletAddress``
field per ``Designation`` (confirmed present in the XSD, currently unpopulated
in live data). As a fallback -- in case an address is published in prose before
the structured field is used, as EU's Garantex designation was -- this adapter
also scans ``OtherInformation`` and ``UKStatementofReasons`` free text.
"""

from __future__ import annotations

from sanctions_address_lists.models import AddressLink, SourceRecord
from sanctions_address_lists.normalize import normalize_address
from sanctions_address_lists.sources.base import SourceAdapter
from sanctions_address_lists.sources.errors import EmptyResultError, SchemaError
from sanctions_address_lists.sources.xmlutil import find_direct, local_name, parse_xml, text_of
from sanctions_address_lists.textscan import scan_text_fields

_FALLBACK_TEXT_TAGS = ("OtherInformation", "UKStatementofReasons")


class UkAdapter(SourceAdapter):
    SOURCE_ID = "uk"
    JURISDICTION = "UK"
    SOURCE_URL = "https://sanctionslist.fcdo.gov.uk/docs/UK-Sanctions-List.xml"
    GATES_BUILD = True

    def parse(self, raw: bytes) -> tuple[list[SourceRecord], list[AddressLink]]:
        try:
            root = parse_xml(raw)
        except Exception as exc:
            raise SchemaError(f"UK Sanctions List did not parse as XML: {exc}") from exc

        if local_name(root.tag) != "Designations":
            raise SchemaError(f"unexpected root element {root.tag!r}, expected Designations")

        designations = list(find_direct(root, "Designation"))
        if not designations:
            raise EmptyResultError("UK Sanctions List contained zero Designation records")

        records: list[SourceRecord] = []
        links: list[AddressLink] = []
        for designation in designations:
            record_id = text_of(next(find_direct(designation, "UniqueID"), None))
            if not record_id:
                raise SchemaError("Designation is missing its required UniqueID")
            records.append(SourceRecord(record_id=record_id))

            addresses: set[str] = set()

            wallets_el = next(find_direct(designation, "CryptoWalletAddresses"), None)
            if wallets_el is not None:
                for wallet_el in find_direct(wallets_el, "CryptoWalletAddress"):
                    address = normalize_address(text_of(wallet_el))
                    if address is not None:
                        addresses.add(address)

            fallback_texts = [
                text_of(next(find_direct(designation, tag), None)) for tag in _FALLBACK_TEXT_TAGS
            ]
            addresses.update(
                scan_text_fields(fallback_texts, record_id=record_id, source_id=self.SOURCE_ID)
            )

            for address in addresses:
                links.append(
                    AddressLink(
                        address=address,
                        jurisdiction=self.JURISDICTION,
                        source=self.SOURCE_ID,
                        source_record_id=record_id,
                        source_url=self.SOURCE_URL,
                    )
                )
        return records, links
