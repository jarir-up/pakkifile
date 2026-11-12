"""Payoneer PDF statements (ADR-0054).

The header has no opening or closing balance, so they come from the running balance: the
first row's balance before it, and the last row's after it. Every row in between must add up.
The layout guesses still to confirm are listed in `evaldata/payoneer.py`.
"""

import re
from dataclasses import replace
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import Connection

from pakkifile.figures.money import net_minor, parse_minor
from pakkifile.vault.statements import (
    Statement,
    StatementError,
    StatementRow,
    checked,
    ingest_pdf,
    is_page_footer,
    statement_lines,
)

_DAY = r"\d{2} [A-Z][a-z]{2} \d{4}"
_FIELD = re.compile(
    r"^\s*(Primary Account Number|Account Currency|Period|Issuing Date):\s*(.+?)\s*$"
)
_PERIOD = re.compile(rf"({_DAY}) - ({_DAY})")
_ROW = re.compile(
    rf"^\s*(?P<day>{_DAY})\s{{2,}}(?P<description>.+?)\s{{2,}}(?P<amount>-?[\d,]+\.\d{{2}})"
    r"\s{2,}(?P<status>\S.*?)\s{2,}(?P<balance>-?[\d,]+\.\d{2})\s*$"
)
_COLUMNS = ("Date", "Description", "Amount", "Status", "Running Balance")
_COMPLETED = "Completed"  # any other status may not have moved the balance


def _day(text: str) -> date:
    return datetime.strptime(text, "%d %b %Y").date()


def _is_header(line: str) -> bool:
    return all(name in line for name in _COLUMNS)


def parse_payoneer(text: str) -> Statement:
    """Read a statement's text, or raise StatementError if it can't be read or doesn't add up."""
    lines = statement_lines(text)
    fields = {m[1]: m[2] for line in lines if (m := _FIELD.match(line))}
    # Above the fields: the company header, then the address block, which opens with the holder.
    above = [
        line.strip()
        for line in lines[: next((i for i, line in enumerate(lines) if _FIELD.match(line)), 0)]
        if line.strip()
    ]
    try:
        title = above[1]
        number, currency = fields["Primary Account Number"], fields["Account Currency"]
        period = _PERIOD.fullmatch(fields["Period"])
        if period is None:
            raise StatementError(f"unreadable period: {fields['Period']!r}")
        period_from, period_to = _day(period[1]), _day(period[2])
    except (IndexError, KeyError) as error:
        raise StatementError(f"not a Payoneer statement: no {error} field") from error

    rows: list[StatementRow] = []
    description_at: int | None = None  # set once the table starts
    for line in lines:
        if _is_header(line):
            description_at = line.index("Description")
            continue
        if description_at is None or not line.strip() or is_page_footer(line):
            continue
        if match := _ROW.match(line):
            if match["status"] != _COMPLETED:
                raise StatementError(f"row status {match['status']!r}, not {_COMPLETED!r}")
            amount = parse_minor(match["amount"])
            rows.append(
                StatementRow(
                    row_no=len(rows) + 1,
                    booked=_day(match["day"]),
                    description=match["description"],
                    credit_minor=max(amount, 0),
                    debit_minor=max(-amount, 0),
                    balance_minor=parse_minor(match["balance"]),
                )
            )
        elif rows and len(line) - len(line.lstrip()) == description_at:
            last = rows[-1]  # a description continued on the next line
            rows[-1] = replace(last, description=f"{last.description} {line.strip()}")
        else:
            raise StatementError(f"unreadable row: {line.strip()}")
    if not rows:
        raise StatementError("no transactions, so the balance is unknown")
    first = rows[0]
    opening = first.balance_minor - net_minor(first.credit_minor, first.debit_minor)
    return checked(
        Statement(
            title,
            number,
            None,
            currency,
            period_from,
            period_to,
            opening,
            rows[-1].balance_minor,
            tuple(rows),
        )
    )


def ingest_payoneer_pdf(
    conn: Connection, person_id: int, path: Path, password: str | None = None
) -> int:
    """Store a Payoneer statement and its new rows for one person, all or nothing."""
    return ingest_pdf(conn, person_id, path, parse_payoneer, "platform", password)
