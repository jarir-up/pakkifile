from datetime import date, timedelta

from pakkifile.registry.model import Citation, Requirement, Source, SourceAuthority, Stance
from pakkifile.registry.publish import publish_status
from tests.helpers import AS_OF, KARACHI, REGISTRY, entry


def _source(authority: SourceAuthority, verified: date = AS_OF) -> Source:
    return Source(
        document="d",
        url="https://example.org",
        retrieved=verified,
        last_verified=verified,
        source_authority=authority,
    )


def _req(*citations: tuple[str, Stance]) -> Requirement:
    return Requirement(
        id="r",
        text="r",
        type="mandatory",
        citations=tuple(Citation(source=s, section="s", stance=st) for s, st in citations),
    )


def test_current_official_source_without_conflict_auto_publishes() -> None:
    sources = {"a": _source("consulate_page")}
    assert publish_status(_req(("a", "supports")), sources, AS_OF) == "auto_publish"


def test_agent_as_top_source_needs_review() -> None:
    sources = {"a": _source("agent")}
    assert publish_status(_req(("a", "supports")), sources, AS_OF) == "needs_review"


def test_verified_more_than_90_days_ago_needs_review() -> None:
    sources = {"a": _source("official_checklist", AS_OF - timedelta(days=91))}
    assert publish_status(_req(("a", "supports")), sources, AS_OF) == "needs_review"


def test_conflict_of_equal_authority_needs_review() -> None:
    sources = {"a": _source("consulate_page"), "b": _source("consulate_page")}
    req = _req(("a", "supports"), ("b", "conflicts"))
    assert publish_status(req, sources, AS_OF) == "needs_review"


def test_conflict_of_lower_authority_does_not_block() -> None:
    sources = {"a": _source("consulate_page"), "b": _source("agent")}
    req = _req(("a", "supports"), ("b", "conflicts"))
    assert publish_status(req, sources, AS_OF) == "auto_publish"


def test_karachi_tuition_needs_review_because_the_checklist_outranks_the_page() -> None:
    req = next(
        r
        for r in entry(KARACHI, "study").requirements
        if r.id == "proof-of-payment-of-tuition-fees"
    )
    assert publish_status(req, REGISTRY.sources, AS_OF) == "needs_review"


def test_stale_karachi_blocked_account_still_auto_publishes_under_adr_0036() -> None:
    # The approved rule ignores document age; logged for the owner in PROGRESS.md.
    req = next(
        r for r in entry(KARACHI, "study").requirements if r.id == "blocked-account-confirmation"
    )
    assert publish_status(req, REGISTRY.sources, AS_OF) == "auto_publish"


def test_any_recently_verified_top_source_counts_whatever_the_order() -> None:
    sources = {
        "stale": _source("official_checklist", AS_OF - timedelta(days=200)),
        "fresh": _source("official_checklist"),
    }
    for order in (("stale", "fresh"), ("fresh", "stale")):
        req = _req(*((k, "supports") for k in order))
        assert publish_status(req, sources, AS_OF) == "auto_publish"
