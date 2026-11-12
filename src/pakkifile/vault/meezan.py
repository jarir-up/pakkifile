"""Meezan Bank PDF statements (ADR-0049).

Columns are found from the header line's positions, so a credit is never read as a debit.
"""

import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import Connection

from pakkifile.figures.money import parse_minor
from pakkifile.vault.statements import (
    Statement,
    StatementError,
    StatementRow,
    checked,
    ingest_pdf,
    is_page_footer,
    statement_lines,
)

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


@dataclass
class _OpenRow:
    """A row while its lines are read: the date line, then any narration or amount lines."""

    booked: date
    words: list[str]
    amounts: dict[str, int]

    def add(self, text: str, amounts: dict[str, int]) -> None:
        if words := _AMOUNT.sub("", text).strip():
            self.words.append(words)
        for column, amount in amounts.items():
            if column in self.amounts:
                raise StatementError(f"two amounts in the {column} column: {text.strip()}")
            self.amounts[column] = amount

    def closed(self, row_no: int) -> StatementRow:
        description = " ".join(self.words)
        if "Available Balance" not in self.amounts:
            raise StatementError(f"row without a balance: {self.booked} {description}")
        return StatementRow(
            row_no=row_no,
            booked=self.booked,
            description=description,
            credit_minor=self.amounts.get("Credit", 0),
            debit_minor=self.amounts.get("Debit", 0),
            balance_minor=self.amounts["Available Balance"],
        )


def parse_meezan(text: str) -> Statement:
    """Read a statement's text, or raise StatementError if it can't be read or doesn't add up."""
    lines = statement_lines(text)
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
    date_end = 0  # where the open row's date ended; its other lines leave that span blank
    rows_read: list[_OpenRow] = []
    for line in lines:
        if _is_header(line):  # repeats on every page, where columns may sit differently
            ends = _column_ends(line)
            continue
        if not line.strip() or is_page_footer(line):
            continue
        if date_match := _DATE.match(line):
            date_end = date_match.end()
            rows_read.append(_OpenRow(_day(date_match.group(1)), [], {}))
            rows_read[-1].add(line[date_end:], _amounts(line, ends))
        elif rows_read and line[:date_end].strip() == "":
            rows_read[-1].add(line, _amounts(line, ends))  # narration or amounts on a later line
    rows = [row.closed(number) for number, row in enumerate(rows_read, start=1)]

    return checked(
        Statement(
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
    )


def ingest_meezan_pdf(
    conn: Connection, person_id: int, path: Path, password: str | None = None
) -> int:
    """Store a Meezan statement and its new rows for one person, all or nothing."""
    return ingest_pdf(conn, person_id, path, parse_meezan, "bank", password)
