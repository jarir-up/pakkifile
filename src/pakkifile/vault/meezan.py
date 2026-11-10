"""Meezan Bank PDF statements (ADR-0049). Files are read, never modified (R-29).

Columns are found from the header line's positions, so a credit is never read as a debit.
A password, when given, is passed to pdftotext and never stored (ADR-0053).
"""

import hashlib
import re
import subprocess
from dataclasses import dataclass, replace
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import Connection, insert, select

from pakkifile.figures.money import net_minor, parse_minor
from pakkifile.figures.reconcile import balance_gaps
from pakkifile.vault.dedupe import IncomingRow, StoredRow, sort_rows
from pakkifile.vault.ingest import store_evidence_item
from pakkifile.vault.schema import evidence_item, statement, statement_row

# The header is a grid: a line of these labels, then their values on the next line.
_LABELS = (
    "Account Title",
    "Account Number",
    "IBAN",
    "Scan Code",  # unused, but it marks the label line
    "Currency",
    "From Date",
    "To Date",
    "Opening Balance",
    "Closing Balance",
    "Address",
)
_CELL = re.compile(r"\S+(?: \S+)*")  # text up to a gap of two or more spaces
_DATE = re.compile(r"^\s*(\d{2}[A-Z][a-z]{2} \d{4})\s")
_CURRENCY = re.compile(r"\(([A-Z]{3})\)$")
# "560,000.00", "PKR560,000.00" or "+ PKR560,000.00": the column, not the sign, says credit.
_AMOUNT = re.compile(r"(?:[+-] ?)?(?:\b[A-Z]{3})?(-?[\d,]+\.\d{2})")
_COLUMNS = ("Credit", "Debit", "Available Balance")
_PAGE = re.compile(r"Page \d+ of \d+")


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
    return datetime.strptime(text, "%d%b %Y").date()


def _header_fields(lines: list[str]) -> dict[str, str]:
    """Pair each label, left to right, with the values on the line below it.

    Values don't line up under their labels, so order decides. A trailing label with no
    value (an empty Scan Code) is simply absent.
    """
    fields: dict[str, str] = {}
    for index, line in enumerate(lines):
        labels = [cell for cell in _CELL.findall(line) if cell in _LABELS]
        if len(labels) < 2:
            continue
        below = next((v for v in lines[index + 1 :] if v.strip()), "")
        fields.update(zip(labels, _CELL.findall(below), strict=False))
    return fields


def _header_amount(text: str, currency: str) -> int:
    return parse_minor(text.removeprefix(currency))


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
        found[column] = parse_minor(match.group(1))
    return found


def parse_meezan(text: str) -> MeezanStatement:
    """Read a statement's text, or raise StatementError if it can't be read or doesn't add up."""
    lines = [line.replace("\f", "") for line in text.splitlines()]
    fields = _header_fields(lines)
    header = next((line for line in lines if _is_header(line)), None)
    if header is None:
        raise StatementError(
            "not a Meezan Bank statement: no Booking Date ... Available Balance row"
        )
    try:
        title, number = fields["Account Title"], fields["Account Number"]
        code = _CURRENCY.search(fields["Currency"])
        currency = code.group(1) if code else fields["Currency"]
        period_from, period_to = _day(fields["From Date"]), _day(fields["To Date"])
        opening = _header_amount(fields["Opening Balance"], currency)
        closing = _header_amount(fields["Closing Balance"], currency)
    except KeyError as error:
        raise StatementError(f"not a Meezan Bank statement: no {error} field") from error
    except ValueError as error:
        raise StatementError(f"unreadable header field: {error}") from error
    ends = _column_ends(header)
    date_end = 0  # where the last row's date ended; continuations leave that span blank
    rows: list[MeezanRow] = []
    for line in lines:
        if _is_header(line):  # repeats on every page, where columns may sit differently
            ends = _column_ends(line)
            continue
        if not line.strip() or _PAGE.fullmatch(line.strip()):
            continue
        if date_match := _DATE.match(line):
            date_end = date_match.end()
            amounts = _amounts(line, ends)
            if "Available Balance" not in amounts:
                raise StatementError(f"row without a balance: {line.strip()}")
            rows.append(
                MeezanRow(
                    row_no=len(rows) + 1,
                    booked=_day(date_match.group(1)),
                    description=_AMOUNT.sub("", line[date_match.end() :]).strip(),
                    credit_minor=amounts.get("Credit", 0),
                    debit_minor=amounts.get("Debit", 0),
                    balance_minor=amounts["Available Balance"],
                )
            )
        elif rows and line[:date_end].strip() == "" and not _AMOUNT.search(line):
            last = rows[-1]  # a narration continued on the next line
            rows[-1] = replace(last, description=f"{last.description} {line.strip()}")

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
    gaps = balance_gaps(opening, rows, closing)
    if gaps:
        raise StatementError("balances don't add up: " + "; ".join(gaps))
    return parsed


def ingest_meezan_pdf(
    conn: Connection, person_id: int, path: Path, password: str | None = None
) -> int:
    """Store a statement and its new rows for one person, all or nothing (ADR-0028).

    A file this person already stored returns its existing evidence item.
    """
    sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    existing = conn.scalar(
        select(evidence_item.c.id).where(
            evidence_item.c.person_id == person_id, evidence_item.c.sha256 == sha256
        )
    )
    if existing is not None:
        return int(existing)
    parsed = parse_meezan(pdf_text(path, password))
    with conn.begin_nested():
        stored = _stored_rows(conn, person_id, parsed)
        item_id = store_evidence_item(conn, person_id, path)
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
                    }
                    for row in new
                ],
            )
    return item_id


def _stored_rows(conn: Connection, person_id: int, parsed: MeezanStatement) -> list[StoredRow]:
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
