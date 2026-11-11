from datetime import date
from pathlib import Path

from sqlalchemy import Connection, func, select

from evaldata.meezan import write_meezan_statement
from evaldata.persona import load_personas, transactions
from evaldata.statement import TRACER_FACTS, write_statement
from pakkifile.vault.dedupe import IncomingRow, StoredRow, sort_rows
from pakkifile.vault.ingest import add_person, ingest_statement_csv
from pakkifile.vault.meezan import ingest_meezan_pdf
from pakkifile.vault.schema import evidence_item, statement_row

DEV = load_personas()["syn-dev-payoneer"]
ATM = IncomingRow(date(2026, 4, 22), "ATM CASH WITHDRAWAL", -4_000_000)


def _rows(db: Connection, person: int) -> int:
    return int(db.scalar(select(func.count()).where(statement_row.c.person_id == person)) or 0)


def test_the_same_file_is_ingested_once(db: Connection, tmp_path: Path) -> None:
    person = add_person(db, "applicant")
    path = write_meezan_statement(DEV, tmp_path)
    first = ingest_meezan_pdf(db, person, path)
    count = _rows(db, person)
    assert ingest_meezan_pdf(db, person, path) == first
    assert _rows(db, person) == count
    assert db.scalar(select(func.count()).select_from(evidence_item)) == 1


def test_overlapping_statements_store_each_transaction_once(db: Connection, tmp_path: Path) -> None:
    person = add_person(db, "applicant")
    early = write_meezan_statement(DEV, tmp_path / "a", end=date(2026, 7, 31))
    late = write_meezan_statement(DEV, tmp_path / "b", start=date(2026, 6, 1))
    ingest_meezan_pdf(db, person, early)
    ingest_meezan_pdf(db, person, late)
    assert _rows(db, person) == len([t for t in transactions(DEV) if t.account == "meezan"])


def test_another_persons_identical_file_is_their_own(db: Connection, tmp_path: Path) -> None:
    path = write_meezan_statement(DEV, tmp_path)
    one, two = add_person(db, "applicant"), add_person(db, "sponsor")
    assert ingest_meezan_pdf(db, one, path) != ingest_meezan_pdf(db, two, path)
    assert _rows(db, two) == _rows(db, one)


def test_two_identical_rows_in_one_statement_are_both_kept() -> None:
    new, duplicates, possible = sort_rows([ATM, ATM], [])
    assert len(new) == 2 and not duplicates and not possible


def test_a_row_already_stored_is_a_duplicate() -> None:
    stored = StoredRow(1, ATM.booked, ATM.description, ATM.amount_minor)
    new, duplicates, possible = sort_rows([ATM], [stored])
    assert (new, duplicates, possible) == ([], [ATM], [])


def test_same_day_and_amount_with_other_words_is_flagged_not_dropped() -> None:
    stored = StoredRow(1, ATM.booked, "ATM WDL KARACHI", ATM.amount_minor)
    new, duplicates, possible = sort_rows([ATM], [stored])
    assert new == [ATM] and not duplicates
    assert possible == [(ATM, 1)]


def test_identical_rows_in_one_statement_keep_their_own_row_and_balance(
    db: Connection, tmp_path: Path
) -> None:
    twice = DEV.model_copy(update={"once": (*DEV.once, *DEV.once[-1:])})  # two cash deposits
    person = add_person(db, "applicant")
    item = ingest_meezan_pdf(db, person, write_meezan_statement(twice, tmp_path))
    deposits = db.execute(
        select(statement_row.c.row_no, statement_row.c.balance_minor).where(
            statement_row.c.evidence_item_id == item,
            statement_row.c.description == "CASH DEPOSIT",
        )
    ).all()
    assert len(deposits) == 2
    assert len({d.row_no for d in deposits}) == 2 and len({d.balance_minor for d in deposits}) == 2


def test_a_statement_with_no_transactions_is_stored(db: Connection, tmp_path: Path) -> None:
    quiet = write_meezan_statement(DEV, tmp_path, start=date(2026, 4, 1), end=date(2026, 4, 2))
    item = ingest_meezan_pdf(db, add_person(db, "applicant"), quiet)
    assert db.scalar(select(func.count()).where(statement_row.c.evidence_item_id == item)) == 0


def test_repeats_across_statements_consume_one_stored_match_each() -> None:
    stored = [StoredRow(i, ATM.booked, ATM.description, ATM.amount_minor) for i in (1, 2)]
    new, duplicates, _ = sort_rows([ATM, ATM, ATM], stored)
    assert (len(new), len(duplicates)) == (1, 2)


def test_a_possible_duplicate_is_stored_and_points_at_its_match(
    db: Connection, tmp_path: Path
) -> None:
    person = add_person(db, "applicant")
    ingest_meezan_pdf(db, person, write_meezan_statement(DEV, tmp_path / "a"))
    renamed = DEV.model_copy(
        update={
            "once": tuple(
                line.model_copy(update={"description": "CASH DEP BRANCH 0101"})
                if line.description == "CASH DEPOSIT"
                else line
                for line in DEV.once
            )
        }
    )
    ingest_meezan_pdf(db, person, write_meezan_statement(renamed, tmp_path / "b"))
    flagged = db.execute(
        select(statement_row.c.description, statement_row.c.possible_duplicate_of).where(
            statement_row.c.person_id == person, statement_row.c.possible_duplicate_of.is_not(None)
        )
    ).all()
    assert [f.description for f in flagged] == ["CASH DEP BRANCH 0101"]


def test_the_same_csv_is_ingested_once(db: Connection, tmp_path: Path) -> None:
    person = add_person(db, "applicant")
    path = write_statement(TRACER_FACTS, seed=7, out_dir=tmp_path)
    assert ingest_statement_csv(db, person, path) == ingest_statement_csv(db, person, path)


def test_every_stored_row_has_a_distinct_fingerprint(db: Connection, tmp_path: Path) -> None:
    person = add_person(db, "applicant")
    ingest_meezan_pdf(db, person, write_meezan_statement(DEV, tmp_path))
    keys = db.scalars(
        select(statement_row.c.fingerprint).where(statement_row.c.person_id == person)
    ).all()
    assert all(keys) and len(set(keys)) == len(keys)
