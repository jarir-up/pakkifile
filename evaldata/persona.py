"""Synthetic personas: fact tables the owner edits, every generator reads (ADR-0021, ADR-0050).

Each transaction line carries its hand-labelled class, the truth the classifier is scored
against. Amounts are written in major units for editing and held as integer minor units.
"""

from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

PERSONAS = Path("evaldata/personas")

AccountName = Literal["payoneer", "meezan"]
MismatchKind = Literal["M1", "M2", "M3", "M4", "M5", "M6"]
# GLOSSARY "Counterparty" and FR-11; the classifier's classes.
RowClass = Literal[
    "client_payment",  # a counterparty pays the applicant on a platform
    "platform_withdrawal",  # money leaves the platform for the applicant's bank
    "remittance_in",  # a foreign credit reaches the bank, with a PRC
    "sponsor_transfer",
    "cash_deposit",
    "own_transfer",
    "fee",
    "tax",
    "spending",
]


def _minor(value: object) -> int:
    """'1,800.50' -> 180050. Exact: a third decimal place is an error, not rounded."""
    amount = Decimal(str(value).replace(",", "")) * 100
    if amount != amount.to_integral_value():
        raise ValueError(f"{value}: more than two decimal places")
    return int(amount)


Minor = Annotated[int, BeforeValidator(_minor)]


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Account(_Frozen):
    currency: str
    opening: Minor
    holder: str
    number: str


class Line(_Frozen):
    account: AccountName
    description: str
    amount: Minor | None = None
    amounts: tuple[Minor, ...] | None = None  # one per month, when it varies
    day: int | None = None  # monthly lines
    only_months: tuple[int, ...] | None = None  # monthly lines that skip some months
    booked: date | None = None  # one-off lines
    row_class: RowClass = Field(alias="class")
    external_id: str | None = None

    def amount_in(self, month: int) -> int:
        if self.amounts is not None:
            return self.amounts[month]
        assert self.amount is not None
        return self.amount


class Seed(_Frozen):
    kind: MismatchKind
    what: str


class Persona(_Frozen):
    id: str
    label: str
    applicant_profile: str
    target: str
    period_from: date
    months: int
    accounts: dict[AccountName, Account]
    usd_pkr: Decimal
    monthly: tuple[Line, ...]
    once: tuple[Line, ...] = ()
    seeds: tuple[Seed, ...]


class Transaction(_Frozen):
    account: AccountName
    date: date
    description: str
    amount_minor: int
    row_class: RowClass


def transactions(persona: Persona) -> list[Transaction]:
    """Every dated transaction in the persona's period, in booking order."""
    out = [
        Transaction(
            account=line.account,
            date=_month(persona.period_from, month).replace(day=line.day or 1),
            description=line.description,
            amount_minor=line.amount_in(month),
            row_class=line.row_class,
        )
        for line in persona.monthly
        for month in range(persona.months)
        if line.only_months is None or month in line.only_months
    ]
    out += [
        Transaction(
            account=line.account,
            date=line.booked or persona.period_from,
            description=line.description,
            amount_minor=line.amount_in(0),
            row_class=line.row_class,
        )
        for line in persona.once
    ]
    return sorted(out, key=lambda t: (t.account, t.date, -t.amount_minor, t.description))


def _month(start: date, offset: int) -> date:
    index = start.month - 1 + offset
    return date(start.year + index // 12, index % 12 + 1, 1)


def load_personas(root: Path = PERSONAS) -> dict[str, Persona]:
    return {
        p.stem: Persona.model_validate(yaml.safe_load(p.read_text()))
        for p in sorted(root.glob("*.yaml"))
    }
