from pathlib import Path

from sqlalchemy import Connection, delete, insert, select

from eval.vault import evaluate, failures, ingest_persona, score_persona
from evaldata.persona import load_personas
from pakkifile.vault.schema import statement_row

ALL = load_personas()


def test_the_dev_split_meets_every_proposed_gate(db: Connection, tmp_path: Path) -> None:
    scores = evaluate(db, ALL.values(), tmp_path)
    assert failures(scores) == []
    assert all(s.expected_rows > 30 for s in scores)


def test_a_lost_row_fails_parse_and_once(db: Connection, tmp_path: Path) -> None:
    persona = ALL["syn-dev-payoneer"]
    person = ingest_persona(db, persona, tmp_path)
    first = db.scalar(select(statement_row.c.id).where(statement_row.c.person_id == person))
    db.execute(delete(statement_row).where(statement_row.c.id == first))
    missed = failures([score_persona(db, persona, person)])
    assert any("parse_exact" in m for m in missed)
    assert any("stored_once" in m for m in missed)


def test_a_wrong_rule_class_fails_its_gate(db: Connection, tmp_path: Path) -> None:
    persona = ALL["syn-dev-payoneer"]
    person = ingest_persona(db, persona, tmp_path)
    db.execute(
        statement_row.update()
        .where(statement_row.c.description == "ATM CASH WITHDRAWAL")
        .values(row_class="fee")
    )
    assert any("rule_wrong" in m for m in failures([score_persona(db, persona, person)]))


def test_a_row_stored_twice_fails_once(db: Connection, tmp_path: Path) -> None:
    persona = ALL["syn-dev-payoneer"]
    person = ingest_persona(db, persona, tmp_path)
    copy = db.execute(select(statement_row).where(statement_row.c.person_id == person)).first()
    assert copy is not None
    columns = {k: v for k, v in copy._asdict().items() if k != "id"}
    db.execute(insert(statement_row).values(columns))
    missed = failures([score_persona(db, persona, person)])
    assert missed == [f"{persona.id}: stored_once 0, gate 1"]
