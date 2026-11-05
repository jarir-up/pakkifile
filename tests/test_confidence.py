from datetime import date
from decimal import Decimal

from pakkifile.registry.confidence import Confidence, confidence
from pakkifile.registry.model import Citation, Requirement, Source, SourceAuthority, Stance
from tests.helpers import AS_OF, ISLAMABAD, KARACHI, REGISTRY, entry


def _confidence(authority: str, purpose: str, requirement_id: str) -> Confidence:
    req = next(r for r in entry(authority, purpose).requirements if r.id == requirement_id)
    return confidence(req, REGISTRY.sources, AS_OF)


def _score(authority: str, purpose: str, requirement_id: str) -> Decimal:
    return _confidence(authority, purpose, requirement_id).score


def _source(authority: SourceAuthority, published: date | None = None) -> Source:
    return Source(
        document="d",
        url="https://example.org",
        published=published,
        retrieved=AS_OF,
        last_verified=AS_OF,
        source_authority=authority,
    )


def _req(*citations: tuple[str, Stance]) -> Requirement:
    return Requirement(
        id="r",
        text="r",
        type="mandatory",
        citations=tuple(Citation(source=s, section="s", stance=st) for s, st in citations),
    )


def test_current_consulate_page_alone_is_high() -> None:
    # consulate page 0.90 x recency 1.0 (published 337 days before)
    assert _score(ISLAMABAD, "study", "degree-transcripts") == Decimal("0.90")


def test_six_year_old_checklist_alone_is_low() -> None:
    # official checklist 1.00 x recency 0.4 (published 2020-01-07)
    result = _confidence(KARACHI, "study", "blocked-account-confirmation")
    assert result.score == Decimal("0.40")
    assert result.level == "Low"


def test_agreement_adds_to_the_strongest_source() -> None:
    # page 0.90 + 0.05 for the agreeing 2020 checklist
    assert _score(KARACHI, "study", "school-degree-certificates") == Decimal("0.95")


def test_weaker_conflict_costs_a_little() -> None:
    # page 0.90 - 0.05 for the 2020 checklist's conflicting wording
    assert _score(KARACHI, "study", "proof-of-payment-of-tuition-fees") == Decimal("0.85")


def test_undated_page_uses_its_last_verification() -> None:
    assert _score(ISLAMABAD, "tourism", "health-insurance") == Decimal("0.90")


def test_equally_strong_conflict_halves_the_score() -> None:
    sources = {"a": _source("consulate_page"), "b": _source("consulate_page")}
    result = confidence(_req(("a", "supports"), ("b", "conflicts")), sources, AS_OF)
    assert result.score == Decimal("0.45")
    assert result.level == "Low"


def test_two_year_old_page_is_medium() -> None:
    sources = {"a": _source("consulate_page", published=date(2025, 1, 1))}
    result = confidence(_req(("a", "supports")), sources, AS_OF)
    assert result.score == Decimal("0.72")
    assert result.level == "Medium"


def test_score_never_exceeds_one() -> None:
    sources = {k: _source("official_checklist") for k in "abcd"}
    req = _req(*((k, "supports") for k in "abcd"))
    assert confidence(req, sources, AS_OF).score == Decimal("1.00")


def test_cap_applies_before_an_equal_conflict_halves() -> None:
    sources = {k: _source("official_checklist") for k in "abcde"}
    req = _req(*((k, "supports") for k in "abcd"), ("e", "conflicts"))
    assert confidence(req, sources, AS_OF).score == Decimal("0.50")


def test_weaker_conflict_still_costs_at_the_cap() -> None:
    sources = {k: _source("official_checklist") for k in "abcd"} | {"x": _source("agent")}
    req = _req(*((k, "supports") for k in "abcd"), ("x", "conflicts"))
    assert confidence(req, sources, AS_OF).score == Decimal("0.95")
