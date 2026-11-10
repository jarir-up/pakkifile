"""Propose requirements for changed sources, for a maintainer to review (ADR-0030).

uv run python -m pakkifile.sources.propose <source id>...
"""

import sys
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from pakkifile.llm.extract import ExtractionError, ExtractionModel, extract_requirements
from pakkifile.registry.files import (
    REGISTRY,
    SOURCES_FILE,
    load_sources,
    save_proposal,
    save_sources,
)
from pakkifile.sources.fetch import FETCH_FAILURES, fetch


def propose(
    source_ids: Sequence[str], root: Path, model: ExtractionModel, as_of: date
) -> dict[str, str]:
    """Write a proposal per source and return what failed, by source ID."""
    path = root / SOURCES_FILE
    sources = load_sources(path)
    failures = {}
    for source_id in source_ids:
        try:
            fetched = fetch(sources[source_id].url)
            items = extract_requirements(fetched.text, model)
        except (ExtractionError, *FETCH_FAILURES) as error:
            failures[source_id] = str(error)
            continue
        save_proposal(source_id, items, root)
        sources[source_id] = sources[source_id].model_copy(
            update={"checksum": fetched.checksum, "retrieved": as_of, "last_verified": as_of}
        )
    save_sources(sources, path)
    return failures


def main() -> None:
    failures = propose(sys.argv[1:], REGISTRY, ExtractionModel.from_env(), date.today())
    for source_id, error in failures.items():
        print(f"failed {source_id} {error}")
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
