"""Checklist pages. Imports only the registry, so the site build stays free of applicant data (R-22)."""

from pakkifile.registry.model import RegistryEntry
from pakkifile.web.templates import env


def render_checklist(entry: RegistryEntry) -> str:
    return env.get_template("checklist.html").render(entry=entry)
