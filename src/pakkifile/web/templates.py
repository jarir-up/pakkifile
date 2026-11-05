"""The shared Jinja2 environment for every page (ADR-0039)."""

from jinja2 import Environment, PackageLoader, select_autoescape

env = Environment(
    loader=PackageLoader("pakkifile.web", "templates"),
    autoescape=select_autoescape(),
)
