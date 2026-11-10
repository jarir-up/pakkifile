import os
import shutil
from pathlib import Path

import pytest
from sqlalchemy import Connection, func, select

from evaldata.meezan import write_meezan_statement
from evaldata.persona import Persona, load_personas, transactions
from pakkifile.vault import meezan
from pakkifile.vault.ingest import add_person
from pakkifile.vault.meezan import StatementError, ingest_meezan_pdf, parse_meezan, pdf_text
from pakkifile.vault.schema import evidence_item, statement, statement_row

ALL = load_personas()
WITH_MEEZAN = [p for p in ALL.values() if "meezan" in p.accounts]
# CI installs qpdf (ADR-0053); a developer without it skips only the encryption tests.
needs_qpdf = pytest.mark.skipif(
    not shutil.which("qpdf") and not os.environ.get("CI"), reason="qpdf not installed"
)


@pytest.mark.parametrize("persona", WITH_MEEZAN, ids=lambda p: p.id)
def test_every_row_and_header_field_reads_back_exactly(persona: Persona, tmp_path: Path) -> None:
    parsed = parse_meezan(pdf_text(write_meezan_statement(persona, tmp_path)))
    account = persona.accounts["meezan"]
    assert (parsed.account_number, parsed.currency) == (account.number, account.currency)
    assert (parsed.period_from, parsed.period_to) == (persona.period_from, persona.period_to)
    assert parsed.opening_minor == account.opening
    assert parsed.closing_minor == persona.expected.closing["meezan"]
    want = [t for t in transactions(persona) if t.account == "meezan"]
    got = [(r.booked, r.description, r.credit_minor - r.debit_minor) for r in parsed.rows]
    assert got == [(t.date, t.description, t.amount_minor) for t in want]


def test_a_wrapped_description_is_joined_back(tmp_path: Path) -> None:
    parsed = parse_meezan(pdf_text(write_meezan_statement(ALL["syn-student-sponsored"], tmp_path)))
    assert "OUTWARD REMITTANCE SYN HOCHSCHULE TUITION FEE" in [r.description for r in parsed.rows]


def test_a_statement_over_several_pages_reads_every_row(tmp_path: Path) -> None:
    long = ALL["syn-designer-direct"].model_copy(update={"months": 24})
    parsed = parse_meezan(pdf_text(write_meezan_statement(long, tmp_path)))
    assert len(parsed.rows) == len([t for t in transactions(long) if t.account == "meezan"])
    assert len(parsed.rows) > 100


def test_ingest_stores_the_statement_and_its_rows(db: Connection, tmp_path: Path) -> None:
    persona = ALL["syn-dev-payoneer"]
    person = add_person(db, "applicant")
    item = ingest_meezan_pdf(db, person, write_meezan_statement(persona, tmp_path))
    stored = db.execute(select(statement).where(statement.c.evidence_item_id == item)).one()
    assert stored.person_id == person
    assert stored.closing_minor == persona.expected.closing["meezan"]
    rows = db.scalar(select(func.count()).where(statement_row.c.evidence_item_id == item))
    assert rows == len([t for t in transactions(persona) if t.account == "meezan"])


def test_balances_that_do_not_add_up_stop_ingestion_and_store_nothing(
    db: Connection, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = write_meezan_statement(ALL["syn-dev-payoneer"], tmp_path)
    tampered = pdf_text(path).replace("745,000.00", "746,000.00", 1)
    monkeypatch.setattr(meezan, "pdf_text", lambda *_: tampered)
    with pytest.raises(StatementError, match="off by 100000"):
        ingest_meezan_pdf(db, add_person(db, "applicant"), path)
    assert db.scalar(select(func.count()).select_from(evidence_item)) == 0


def test_page_footers_are_not_read_as_narration(tmp_path: Path) -> None:
    text = pdf_text(write_meezan_statement(ALL["syn-dev-payoneer"], tmp_path))
    assert "Page 1 of 1" in text
    assert all("Page" not in r.description for r in parse_meezan(text).rows)


@needs_qpdf
def test_a_protected_statement_opens_with_its_password(tmp_path: Path) -> None:
    path = write_meezan_statement(ALL["syn-dev-payoneer"], tmp_path, password="4417")
    assert parse_meezan(pdf_text(path, password="4417")).rows


@needs_qpdf
def test_a_wrong_password_fails_and_stores_nothing(db: Connection, tmp_path: Path) -> None:
    path = write_meezan_statement(ALL["syn-dev-payoneer"], tmp_path, password="4417")
    person = add_person(db, "applicant")
    with pytest.raises(StatementError, match="password"):
        ingest_meezan_pdf(db, person, path, password="0000")
    assert db.scalar(select(func.count()).select_from(statement)) == 0
