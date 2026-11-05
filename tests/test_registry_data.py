from pakkifile.web.checklist import render_checklist
from tests.helpers import AS_OF, ISLAMABAD, KARACHI, REGISTRY, entry


def test_karachi_study_is_a_national_visa_at_a_consulate() -> None:
    karachi = entry(KARACHI, "study")
    assert karachi.authority.kind == "consulate"
    assert karachi.application.visa_category == "D"


def test_islamabad_tourism_is_a_schengen_visa() -> None:
    assert entry(ISLAMABAD, "tourism").application.visa_category == "C"


def test_a_karachi_requirement_is_supported_by_two_sources() -> None:
    assert any(
        len({c.source for c in r.citations if c.stance == "supports"}) >= 2
        for r in entry(KARACHI, "study").requirements
    )


def test_embassy_and_consulate_both_cite_the_shared_study_page() -> None:
    for authority in (ISLAMABAD, KARACHI):
        cited = {c.source for r in entry(authority, "study").requirements for c in r.citations}
        assert "de-missions-pk-study-visa-page" in cited


def test_every_entry_renders_one_row_per_requirement() -> None:
    for e in REGISTRY.entries:
        html = render_checklist(e, REGISTRY.sources, AS_OF)
        assert html.count('class="requirement"') == len(e.requirements)


def test_stale_blocked_account_row_shows_low_confidence() -> None:
    html = render_checklist(entry(KARACHI, "study"), REGISTRY.sources, AS_OF)
    row = html.split("blocked account holding")[1].split("</tr>")[0]
    assert "<td>Low</td>" in row
