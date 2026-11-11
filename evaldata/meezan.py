"""Synthetic statements in the Meezan Bank layout (ADR-0049).

Layout source: the owner's own statement, 2026-11-10 and 2026-11-11. The header is a grid of
labels with their values on the line below: Account Title, Account Number, IBAN, Scan Code;
Currency (as "Pakistan Rupee(PKR)"), From Date, To Date; Opening Balance, Closing Balance
(as "PKR60,964.71"), Address. Dates read "01Jul 2024". The table header is indented: Booking
Date, Description, Credit, Debit, Available Balance.

Not yet confirmed: how rows write their dates and amounts. They follow the header here.
Long descriptions wrap onto continuation lines, as bank narrations do.
"""

import textwrap
from datetime import date
from pathlib import Path

from evaldata.pdf import encrypt, paginate, write_pdf
from evaldata.persona import Persona, transactions

DESCRIPTION_WIDTH = 38
# Where each column's text starts or ends, in characters; amounts are right-aligned.
DATE_AT, DESCRIPTION_AT = 5, 19
CREDIT_END, DEBIT_END, BALANCE_END = 73, 88, 108
GRID = (26, 22, 30)  # widths of the header grid's first three columns
ADDRESS = "House 0, Synthetic Town"
CURRENCY_NAMES = {"PKR": "Pakistan Rupee"}


def _date(day: date) -> str:
    return day.strftime("%d%b %Y")


def _grid(*cells: tuple[str, str]) -> list[str]:
    """A header block: labels on one line, their values on the line below."""
    labels = values = ""
    for (label, value), width in zip(cells, (*GRID, 0), strict=False):
        labels += label.ljust(width)
        values += value.ljust(width)
    return [labels.rstrip(), values.rstrip(), "", ""]


def _amount(minor: int) -> str:
    sign = "-" if minor < 0 else ""
    major, cents = divmod(abs(minor), 100)
    return f"{sign}{major:,}.{cents:02d}"


def _row(left: str, credit: str = "", debit: str = "", balance: str = "") -> str:
    line = left.ljust(DESCRIPTION_AT + DESCRIPTION_WIDTH)
    line += credit.rjust(CREDIT_END - len(line))
    line += debit.rjust(DEBIT_END - len(line))
    return line + balance.rjust(BALANCE_END - len(line))


def iban(number: str) -> str:
    return "PK00SYNM" + "".join(ch for ch in number if ch.isdigit()).rjust(16, "0")


def write_meezan_statement(persona: Persona, out_dir: Path, password: str | None = None) -> Path:
    account = persona.accounts["meezan"]
    rows = [t for t in transactions(persona) if t.account == "meezan"]
    balance = account.opening
    lines = []
    for t in rows:
        balance += t.amount_minor
        first, *rest = textwrap.wrap(t.description, DESCRIPTION_WIDTH)
        credit = _amount(t.amount_minor) if t.amount_minor > 0 else ""
        debit = _amount(-t.amount_minor) if t.amount_minor < 0 else ""
        lines.append(
            _row(
                f"{' ' * DATE_AT}{_date(t.date)}".ljust(DESCRIPTION_AT) + first,
                credit,
                debit,
                _amount(balance),
            )
        )
        lines += [_row(" " * DESCRIPTION_AT + more) for more in rest]
    code = account.currency
    first_page = [
        "SYNTHETIC STATEMENT - NOT A BANK DOCUMENT",
        "",
        *_grid(
            ("Account Title", account.holder),
            ("Account Number", account.number),
            ("IBAN", iban(account.number)),
            ("Scan Code", ""),
        ),
        *_grid(
            ("Currency", f"{CURRENCY_NAMES.get(code, code)}({code})"),
            ("From Date", _date(persona.period_from)),
            ("To Date", _date(persona.period_to)),
        ),
        *_grid(
            ("Opening Balance", f"{code}{_amount(account.opening)}"),
            ("Closing Balance", f"{code}{_amount(balance)}"),
            ("Address", ADDRESS),
        ),
    ]
    header = [
        _row(
            f"{' ' * DATE_AT}Booking Date".ljust(DESCRIPTION_AT) + "Description",
            "Credit",
            "Debit",
            "Available Balance",
        )
    ]
    out_dir.mkdir(parents=True, exist_ok=True)
    path = write_pdf(
        paginate(header, lines, first_page, BALANCE_END),
        out_dir / f"{persona.id}-meezan-statement-synthetic.pdf",
    )
    return encrypt(path, password) if password else path
