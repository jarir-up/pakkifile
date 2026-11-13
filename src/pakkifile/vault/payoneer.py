"""Payoneer PDF statements (ADR-0054).

Rows are printed newest first (owner, 2026-11-12) and stored oldest first. The header has no
opening or closing balance, so they come from the running balance: the oldest row's balance
before it, and the newest row's after it. Every row in between must add up. The layout
guesses still to confirm are listed in `evaldata/payoneer.py`.
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

_DAY = r"\d{1,2} [A-Z][a-z]{2}, \d{4}"  # "19 Sep, 2024"
# The header (a public sample, 2026-11-13): the holder's name and address on the left; on the
# right "Account USD balance", "Period 02/01/2024 - 06/24/2024" and "Issuing Date". It
# prints no account number, so the account is named by its currency.
_ACCOUNT = re.compile(r"\s*Account (?P<currency>[A-Z]{3}) balance\s*")
_US_DAY = r"\d{2}/\d{2}/\d{4}"
_PERIOD = re.compile(rf"Period ({_US_DAY}) - ({_US_DAY})")
# "-12.00 USD Completed 88.00": the amount carries its currency; some rows have no status.
_ROW = re.compile(
    rf"^\s*(?P<day>{_DAY})\s+(?P<description>.+?)\s+(?P<amount>-?[\d,]+\.\d{{2}}) (?P<code>[A-Z]{{3}})"
    r"(?:\s+(?P<status>[A-Za-z][A-Za-z -]*?))?\s+(?P<balance>-?[\d,]+\.\d{2})\s*$"
)
_COLUMNS = ("Date", "Description", "Amount", "Status", "Running Balance")
_COMPLETED = "Completed"  # any other status may not have moved the balance


def _day(text: str) -> date:
    return datetime.strptime(text, "%d %b, %Y").date()


def account_name(currency: str) -> str:
    """What the vault calls a Payoneer account: its statement prints no account number."""
    return f"Payoneer {currency}"


def _holder(lines: list[str]) -> str:
    """The first line's left column: the holder's name, above their address."""
    first = next(line for line in lines if line.strip())
    left = _PERIOD.sub("", _ACCOUNT.sub("  ", first))
    return re.split(r"\s{2,}", left.strip())[0]


def _us_day(text: str) -> date:
    return datetime.strptime(text, "%m/%d/%Y").date()


def _is_header(line: str) -> bool:
    return all(name in line for name in _COLUMNS)


def parse_payoneer(text: str) -> Statement:
    """Read a statement's text, or raise StatementError if it can't be read or doesn't add up."""
    lines = statement_lines(text)
    account = next((m for line in lines if (m := _ACCOUNT.search(line))), None)
    if account is None:
        raise StatementError("not a Payoneer statement: no 'Account ... balance'")
    period = next((m for line in lines if (m := _PERIOD.search(line))), None)
    if period is None:
        raise StatementError("not a Payoneer statement: no 'Period MM/DD/YYYY - MM/DD/YYYY'")
    currency = account["currency"]
    title = _holder(lines)
    number = account_name(currency)
    period_from, period_to = _us_day(period[1]), _us_day(period[2])

    rows: list[StatementRow] = []
    description_at: int | None = None  # set once the table starts
    for line in lines:
        if _is_header(line):
            description_at = line.index("Description")
            continue
        if description_at is None or not line.strip() or is_page_footer(line):
            continue
        if match := _ROW.match(line):
            if match["status"] not in (None, _COMPLETED):
                raise StatementError(f"row status {match['status']!r}, not {_COMPLETED!r}")
            if match["code"] != currency:
                raise StatementError(f"a {match['code']} row on a {currency} statement: {line}")
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
    if description_at is None:
        raise StatementError("no Date, Description, Amount, Status, Running Balance header")
    if not rows:
        raise StatementError("no transactions, so the balance is unknown")
    if rows[0].booked < rows[-1].booked:
        raise StatementError("rows run oldest first; Payoneer prints them newest first")
    oldest_first = [replace(row, row_no=n) for n, row in enumerate(reversed(rows), start=1)]
    first = oldest_first[0]
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
            oldest_first[-1].balance_minor,
            tuple(oldest_first),
        )
    )


def ingest_payoneer_pdf(
    conn: Connection, person_id: int, path: Path, password: str | None = None
) -> int:
    """Store a Payoneer statement and its new rows for one person, all or nothing."""
    return ingest_pdf(conn, person_id, path, parse_payoneer, "platform", password)
