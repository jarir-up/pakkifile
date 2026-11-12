"""PDF statements in the vault: reading, checking and storing, whatever the bank or platform.

Files are read, never modified (R-29). A password, when given, is passed to pdftotext and
never stored (ADR-0053). Each format's parser turns text into a `Statement`; storing it is
the same for every format.
"""

import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from sqlalchemy import Connection, insert, select

from pakkifile.figures.money import net_minor
from pakkifile.figures.reconcile import balance_gaps
from pakkifile.vault.classify import AccountKind, rule_columns
from pakkifile.vault.dedupe import IncomingRow, StoredRow, fingerprint, sort_rows
from pakkifile.vault.ingest import file_sha256, store_evidence_item, stored_evidence_item
from pakkifile.vault.schema import statement, statement_row


class StatementError(ValueError):
    """The statement can't be read in its format, or doesn't add up."""


@dataclass(frozen=True)
class StatementRow:
    row_no: int
    booked: date
    description: str
    credit_minor: int
    debit_minor: int
    balance_minor: int


@dataclass(frozen=True)
class Statement:
    account_title: str
    account_number: str
    iban: str | None
    currency: str
    period_from: date
    period_to: date
    opening_minor: int
    closing_minor: int
    rows: tuple[StatementRow, ...]


Parser = Callable[[str], Statement]
_PAGE = re.compile(r"Page \d+ of \d+")


def statement_lines(text: str) -> list[str]:
    """pdftotext's lines, without the form feeds between pages."""
    return [line.replace("\f", "") for line in text.splitlines()]


def is_page_footer(line: str) -> bool:
    return bool(_PAGE.fullmatch(line.strip()))


def pdf_text(path: Path, password: str | None = None) -> str:
    args = ["pdftotext", "-layout", *(["-upw", password] if password else []), str(path), "-"]
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        if "password" in result.stderr.lower():
            raise StatementError(f"{path.name}: wrong or missing password")
        raise StatementError(f"{path.name}: unreadable PDF ({result.stderr.strip()})")
    return result.stdout


def checked(parsed: Statement) -> Statement:
    """The statement, if its balances add up; otherwise StatementError with each gap."""
    gaps = balance_gaps(parsed.opening_minor, parsed.rows, parsed.closing_minor)
    if gaps:
        raise StatementError("balances don't add up: " + "; ".join(gaps))
    return parsed


def ingest_pdf(
    conn: Connection,
    person_id: int,
    path: Path,
    parse: Parser,
    account: AccountKind,
    password: str | None = None,
) -> int:
    """Store a statement and its new rows for one person, all or nothing (ADR-0028).

    A file this person already stored returns its existing evidence item.
    """
    sha256 = file_sha256(path)
    if (existing := stored_evidence_item(conn, person_id, sha256)) is not None:
        return existing
    parsed = parse(pdf_text(path, password))
    with conn.begin_nested():
        stored = _stored_rows(conn, person_id, parsed)
        item_id = store_evidence_item(conn, person_id, path, sha256)
        conn.execute(
            insert(statement).values(
                person_id=person_id,
                evidence_item_id=item_id,
                account_title=parsed.account_title,
                account_number=parsed.account_number,
                iban=parsed.iban,
                currency=parsed.currency,
                period_from=parsed.period_from,
                period_to=parsed.period_to,
                opening_minor=parsed.opening_minor,
                closing_minor=parsed.closing_minor,
            )
        )
        new, _, possible = sort_rows(
            [
                IncomingRow(
                    r.booked,
                    r.description,
                    net_minor(r.credit_minor, r.debit_minor),
                    r.row_no,
                    r.balance_minor,
                )
                for r in parsed.rows
            ],
            stored,
        )
        flagged = {row.row_no: stored_id for row, stored_id in possible}
        if new:  # a dormant month, or a statement fully covered by earlier ones, has none
            conn.execute(
                insert(statement_row),
                [
                    {
                        "person_id": person_id,
                        "evidence_item_id": item_id,
                        "row_no": row.row_no,
                        "date": row.booked,
                        "description": row.description,
                        "amount_minor": row.amount_minor,
                        "currency": parsed.currency,
                        "balance_minor": row.balance_minor,
                        "possible_duplicate_of": flagged.get(row.row_no),
                        "fingerprint": fingerprint(parsed.account_number, row),
                        **rule_columns(row.description, row.amount_minor, account),
                    }
                    for row in new
                ],
            )
    return item_id


def _stored_rows(conn: Connection, person_id: int, parsed: Statement) -> list[StoredRow]:
    """This person's rows already stored for the same account within the statement's period."""
    query = (
        select(
            statement_row.c.id,
            statement_row.c.date,
            statement_row.c.description,
            statement_row.c.amount_minor,
        )
        .join(statement, statement.c.evidence_item_id == statement_row.c.evidence_item_id)
        .where(
            statement_row.c.person_id == person_id,
            statement.c.account_number == parsed.account_number,
            statement_row.c.date.between(parsed.period_from, parsed.period_to),
        )
    )
    return [StoredRow(*row) for row in conn.execute(query)]
