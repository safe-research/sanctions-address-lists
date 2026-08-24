"""EU consolidated financial sanctions list adapter.

The EU list has no dedicated/typed field for crypto addresses. Confirmed by
inspecting the live dataset: real wallet addresses (e.g. for the Garantex
exchange) exist only inside free-text ``<remark>`` elements -- and those can
be nested under a ``sanctionEntity``'s child elements (e.g. under a specific
``nameAlias``), not just as a direct child of ``sanctionEntity`` itself. This
adapter therefore scans every ``<remark>`` descendant within each
``sanctionEntity`` record with the shared boundary-safe regex -- never entity
names, never other fields, never anything outside that record.
"""

from __future__ import annotations

from sanctions_address_lists.models import AddressLink, SourceRecord
from sanctions_address_lists.sources.base import SourceAdapter
from sanctions_address_lists.sources.errors import EmptyResultError, SchemaError
from sanctions_address_lists.sources.xmlutil import (
    find_all,
    find_direct,
    local_name,
    parse_xml,
    text_of,
)
from sanctions_address_lists.textscan import scan_text_fields


class EuAdapter(SourceAdapter):
    SOURCE_ID = "eu"
    JURISDICTION = "EU"
    SOURCE_URL = (
        "https://webgate.ec.europa.eu/fsd/fsf/public/files/"
        "xmlFullSanctionsList_1_1/content?token=dG9rZW4tMjAxNw"
    )
    GATES_BUILD = True

    def parse(self, raw: bytes) -> tuple[list[SourceRecord], list[AddressLink]]:
        try:
            root = parse_xml(raw)
        except Exception as exc:
            raise SchemaError(f"EU consolidated list did not parse as XML: {exc}") from exc

        if local_name(root.tag) != "export":
            raise SchemaError(f"unexpected root element {root.tag!r}, expected export")

        entities = list(find_direct(root, "sanctionEntity"))
        if not entities:
            raise EmptyResultError("EU consolidated list contained zero sanctionEntity records")

        records: list[SourceRecord] = []
        links: list[AddressLink] = []
        for entity in entities:
            record_id = entity.get("logicalId") or entity.get("euReferenceNumber")
            if not record_id:
                raise SchemaError("sanctionEntity is missing its required logicalId")
            records.append(SourceRecord(record_id=record_id))

            remark_texts = [text_of(remark) for remark in find_all(entity, "remark")]
            for address in scan_text_fields(
                remark_texts, record_id=record_id, source_id=self.SOURCE_ID
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
        return records, links
