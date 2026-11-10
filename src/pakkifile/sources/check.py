"""Check every registry source for change (FR-4, ADR-0036).

uv run python -m pakkifile.sources.check
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Literal

from pakkifile.registry.files import REGISTRY, SOURCES_FILE, load_sources, save_sources
from pakkifile.registry.model import Source
from pakkifile.sources.fetch import FETCH_FAILURES, FetchedSource, fetch

CheckStatus = Literal["unchanged", "changed", "new", "failed"]


@dataclass(frozen=True)
class SourceCheck:
    source: Source
    status: CheckStatus
    text: str | None = None
    error: str | None = None


def _compare(source: Source, fetched: FetchedSource, as_of: date) -> SourceCheck:
    if not fetched.has_text:
        return SourceCheck(source, "failed", error="no text found")
    if source.checksum is None:
        update = {"checksum": fetched.checksum, "retrieved": as_of, "last_verified": as_of}
        return SourceCheck(source.model_copy(update=update), "new", text=fetched.text)
    if source.checksum == fetched.checksum:
        return SourceCheck(source.model_copy(update={"last_verified": as_of}), "unchanged")
    return SourceCheck(source, "changed", text=fetched.text)


def check_sources(sources: Mapping[str, Source], as_of: date) -> dict[str, SourceCheck]:
    checks = {}
    for source_id, source in sources.items():
        try:
            checks[source_id] = _compare(source, fetch(source.url), as_of)
        except FETCH_FAILURES as error:
            checks[source_id] = SourceCheck(source, "failed", error=repr(error))
    return checks


def run(root: Path, as_of: date) -> dict[str, SourceCheck]:
    """Check the sources under `root` and save what the check learned."""
    path = root / SOURCES_FILE
    checks = check_sources(load_sources(path), as_of)
    save_sources({source_id: c.source for source_id, c in checks.items()}, path)
    return checks


def main() -> None:
    for source_id, c in run(REGISTRY, date.today()).items():
        print(f"{c.status:<10} {source_id}{f' {c.error}' if c.error else ''}")


if __name__ == "__main__":
    main()
