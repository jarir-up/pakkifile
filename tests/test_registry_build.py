from datetime import date
from pathlib import Path

import yaml

from pakkifile.registry.files import load_registry
from pakkifile.registry.model import RegistryEntry, Source
from pakkifile.sources.pipeline import TRACER_SOURCE, build_entry, same_source

EXCERPT = Path("registry-data/sources/de-missions-pk-study-visa.html")
LABELS = Path("evaldata/labels/de-islamabad-study-d.yaml")
VERIFIED = date(2026, 10, 30)


def _built() -> tuple[RegistryEntry, Source]:
    return build_entry(EXCERPT.read_text(), TRACER_SOURCE, verified=VERIFIED)


def test_extraction_matches_hand_labels() -> None:
    expected = {
        (item["text"], item["type"], item["condition"])
        for item in yaml.safe_load(LABELS.read_text())
    }
    entry, _ = _built()
    assert {(r.text, r.type, r.condition) for r in entry.requirements} == expected


def test_every_requirement_cites_the_page_section() -> None:
    entry, source = _built()
    assert source.url.startswith("https://pakistan.diplo.de/")
    assert source.published == date(2025, 11, 27)
    assert source.last_verified == VERIFIED
    for req in entry.requirements:
        (citation,) = req.citations
        assert citation.source == TRACER_SOURCE.source_id
        assert citation.section == "Mandatory documents"


def test_published_registry_matches_its_source() -> None:
    registry = load_registry(Path("registry-data"))
    entry, source = build_entry(EXCERPT.read_text(), TRACER_SOURCE, verified=VERIFIED)
    assert entry in registry.entries
    assert same_source(registry.sources[TRACER_SOURCE.source_id], source)


def test_job_dates_and_checksum_do_not_make_a_different_source() -> None:
    _, source = _built()
    refreshed = source.model_copy(
        update={
            "retrieved": date(2026, 11, 10),
            "last_verified": date(2026, 11, 10),
            "checksum": "x",
        }
    )
    assert same_source(refreshed, source)
    assert not same_source(refreshed.model_copy(update={"url": "https://example.org"}), source)
