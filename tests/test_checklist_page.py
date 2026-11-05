import re
from html.parser import HTMLParser
from pathlib import Path

from pakkifile.web.checklist import render_checklist
from tests.helpers import AS_OF, REGISTRY, islamabad_study

ENTRY = islamabad_study()


class _Rows(HTMLParser):
    """Collects the text of each checklist row, independent of the renderer."""

    def __init__(self) -> None:
        super().__init__()
        self.rows: list[str] = []
        self._depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "tr" and ("class", "requirement") in attrs:
            self.rows.append("")
            self._depth = 1
        elif self._depth:
            self._depth += 1

    def handle_endtag(self, tag: str) -> None:
        if self._depth:
            self._depth -= 1

    def handle_data(self, data: str) -> None:
        if self._depth:
            self.rows[-1] += data


def _rows() -> list[str]:
    parser = _Rows()
    parser.feed(render_checklist(ENTRY, REGISTRY.sources, AS_OF))
    return [" ".join(r.split()) for r in parser.rows]


def test_each_requirement_is_one_row_with_type_and_citation() -> None:
    rows = _rows()
    assert len(rows) == 3
    assert "Degree transcripts" in rows[1] and "Mandatory" in rows[1]
    assert "Conditional" in rows[2] and "applicable to the course of study" in rows[2]
    for row in rows:
        assert "Mandatory documents" in row
        assert "High" in row


def test_page_links_to_the_source() -> None:
    assert 'href="https://pakistan.diplo.de/pk-en/service/2-study-visa-seite-1676104"' in (
        render_checklist(ENTRY, REGISTRY.sources, AS_OF)
    )


def test_templates_use_only_design_tokens() -> None:
    for path in Path("src/pakkifile/web/templates").glob("*.html"):
        if path.name == "tokens.html":
            continue
        assert not re.search(r"#[0-9a-fA-F]{3,6}\b|\d+px", path.read_text()), path.name
