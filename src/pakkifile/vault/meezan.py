"""Meezan Bank PDF statements (ADR-0049). Files are read, never modified (R-29).

Columns are found from the header line's positions, so a credit is never read as a debit.
A password, when given, is passed to pdftotext and never stored (ADR-0053).
"""

import hashlib
import re
import subprocess
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import Connection, insert

from pakkifile.figures.money import parse_minor
from pakkifile.figures.reconcile import BalanceRow, balance_gaps
from pakkifile.vault.schema import evidence_item, statement, statement_row

_FIELD = re.compile(r"^\s*(?P<name>[A-Za-z ]+?)\s*:\s*(?P<value>.+?)\s*$")
_DATE = re.compile(r"^\s*(\d{2}/\d{2}/\d{4})\s")
_AMOUNT = re.compile(r"-?[\d,]+\.\d{2}")
_COLUMNS = ("Credit", "Debit", "Available Balance")


class StatementError(ValueError):
    """The statement can't be read as a Meezan Bank statement, or doesn't add up."""


@dataclass(frozen=True)
class MeezanRow:
    row_no: int
    booked: date
    description: str
    credit_minor: int
    debit_minor: int
    balance_minor: int


@dataclass(frozen=True)
class MeezanStatement:
    account_title: str
    account_number: str
    iban: str | None
    currency: str
    period_from: date
    period_to: date
    opening_minor: int
    closing_minor: int
    rows: tuple[MeezanRow, ...]


def pdf_text(path: Path, password: str | None = None) -> str:
    args = ["pdftotext", "-layout", *(["-upw", password] if password else []), str(path), "-"]
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode != 0:
        if "password" in result.stderr.lower():
            raise StatementError(f"{path.name}: wrong or missing password")
        raise StatementError(f"{path.name}: unreadable PDF ({result.stderr.strip()})")
    return result.stdout


def _day(text: str) -> date:
    return datetime.strptime(text, "%d/%m/%Y").date()


def _is_header(line: str) -> bool:
    return "Booking Date" in line and "Available Balance" in line


def _column_ends(header: str) -> dict[str, int]:
    return {name: header.index(name) + len(name) for name in _COLUMNS}


def _amounts(line: str, ends: dict[str, int]) -> dict[str, int]:
    """Assign each amount on a line to the column whose right edge it sits nearest."""
    found: dict[str, int] = {}
    for match in _AMOUNT.finditer(line):
        column = min(ends, key=lambda name: abs(ends[name] - match.end()))
        if column in found:
            raise StatementError(f"two amounts in the {column} column: {line.strip()}")
        found[column] = parse_minor(match.group())
    return found


def parse_meezan(text: str, check_balances: bool = True) -> MeezanStatement:
    lines = [line.replace("\f", "") for line in text.splitlines()]
    fields = {
        m["name"]: m["value"]
        for line in lines
        if (m := _FIELD.match(line)) and "  " not in m["name"]
    }
    try:
        header = next(line for line in lines if _is_header(line))
        title, number, currency = (
            fields["Account Title"],
            fields["Account Number"],
            fields["Currency"],
        )
        period_from, period_to = _day(fields["From Date"]), _day(fields["To Date"])
        opening = parse_minor(fields["Opening Balance"])
        closing = parse_minor(fields["Closing Balance"])
    except (StopIteration, KeyError, ValueError) as error:
        raise StatementError(f"not a Meezan Bank statement: missing {error}") from error
    ends, description_at = _column_ends(header), header.index("Description")
    rows: list[MeezanRow] = []
    for line in lines:
        if _is_header(line):  # repeats on every page, where columns may sit differently
            ends, description_at = _column_ends(line), line.index("Description")
            continue
        if not line.strip():
            continue
        if _DATE.match(line):
            amounts = _amounts(line, ends)
            if "Available Balance" not in amounts:
                raise StatementError(f"row without a balance: {line.strip()}")
            rows.append(
                MeezanRow(
                    row_no=len(rows) + 1,
                    booked=_day(line.split()[0]),
                    description=_AMOUNT.sub("", line[description_at:]).strip(),
                    credit_minor=amounts.get("Credit", 0),
                    debit_minor=amounts.get("Debit", 0),
                    balance_minor=amounts["Available Balance"],
                )
            )
        elif rows and line[:description_at].strip() == "" and not _AMOUNT.search(line):
            last = rows[-1]  # a narration continued on the next line
            rows[-1] = MeezanRow(
                last.row_no,
                last.booked,
                f"{last.description} {line.strip()}",
                last.credit_minor,
                last.debit_minor,
                last.balance_minor,
            )

    parsed = MeezanStatement(
        title,
        number,
        fields.get("IBAN"),
        currency,
        period_from,
        period_to,
        opening,
        closing,
        tuple(rows),
    )
    if check_balances:
        gaps = balance_gaps(
            opening,
            [BalanceRow(r.row_no, r.credit_minor, r.debit_minor, r.balance_minor) for r in rows],
            closing,
        )
        if gaps:
            raise StatementError("balances don't add up: " + "; ".join(gaps))
    return parsed


def ingest_meezan_pdf(
    conn: Connection, person_id: int, path: Path, password: str | None = None
) -> int:
    """Store a statement and its rows for one person. Nothing is stored if it fails to read."""
    parsed = parse_meezan(pdf_text(path, password))
    item_id = int(
        conn.execute(
            insert(evidence_item)
            .values(
                person_id=person_id,
                file_name=path.name,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            )
            .returning(evidence_item.c.id)
        ).scalar_one()
    )
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
    conn.execute(
        insert(statement_row),
        [
            {
                "person_id": person_id,
                "evidence_item_id": item_id,
                "row_no": r.row_no,
                "date": r.booked,
                "description": r.description,
                "amount_minor": r.credit_minor - r.debit_minor,
                "currency": parsed.currency,
                "balance_minor": r.balance_minor,
            }
            for r in parsed.rows
        ],
    )
    return item_id
