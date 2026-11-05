from datetime import date
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from pakkifile.registry.files import load_entry, save_entry
from pakkifile.registry.model import RegistryEntry
from pakkifile.sources.pipeline import TRACER_SOURCE, build_entry

EXCERPT = Path("registry-data/sources/de-missions-pk-study-visa.html")
LABELS = Path("evaldata/labels/de-islamabad-study-d.yaml")


def _entry() -> RegistryEntry:
    return build_entry(EXCERPT.read_text(), TRACER_SOURCE, verified=date(2026, 10, 30))


def test_extraction_matches_hand_labels() -> None:
    expected = {
        (item["text"], item["type"], item["condition"])
        for item in yaml.safe_load(LABELS.read_text())
    }
    got = {(r.text, r.type, r.condition) for r in _entry().requirements}
    assert got == expected


def test_every_requirement_cites_its_source() -> None:
    for req in _entry().requirements:
        assert req.source.url.startswith("https://pakistan.diplo.de/")
        assert req.source.section == "Mandatory documents"
        assert req.source.last_verified == date(2026, 10, 30)


def test_entry_round_trips_through_yaml(tmp_path: Path) -> None:
    path = tmp_path / "entry.yaml"
    save_entry(_entry(), path)
    assert load_entry(path) == _entry()


def test_requirement_without_retrieval_date_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "entry.yaml"
    save_entry(_entry(), path)
    data = yaml.safe_load(path.read_text())
    del data["requirements"][0]["source"]["retrieved"]
    with pytest.raises(ValidationError):
        RegistryEntry.model_validate(data)


def test_published_entry_matches_its_source() -> None:
    published = load_entry(Path("registry-data/entries/de-islamabad-study-d.yaml"))
    rebuilt = build_entry(
        EXCERPT.read_text(), TRACER_SOURCE, verified=published.requirements[0].source.last_verified
    )
    assert published == rebuilt
