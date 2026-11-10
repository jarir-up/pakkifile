"""Money as integer minor units plus an ISO currency code (ADR-0027, R-24)."""

import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

ROUNDING = ROUND_HALF_UP


@dataclass(frozen=True)
class Money:
    amount_minor: int
    currency: str

    def display(self) -> str:
        major = (Decimal(self.amount_minor) / 100).quantize(Decimal("1"), rounding=ROUNDING)
        return f"{self.currency} {major:,}"


_AMOUNT = re.compile(r"-?\d{1,3}(,\d{3})*(\.\d{2})?|-?\d+(\.\d{2})?")


def parse_minor(text: str) -> int:
    """'560,000.00' -> 56000000, exactly. Anything else is an error, never a guess."""
    if not _AMOUNT.fullmatch(text):
        raise ValueError(f"not an amount: {text!r}")
    return int(Decimal(text.replace(",", "")) * 100)


def net_minor(credit_minor: int, debit_minor: int) -> int:
    """A statement row's signed amount: credits positive, debits negative."""
    return credit_minor - debit_minor
