import os
import shutil
from pathlib import Path

import pytest
from sqlalchemy import Connection, Table, func, select

from evaldata.meezan import write_meezan_statement
from evaldata.payoneer import write_payoneer_statement
from evaldata.persona import load_personas, transactions
from evaldata.prc import prc_remittances, write_sprc
from pakkifile.llm.ollama import LocalModel
from pakkifile.vault.__main__ import ingest_files, kind_of
from pakkifile.vault.ingest import add_person
from pakkifile.vault.schema import prc_certificate, statement, statement_row
from pakkifile.vault.statements import StatementError, pdf_text

# CI installs qpdf (ADR-0053); a developer without it skips only the password test.
needs_qpdf = pytest.mark.skipif(
    not shutil.which("qpdf") and not os.environ.get("CI"), reason="qpdf not installed"
)
PERSONA = load_personas()["syn-dev-payoneer"]


def test_each_kind_of_file_is_told_from_its_text(tmp_path: Path) -> None:
    kinds = [
        kind_of(pdf_text(path))
        for path in (
            write_meezan_statement(PERSONA, tmp_path),
            write_payoneer_statement(PERSONA, tmp_path),
            write_sprc(PERSONA, tmp_path),
        )
    ]
    assert kinds == ["meezan", "payoneer", "prc"]


def test_a_file_of_no_known_kind_is_refused() -> None:
    with pytest.raises(StatementError, match="not a Meezan or Payoneer statement or an e-PRC"):
        kind_of("A utility bill")


def _count(db: Connection, table: Table, person: int) -> int:
    return int(db.scalar(select(func.count()).where(table.c.person_id == person)) or 0)


def test_every_file_is_stored_for_the_person(db: Connection, tmp_path: Path) -> None:
    person = add_person(db, "applicant")
    files = [
        write_meezan_statement(PERSONA, tmp_path),
        write_payoneer_statement(PERSONA, tmp_path),
        write_sprc(PERSONA, tmp_path),
    ]
    done = ingest_files(db, person, files, password=lambda _: None, model=None)
    assert [kind for _, kind in done.files] == ["meezan", "payoneer", "prc"]
    assert done.classified is None
    assert _count(db, statement, person) == 2
    assert _count(db, prc_certificate, person) == len(prc_remittances(PERSONA))
    assert _count(db, statement_row, person) == len(transactions(PERSONA))


@needs_qpdf
def test_a_password_is_asked_for_only_when_a_file_has_one(db: Connection, tmp_path: Path) -> None:
    asked: list[str] = []

    def ask(path: Path) -> str:
        asked.append(path.name)
        return "4417"

    locked = write_meezan_statement(PERSONA, tmp_path / "locked", password="4417")
    plain = write_payoneer_statement(PERSONA, tmp_path)
    ingest_files(db, add_person(db, "applicant"), [locked, plain], ask, None)
    assert asked == [locked.name]


def test_a_person_not_in_the_vault_is_refused(db: Connection, tmp_path: Path) -> None:
    with pytest.raises(StatementError, match="no person -1"):
        ingest_files(db, -1, [write_sprc(PERSONA, tmp_path)], lambda _: None, None)


def test_an_unavailable_model_leaves_rows_waiting_for_review(
    db: Connection, tmp_path: Path
) -> None:
    person = add_person(db, "applicant")
    gone = LocalModel("qwen3:8b", "http://127.0.0.1:9")  # nothing listens on port 9
    student = load_personas()["syn-student-sponsored"]  # its sponsor transfer is ambiguous
    done = ingest_files(
        db, person, [write_meezan_statement(student, tmp_path)], lambda _: None, gone
    )
    assert done.model_error and done.classified is None
    unplaced = select(func.count()).where(
        statement_row.c.person_id == person, statement_row.c.class_source.is_(None)
    )
    assert db.scalar(unplaced) == 1
