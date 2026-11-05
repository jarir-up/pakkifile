import dataclasses
from decimal import Decimal
from pathlib import Path

from sqlalchemy import Connection

from evaldata.statement import TRACER_FACTS, StatementFacts, write_statement
from pakkifile.figures.continuity import largest_unattributed_credit
from pakkifile.figures.money import Money
from pakkifile.vault.ingest import add_person, ingest_statement_csv


def _load(db: Connection, facts: StatementFacts, tmp_path: Path) -> int:
    person = add_person(db, "applicant")
    return ingest_statement_csv(db, person, write_statement(facts, seed=7, out_dir=tmp_path))


def test_largest_unattributed_credit_is_the_seeded_cash_deposit(
    db: Connection, tmp_path: Path
) -> None:
    figure = largest_unattributed_credit(db, _load(db, TRACER_FACTS, tmp_path))
    assert figure is not None
    # From the fact table: PKR 900,000 cash deposit out of PKR 2,400,000 credits.
    assert figure.amount == Money(90_000_000, "PKR")
    assert figure.share_of_credits == Decimal("0.3750")
    assert len(figure.rows) == 1
    assert figure.rows[0].description == "CASH DEPOSIT"


def test_no_figure_when_every_credit_has_a_counterparty(db: Connection, tmp_path: Path) -> None:
    facts = dataclasses.replace(TRACER_FACTS, cash_deposit=None)
    assert largest_unattributed_credit(db, _load(db, facts, tmp_path)) is None
