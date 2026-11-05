"""Registry entries as YAML files, one per application (ADR-0040)."""

from pathlib import Path

import yaml

from pakkifile.registry.model import RegistryEntry


def save_entry(entry: RegistryEntry, path: Path) -> None:
    path.write_text(yaml.safe_dump(entry.model_dump(mode="json"), sort_keys=False))


def load_entry(path: Path) -> RegistryEntry:
    return RegistryEntry.model_validate(yaml.safe_load(path.read_text()))
