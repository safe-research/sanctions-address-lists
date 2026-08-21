"""Switzerland SECO consolidated sanctions list adapter.

Built from SECO's published XSD (element names confirmed: ``identity``,
``identification-document``, ``address``, ``other-information``, ``remark``).

Live-verified: a fetch against the real endpoint returned HTTP 200 with a
dated ``consolidated-list_*.xml`` attachment, and this adapter correctly
parsed all 24,483 ``identity`` records from it (0 addresses -- expected,
since SECO's schema has no crypto field). Earlier attempts from two
independent networks (a dev sandbox and a maintainer's own machine on a VPN)
timed out at the TCP level; disabling the VPN resolved it, suggesting SECO's
infrastructure blocks some VPN/proxy IP ranges. See FEASIBILITY.md for the
full diagnosis -- if this source starts failing again, check that history
before assuming the code or schema broke.
"""

from __future__ import annotations

from sanctions_address_lists.models import AddressLink, SourceRecord
from sanctions_address_lists.sources.base import SourceAdapter
from sanctions_address_lists.sources.errors import EmptyResultError, SchemaError
from sanctions_address_lists.sources.xmlutil import find_all, local_name, parse_xml, text_of
from sanctions_address_lists.textscan import scan_text_fields

_RECORD_TAG = "identity"
_ID_ATTRS = ("id", "identity-id", "logicalId")
_TEXT_TAGS = ("remark", "other-information")


class SecoAdapter(SourceAdapter):
    SOURCE_ID = "ch-seco"
    JURISDICTION = "CH"
    SOURCE_URL = (
        "https://www.sesam.search.admin.ch/sesam-search-web/pages/"
        "downloadXmlGesamtliste.xhtml?lang=en&action=downloadXmlGesamtlisteAction"
    )
    GATES_BUILD = True

    def parse(self, raw: bytes) -> tuple[list[SourceRecord], list[AddressLink]]:
        try:
            root = parse_xml(raw)
        except Exception as exc:
            raise SchemaError(f"SECO list did not parse as XML: {exc}") from exc

        identities = list(find_all(root, _RECORD_TAG))
        if not identities:
            raise EmptyResultError(
                f"SECO list (root {local_name(root.tag)!r}) contained zero {_RECORD_TAG!r} records"
            )

        records: list[SourceRecord] = []
        links: list[AddressLink] = []
        for index, identity in enumerate(identities):
            record_id = next(
                (identity.get(attr) for attr in _ID_ATTRS if identity.get(attr)), None
            ) or str(index)
            records.append(SourceRecord(record_id=record_id))

            text_fields = [
                text_of(el) for el in identity.iter() if local_name(el.tag) in _TEXT_TAGS
            ]
            for address in scan_text_fields(
                text_fields, record_id=record_id, source_id=self.SOURCE_ID
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
