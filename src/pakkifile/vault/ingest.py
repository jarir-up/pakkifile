"""Ingest evidence items into the vault. Files are read, never modified (R-29)."""

import csv
import hashlib
import re
from datetime import date
from pathlib import Path

from sqlalchemy import Connection, insert, select

from pakkifile.vault.classify import rule_columns
from pakkifile.vault.schema import evidence_item, person, statement_row

# Rules first (ADR-0018): a remittance memo names its sender; anything else is unattributed.
_REMITTANCE = re.compile(r"^HOME REMITTANCE - (?P<counterparty>.+?) - PRC \d+$")


def add_person(conn: Connection, role: str) -> int:
    return int(conn.execute(insert(person).values(role=role).returning(person.c.id)).scalar_one())


def counterparty_of(description: str) -> str | None:
    match = _REMITTANCE.match(description)
    return match["counterparty"] if match else None


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def stored_evidence_item(conn: Connection, person_id: int, sha256: str) -> int | None:
    """The evidence item this person already stored for this file, if any (ADR-0028)."""
    found = conn.scalar(
        select(evidence_item.c.id).where(
            evidence_item.c.person_id == person_id, evidence_item.c.sha256 == sha256
        )
    )
    return None if found is None else int(found)


def store_evidence_item(conn: Connection, person_id: int, path: Path, sha256: str) -> int:
    """Record a file for one person by name and sha256; the file is not changed (R-29)."""
    return int(
        conn.execute(
            insert(evidence_item)
            .values(person_id=person_id, file_name=path.name, sha256=sha256)
            .returning(evidence_item.c.id)
        ).scalar_one()
    )


def _csv_row(person_id: int, item_id: int, r: dict[str, str]) -> dict[str, object]:
    amount_minor = int(r["amount_minor"])
    return {
        "person_id": person_id,
        "evidence_item_id": item_id,
        "row_no": int(r["row_id"]),
        "date": date.fromisoformat(r["date"]),
        "description": r["description"],
        "counterparty": counterparty_of(r["description"]),
        "amount_minor": amount_minor,
        "currency": r["currency"],
        **rule_columns(r["description"], amount_minor, "bank"),
    }


def ingest_statement_csv(conn: Connection, person_id: int, path: Path) -> int:
    data = path.read_bytes()
    sha256 = file_sha256(path)
    if (existing := stored_evidence_item(conn, person_id, sha256)) is not None:
        return existing
    item_id = store_evidence_item(conn, person_id, path, sha256)
    rows = csv.DictReader(data.decode().splitlines())
    conn.execute(insert(statement_row), [_csv_row(person_id, item_id, r) for r in rows])
    return item_id
