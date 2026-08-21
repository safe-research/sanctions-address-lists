"""UN Security Council Consolidated List adapter.

Confirmed via a full grep of the live dataset: the UN list has no structured
crypto-address field at all. This adapter scans each individual/entity's
``COMMENTS*`` free-text elements (the only narrative fields on a record) with
the shared boundary-safe regex, in case a future designation states an address
there, and otherwise correctly yields zero addresses.
"""

from __future__ import annotations

from sanctions_address_lists.models import AddressLink, SourceRecord
from sanctions_address_lists.sources.base import SourceAdapter
from sanctions_address_lists.sources.errors import EmptyResultError, SchemaError
from sanctions_address_lists.sources.xmlutil import find_direct, local_name, parse_xml, text_of
from sanctions_address_lists.textscan import scan_text_fields

_RECORD_GROUPS = (("INDIVIDUALS", "INDIVIDUAL"), ("ENTITIES", "ENTITY"))


class UnAdapter(SourceAdapter):
    SOURCE_ID = "un"
    JURISDICTION = "UN"
    SOURCE_URL = "https://scsanctions.un.org/resources/xml/en/consolidated.xml"
    GATES_BUILD = True

    def parse(self, raw: bytes) -> tuple[list[SourceRecord], list[AddressLink]]:
        try:
            root = parse_xml(raw)
        except Exception as exc:
            raise SchemaError(f"UN consolidated list did not parse as XML: {exc}") from exc

        if local_name(root.tag) != "CONSOLIDATED_LIST":
            raise SchemaError(f"unexpected root element {root.tag!r}, expected CONSOLIDATED_LIST")

        records: list[SourceRecord] = []
        links: list[AddressLink] = []
        for group_tag, item_tag in _RECORD_GROUPS:
            group_el = next(find_direct(root, group_tag), None)
            if group_el is None:
                continue
            for item in find_direct(group_el, item_tag):
                record_id = text_of(next(find_direct(item, "DATAID"), None))
                if not record_id:
                    raise SchemaError(f"{item_tag} is missing its required DATAID")
                records.append(SourceRecord(record_id=record_id))

                comment_texts = [
                    text_of(child) for child in item if local_name(child.tag).startswith("COMMENTS")
                ]
                for address in scan_text_fields(
                    comment_texts, record_id=record_id, source_id=self.SOURCE_ID
                ):
                    links.append(
                        AddressLink(
                            address=address,
                            jurisdiction=self.JURISDICTION,
                            source=self.SOURCE_ID,
                            source_record_id=record_id,
                            source_url=self.SOURCE_URL,
                        )
                    )

        if not records:
            raise EmptyResultError("UN consolidated list contained zero INDIVIDUAL/ENTITY records")
        return records, links
