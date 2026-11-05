"""Run the tracer path end to end and evaluate every stage (brief 01).

Expected values come from the hand-labelled checklist and the generator's
fact table, never from the code under test. Exits non-zero if any stage fails.

    uv run python -m eval.tracer --out build/tracer
"""

import argparse
import dataclasses
import os
import sys
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from html.parser import HTMLParser
from pathlib import Path

import yaml
from sqlalchemy import Connection, create_engine

from evaldata.statement import TRACER_EXPECTED_SHARE, TRACER_FACTS, write_statement
from pakkifile.dossier.build import EvidenceLink, build_dossier
from pakkifile.figures.continuity import largest_unattributed_credit
from pakkifile.mismatch.continuity import check_unattributed_credit
from pakkifile.registry.files import load_registry
from pakkifile.registry.model import RegistryEntry
from pakkifile.sources.pipeline import TRACER_SOURCE, build_entry
from pakkifile.vault.ingest import add_person, ingest_statement_csv
from pakkifile.vault.schema import metadata
from pakkifile.web.checklist import render_checklist
from pakkifile.web.dossier import render_dossier

EXCERPT = Path("registry-data/sources/de-missions-pk-study-visa.html")
REGISTRY = Path("registry-data")
LABELS = Path("evaldata/labels/de-islamabad-study-d.yaml")
DEFAULT_URL = "postgresql+psycopg://pakkifile:pakkifile@127.0.0.1:5433/pakkifile"
TUITION = "proof-of-payment-of-tuition-fees"


@dataclass(frozen=True)
class Result:
    stage: str
    metric: str
    value: str
    passed: bool


class _Attr(HTMLParser):
    def __init__(self, cls: str) -> None:
        super().__init__()
        self.cls = cls
        self.found: list[dict[str, str | None]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if ("class", self.cls) in attrs:
            self.found.append(dict(attrs))


def _found(html: str, cls: str) -> list[dict[str, str | None]]:
    parser = _Attr(cls)
    parser.feed(html)
    return parser.found


def _extraction(entry: RegistryEntry) -> list[Result]:
    expected = {(i["text"], i["type"], i["condition"]) for i in yaml.safe_load(LABELS.read_text())}
    got = {(r.text, r.type, r.condition) for r in entry.requirements}
    hits = len(expected & got)
    precision = Decimal(hits) / len(got) if got else Decimal(0)
    recall = Decimal(hits) / len(expected)
    return [
        Result("extraction", "precision", f"{precision:.2f}", precision == 1),
        Result("extraction", "recall", f"{recall:.2f}", recall == 1),
    ]


def run(conn: Connection, out: Path) -> list[Result]:
    results: list[Result] = []
    entry, _ = build_entry(EXCERPT.read_text(), TRACER_SOURCE, verified=date.today())
    results += _extraction(entry)

    registry = load_registry(REGISTRY)
    published = next(
        e
        for e in registry.entries
        if e.authority.name == TRACER_SOURCE.authority.name
        and e.application == TRACER_SOURCE.application
    )
    rebuilt, source = build_entry(
        EXCERPT.read_text(),
        TRACER_SOURCE,
        verified=registry.sources[TRACER_SOURCE.source_id].last_verified,
    )
    same = published == rebuilt and registry.sources[TRACER_SOURCE.source_id] == source
    results.append(Result("registry", "published entry matches source", str(same), same))

    checklist = render_checklist(published, registry.sources, date.today())
    rows = len(_found(checklist, "requirement"))
    results.append(
        Result(
            "checklist",
            "rows",
            f"{rows}/{len(published.requirements)}",
            rows == len(published.requirements),
        )
    )

    metadata.create_all(conn)
    statement = write_statement(TRACER_FACTS, seed=7, out_dir=out)
    applicant = add_person(conn, "applicant")
    item = ingest_statement_csv(conn, applicant, statement)
    figure = largest_unattributed_credit(conn, item)
    assert TRACER_FACTS.cash_deposit is not None
    deposit = TRACER_FACTS.cash_deposit[1]
    figure_ok = (
        figure is not None
        and figure.amount.amount_minor == deposit
        and figure.share_of_credits == TRACER_EXPECTED_SHARE
    )
    results.append(
        Result(
            "figure", "matches fact table", figure.amount.display() if figure else "none", figure_ok
        )
    )

    tuition = next(r for r in published.requirements if r.id == TUITION)
    finding = check_unattributed_credit(figure, tuition)
    clean = write_statement(
        dataclasses.replace(TRACER_FACTS, cash_deposit=None), seed=7, out_dir=out / "clean"
    )
    clean_item = ingest_statement_csv(conn, add_person(conn, "applicant"), clean)
    false_alarm = check_unattributed_credit(largest_unattributed_credit(conn, clean_item), tuition)
    found = finding is not None and finding.kind == "M2"
    results.append(Result("mismatch", "seeded M2 found", str(found), found))
    results.append(
        Result(
            "mismatch",
            "false findings on clean statement",
            str(int(false_alarm is not None)),
            false_alarm is None,
        )
    )

    dossier = render_dossier(
        build_dossier(
            published,
            f"{TRACER_FACTS.persona} (synthetic)",
            [EvidenceLink(TUITION, statement.name, figure)],
        )
    )
    figures = _found(dossier, "figure")
    cited = sum(1 for f in figures if f.get("data-source"))
    results.append(
        Result(
            "dossier",
            "figures cited",
            f"{cited}/{len(figures)}",
            bool(figures) and cited == len(figures),
        )
    )

    (out / "checklist.html").write_text(checklist)
    (out / "dossier.html").write_text(dossier)
    if finding:
        print(f"Finding {finding.kind} on '{finding.requirement.text}': {finding.statement}")
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("build/tracer"))
    out = parser.parse_args().out
    out.mkdir(parents=True, exist_ok=True)
    engine = create_engine(os.environ.get("PAKKIFILE_DATABASE_URL", DEFAULT_URL))
    with engine.connect() as conn:
        transaction = conn.begin()
        results = run(conn, out)
        transaction.rollback()
    for r in results:
        print(f"{'PASS' if r.passed else 'FAIL'}  {r.stage:<10} {r.metric:<34} {r.value}")
    if not all(r.passed for r in results):
        sys.exit(1)


if __name__ == "__main__":
    main()
