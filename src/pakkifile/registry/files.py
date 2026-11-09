"""Registry data files (ADR-0040, ADR-0043): sources once, one entry per application."""

from collections.abc import Sequence
from pathlib import Path

import yaml

from pakkifile.registry.model import ExtractedItem, Registry, RegistryEntry, Source

SOURCES_FILE = "sources.yaml"
ENTRIES_DIR = "entries"
PROPOSALS_DIR = "proposals"


def save_entry(entry: RegistryEntry, path: Path) -> None:
    data = entry.model_dump(mode="json", exclude_defaults=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))


def _load_entry(path: Path) -> RegistryEntry:
    return RegistryEntry.model_validate(yaml.safe_load(path.read_text()))


def load_sources(path: Path) -> dict[str, Source]:
    raw = yaml.safe_load(path.read_text()) or {}
    return {key: Source.model_validate(value) for key, value in raw.items()}


def save_sources(sources: dict[str, Source], path: Path) -> None:
    data = {k: v.model_dump(mode="json", exclude_defaults=True) for k, v in sorted(sources.items())}
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))


def save_proposal(source_id: str, items: Sequence[ExtractedItem], root: Path) -> None:
    """What a model read from a changed source, for a maintainer to compare with the entries."""
    proposal = {
        "source": source_id,
        "requirements": [i.model_dump(exclude_none=True) for i in items],
    }
    (root / PROPOSALS_DIR).mkdir(exist_ok=True)
    (root / PROPOSALS_DIR / f"{source_id}.yaml").write_text(
        yaml.safe_dump(proposal, sort_keys=False, allow_unicode=True)
    )


def load_registry(root: Path) -> Registry:
    return Registry(
        sources=load_sources(root / SOURCES_FILE),
        entries=tuple(_load_entry(p) for p in sorted((root / ENTRIES_DIR).glob("*.yaml"))),
    )
