"""Deterministic extraction of a checklist section's list items.

Crude by design for the tracer: one list item is one requirement, and a
trailing "(if ...)" makes it conditional. Model extraction replaces this in
brief 03.
"""

import re
from dataclasses import dataclass
from html.parser import HTMLParser

from pakkifile.registry.model import RequirementType

_CONDITION = re.compile(r"^(?P<text>.+?)\s*\(if (?P<condition>[^)]+)\)$")


@dataclass(frozen=True)
class ExtractedItem:
    text: str
    type: RequirementType
    condition: str | None


class _SectionItems(HTMLParser):
    def __init__(self, heading: str) -> None:
        super().__init__()
        self.heading = heading
        self.items: list[str] = []
        self._tag = ""
        self._in_section = False
        self._item: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self._tag = tag
        if tag == "li" and self._in_section:
            self._item = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "li" and self._item is not None:
            self.items.append(" ".join("".join(self._item).split()))
            self._item = None

    def handle_data(self, data: str) -> None:
        if self._tag in {"h1", "h2", "h3"} and data.strip():
            self._in_section = data.strip() == self.heading
        elif self._item is not None:
            self._item.append(data)


def extract_section(html: str, heading: str) -> list[ExtractedItem]:
    parser = _SectionItems(heading)
    parser.feed(html)
    extracted = []
    for item in parser.items:
        match = _CONDITION.match(item)
        if match:
            extracted.append(ExtractedItem(match["text"], "conditional", match["condition"]))
        else:
            extracted.append(ExtractedItem(item, "mandatory", None))
    return extracted
