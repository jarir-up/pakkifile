"""Synthetic statements in the Meezan Bank layout (ADR-0049).

Layout source: the owner's own statement, 2026-11-10 and 2026-11-11. The header is a grid of
labels with their values on the line below: Account Title, Account Number, IBAN, Scan Code;
Currency (as "Pakistan Rupee(PKR)"), From Date, To Date; Opening Balance, Closing Balance
(as "PKR60,964.71"), Address. Dates read "01Jul 2024". The table header is indented: Booking
Date, Description, Credit, Debit, Available Balance.

Rows (confirmed 2026-11-11) read "02Jul 2024", a credit as "+ PKR248,500.00" and the balance as
"PKR299,464.71". Not yet confirmed: a debit, written here as "- PKR1,000.00".
Long descriptions wrap onto continuation lines, as bank narrations do.
"""

import textwrap
from datetime import date
from pathlib import Path

from evaldata.pdf import ADDRESS, amount_text, encrypt, paginate, write_pdf
from evaldata.persona import Persona, transactions

DESCRIPTION_WIDTH = 32
# Where each column's text starts or ends, in characters; amounts are right-aligned.
DATE_AT, DESCRIPTION_AT = 5, 19
CREDIT_END, DEBIT_END, BALANCE_END = 70, 89, 108
GRID = (26, 22, 30)  # widths of the header grid's first three columns
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


def _money(minor: int, code: str, sign: str = "") -> str:
    """As the statement prints it: "PKR60,964.71", or "+ PKR248,500.00" in a row."""
    return f"{sign} {code}{amount_text(minor)}" if sign else f"{code}{amount_text(minor)}"


def _row(left: str, credit: str = "", debit: str = "", balance: str = "") -> str:
    line = left.ljust(DESCRIPTION_AT + DESCRIPTION_WIDTH)
    line += credit.rjust(CREDIT_END - len(line))
    line += debit.rjust(DEBIT_END - len(line))
    return line + balance.rjust(BALANCE_END - len(line))


def iban(number: str) -> str:
    return "PK00SYNM" + "".join(ch for ch in number if ch.isdigit()).rjust(16, "0")


def write_meezan_statement(
    persona: Persona,
    out_dir: Path,
    password: str | None = None,
    start: date | None = None,
    end: date | None = None,
) -> Path:
    """The statement for the persona's whole period, or for the window `start` to `end`."""
    account = persona.accounts["meezan"]
    start, end = start or persona.period_from, end or persona.period_to
    every = [t for t in transactions(persona) if t.account == "meezan"]
    rows = [t for t in every if start <= t.date <= end]
    opening = account.opening + sum(t.amount_minor for t in every if t.date < start)
    balance = opening
    code = account.currency
    lines = []
    for t in rows:
        balance += t.amount_minor
        first, *rest = textwrap.wrap(t.description, DESCRIPTION_WIDTH)
        credit = _money(t.amount_minor, code, "+") if t.amount_minor > 0 else ""
        debit = _money(-t.amount_minor, code, "-") if t.amount_minor < 0 else ""
        lines.append(
            _row(
                f"{' ' * DATE_AT}{_date(t.date)}".ljust(DESCRIPTION_AT) + first,
                credit,
                debit,
                _money(balance, code),
            )
        )
        lines += [_row(" " * DESCRIPTION_AT + more) for more in rest]
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
            ("From Date", _date(start)),
            ("To Date", _date(end)),
        ),
        *_grid(
            ("Opening Balance", _money(opening, code)),
            ("Closing Balance", _money(balance, code)),
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
