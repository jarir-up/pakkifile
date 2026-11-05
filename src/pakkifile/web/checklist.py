"""Checklist pages. Imports only the registry, so the site build stays free of applicant data (R-22)."""

from collections.abc import Mapping
from datetime import date

from pakkifile.registry.confidence import confidence
from pakkifile.registry.model import RegistryEntry, Source
from pakkifile.web.templates import env


def render_checklist(entry: RegistryEntry, sources: Mapping[str, Source], as_of: date) -> str:
    levels = {r.id: confidence(r, sources, as_of).level for r in entry.requirements}
    return env.get_template("checklist.html").render(entry=entry, sources=sources, levels=levels)
