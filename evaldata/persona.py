"""Synthetic personas: fact tables the owner edits, every generator reads (ADR-0021, ADR-0050).

Each transaction line carries its hand-labelled class, the truth the classifier is scored
against. Amounts are written in major units for editing and held as integer minor units.
"""

from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Annotated, Literal, Self

import yaml
from pydantic import BaseModel, BeforeValidator, ConfigDict, Field, model_validator

PERSONAS = Path("evaldata/personas")

AccountName = Literal["payoneer", "meezan"]
MismatchKind = Literal["M1", "M2", "M3", "M4", "M5", "M6"]
# GLOSSARY "Counterparty" and FR-11; the classifier's classes.
RowClass = Literal[
    "client_payment",  # a counterparty pays the applicant on a platform
    "platform_withdrawal",  # money leaves the platform for the applicant's bank
    "remittance_in",  # a foreign credit reaches the bank
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


class MonthlyLine(_Frozen):
    """A transaction on the same day each month: one amount, or one per month."""

    account: AccountName
    description: str
    row_class: RowClass = Field(alias="class")
    day: int
    amount: Minor | None = None
    amounts: tuple[Minor, ...] | None = None
    only_months: tuple[int, ...] | None = None  # month offsets, when it skips some

    @model_validator(mode="after")
    def _one_amount(self) -> Self:
        if (self.amount is None) == (self.amounts is None):
            raise ValueError(f"{self.description}: give amount or amounts, not both")
        return self

    def amount_in(self, month: int) -> int:
        return self.amounts[month] if self.amounts is not None else self.amount or 0


class OnceLine(_Frozen):
    account: AccountName
    description: str
    row_class: RowClass = Field(alias="class")
    booked: date
    amount: Minor


class Seed(_Frozen):
    kind: MismatchKind
    what: str


class Expected(_Frozen):
    """Figures a correct pipeline must find, worked out from the lines above by hand."""

    closing: dict[AccountName, Minor]
    remittances_in_pkr: Minor
    sponsor_transfers_pkr: Minor
    largest_unattributed_credit_pkr: Minor | None


class Persona(_Frozen):
    id: str
    label: str
    applicant_profile: str
    target: str
    period_from: date
    months: int
    accounts: dict[AccountName, Account]
    usd_pkr: Decimal
    monthly: tuple[MonthlyLine, ...]
    once: tuple[OnceLine, ...] = ()
    seeds: tuple[Seed, ...]
    expected: Expected

    @model_validator(mode="after")
    def _months_fit(self) -> Self:
        for line in self.monthly:
            if line.amounts is not None and len(line.amounts) != self.months:
                raise ValueError(f"{line.description}: needs {self.months} amounts")
        return self

    @property
    def period_to(self) -> date:
        return _month(self.period_from, self.months) - timedelta(days=1)


class Transaction(_Frozen):
    account: AccountName
    date: date
    description: str
    amount_minor: int
    row_class: RowClass


def transactions(persona: Persona) -> list[Transaction]:
    """Every dated transaction in the persona's period, in booking order."""
    dated = [
        (line, _month(persona.period_from, month).replace(day=line.day), line.amount_in(month))
        for line in persona.monthly
        for month in range(persona.months)
        if line.only_months is None or month in line.only_months
    ] + [(line, line.booked, line.amount) for line in persona.once]
    out = [
        Transaction(
            account=line.account,
            date=day,
            description=line.description,
            amount_minor=amount,
            row_class=line.row_class,
        )
        for line, day, amount in dated
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
