"""Namespace-agnostic XML helpers shared by XML-based source adapters.

Several official sources have changed XML namespaces over time (OFAC did so in
2024); matching on local element names rather than fully-qualified names keeps
adapters resilient to that specific kind of change while still failing loudly
if the actual element structure disappears.
"""

from __future__ import annotations

from collections.abc import Iterator
from xml.etree.ElementTree import Element

from defusedxml import ElementTree as DefusedET


def parse_xml(raw: bytes) -> Element:
    result: Element = DefusedET.fromstring(raw)
    return result


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def find_direct(element: Element, name: str) -> Iterator[Element]:
    """Yield direct children of ``element`` whose local tag name equals ``name``."""
    for child in element:
        if local_name(child.tag) == name:
            yield child


def find_all(element: Element, name: str) -> Iterator[Element]:
    """Yield descendants (any depth) of ``element`` whose local tag name equals ``name``."""
    for child in element.iter():
        if local_name(child.tag) == name:
            yield child


def text_of(element: Element | None) -> str | None:
    if element is None or element.text is None:
        return None
    return element.text
