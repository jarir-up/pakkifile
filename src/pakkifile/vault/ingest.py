"""Ingest evidence items into the vault. Files are read, never modified (R-29)."""

import csv
import hashlib
import re
from datetime import date
from pathlib import Path

from sqlalchemy import Connection, insert

from pakkifile.vault.schema import evidence_item, person, statement_row

# Rules first (ADR-0018): a remittance memo names its sender; anything else is unattributed.
_REMITTANCE = re.compile(r"^HOME REMITTANCE - (?P<counterparty>.+?) - PRC \d+$")


def add_person(conn: Connection, role: str) -> int:
    return int(conn.execute(insert(person).values(role=role).returning(person.c.id)).scalar_one())


def counterparty_of(description: str) -> str | None:
    match = _REMITTANCE.match(description)
    return match["counterparty"] if match else None


def ingest_statement_csv(conn: Connection, person_id: int, path: Path) -> int:
    data = path.read_bytes()
    item_id = int(
        conn.execute(
            insert(evidence_item)
            .values(
                person_id=person_id, file_name=path.name, sha256=hashlib.sha256(data).hexdigest()
            )
            .returning(evidence_item.c.id)
        ).scalar_one()
    )
    rows = list(csv.DictReader(data.decode().splitlines()))
    conn.execute(
        insert(statement_row),
        [
            {
                "person_id": person_id,
                "evidence_item_id": item_id,
                "row_no": int(r["row_id"]),
                "date": date.fromisoformat(r["date"]),
                "description": r["description"],
                "counterparty": counterparty_of(r["description"]),
                "amount_minor": int(r["amount_minor"]),
                "currency": r["currency"],
            }
            for r in rows
        ],
    )
    return item_id
