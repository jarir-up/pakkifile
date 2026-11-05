"""Dossier pages for the reviewing officer."""

from pakkifile.dossier.build import Dossier
from pakkifile.web.templates import env


def render_dossier(dossier: Dossier) -> str:
    return env.get_template("dossier.html").render(dossier=dossier)
