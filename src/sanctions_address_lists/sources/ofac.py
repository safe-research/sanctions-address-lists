"""US OFAC Sanctions List Service adapter (SDN.XML).

OFAC publishes a dedicated, typed identification field for crypto addresses:
each ``sdnEntry/idList/id`` whose ``idType`` starts with "Digital Currency
Address" carries the address itself in ``idNumber``. We accept any such id
whose value happens to match the strict EVM format, regardless of which
currency suffix (ETH, ARB, BSC, ETC, ...) OFAC used -- filtering by address
*format*, not by hardcoding which currency codes are EVM-compatible.
"""

from __future__ import annotations

from sanctions_address_lists.models import AddressLink, SourceRecord
from sanctions_address_lists.normalize import normalize_address
from sanctions_address_lists.sources.base import SourceAdapter
from sanctions_address_lists.sources.errors import EmptyResultError, SchemaError
from sanctions_address_lists.sources.xmlutil import find_direct, local_name, parse_xml, text_of

_DIGITAL_CURRENCY_PREFIX = "Digital Currency Address"


class OfacAdapter(SourceAdapter):
    SOURCE_ID = "us-ofac"
    JURISDICTION = "US"
    SOURCE_URL = "https://sanctionslistservice.ofac.treas.gov/api/download/SDN.XML"
    GATES_BUILD = True

    def parse(self, raw: bytes) -> tuple[list[SourceRecord], list[AddressLink]]:
        try:
            root = parse_xml(raw)
        except Exception as exc:
            raise SchemaError(f"OFAC SDN.XML did not parse as XML: {exc}") from exc

        if local_name(root.tag) != "sdnList":
            raise SchemaError(f"unexpected root element {root.tag!r}, expected sdnList")

        entries = list(find_direct(root, "sdnEntry"))
        if not entries:
            raise EmptyResultError("OFAC SDN.XML contained zero sdnEntry records")

        records: list[SourceRecord] = []
        links: list[AddressLink] = []
        for entry in entries:
            record_id = text_of(next(find_direct(entry, "uid"), None))
            if not record_id:
                raise SchemaError("sdnEntry is missing its required uid")
            records.append(SourceRecord(record_id=record_id))

            id_list = next(find_direct(entry, "idList"), None)
            if id_list is None:
                continue
            for id_el in find_direct(id_list, "id"):
                id_type = text_of(next(find_direct(id_el, "idType"), None))
                if not id_type or not id_type.startswith(_DIGITAL_CURRENCY_PREFIX):
                    continue
                address = normalize_address(text_of(next(find_direct(id_el, "idNumber"), None)))
                if address is None:
                    continue
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
