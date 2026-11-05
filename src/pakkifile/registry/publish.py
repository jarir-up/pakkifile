"""Auto-publish or review, by the rule in ADR-0036."""

from collections.abc import Mapping
from datetime import date, timedelta
from typing import Literal

from pakkifile.registry.model import AUTHORITY_ORDER, Requirement, Source, SourceAuthority

PublishStatus = Literal["auto_publish", "needs_review"]
PUBLISHABLE_TOP: frozenset[SourceAuthority] = frozenset({"official_checklist", "consulate_page"})
MAX_UNVERIFIED = timedelta(days=90)


def publish_status(req: Requirement, sources: Mapping[str, Source], as_of: date) -> PublishStatus:
    def rank(source: Source) -> int:
        return AUTHORITY_ORDER.index(source.source_authority)

    supporting = req.cited(sources, "supports")
    best = min(rank(s) for s in supporting)
    # Among equally ranked top sources, the most recently verified one counts.
    top = max((s for s in supporting if rank(s) == best), key=lambda s: s.last_verified)
    conflicting = req.cited(sources, "conflicts")
    if top.source_authority not in PUBLISHABLE_TOP:
        return "needs_review"
    if any(rank(c) <= rank(top) for c in conflicting):
        return "needs_review"
    if as_of - top.last_verified > MAX_UNVERIFIED:
        return "needs_review"
    return "auto_publish"
