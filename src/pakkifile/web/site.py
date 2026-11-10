"""The static checklist site (brief 04, ADR-0030). Built from the registry only (R-22).

uv run python -m pakkifile.web.site --out build/site
"""

import argparse
import re
from datetime import date
from itertools import groupby
from pathlib import Path

from pakkifile.registry.files import REGISTRY, load_registry
from pakkifile.registry.model import Registry, RegistryEntry
from pakkifile.web.checklist import render_checklist
from pakkifile.web.templates import env


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def entry_path(entry: RegistryEntry) -> Path:
    """Where an entry's page lives: by authority, application and applicant profile."""
    return (
        Path(_slug(entry.authority.name))
        / _slug(entry.application.label)
        / f"{_slug(entry.applicant_profile)}.html"
    )


def build_site(registry: Registry, out: Path, as_of: date) -> None:
    entries = sorted(registry.entries, key=lambda e: (e.authority.name, e.application.label))
    for entry in entries:
        page = out / entry_path(entry)
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(render_checklist(entry, registry.sources, as_of))
    authorities = [
        (name, [(e, entry_path(e).as_posix()) for e in group])
        for name, group in groupby(entries, key=lambda e: e.authority.name)
    ]
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(env.get_template("index.html").render(authorities=authorities))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("build/site"))
    build_site(load_registry(REGISTRY), parser.parse_args().out, date.today())


if __name__ == "__main__":
    main()
