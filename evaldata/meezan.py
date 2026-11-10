"""Synthetic statements in the Meezan Bank layout (ADR-0049).

Layout source: the owner's own statement, 2026-11-10. Header fields: account title, account
number, IBAN, currency, from date, to date, opening balance, closing balance, address.
Columns: Booking Date, Description, Credit, Debit, Available Balance.

Dates are DD/MM/YYYY and amounts carry thousands separators; neither is confirmed against a
real statement yet. Long descriptions wrap onto continuation lines, as bank narrations do.
"""

import textwrap
from datetime import date
from pathlib import Path

from evaldata.pdf import encrypt, paginate, write_pdf
from evaldata.persona import Persona, transactions

DESCRIPTION_WIDTH = 40
# Where each column's text ends, in characters; amounts are right-aligned to these.
CREDIT_END, DEBIT_END, BALANCE_END = 72, 89, 107
DESCRIPTION_AT = 14
ADDRESS = "House 0, Street 0, Synthetic Town, Karachi"


def _date(day: date) -> str:
    return day.strftime("%d/%m/%Y")


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
            _row(f"{_date(t.date):<{DESCRIPTION_AT}}{first}", credit, debit, _amount(balance))
        )
        lines += [_row(" " * DESCRIPTION_AT + more) for more in rest]
    first_page = [
        "SYNTHETIC STATEMENT - NOT A BANK DOCUMENT",
        "",
        f"Account Title     : {account.holder}",
        f"Account Number    : {account.number}",
        f"IBAN              : {iban(account.number)}",
        f"Currency          : {account.currency}",
        f"From Date         : {_date(persona.period_from)}",
        f"To Date           : {_date(persona.period_to)}",
        f"Opening Balance   : {_amount(account.opening)}",
        f"Closing Balance   : {_amount(balance)}",
        f"Address           : {ADDRESS}",
        "",
    ]
    header = [
        _row(
            f"{'Booking Date':<{DESCRIPTION_AT}}Description", "Credit", "Debit", "Available Balance"
        )
    ]
    out_dir.mkdir(parents=True, exist_ok=True)
    path = write_pdf(
        paginate(header, lines, first_page),
        out_dir / f"{persona.id}-meezan-statement-synthetic.pdf",
    )
    return encrypt(path, password) if password else path
