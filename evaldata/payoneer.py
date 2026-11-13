"""Synthetic statements in the Payoneer PDF layout (ADR-0054).

Layout source: a public sample statement (Scribd document 788425026), as the owner read it on
2026-11-10, and a second sample, 2026-11-13. Header: the holder's name, address and phone on
the left; "Account USD balance", "Period MM/DD/YYYY - MM/DD/YYYY" and "Issuing Date" on the
right. Columns: Date, Description, Amount, Status, Running Balance.

Rows (owner, 2026-11-12) run newest first, dated "19 Sep, 2024", the amount carrying its
currency ("-12.00 USD"), a status such as "Completed" on some rows, then the running balance.
Not yet confirmed, so guessed here: which rows show a status (here, money out only).
"""

import textwrap
from datetime import date, timedelta
from pathlib import Path

from evaldata.pdf import ADDRESS, amount_text, encrypt, paginate, write_pdf
from evaldata.persona import Persona, transactions

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
        f"{account.holder:<48}Account {account.currency} balance",
        f"{ADDRESS:<48}Period {persona.period_from:%m/%d/%Y} - {persona.period_to:%m/%d/%Y}",
        f"{'Synthetic City 00000':<48}Issuing Date {persona.period_to + timedelta(days=1):%m/%d/%Y}",
        "0000000000",
        "",
        "SYNTHETIC STATEMENT - NOT A PLATFORM DOCUMENT",  # below the header: not the holder
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
