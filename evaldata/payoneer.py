"""Synthetic statements in the Payoneer PDF layout (ADR-0054).

Layout source: a public sample statement (Scribd document 788425026), as the owner read it on
2026-11-10. Header: company header, address, Primary Account Number, Account Currency,
Period, Issuing Date. Columns: Date, Description, Amount, Status, Running Balance.

Rows (owner, 2026-11-12) run newest first, dated "19 Sep, 2024", the amount carrying its
currency ("-12.00 USD"), a status such as "Completed" on some rows, then the running balance.
Not yet confirmed, so guessed here: "Label: value" header lines, and which rows show a status
(here, money out only).
"""

import textwrap
from datetime import date, timedelta
from pathlib import Path

from evaldata.pdf import ADDRESS, amount_text, encrypt, paginate, write_pdf
from evaldata.persona import Persona, transactions

COMPANY = "SYN PAYMENTS PLATFORM"  # not Payoneer's own header: this file imitates no one
DESCRIPTION_WIDTH = 40
DESCRIPTION_AT = 14
AMOUNT_END, STATUS_AT, BALANCE_END = 70, 74, 104


def _date(day: date) -> str:
    return f"{day.day} {day:%b}, {day.year}"


def _row(left: str, amount: str = "", status: str = "", balance: str = "") -> str:
    line = left.ljust(DESCRIPTION_AT + DESCRIPTION_WIDTH)
    line += amount.rjust(AMOUNT_END - len(line))
    line = line.ljust(STATUS_AT) + status
    return line + balance.rjust(BALANCE_END - len(line))


def write_payoneer_statement(persona: Persona, out_dir: Path, password: str | None = None) -> Path:
    account = persona.accounts["payoneer"]
    rows = [t for t in transactions(persona) if t.account == "payoneer"]
    balance = account.opening
    blocks = []  # one per row, oldest first; printed newest first
    for t in rows:
        balance += t.amount_minor
        first, *rest = textwrap.wrap(t.description, DESCRIPTION_WIDTH)
        left = _date(t.date).ljust(DESCRIPTION_AT) + first
        amount = f"{amount_text(t.amount_minor)} {account.currency}"
        status = "Completed" if t.amount_minor < 0 else ""  # only some rows show one
        blocks.append(
            [
                _row(left, amount, status, amount_text(balance)),
                *(_row(" " * DESCRIPTION_AT + more) for more in rest),
            ]
        )
    lines = [line for block in reversed(blocks) for line in block]
    first_page = [
        COMPANY,
        "",
        account.holder,
        ADDRESS,
        "",
        f"Primary Account Number: {account.number}",
        f"Account Currency: {account.currency}",
        f"Period: {_date(persona.period_from)} - {_date(persona.period_to)}",
        f"Issuing Date: {_date(persona.period_to + timedelta(days=1))}",
        "",
        "SYNTHETIC STATEMENT - NOT A PLATFORM DOCUMENT",  # below the fields: not the holder
        "",
    ]
    header = [
        _row(
            "Date".ljust(DESCRIPTION_AT) + "Description",
            "Amount",
            "Status",
            "Running Balance",
        )
    ]
    out_dir.mkdir(parents=True, exist_ok=True)
    path = write_pdf(
        paginate(header, lines, first_page, BALANCE_END),
        out_dir / f"{persona.id}-payoneer-statement-synthetic.pdf",
    )
    return encrypt(path, password) if password else path
