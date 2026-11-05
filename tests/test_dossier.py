from datetime import date
from decimal import Decimal
from html.parser import HTMLParser
from pathlib import Path

from pakkifile.dossier.build import EvidenceLink, build_dossier
from pakkifile.figures.continuity import SourceRow, UnattributedCredit
from pakkifile.figures.money import Money
from pakkifile.registry.files import load_entry
from pakkifile.web.dossier import render_dossier

ENTRY = load_entry(Path("registry-data/entries/de-islamabad-study-d.yaml"))
CREDIT = UnattributedCredit(
    Money(90_000_000, "PKR"),
    Decimal("0.3750"),
    (SourceRow("syn-statement-synthetic.csv", 14, date(2026, 9, 12), "CASH DEPOSIT"),),
)
LINK = EvidenceLink("proof-of-payment-of-tuition-fees", "syn-statement-synthetic.csv", CREDIT)


class _Figures(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.citations: list[str | None] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if ("class", "figure") in attrs:
            self.citations.append(dict(attrs).get("data-source"))


def _html() -> str:
    return render_dossier(build_dossier(ENTRY, "syn-freelancer-01 (synthetic)", [LINK]))


def test_dossier_follows_checklist_order() -> None:
    html = _html()
    positions = [html.index(r.text) for r in ENTRY.requirements]
    assert positions == sorted(positions)


def test_every_figure_cites_its_source_rows() -> None:
    parser = _Figures()
    parser.feed(_html())
    assert parser.citations == ["syn-statement-synthetic.csv, row 14"]


def test_dossier_shows_figure_value_and_marks_missing_evidence() -> None:
    html = _html()
    assert "PKR 900,000" in html
    assert html.count("Not provided") == 2
