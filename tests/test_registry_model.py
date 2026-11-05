from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import ValidationError

from pakkifile.registry.files import load_registry, save_entry, save_sources
from pakkifile.registry.model import Registry, RegistryEntry, Source

ROOT = Path("registry-data")
ENTRY = ROOT / "entries" / "de-islamabad-study-d.yaml"
SOURCE = {
    "document": "Study visa",
    "url": "https://pakistan.diplo.de/x",
    "retrieved": "2026-10-30",
    "last_verified": "2026-10-30",
    "source_authority": "consulate_page",
}


def _entry() -> Any:
    return yaml.safe_load(ENTRY.read_text())


def test_entry_names_authority_application_and_profile() -> None:
    entry = RegistryEntry.model_validate(_entry())
    assert entry.authority.kind == "embassy"
    assert entry.authority.authority_class == "Schengen missions"
    assert entry.application.label == "Study visa (D)"
    assert entry.applicant_profile == "Self-funded freelancer"


@pytest.mark.parametrize("category", ["C", "D", None])
def test_visa_category_may_be_c_d_or_none(category: str | None) -> None:
    data = _entry()
    data["application"]["visa_category"] = category
    assert RegistryEntry.model_validate(data).application.visa_category == category


def test_visa_category_outside_c_and_d_is_rejected() -> None:
    data = _entry()
    data["application"]["visa_category"] = "E"
    with pytest.raises(ValidationError):
        RegistryEntry.model_validate(data)


def test_requirement_without_a_citation_is_rejected() -> None:
    data = _entry()
    data["requirements"][0]["citations"] = []
    with pytest.raises(ValidationError):
        RegistryEntry.model_validate(data)


def test_requirement_with_only_conflicting_citations_is_rejected() -> None:
    data = _entry()
    data["requirements"][0]["citations"][0]["stance"] = "conflicts"
    with pytest.raises(ValidationError):
        RegistryEntry.model_validate(data)


@pytest.mark.parametrize(
    "field", ["document", "url", "retrieved", "last_verified", "source_authority"]
)
def test_source_missing_a_required_field_is_rejected(field: str) -> None:
    data = dict(SOURCE)
    del data[field]
    with pytest.raises(ValidationError):
        Source.model_validate(data)


def test_source_without_published_date_or_checksum_is_accepted() -> None:
    source = Source.model_validate(SOURCE)
    assert source.published is None and source.checksum is None


def test_citation_of_an_unknown_source_is_rejected() -> None:
    entry = RegistryEntry.model_validate(_entry())
    with pytest.raises(ValidationError):
        Registry(sources={}, entries=(entry,))


def test_published_registry_loads() -> None:
    assert load_registry(ROOT).entries


def test_registry_files_round_trip(tmp_path: Path) -> None:
    registry = load_registry(ROOT)
    (tmp_path / "entries").mkdir()
    save_sources(dict(registry.sources), tmp_path / "sources.yaml")
    for i, entry in enumerate(registry.entries):
        save_entry(entry, tmp_path / "entries" / f"{i}.yaml")
    assert load_registry(tmp_path) == registry


def test_citation_without_a_section_is_rejected() -> None:
    data = _entry()
    del data["requirements"][0]["citations"][0]["section"]
    with pytest.raises(ValidationError):
        RegistryEntry.model_validate(data)
