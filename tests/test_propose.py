from datetime import date
from pathlib import Path
from typing import Any

import pytest
import yaml

from pakkifile.llm.extract import ExtractionError, ExtractionModel
from pakkifile.registry.files import load_sources, save_sources
from pakkifile.registry.model import ExtractedItem, Source
from pakkifile.sources import propose as propose_module
from pakkifile.sources.fetch import FetchedSource
from pakkifile.sources.propose import main, propose

AS_OF = date(2026, 11, 9)
MODEL = ExtractionModel("m")


def _source(checksum: str) -> Source:
    return Source(
        document="d",
        url="https://example.org/a",
        retrieved=date(2026, 10, 30),
        last_verified=date(2026, 10, 30),
        source_authority="consulate_page",
        checksum=checksum,
    )


@pytest.fixture
def root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    save_sources({"a": _source("old"), "b": _source("keep")}, tmp_path / "sources.yaml")
    monkeypatch.setattr(
        propose_module,
        "fetch",
        lambda url: FetchedSource(url, AS_OF, "<p>x</p>", "x", "new", True),
    )
    return tmp_path


def _extract(text: str, model: ExtractionModel) -> tuple[ExtractedItem, ...]:
    return (ExtractedItem(text="Passport", type="mandatory", condition=None),)


def test_changed_source_gets_a_proposal_and_its_new_checksum(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(propose_module, "extract_requirements", _extract)
    assert propose(["a"], root, MODEL, AS_OF) == {}
    proposal: Any = yaml.safe_load((root / "proposals" / "a.yaml").read_text())
    assert proposal["source"] == "a"
    assert proposal["requirements"][0]["text"] == "Passport"
    sources = load_sources(root / "sources.yaml")
    assert (sources["a"].checksum, sources["a"].retrieved) == ("new", AS_OF)
    assert sources["a"].last_verified == AS_OF
    assert sources["b"].checksum == "keep"


def test_failed_extraction_leaves_the_source_changed_for_next_week(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail(text: str, model: ExtractionModel) -> tuple[ExtractedItem, ...]:
        raise ExtractionError("bad output")

    monkeypatch.setattr(propose_module, "extract_requirements", fail)
    assert propose(["a"], root, MODEL, AS_OF) == {"a": "bad output"}
    assert load_sources(root / "sources.yaml")["a"].checksum == "old"
    assert not (root / "proposals" / "a.yaml").exists()


def test_one_failure_does_not_lose_the_other_proposals(
    root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fetch_or_fail(url: str) -> FetchedSource:
        if url.endswith("/b"):
            raise OSError("refused")
        return FetchedSource(url, AS_OF, "<p>x</p>", "x", "new", True)

    sources = load_sources(root / "sources.yaml")
    sources["b"] = sources["b"].model_copy(update={"url": "https://example.org/b"})
    save_sources(sources, root / "sources.yaml")
    monkeypatch.setattr(propose_module, "fetch", fetch_or_fail)
    monkeypatch.setattr(propose_module, "extract_requirements", _extract)
    assert list(propose(["a", "b"], root, MODEL, AS_OF)) == ["b"]
    saved = load_sources(root / "sources.yaml")
    assert (saved["a"].checksum, saved["b"].checksum) == ("new", "keep")


def test_command_exits_non_zero_when_a_source_failed(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(propose_module, "propose", lambda *args: {"a": "bad output"})
    monkeypatch.setenv("PAKKIFILE_EXTRACTION_MODEL", "m")
    monkeypatch.setattr("sys.argv", ["propose", "a"])
    with pytest.raises(SystemExit) as exit_info:
        main()
    assert exit_info.value.code == 1
    assert "failed a bad output" in capsys.readouterr().out
