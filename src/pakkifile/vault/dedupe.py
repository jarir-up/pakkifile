"""Store each transaction once (ADR-0028).

Statements from one account often overlap. A row already stored is a duplicate; a row on the
same day for the same amount but described differently might be one, so it is kept and flagged.
Identical rows inside one statement are separate transactions (two ATM withdrawals in a day).
"""

import hashlib
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class IncomingRow:
    booked: date
    description: str
    amount_minor: int
    row_no: int = 0
    balance_minor: int | None = None


@dataclass(frozen=True)
class StoredRow:
    id: int
    booked: date
    description: str
    amount_minor: int


def _key(row: IncomingRow | StoredRow) -> tuple[date, str, int]:
    return row.booked, " ".join(row.description.upper().split()), row.amount_minor


def fingerprint(account_number: str, row: IncomingRow) -> str:
    """A row's stable key when the statement gives no transaction ID (ADR-0028).

    Includes the row number, so identical rows in one statement keep distinct keys.
    """
    booked, description, amount = _key(row)
    raw = f"{account_number}|{booked.isoformat()}|{description}|{amount}|{row.row_no}"
    return hashlib.sha256(raw.encode()).hexdigest()


def sort_rows(
    incoming: Sequence[IncomingRow], stored: Sequence[StoredRow]
) -> tuple[list[IncomingRow], list[IncomingRow], list[tuple[IncomingRow, int]]]:
    """Split incoming rows into (new, duplicates, possible duplicates with the stored row's id).

    Possible duplicates are also in `new`: they are stored, never dropped.
    """
    unclaimed = Counter(_key(row) for row in stored)
    new, duplicates = [], []
    for row in incoming:
        if unclaimed[_key(row)]:
            unclaimed[_key(row)] -= 1
            duplicates.append(row)
        else:
            new.append(row)
    by_day_amount = {(s.booked, s.amount_minor): s.id for s in stored}
    possible = [
        (row, by_day_amount[(row.booked, row.amount_minor)])
        for row in new
        if (row.booked, row.amount_minor) in by_day_amount
    ]
    return new, duplicates, possible
