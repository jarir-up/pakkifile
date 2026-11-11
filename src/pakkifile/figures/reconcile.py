"""Check that a statement's own balances add up (FR-13): nothing is stored if they don't."""

from collections.abc import Sequence
from typing import Protocol


class BalanceRow(Protocol):
    @property
    def row_no(self) -> int: ...
    @property
    def credit_minor(self) -> int: ...
    @property
    def debit_minor(self) -> int: ...
    @property
    def balance_minor(self) -> int: ...


def balance_gaps(opening: int, rows: Sequence[BalanceRow], closing: int) -> list[str]:
    """Each place where opening plus credits minus debits disagrees with the stated balance."""
    gaps = []
    expected = opening
    for row in rows:
        expected += row.credit_minor - row.debit_minor
        if row.balance_minor != expected:
            gaps.append(
                f"row {row.row_no}: balance {row.balance_minor}, expected {expected} "
                f"(off by {row.balance_minor - expected})"
            )
            expected = row.balance_minor  # one bad row should not flag every later one
    if closing != expected:
        gaps.append(f"closing balance {closing}, expected {expected} (off by {closing - expected})")
    return gaps
