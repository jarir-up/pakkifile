"""Money as integer minor units plus an ISO currency code (ADR-0027, R-24)."""

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
